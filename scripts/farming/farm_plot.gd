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
## Planting is chosen, not fixed: interacting with prepared soil asks
## FarmManager to open the seed picker for this plot, and FarmManager calls
## plant() back with whichever seed the player chose (having checked and
## consumed the seed). While a crop grows, the plot's indicator takes that
## crop's identity color. Plot state is saved via capture()/restore().
##
## The soil remembers: each harvest's crop id is kept (the last
## FarmManager.SOIL_MEMORY of them), and FarmManager rates the next
## planting's soil from that memory. The plot also notes how long its crop
## waited thirsty each time (timestamps only — no polling); at ripening
## FarmManager turns soil + care into the crop's quality, which shows as a
## slightly smaller or larger mature crop and scales its harvest points.

enum PlotState { EMPTY, SOIL, PLANTED, GROWING, READY }

## Stable identity, set per instance in the scene ("farm_plot_01"...). Never
## derived from the node name or tree order. FarmManager tracks plots by it.
@export var plot_id: String = ""
## Expansion-ready: a future plot is just another FarmPlot with a new
## plot_id and unlocked = false, opened later via FarmManager.unlock_plot().
## A locked plot is invisible to interaction and shows nothing.
@export var unlocked: bool = true
## Gradual garden: the FarmManager milestone id that opens this plot while
## it starts locked (e.g. "first_harvest"). Empty = only unlock_plot().
@export var unlock_on_milestone: String = ""
## Optional wild growth standing where the plot will be while it's locked
## (e.g. a few grass clumps and wildflowers under this plot) — it gives
## way when the plot opens, so the new bed is cleared out of the meadow
## rather than appearing from nothing.
@export var overgrowth_path: NodePath

## The crop currently in the ground — set by plant(), cleared on harvest.
var crop_definition: CropDefinition
## The soil rating this crop was planted into, its care rating and final
## quality (FarmManager's 0..2 scales). care and quality are decided when
## it ripens; until then quality reads Good.
var crop_soil: int = 1
var crop_care: int = 2
var crop_quality: int = 1

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
## Crop ids of this plot's past harvests, oldest first.
var _recent_crop_ids: Array[String] = []
## When the current wait for water began (-1 = not thirsty), and the
## longest single wait so far for the crop in the ground.
var _thirsty_since_msec: int = -1
var _longest_thirst_seconds: float = 0.0

## Guards _run_harvest_sequence()'s awaited animation. A FarmPlot stays in
## the player's nearby-interactables list (remove_on_harvest is false), so a
## rapid second tap/interaction during the harvest animation would otherwise
## re-enter this coroutine and double-award points.
var _is_harvesting: bool = false
## Set once a harvest in progress has been reported to FarmManager (seed
## returned, produce in the basket) — from then on a save must see this
## plot as the empty soil it's about to become, or the harvest would count
## twice after a reload.
var _harvest_paid: bool = false

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
	_apply_unlocked()
	FarmManager.register_plot(self)

func set_unlocked(value: bool) -> void:
	var opening := value and not unlocked and is_node_ready()
	unlocked = value
	_apply_unlocked()
	if opening and plot_state == PlotState.EMPTY:
		_play_unlock_reveal()

## A newly opened plot: the worn patch spreads out of the grass with a
## small puff of dust — seen if the player is nearby, harmless if not.
func _play_unlock_reveal() -> void:
	var overgrowth := _get_overgrowth()
	var delay := 0.0
	if overgrowth and overgrowth.visible:
		var clear := create_tween()
		clear.tween_property(overgrowth, "scale", Vector3(0.05, 0.05, 0.05), 0.45) \
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
		clear.tween_callback(overgrowth.hide)
		delay = 0.3
	patch_mesh.scale = Vector3(0.2, 1.0, 0.2)
	var tween := create_tween()
	tween.tween_property(patch_mesh, "scale", Vector3.ONE, 0.6).set_delay(delay) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_spawn_burst(DUST_TINT, 0.45, 0.45, 0.04)

func _get_overgrowth() -> Node3D:
	if overgrowth_path == NodePath():
		return null
	return get_node_or_null(overgrowth_path) as Node3D

## The soil's memory, oldest first — read by FarmManager to rate a planting.
func get_recent_crop_ids() -> Array[String]:
	return _recent_crop_ids.duplicate()

## Locked: not detectable by the player's interaction zone (so it can never
## be targeted) and no worn patch in the grass. Unlocking reveals the patch.
func _apply_unlocked() -> void:
	monitorable = unlocked and not _is_harvesting
	if plot_state == PlotState.EMPTY:
		patch_mesh.visible = unlocked
	var overgrowth := _get_overgrowth()
	if overgrowth and not unlocked:
		overgrowth.visible = true
		overgrowth.scale = Vector3.ONE
	elif overgrowth and not is_node_ready():
		# Opened before it ever showed (e.g. its milestone was already
		# reached when it loaded): no clearing moment, just no overgrowth.
		overgrowth.visible = false

