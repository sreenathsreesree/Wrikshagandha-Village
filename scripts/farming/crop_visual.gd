extends Node3D
class_name CropVisual

## Generic presentation shared by every crop scene (Wild Carrot, Meadow
## Herb, Golden Sunflower, and any future crop). Only the mesh/material
## differ per crop scene, and every behavioral difference — silhouette,
## how much it moves, whether it "breathes" when ready, how it leaves the
## ground at harvest — comes from its CropDefinition via configure(). No
## crop-specific code lives here or in FarmPlot.
##
## The node's transform is composed from independent channels, each a
## plain property with a setter:
##   stage_scale — persistent growth size (only growth/removal touch it)
##   droop       — persistent "thirsty" lean + slight sag (0..1)
##   squash      — transient squash/stretch, always settles back to ONE
##   lift        — transient vertical offset, always settles back to 0
##   sway        — rotation about the base (idle, harvest)
## Each tween drives only its own channels, so e.g. a watering bounce can
## never overwrite a growth-stage tween. No _process — all Tween-driven.
##
## Readable at a glance: a crop waiting for water droops and holds still;
## a watered, growing crop stands up and barely stirs; a ready crop is at
## full size, riper in color, and moves a little more (plus a gentle
## swell for crops with ready_pulse).

const STAGE_SCALES := [0.28, 0.55, 0.8, 1.0]
const MATURE_STAGE := 3
const MIN_SCALE := 0.001
const SEED_SINK := -0.05
const GROWING_SWAY := 0.02
const GROWING_SWAY_PERIOD := 2.2
const READY_SWAY := 0.06
const READY_SWAY_PERIOD := 1.4
const READY_BOB := 0.012
const READY_LIGHTEN := 0.18
const DROOP_TILT := 0.22
const DROOP_SAG := 0.1

var stage_scale: float = 0.0:
	set(value):
		stage_scale = value
		_apply()
var droop: float = 0.0:
	set(value):
		droop = value
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

var _mature_scale: float = 1.0
var _base_mature_scale: float = 1.0
var _sway_amount: float = 1.0
var _ready_pulse: float = 0.0
var _current_stage: int = 0
var _thirsty: bool = false

var _materials: Array[StandardMaterial3D] = []
var _base_albedo: Array[Color] = []
var _stage_tween: Tween
var _motion_tween: Tween
var _idle_tween: Tween
var _droop_tween: Tween

func _ready() -> void:
	_make_materials_unique()
	_apply()

## Called by FarmPlot right after instancing, before appear().
func configure(crop: CropDefinition) -> void:
	_base_mature_scale = maxf(crop.mature_scale, 0.1)
	_mature_scale = _base_mature_scale
	_sway_amount = maxf(crop.sway_amount, 0.0)
	_ready_pulse = maxf(crop.ready_pulse, 0.0)
	_apply()

## Quality shows as a slightly smaller (Plain) or larger (Fine) mature
## crop. Set as it ripens; the running growth tween eases into the new size.
func set_size_factor(size_factor: float) -> void:
	_mature_scale = maxf(_base_mature_scale * size_factor, 0.1)
	_apply()

## Restoring a saved crop: jump straight to its stage and posture with no
## growth animation, then start the idle that matches. Called after the
## visual is in the tree (its materials are made unique in _ready).
func snap_to(stage_index: int, thirsty: bool) -> void:
	_stop_all_tweens()
	_current_stage = clampi(stage_index, 0, MATURE_STAGE)
	_thirsty = thirsty
	stage_scale = STAGE_SCALES[_current_stage]
	droop = 1.0 if thirsty else 0.0
	squash = Vector3.ONE
	lift = 0.0
	sway = 0.0
	if _current_stage == MATURE_STAGE:
		for i in _materials.size():
			_materials[i].albedo_color = _base_albedo[i].lightened(READY_LIGHTEN)
	_resume_idle()

