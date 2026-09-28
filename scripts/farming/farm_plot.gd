extends Interactable
class_name FarmPlot

## A small, persistent, multi-state interactable:
## EMPTY -> SOIL -> PLANTED -> GROWING -> READY -> (harvest) -> SOIL.
##
## Unlike a one-shot discovery, a plot is never freed — it cycles back to
## SOIL after harvest. Only Interactable's proximity/highlight behavior and
## harvest helpers are inherited; interact() is fully overridden with the
## farming state machine below.
##
## Readable at a glance, without any UI:
##   EMPTY   — a faintly worn patch in the grass
##   SOIL    — a small tilled mound of dry soil
##   PLANTED — a seed mound with a tiny seedling; dry soil = needs water
##   GROWING — dark, wet soil while the current stage grows; the soil
##             dries back out when the crop needs water again
##   READY   — the crop at full size, riper color, swaying gently
##
## Planting is chosen, not fixed: pressing Interact on prepared soil asks
## FarmManager to open the seed picker for this plot, and FarmManager calls
## plant() back with whichever seed the player chose (having checked and
## consumed the seed). While a crop grows, the plot's indicator takes that
## crop's identity color. Plot state is session-only (never saved).

enum PlotState { EMPTY, SOIL, PLANTED, GROWING, READY }

## The crop currently in the ground — set by plant(), cleared on harvest.
var crop_definition: CropDefinition

const SOIL_COLOR_FRESH := Color(0.5, 0.4, 0.27, 1.0)
const SOIL_COLOR_DRY := Color(0.42, 0.32, 0.22, 1.0)
const SOIL_COLOR_WET := Color(0.24, 0.17, 0.11, 1.0)
const DUST_TINT := Color(0.52, 0.42, 0.3, 1.0)
const WATER_TINT := Color(0.62, 0.8, 0.95, 1.0)
const MOUND_HIDDEN_SCALE := Vector3(0.4, 0.1, 0.4)
const SEED_DROP_HEIGHT := 0.42
const SEED_REST_HEIGHT := 0.07
const SEED_DROP_SECONDS := 0.22
## Watering soaks in over time rather than snapping dark.
const SOIL_ABSORB_SECONDS := 1.3

## Minimum gap between two farming actions on the same plot, so a double-tap
## can't water twice or skip past an animation before it reads.
const ACTION_COOLDOWN_MSEC := 450

var plot_state: PlotState = PlotState.EMPTY

var _stage_index: int = 0
var _needs_water: bool = false
var _crop_visual: CropVisual
var _soil_material: StandardMaterial3D
var _soil_tween: Tween
var _mound_tween: Tween
var _seed_tween: Tween
var _ripple_tween: Tween
var _seed_material: StandardMaterial3D
var _ripple_material: StandardMaterial3D
var _last_action_msec: int = -ACTION_COOLDOWN_MSEC

## Guards _run_harvest_sequence()'s awaited animation. A FarmPlot stays in
## the player's nearby-interactables list (remove_on_harvest is false), so a
## rapid second Interact press during the harvest animation would otherwise
## re-enter this coroutine and double-award points.
var _is_harvesting: bool = false

## The plot's own quiet green, restored when the soil is empty again.
var _default_indicator_tint: Color = Color(0, 0, 0, 0)

@onready var patch_mesh: MeshInstance3D = $PatchMesh
@onready var soil_mesh: MeshInstance3D = $SoilMesh
@onready var seed_mound: MeshInstance3D = $SeedMound
@onready var seed_mesh: MeshInstance3D = $Seed
@onready var ripple_mesh: MeshInstance3D = $Ripple
@onready var crop_root: Node3D = $CropRoot
@onready var growth_timer: Timer = $GrowthTimer

func _ready() -> void:
	# A plot is persistent, never consumed: player.gd must keep tracking it
	# across repeated presses instead of dropping it after the first one.
	# (Set here rather than redeclared — GDScript doesn't allow a subclass
	# to redefine a parent's member variable.)
	remove_on_harvest = false
	growth_timer.timeout.connect(_on_growth_timer_timeout)
	_make_soil_material_unique()
	_seed_material = _make_unique_material(seed_mesh)
	_ripple_material = _make_unique_material(ripple_mesh)
	var indicator := _get_indicator()
	if indicator:
		_default_indicator_tint = indicator.tint