## Leaving range also closes this plot's seed picker if it's the one open,
## so a picker can never outlive the player standing at its plot.
func set_highlighted(active: bool) -> void:
	super(active)
	if not active:
		FarmManager.cancel_seed_choice(self)

## True only for prepared, empty soil — the one state a seed can go into.
func can_plant() -> bool:
	return unlocked and plot_state == PlotState.SOIL and not _is_harvesting

func interact() -> bool:
	if not unlocked:
		return true
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

## The verb interact() would perform in the current state — a read-only
## description, it changes nothing. Preparing an EMPTY plot has no verb yet
## (open question O-10), so it offers none; the short action cooldown isn't
## reflected. Locked or mid-harvest plots are unavailable, so offer nothing.
func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	match plot_state:
		PlotState.SOIL:
			if can_plant():
				verbs.append(Verb.PLANT)
		PlotState.PLANTED, PlotState.GROWING:
			if _needs_water:
				verbs.append(Verb.WATER)
		PlotState.READY:
			if crop_definition != null and not _is_harvesting:
				verbs.append(Verb.HARVEST)
	return verbs

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

## Called by FarmManager with the player's chosen seed and the soil rating
## it gave this plot, after it has verified a seed is available (it
## consumes the seed only if this returns true). A seed in the crop's
## identity color drops into the soil; when it lands, the mound rises with
## a small puff and the seedling emerges.
func plant(crop: CropDefinition, soil: int) -> bool:
	if not can_plant() or crop == null or crop.visual_scene == null:
		return false
	var node := crop.visual_scene.instantiate()
	var visual := node as CropVisual
	if visual == null:
		push_warning("FarmPlot: visual_scene for '%s' has no CropVisual script" % crop.crop_id)
		node.free()
		return false

	crop_definition = crop
	crop_soil = soil
	crop_care = FarmManager.CARE_CAREFUL
	crop_quality = FarmManager.QUALITY_GOOD
	_longest_thirst_seconds = 0.0
	plot_state = PlotState.PLANTED
	_stage_index = 0
	_needs_water = true
	_start_thirst()
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
	_end_thirst()
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
		_start_thirst()
		_tween_soil_color(SOIL_COLOR_DRY, 1.2)
		if _crop_visual:
			_crop_visual.set_thirsty(true)

func _start_thirst() -> void:
	_thirsty_since_msec = Time.get_ticks_msec()

func _end_thirst() -> void:
	if _thirsty_since_msec < 0:
		return
	var waited := (Time.get_ticks_msec() - _thirsty_since_msec) / 1000.0
	_longest_thirst_seconds = maxf(_longest_thirst_seconds, waited)
	_thirsty_since_msec = -1

## Ripening: a few soft motes in the crop's own color drift up once, and
## FarmManager hears about it (the garden's "something is ready" state).
func _become_ready() -> void:
	plot_state = PlotState.READY
	_needs_water = false
	_tween_soil_color(SOIL_COLOR_DRY, 1.2)
	if crop_definition:
		crop_care = FarmManager.rate_care(crop_definition, _longest_thirst_seconds)
		crop_quality = FarmManager.combine_quality(crop_soil, crop_care)
		if _crop_visual:
			_crop_visual.set_size_factor(FarmManager.get_quality_size(crop_quality))
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
	_harvest_paid = false
	monitorable = false
	var intensity: float = RARITY_INTENSITY.get(crop_definition.rarity, 1.0)
	if _crop_visual:
		await _crop_visual.play_harvest(crop_definition.harvest_style, intensity)
	_spawn_burst(crop_definition.identity_color, 0.35, 0.6, 0.25)
	_play_harvest_sound()

	var points_awarded := FarmManager.get_harvest_points(crop_definition, crop_quality)
	PointsManager.add_points(points_awarded)
	_remember_harvest(crop_definition.crop_id)
	_harvest_paid = true
	FarmManager.notify_crop_harvested(plot_id, crop_definition, points_awarded, crop_quality, crop_care)

	_play_seed_return(crop_definition.identity_color)
	if _crop_visual:
		await _crop_visual.play_remove(crop_definition.harvest_style)
		_crop_visual.queue_free()
		_crop_visual = null
	_reset_to_soil()
	_is_harvesting = false
	_harvest_paid = false
	monitorable = unlocked

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

func _remember_harvest(crop_id: String) -> void:
	_recent_crop_ids.append(crop_id)
	while _recent_crop_ids.size() > FarmManager.SOIL_MEMORY:
		_recent_crop_ids.remove_at(0)

func _reset_to_soil() -> void:
	plot_state = PlotState.SOIL
	crop_definition = null
	_stage_index = 0
	_needs_water = false
	_thirsty_since_msec = -1
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