## Planting: the seedling starts slightly sunk and flattened, then rises
## and un-squashes out of the soil — a tiny upward emergence cue.
func appear() -> void:
	_stop_all_tweens()
	_current_stage = 0
	stage_scale = 0.0
	droop = 0.0
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
## also stands the crop fully up, ripens its colors, and starts the ready
## idle.
func set_stage(stage_index: int) -> void:
	_current_stage = clampi(stage_index, 0, MATURE_STAGE)
	_kill(_stage_tween)
	_kill(_motion_tween)
	_kill(_idle_tween)
	_stage_tween = create_tween()
	_stage_tween.tween_property(self, "stage_scale", STAGE_SCALES[_current_stage], 0.55) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)

	_motion_tween = create_tween()
	_motion_tween.tween_property(self, "squash", Vector3(0.9, 1.15, 0.9), 0.25) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_motion_tween.parallel().tween_property(self, "lift", 0.02, 0.25) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	_motion_tween.tween_property(self, "squash", Vector3(1.06, 0.94, 1.06), 0.15).set_trans(Tween.TRANS_SINE)
	_motion_tween.parallel().tween_property(self, "lift", 0.0, 0.15).set_trans(Tween.TRANS_SINE)
	_motion_tween.tween_property(self, "squash", Vector3.ONE, 0.2).set_trans(Tween.TRANS_SINE)
	_motion_tween.tween_callback(_resume_idle)

	if _current_stage == MATURE_STAGE:
		_ripen_colors()
		# Stand up fully, but let the settle callback above start the ready
		# idle — it uses squash/lift, which the settle is still driving.
		_set_droop(false)

## Thirsty = waiting for water: lean over a little, sag slightly, and hold
## still. Watering (set_thirsty(false)) stands it back up and lets it stir.
func set_thirsty(thirsty: bool) -> void:
	_set_droop(thirsty)
	if thirsty:
		_kill(_idle_tween)
		_droop_tween.parallel().tween_property(self, "sway", 0.0, 0.8).set_trans(Tween.TRANS_SINE)
	else:
		# Only ever reached for a growing crop (the ready idle is started by
		# set_stage's settle), and the growing idle drives sway alone.
		_resume_idle()

func _set_droop(thirsty: bool) -> void:
	_thirsty = thirsty
	_kill(_droop_tween)
	_droop_tween = create_tween()
	_droop_tween.tween_property(self, "droop", 1.0 if thirsty else 0.0, 1.2 if thirsty else 0.5) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

## A gentle bounce when watered. Touches only the transient channels, and
## always returns them to neutral.
func play_water_response() -> void:
	_kill(_motion_tween)
	_motion_tween = create_tween()
	_motion_tween.tween_property(self, "squash", Vector3(1.1, 0.88, 1.1), 0.12).set_trans(Tween.TRANS_SINE)
	_motion_tween.parallel().tween_property(self, "lift", 0.0, 0.12)
	_motion_tween.tween_property(self, "squash", Vector3(0.96, 1.06, 0.96), 0.14).set_trans(Tween.TRANS_SINE)
	_motion_tween.tween_property(self, "squash", Vector3.ONE, 0.18).set_trans(Tween.TRANS_SINE)

## The crop's harvest personality (CropDefinition.harvest_style), scaled by
## rarity intensity: the anticipation beat. Uses a local tween nothing else
## can kill, so awaiting it can never hang the caller.
func play_harvest(style: String, intensity: float) -> void:
	_stop_all_tweens()
	var tween := create_tween()
	match style:
		"sway":
			tween.tween_property(self, "sway", 0.22 * intensity, 0.12).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "sway", -0.18 * intensity, 0.16).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "sway", 0.08 * intensity, 0.12).set_trans(Tween.TRANS_SINE)
		"bloom":
			tween.tween_property(self, "squash", Vector3.ONE * (1.0 + 0.2 * intensity), 0.14) \
				.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
			tween.tween_property(self, "squash", Vector3.ONE * 0.95, 0.1).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "squash", Vector3.ONE * (1.0 + 0.12 * intensity), 0.12).set_trans(Tween.TRANS_SINE)
		_:
			tween.tween_property(self, "squash", Vector3(1.14, 0.8, 1.14), 0.1).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "lift", 0.1 * intensity, 0.1) \
				.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			tween.parallel().tween_property(self, "squash", Vector3(0.86, 1.24, 0.86), 0.1).set_trans(Tween.TRANS_SINE)
	await tween.finished