## Leaving range also closes this plot's seed picker if it's the one open,
## so a picker can never outlive the player standing at its plot.
func set_highlighted(active: bool) -> void:
	super(active)
	if not active:
		FarmManager.cancel_seed_choice(self)

## True only for prepared, empty soil — the one state a seed can go into.
func can_plant() -> bool:
	return plot_state == PlotState.SOIL and not _is_harvesting

func interact() -> bool:
	var now := Time.get_ticks_msec()
	if now - _last_action_msec < ACTION_COOLDOWN_MSEC:
		return true
	var acted := false
	match plot_state:
		PlotState.EMPTY:
			_prepare_soil()
			acted = true
		PlotState.SOIL:
			FarmManager.request_seed_choice(self)
			_pulse_indicator(0.3)
			acted = true
		PlotState.PLANTED, PlotState.GROWING:
			if _needs_water:
				_water_crop()
				acted = true
		PlotState.READY:
			acted = _harvest_crop()
	if acted:
		_last_action_msec = now
	return true

## Worn grass gives way to a freshly turned mound that settles into dry
## soil, with a small puff of soil dust.
func _prepare_soil() -> void:
	plot_state = PlotState.SOIL
	patch_mesh.visible = false
	soil_mesh.visible = true
	soil_mesh.scale = Vector3(1.15, 0.2, 1.15)
	var tween := create_tween()
	tween.tween_property(soil_mesh, "scale", Vector3.ONE, 0.35) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	if _soil_material:
		_soil_material.albedo_color = SOIL_COLOR_FRESH
	_tween_soil_color(SOIL_COLOR_DRY, 0.9)
	_spawn_burst(DUST_TINT, 0.4, 0.5, 0.04)
	get_tree().create_timer(0.14).timeout.connect(_spawn_burst.bind(DUST_TINT, 0.26, 0.35, 0.05))
	_pulse_indicator(0.25)
	AmbientAudioManager.play_soil_sound()

## Called by FarmManager with the player's chosen seed, after it has
## verified a seed is available (it consumes the seed only if this returns
## true). A seed in the crop's identity color drops into the soil; when it
## lands, the mound rises with a small puff and the seedling emerges.
func plant(crop: CropDefinition) -> bool:
	if not can_plant() or crop == null or crop.visual_scene == null:
		return false
	var node := crop.visual_scene.instantiate()
	var visual := node as CropVisual
	if visual == null:
		push_warning("FarmPlot: visual_scene for '%s' has no CropVisual script" % crop.crop_id)
		node.free()
		return false

	crop_definition = crop
	plot_state = PlotState.PLANTED
	_stage_index = 0
	_needs_water = true
	# Planting comes from a seed-picker tap, not interact(), so start the
	# action cooldown here too: an immediate Interact can't water before the
	# seed has landed and the seedling has appeared (the drop is shorter
	# than the cooldown).
	_last_action_msec = Time.get_ticks_msec()
	_crop_visual = visual
	_crop_visual.configure(crop)
	crop_root.add_child(_crop_visual)
	crop_root.visible = true

	var indicator := _get_indicator()
	if indicator:
		indicator.set_tint(crop.identity_color)
	_pulse_indicator(0.3)
	AmbientAudioManager.play_soil_sound()

	_play_seed_drop(crop.identity_color)
	return true

func _play_seed_drop(color: Color) -> void:
	if _seed_material:
		_seed_material.albedo_color = color
	_kill_tween(_seed_tween)
	seed_mesh.visible = true
	seed_mesh.position.y = SEED_DROP_HEIGHT
	seed_mesh.scale = Vector3.ONE
	_seed_tween = create_tween()
	_seed_tween.tween_property(seed_mesh, "position:y", SEED_REST_HEIGHT, SEED_DROP_SECONDS) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	_seed_tween.tween_callback(_on_seed_landed)
	_seed_tween.tween_property(seed_mesh, "scale", Vector3.ZERO, 0.08)
	_seed_tween.tween_callback(seed_mesh.hide)