# --- Persistence (called by FarmManager only) --------------------------------

## This plot's saveable state (see docs/farming_persistence_plan.md). Times
## are stored as durations, never as session clock values. Unlocked-ness
## is not saved — FarmManager derives it from milestones.
func capture() -> Dictionary:
	var state := String(PlotState.keys()[plot_state])
	var crop_id := crop_definition.crop_id if crop_definition else ""
	if _is_harvesting and _harvest_paid:
		# Already paid out; it's soil in every way that matters.
		state = "SOIL"
		crop_id = ""
	var data := {"state": state, "soil_memory": Array(_recent_crop_ids)}
	if crop_id == "":
		return data
	var thirsty_for := -1.0
	if _thirsty_since_msec >= 0:
		thirsty_for = (Time.get_ticks_msec() - _thirsty_since_msec) / 1000.0
	data.merge({
		"crop": crop_id,
		"stage": _stage_index,
		"needs_water": _needs_water,
		"stage_time_left": growth_timer.time_left if not growth_timer.is_stopped() else 0.0,
		"soil": crop_soil,
		"care": crop_care,
		"quality": crop_quality,
		"longest_thirst": _longest_thirst_seconds,
		"thirsty_for": thirsty_for,
	})
	return data

## Puts a saved state back without any planting/growth animation. Returns
## the crop now in the ground (null if none). A crop id with no matching
## CropDefinition (removed from data) leaves the plot as prepared soil.
func restore(data: Dictionary, crop: CropDefinition) -> CropDefinition:
	if is_instance_valid(_crop_visual):
		# Restored in place (a parked area coming back, M08.1): the visual
		# it already shows is replaced, never doubled.
		crop_root.remove_child(_crop_visual)
		_crop_visual.queue_free()
	_crop_visual = null
	_recent_crop_ids.clear()
	for crop_id: Variant in data.get("soil_memory", []):
		_recent_crop_ids.append(String(crop_id))
	while _recent_crop_ids.size() > FarmManager.SOIL_MEMORY:
		_recent_crop_ids.remove_at(0)
	var state_name := String(data.get("state", "EMPTY"))
	# Enum values are 0..n in declaration order, so the key's index is it.
	var restored_state := PlotState.keys().find(state_name)
	if restored_state <= PlotState.EMPTY:
		return null
	_show_soil()
	if restored_state == PlotState.SOIL or crop == null or crop.visual_scene == null:
		plot_state = PlotState.SOIL
		return null
	var visual := crop.visual_scene.instantiate() as CropVisual
	if visual == null:
		plot_state = PlotState.SOIL
		return null
	crop_definition = crop
	plot_state = restored_state as PlotState
	_stage_index = clampi(int(data.get("stage", 0)), 0, CropVisual.MATURE_STAGE)
	_needs_water = bool(data.get("needs_water", false)) and plot_state != PlotState.READY
	crop_soil = clampi(int(data.get("soil", FarmManager.QUALITY_GOOD)), 0, 2)
	crop_care = clampi(int(data.get("care", FarmManager.CARE_CAREFUL)), 0, 2)
	crop_quality = clampi(int(data.get("quality", FarmManager.QUALITY_GOOD)), 0, 2)
	_longest_thirst_seconds = maxf(float(data.get("longest_thirst", 0.0)), 0.0)
	var thirsty_for := float(data.get("thirsty_for", -1.0))
	_thirsty_since_msec = -1
	if _needs_water:
		# Time away from the app doesn't count as thirst: resume the wait
		# where it was when the game was saved.
		_thirsty_since_msec = Time.get_ticks_msec() - int(maxf(thirsty_for, 0.0) * 1000.0)

	_crop_visual = visual
	_crop_visual.configure(crop)
	crop_root.add_child(_crop_visual)
	crop_root.visible = true
	if plot_state == PlotState.READY:
		_crop_visual.set_size_factor(FarmManager.get_quality_size(crop_quality))
	_crop_visual.snap_to(_stage_index, _needs_water)
	seed_mound.visible = true
	seed_mound.scale = Vector3.ONE
	if _soil_material:
		_soil_material.albedo_color = SOIL_COLOR_DRY if _needs_water or plot_state == PlotState.READY else SOIL_COLOR_WET
	var indicator := _get_indicator()
	if indicator:
		indicator.set_tint(crop.identity_color)
	if plot_state == PlotState.GROWING and not _needs_water:
		growth_timer.start(maxf(float(data.get("stage_time_left", 0.0)), 0.1))
	return crop

func _show_soil() -> void:
	plot_state = PlotState.SOIL
	patch_mesh.visible = false
	soil_mesh.visible = true
	soil_mesh.scale = Vector3.ONE
	if _soil_material:
		_soil_material.albedo_color = SOIL_COLOR_DRY
	var overgrowth := _get_overgrowth()
	if overgrowth:
		overgrowth.visible = false

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