## The release: each style leaves the ground in its own way instead of
## everything shrinking in place. Carrot keeps rising as it pops free;
## herb floats up softly as its sway settles; sunflower swells once more,
## then gently closes. Same local-tween rule as play_harvest().
func play_remove(style: String) -> void:
	_stop_all_tweens()
	var tween := create_tween().set_parallel(true)
	match style:
		"sway":
			tween.tween_property(self, "lift", lift + 0.16, 0.38).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
			tween.tween_property(self, "sway", 0.0, 0.38).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "stage_scale", 0.0, 0.38).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
		"bloom":
			tween.tween_property(self, "squash", Vector3.ONE * 1.18, 0.12).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "stage_scale", 0.0, 0.3).set_delay(0.08) \
				.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
		_:
			tween.tween_property(self, "lift", lift + 0.32, 0.28).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
			tween.tween_property(self, "sway", 0.35, 0.28).set_trans(Tween.TRANS_SINE)
			tween.tween_property(self, "stage_scale", 0.0, 0.28).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await tween.finished

func _apply() -> void:
	var sag := Vector3(1.0, 1.0 - droop * DROOP_SAG, 1.0)
	scale = squash * sag * maxf(stage_scale * _mature_scale, MIN_SCALE)
	position.y = lift
	rotation.x = droop * DROOP_TILT
	rotation.z = sway

## Picks the idle that matches the crop's state: none for a seed or a
## thirsty crop, a barely-there stir while growing, and the livelier
## ready idle (with the crop's own ready_pulse swell) once mature.
func _resume_idle() -> void:
	if _current_stage >= MATURE_STAGE:
		_start_idle(READY_SWAY * _sway_amount, READY_SWAY_PERIOD, READY_BOB, _ready_pulse)
	elif _current_stage > 0 and not _thirsty:
		_start_idle(GROWING_SWAY * _sway_amount, GROWING_SWAY_PERIOD, 0.0, 0.0)
	else:
		_kill(_idle_tween)

## One looping tween per crop. Only started once transient motion has
## settled (from set_stage's settle callback or set_thirsty(false) on a
## growing crop, which only uses sway), so it never fights another tween.
func _start_idle(amplitude: float, period: float, bob: float, pulse: float) -> void:
	_kill(_idle_tween)
	if amplitude <= 0.0 and bob <= 0.0 and pulse <= 0.0:
		return
	_idle_tween = create_tween().set_loops()
	_idle_tween.tween_property(self, "sway", amplitude, period) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if bob > 0.0:
		_idle_tween.parallel().tween_property(self, "lift", bob, period) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if pulse > 0.0:
		_idle_tween.parallel().tween_property(self, "squash", Vector3.ONE * (1.0 + pulse), period) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_idle_tween.tween_property(self, "sway", -amplitude, period) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if bob > 0.0:
		_idle_tween.parallel().tween_property(self, "lift", 0.0, period) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	if pulse > 0.0:
		_idle_tween.parallel().tween_property(self, "squash", Vector3.ONE, period) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)

## Ready crops read slightly lighter/riper — a value change, not a glow.
func _ripen_colors() -> void:
	for i in _materials.size():
		var tween := create_tween()
		tween.tween_property(_materials[i], "albedo_color", _base_albedo[i].lightened(READY_LIGHTEN), 0.6)

func _stop_all_tweens() -> void:
	for tween: Tween in [_stage_tween, _motion_tween, _idle_tween, _droop_tween]:
		_kill(tween)
	_stage_tween = null
	_motion_tween = null
	_idle_tween = null
	_droop_tween = null

func _kill(tween: Tween) -> void:
	if tween and tween.is_valid():
		tween.kill()

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
