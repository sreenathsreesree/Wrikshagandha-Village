extends Node3D
class_name CropVisual

## Generic presentation shared by every crop scene (Wild Carrot, Meadow
## Herb, Golden Sunflower, and any future crop). Only the mesh/material
## differ per crop scene; adding a new crop later means a new .tscn + .tres
## pair, not new presentation logic.
##
## The node's transform is composed from four independent channels, each a
## plain property with a setter:
##   stage_scale — persistent growth size (only growth/removal touch it)
##   squash      — transient squash/stretch, always settles back to ONE
##   lift        — transient vertical offset, always settles back to 0
##   sway        — rotation about the base (growing/ready idle, harvest sway)
## Every tween drives exactly one channel, so a watering bounce can never
## overwrite a growth-stage tween the way two tweens both writing `scale`
## would (the last one to finish won, which could leave a sprouted crop
## stuck at seed size). No _process anywhere — all motion is Tween-driven.

const STAGE_SCALES := [0.28, 0.55, 0.8, 1.0]
const MATURE_STAGE := 3
const MIN_SCALE := 0.001
const SEED_SINK := -0.05
## Idle life by stage: a seed is still; a growing crop barely stirs; a ready
## crop sways a little more and gently rises and settles — the most
## noticeable thing on the plot, but still calm.
const GROWING_SWAY := 0.02
const GROWING_SWAY_PERIOD := 2.2
const READY_SWAY := 0.06
const READY_SWAY_PERIOD := 1.4
const READY_BOB := 0.012
const READY_LIGHTEN := 0.18

var stage_scale: float = 0.0:
	set(value):
		stage_scale = value
		_apply()
var squash: Vector3 = Vector3.ONE:
	set(value):
		squash = value
		_apply()
var lift: float = 0.0:
	set(value):
		lift = value
		_apply()
var sway: float = 0.0:
	set(value):
		sway = value
		_apply()

var _materials: Array[StandardMaterial3D] = []
var _base_albedo: Array[Color] = []
var _stage_tween: Tween
var _motion_tween: Tween
var _idle_tween: Tween

func _ready() -> void:
	_make_materials_unique()
	_apply()

## Planting: the seedling starts slightly sunk and flattened, then rises
## and un-squashes out of the soil — a tiny upward emergence cue.
func appear() -> void:
	_stop_all_tweens()
	stage_scale = 0.0
	lift = SEED_SINK
	squash = Vector3(1.3, 0.6, 1.3)
	_stage_tween = create_tween()
	_stage_tween.tween_property(self, "stage_scale", STAGE_SCALES[0], 0.3) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_motion_tween = create_tween().set_parallel(true)
	_motion_tween.tween_property(self, "lift", 0.0, 0.45).set_delay(0.12) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_motion_tween.tween_property(self, "squash", Vector3.ONE, 0.45).set_delay(0.12) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

## Growth: a smooth scale-in rather than a size swap, stretching slightly
## upward as it grows, then a small squash and settle. Reaching maturity
## also ripens the colors and starts a gentle idle sway — the ready crop is
## the one thing on the plot that's both biggest and moving.
func set_stage(stage_index: int) -> void:
	var clamped: int = clampi(stage_index, 0, MATURE_STAGE)
	_stop_all_tweens()
	_stage_tween = create_tween()
	_stage_tween.tween_property(self, "stage_scale", STAGE_SCALES[clamped], 0.55) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)

	_motion_tween = create_tween()
	_motion_tween.tween_property(self, "squash", Vector3(0.9, 1.15, 0.9), 0.25) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_motion_tween.parallel().tween_property(self, "lift", 0.02, 0.25) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_motion_tween.tween_property(self, "squash", Vector3(1.06, 0.94, 1.06), 0.15).set_trans(Tween.TRANS_SINE)
	_motion_tween.parallel().tween_property(self, "lift", 0.0, 0.15).set_trans(Tween.TRANS_SINE)
	_motion_tween.tween_property(self, "squash", Vector3.ONE, 0.2).set_trans(Tween.TRANS_SINE)

	if clamped == MATURE_STAGE:
		_ripen_colors()
		_motion_tween.tween_callback(_start_idle.bind(READY_SWAY, READY_SWAY_PERIOD, READY_BOB))
	elif clamped > 0:
		_motion_tween.tween_callback(_start_idle.bind(GROWING_SWAY, GROWING_SWAY_PERIOD, 0.0))

