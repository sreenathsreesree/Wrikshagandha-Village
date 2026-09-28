extends Interactable
class_name FarmPlot

## A small, persistent, multi-state interactable:
## EMPTY -> SOIL -> PLANTED -> GROWING -> READY -> (harvest) -> SOIL.
##
## Unlike a one-shot discovery, a plot is never freed — it cycles back to
## SOIL after harvest instead of disappearing. Only Interactable's
## proximity/highlight methods (update_proximity, set_highlighted) are
## inherited unchanged; interact() is fully overridden with the farming
## state machine below, and remove_on_harvest is forced to false so
## player.gd keeps tracking this plot across repeated interact() presses
## instead of dropping it after the first one, the way it correctly does
## for a one-shot discovery (see player.gd's _on_interact_requested).
##
## Milestone 1 keeps crop selection out of scope entirely: each plot has
## one deterministic starter crop assigned per-instance in the scene, so
## the whole loop (prepare/plant/water/harvest) can be validated before
## any seed inventory exists.

enum PlotState { EMPTY, SOIL, PLANTED, GROWING, READY }

@export var remove_on_harvest: bool = false
@export var crop_definition: CropDefinition

const SOIL_COLOR_DRY := Color(0.42, 0.32, 0.22, 1.0)
const SOIL_COLOR_WATERED := Color(0.24, 0.17, 0.11, 1.0)
const SOIL_DARKEN_HOLD_SECONDS := 2.5

var plot_state: PlotState = PlotState.EMPTY

var _stage_index: int = 0
var _needs_water: bool = false
var _crop_visual: Node3D
var _soil_material: StandardMaterial3D

## Guards _run_harvest_sequence()'s awaited animation. Unlike a one-shot
## discovery (which player.gd immediately stops tracking after one
## interact() call), a FarmPlot stays in the player's nearby-interactables
## list throughout — see player.gd's remove_on_harvest check — so a rapid
## second Interact press during the harvest animation would otherwise
## re-enter this coroutine and double-award points.
var _is_harvesting: bool = false

@onready var soil_mesh: MeshInstance3D = $SoilMesh
@onready var crop_root: Node3D = $CropRoot
@onready var growth_timer: Timer = $GrowthTimer

func _ready() -> void:
	growth_timer.timeout.connect(_on_growth_timer_timeout)
	_soil_material = soil_mesh.get_surface_override_material(0) as StandardMaterial3D
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator:
		indicator.set_rarity(crop_definition.rarity if crop_definition else "common")

func interact() -> bool:
	match plot_state:
		PlotState.EMPTY:
			_prepare_soil()
		PlotState.SOIL:
			_plant_crop()
		PlotState.PLANTED, PlotState.GROWING:
			if _needs_water:
				_water_crop()
		PlotState.READY:
			_harvest_crop()
	return true

func _prepare_soil() -> void:
	plot_state = PlotState.SOIL
	soil_mesh.visible = true
	soil_mesh.scale = Vector3.ZERO
	var tween := create_tween()
	tween.tween_property(soil_mesh, "scale", Vector3.ONE, 0.3) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	AmbientAudioManager.play_ui_feedback()

func _plant_crop() -> void:
	if crop_definition == null or crop_definition.visual_scene == null:
		return
	plot_state = PlotState.PLANTED
	_stage_index = 0
	_needs_water = true
	_crop_visual = crop_definition.visual_scene.instantiate()
	crop_root.add_child(_crop_visual)
	crop_root.visible = true
	AmbientAudioManager.play_ui_feedback()

## Watering both unlocks progress on the current growth stage and (once
## its duration elapses) advances to the next one. Only reachable from
## interact() while _needs_water is true, so repeatedly pressing Interact
## on an already-watered, still-growing plot is a no-op — it can't be
## watered every frame or spammed to skip ahead.
func _water_crop() -> void:
	_needs_water = false
	plot_state = PlotState.GROWING
	_darken_soil()
	if _crop_visual and _crop_visual.has_method("play_water_response"):
		_crop_visual.call("play_water_response")
	AmbientAudioManager.play_ui_feedback()

	var duration := crop_definition.get_stage_duration(_stage_index)
	if duration <= 0.0:
		_advance_stage()
	else:
		growth_timer.start(duration)

func _on_growth_timer_timeout() -> void:
	_advance_stage()

func _advance_stage() -> void:
	_stage_index += 1
	if _crop_visual and _crop_visual.has_method("set_stage"):
		_crop_visual.call("set_stage", _stage_index)
	if _stage_index >= 3:
		plot_state = PlotState.READY
	else:
		_needs_water = true

func _darken_soil() -> void:
	if _soil_material == null:
		return
	var tween := create_tween()
	tween.tween_property(_soil_material, "albedo_color", SOIL_COLOR_WATERED, 0.3)
	tween.tween_interval(SOIL_DARKEN_HOLD_SECONDS)
	tween.tween_property(_soil_material, "albedo_color", SOIL_COLOR_DRY, 0.8)

func _harvest_crop() -> void:
	if crop_definition == null or _is_harvesting:
		return
	_run_harvest_sequence()

## APPROACH -> interact() -> (this) a small crop-flavored windup -> the
## existing indicator sparkle + harvest particles/sound, exactly like a
## discovery harvest -> points -> the shared notification card -> the
## crop shrinks away and the plot returns to prepared soil, ready to
## plant again. Reuses Interactable's own harvest helpers/consts
## (CATEGORY_WINDUP, RARITY_INTENSITY, _play_collected_burst(),
## _spawn_harvest_particles(), _play_harvest_sound()) instead of a
## parallel harvest-feedback implementation.
func _run_harvest_sequence() -> void:
	_is_harvesting = true
	monitorable = false
	await _play_crop_windup()
	_play_collected_burst()
	_spawn_harvest_particles()
	_play_harvest_sound()

	var points_awarded := crop_definition.points_value
	PointsManager.add_points(points_awarded)
	FarmManager.notify_crop_harvested(crop_definition, points_awarded)

	await _shrink_and_remove_crop_visual()
	_reset_to_soil()
	monitorable = true
	_is_harvesting = false

func _play_crop_windup() -> void:
	if _crop_visual == null:
		return
	var preset: Dictionary = CATEGORY_WINDUP.get(crop_definition.category, DEFAULT_WINDUP)
	var intensity: float = RARITY_INTENSITY.get(crop_definition.rarity, 1.0)
	var preset_scale: Vector3 = preset["scale"]
	var base_scale := _crop_visual.scale
	var windup_scale := base_scale * (Vector3.ONE + (preset_scale - Vector3.ONE) * intensity)
	var tween := create_tween()
	tween.tween_property(_crop_visual, "scale", windup_scale, WINDUP_DURATION) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	await tween.finished

func _shrink_and_remove_crop_visual() -> void:
	if _crop_visual == null:
		return
	var tween := create_tween()
	tween.tween_property(_crop_visual, "scale", Vector3.ZERO, 0.25) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	await tween.finished
	_crop_visual.queue_free()
	_crop_visual = null

func _reset_to_soil() -> void:
	plot_state = PlotState.SOIL
	_stage_index = 0
	_needs_water = false
	crop_root.visible = false
	if _soil_material:
		_soil_material.albedo_color = SOIL_COLOR_DRY