## The seed has gone into the soil: the mound rises around it and the
## seedling emerges. Guarded so a harvest/reset that raced the drop can't
## resurrect a seedling on empty soil.
func _on_seed_landed() -> void:
	if plot_state != PlotState.PLANTED or _crop_visual == null or _stage_index != 0:
		return
	_kill_tween(_mound_tween)
	seed_mound.visible = true
	seed_mound.scale = MOUND_HIDDEN_SCALE
	_mound_tween = create_tween()
	_mound_tween.tween_property(seed_mound, "scale", Vector3.ONE, 0.3) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_spawn_burst(DUST_TINT, 0.22, 0.4, 0.06)
	_crop_visual.appear()
	_crop_visual.set_thirsty(true)

## Watering: droplets fall, a faint ring spreads as the water soaks in,
## the soil darkens gradually (and stays dark while this stage grows), and
## the crop straightens up out of its thirsty droop with a small bounce.
## Only reachable from interact() while _needs_water is true, so an
## already-watered, still-growing plot ignores further presses.
func _water_crop() -> void:
	_needs_water = false
	plot_state = PlotState.GROWING
	_tween_soil_color(SOIL_COLOR_WET, SOIL_ABSORB_SECONDS)
	_spawn_burst(WATER_TINT, 0.28, -0.9, 0.5)
	_play_ripple()
	_pulse_indicator(0.2)
	if _crop_visual:
		_crop_visual.set_thirsty(false)
		_crop_visual.play_water_response()
	AmbientAudioManager.play_water_sound()
	_start_current_stage()

func _play_ripple() -> void:
	if _ripple_material == null:
		return
	_kill_tween(_ripple_tween)
	ripple_mesh.visible = true
	ripple_mesh.scale = Vector3(0.35, 0.3, 0.35)
	_ripple_material.albedo_color.a = 0.55
	_ripple_tween = create_tween().set_parallel(true)
	_ripple_tween.tween_property(ripple_mesh, "scale", Vector3(1.05, 0.3, 1.05), 0.7) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_ripple_tween.tween_property(_ripple_material, "albedo_color:a", 0.0, 0.7) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	_ripple_tween.chain().tween_callback(ripple_mesh.hide)

## Stages with no duration (seed, by default: "Seed: immediate") pass
## straight through on the same watering, so one watering both sprouts the
## seed and starts the sprout timer — the player never has to water twice
## in a row with nothing visible in between.
func _start_current_stage() -> void:
	while _stage_index < CropVisual.MATURE_STAGE and crop_definition.get_stage_duration(_stage_index) <= 0.0:
		_stage_index += 1
		if _crop_visual:
			_crop_visual.set_stage(_stage_index)
	if _stage_index >= CropVisual.MATURE_STAGE:
		_become_ready()
	else:
		growth_timer.start(crop_definition.get_stage_duration(_stage_index))

func _on_growth_timer_timeout() -> void:
	if plot_state != PlotState.GROWING:
		return
	_stage_index += 1
	if _crop_visual:
		_crop_visual.set_stage(_stage_index)
	if _stage_index >= CropVisual.MATURE_STAGE:
		_become_ready()
	else:
		_needs_water = true
		_tween_soil_color(SOIL_COLOR_DRY, 1.2)
		if _crop_visual:
			_crop_visual.set_thirsty(true)

## Ripening: a few soft motes in the crop's own color drift up once, and
## FarmManager hears about it (the garden's "something is ready" state).
func _become_ready() -> void:
	plot_state = PlotState.READY
	_needs_water = false
	_tween_soil_color(SOIL_COLOR_DRY, 1.2)
	if crop_definition:
		_spawn_burst(crop_definition.identity_color, 0.16, 1.4, 0.25)
		FarmManager.notify_crop_ready(crop_definition)

func _harvest_crop() -> bool:
	if crop_definition == null or _is_harvesting:
		return false
	_run_harvest_sequence()
	return true