## A gentle bounce when watered. Touches only the transient channels, and
## always returns them to neutral.
func play_water_response() -> void:
	if _motion_tween and _motion_tween.is_valid():
		_motion_tween.kill()
	_motion_tween = create_tween()
	_motion_tween.tween_property(self, "squash", Vector3(1.1, 0.88, 1.1), 0.12).set_trans(Tween.TRANS_SINE)
	_motion_tween.parallel().tween_property(self, "lift", 0.0, 0.12)
	_motion_tween.tween_property(self, "squash", Vector3(0.96, 1.06, 0.96), 0.14).set_trans(Tween.TRANS_SINE)
	_motion_tween.tween_property(self, "squash", Vector3.ONE, 0.18).set_trans(Tween.TRANS_SINE)

## The crop's small harvest personality (CropDefinition.harvest_style),
## scaled by rarity intensity. Uses a local tween nothing else can kill, so
## awaiting it can never hang the caller.
func play_harvest(style: String, intensity: float) -> void:
	_stop_all_tweens()
	var tween := create_tween()
	match style:
		"sway":
			tween.tween_property(self, "sway", 0.22 * intensity, 0.1).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "sway", -0.18 * intensity, 0.14).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "sway", 0.0, 0.1).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "lift", 0.08 * intensity, 0.14) \
				.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		"bloom":
			tween.tween_property(self, "squash", Vector3.ONE * (1.0 + 0.2 * intensity), 0.12) \
				.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
			tween.tween_property(self, "squash", Vector3.ONE * 0.95, 0.1).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "squash", Vector3.ONE * (1.0 + 0.12 * intensity), 0.1).set_trans(Tween.TRANS_SINE)
		_:
			tween.tween_property(self, "squash", Vector3(1.12, 0.82, 1.12), 0.08).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "lift", 0.16 * intensity, 0.12) \
				.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			tween.parallel().tween_property(self, "squash", Vector3(0.88, 1.2, 0.88), 0.12).set_trans(Tween.TRANS_SINE)
	await tween.finished

## Shrink away after harvest. Same local-tween rule as play_harvest().
func play_remove() -> void:
	_stop_all_tweens()
	var tween := create_tween()
	tween.tween_property(self, "stage_scale", 0.0, 0.22).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	await tween.finished

func _apply() -> void:
	scale = squash * maxf(stage_scale, MIN_SCALE)
	position.y = lift
	rotation.z = sway

## One looping tween per crop. Uses only sway (and lift, when bobbing) —
## watering touches squash/lift but can't happen once a crop is ready, and
## a growing crop's idle never uses lift, so the channels never collide.
func _start_idle(amplitude: float, period: float, bob: float) -> void:
	if _idle_tween and _idle_tween.is_valid():
		_idle_tween.kill()
	_idle_tween = create_tween().set_loops()
	_idle_tween.tween_property(self, "sway", amplitude, period) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if bob > 0.0:
		_idle_tween.parallel().tween_property(self, "lift", bob, period) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_idle_tween.tween_property(self, "sway", -amplitude, period) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if bob > 0.0:
		_idle_tween.parallel().tween_property(self, "lift", 0.0, period) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

## Ready crops read slightly lighter/riper — a value change, not a glow.
func _ripen_colors() -> void:
	for i in _materials.size():
		var tween := create_tween()
		tween.tween_property(_materials[i], "albedo_color", _base_albedo[i].lightened(READY_LIGHTEN), 0.6)

func _stop_all_tweens() -> void:
	for tween: Tween in [_stage_tween, _motion_tween, _idle_tween]:
		if tween and tween.is_valid():
			tween.kill()
	_stage_tween = null
	_motion_tween = null
	_idle_tween = null

## Scene sub-resource materials are shared across every instance of this
## crop scene; ripening edits albedo, so each instance needs its own copy
## (one per distinct source material, not one per mesh).
func _make_materials_unique() -> void:
	var copies := {}
	for child in get_children():
		var mesh_instance := child as MeshInstance3D
		if mesh_instance == null:
			continue
		var source := mesh_instance.get_surface_override_material(0) as StandardMaterial3D
		if source == null:
			continue
		if not copies.has(source):
			var copy := source.duplicate() as StandardMaterial3D
			copies[source] = copy
			_materials.append(copy)
			_base_albedo.append(copy.albedo_color)
		mesh_instance.set_surface_override_material(0, copies[source])