## interact() -> the crop's own harvest personality (data-driven via
## CropDefinition.harvest_style, scaled by the same RARITY_INTENSITY table
## discoveries use) -> the shared HarvestBurst in the crop's own color (a
## soft puff, not a golden loot sparkle) + harvest sound -> points -> the
## shared notification card (via FarmManager) -> the crop leaves the ground
## in its style while its seed pops back up out of the soil -> the plot
## returns to prepared soil, ready to plant again.
func _run_harvest_sequence() -> void:
	_is_harvesting = true
	monitorable = false
	var intensity: float = RARITY_INTENSITY.get(crop_definition.rarity, 1.0)
	if _crop_visual:
		await _crop_visual.play_harvest(crop_definition.harvest_style, intensity)
	_spawn_burst(crop_definition.identity_color, 0.35, 0.6, 0.25)
	_play_harvest_sound()

	var points_awarded := crop_definition.points_value
	PointsManager.add_points(points_awarded)
	FarmManager.notify_crop_harvested(crop_definition, points_awarded)

	_play_seed_return(crop_definition.identity_color)
	if _crop_visual:
		await _crop_visual.play_remove(crop_definition.harvest_style)
		_crop_visual.queue_free()
		_crop_visual = null
	_reset_to_soil()
	monitorable = true
	_is_harvesting = false

## The seed that comes back with every harvest, shown in the world: it
## pops up out of the soil in the crop's color and is gone.
func _play_seed_return(color: Color) -> void:
	if _seed_material:
		_seed_material.albedo_color = color
	_kill_tween(_seed_tween)
	seed_mesh.visible = true
	seed_mesh.position.y = SEED_REST_HEIGHT
	seed_mesh.scale = Vector3.ONE * 0.6
	_seed_tween = create_tween()
	_seed_tween.tween_property(seed_mesh, "position:y", SEED_DROP_HEIGHT + 0.1, 0.3) \
		.set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	_seed_tween.parallel().tween_property(seed_mesh, "scale", Vector3.ONE * 1.2, 0.3)
	_seed_tween.tween_property(seed_mesh, "scale", Vector3.ZERO, 0.15)
	_seed_tween.tween_callback(seed_mesh.hide)

func _reset_to_soil() -> void:
	plot_state = PlotState.SOIL
	crop_definition = null
	_stage_index = 0
	_needs_water = false
	var indicator := _get_indicator()
	if indicator:
		indicator.set_tint(_default_indicator_tint)
	growth_timer.stop()
	crop_root.visible = false
	_kill_tween(_mound_tween)
	_mound_tween = create_tween()
	_mound_tween.tween_property(seed_mound, "scale", MOUND_HIDDEN_SCALE, 0.2)
	_mound_tween.tween_callback(seed_mound.hide)
	_tween_soil_color(SOIL_COLOR_DRY, 0.4)

## Reuses the discovery harvest's own tiny tween-driven burst scene, tinted
## for soil dust / water droplets (alpha-0 tint = its original gold).
func _spawn_burst(tint: Color, radius: float, vertical: float, start_height: float) -> void:
	var burst := HarvestBurstScene.instantiate() as HarvestBurst
	if burst == null:
		return
	burst.tint = tint
	burst.burst_radius = radius
	burst.vertical = vertical
	burst.start_height = start_height
	add_child(burst)

func _tween_soil_color(color: Color, duration: float) -> void:
	if _soil_material == null:
		return
	_kill_tween(_soil_tween)
	_soil_tween = create_tween()
	_soil_tween.tween_property(_soil_material, "albedo_color", color, duration)

func _pulse_indicator(amount: float) -> void:
	var indicator := _get_indicator()
	if indicator:
		indicator.pulse(amount)

func _get_indicator() -> DiscoveryIndicator:
	return get_node_or_null("Indicator") as DiscoveryIndicator

func _kill_tween(tween: Tween) -> void:
	if tween and tween.is_valid():
		tween.kill()

## The soil material is a scene sub-resource shared by every FarmPlot
## instance; without a per-plot copy, watering one plot darkened the soil of
## every plot on the farm. The seed mound shares this plot's copy so it
## wets and dries together with the soil around it.
func _make_unique_material(mesh: MeshInstance3D) -> StandardMaterial3D:
	var source := mesh.get_surface_override_material(0) as StandardMaterial3D
	if source == null:
		return null
	var copy := source.duplicate() as StandardMaterial3D
	mesh.set_surface_override_material(0, copy)
	return copy

func _make_soil_material_unique() -> void:
	var source := soil_mesh.get_surface_override_material(0) as StandardMaterial3D
	if source == null:
		return
	_soil_material = source.duplicate() as StandardMaterial3D
	soil_mesh.set_surface_override_material(0, _soil_material)
	seed_mound.set_surface_override_material(0, _soil_material)
