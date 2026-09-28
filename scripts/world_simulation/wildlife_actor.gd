extends Node3D
class_name WildlifeActor

## Generic, lightweight wildlife behavior shared by every ground/hovering
## creature: idle -> wander -> pause -> (flee if the player gets close) ->
## idle. Movement is plain position interpolation, not physics — these are
## decorative, non-interactable actors, so a physics body would be wasted
## cost on Android. Different creatures (Rabbit, Small Bird) reuse this
## script unchanged with different exported tuning; Butterfly subclasses it
## for hover/landing behavior.

@export var wander_radius: float = 2.5
@export var move_speed: float = 0.8
@export var idle_time_min: float = 1.5
@export var idle_time_max: float = 4.0
@export var flee_distance: float = 2.5
@export var flee_speed: float = 3.0
@export var turn_speed: float = 6.0

## Beyond flee_distance but inside this radius, the creature doesn't run —
## it just turns to watch the player while idling/paused. Gives a sense of
## noticing the player before actually reacting.
@export var alert_distance: float = 4.0

## Optional handful of notable nearby spots (pond edge, a flower patch, a
## tree line) in the same position space as this actor — not necessarily
## close to wander_radius. Left empty, wandering behaves exactly as
## before (a random point near home). With points set, each time the
## actor starts wandering there's an interest_chance roll to head toward
## one of them instead — an occasional, non-repeating "going somewhere"
## moment rather than a fixed patrol, since it's decided fresh every
## wander cycle and still returns to ordinary near-home wandering the
## rest of the time.
@export var interest_points: Array[Vector3] = []
@export_range(0.0, 1.0) var interest_chance: float = 0.35

## Harmless curiosity, inside the existing pause state (no new AI state):
## when the actor arrives at interest_points[i] and pauses, it turns to
## face interest_look_targets[i] (if one exists at that index) — e.g. a
## rabbit at the garden's edge looking in at the crops — and its usual
## idle look-around centers on that direction. interest_linger stretches
## the pause at an interest point so it reads as lingering, not passing.
@export var interest_look_targets: Array[Vector3] = []
@export var interest_linger: float = 1.8

## Optional outside pull toward one of this actor's own interest points
## (e.g. "garden"). WildlifeController relays a strength (0..1) under a
## key; if it matches attraction_key, each wander has an extra
## strength × attraction_sensitivity chance of heading to
## interest_points[attraction_interest_index] — the same visit, look
## target and linger as an ordinary interest visit. The actor never learns
## why the place is interesting; empty key = unaffected.
@export var attraction_key: String = ""
@export var attraction_interest_index: int = 0
@export_range(0.0, 1.0) var attraction_sensitivity: float = 1.0

## How lively this creature stays in full darkness (1 = unchanged). Below
## 1 it rests longer between wanders and is less drawn to attractions —
## a butterfly settling for the night, a bird quieting down.
@export_range(0.05, 1.0) var night_activity: float = 1.0

## Optional flat circle of ground (same position space as this actor) the
## creature never crosses — while wandering, fleeing or heading back it
## slides around the edge instead, e.g. a rabbit that visits the garden's
## edge but never runs over the crop plots. keep_out_radius 0 = none, and
## movement is then exactly as before.
@export var keep_out_center: Vector3 = Vector3.ZERO
@export var keep_out_radius: float = 0.0

## Set by WildlifeController once, after every actor in the scene exists —
## never touched by the actor itself.
var player: Node3D

var state: String = "idle"

var _home_position: Vector3
var _target_position: Vector3
var _state_timer: float = 0.0
var _idle_wiggle_time: float = 0.0
var _idle_base_rotation: float = 0.0
var _current_interest_index: int = -1
var _attraction: float = 0.0
var _activity: float = 1.0

func _ready() -> void:
	_home_position = position
	_enter_idle()

func _process(delta: float) -> void:
	var player_distance := INF
	if player:
		player_distance = position.distance_to(player.global_position)
		if state != "flee" and player_distance < flee_distance:
			_enter_flee()
			return

	match state:
		"idle", "pause":
			if player_distance < alert_distance:
				_face_player(delta)
			else:
				_idle_look_around(delta)
			_state_timer -= delta
			if _state_timer <= 0.0:
				_enter_wander()
		"wander":
			_move_toward(_target_position, move_speed, delta)
			if position.distance_to(_target_position) < 0.1:
				_enter_pause()
		"flee":
			_move_toward(_flee_target(), flee_speed, delta)
			_state_timer -= delta
			if _state_timer <= 0.0 and (player == null or position.distance_to(player.global_position) > flee_distance * 1.5):
				_enter_idle()

## A tiny head-turn-like wiggle while idling with no player nearby to react
## to — makes the creature read as alive/curious rather than frozen,
## without any new state or extra processing cost beyond a sine.
func _idle_look_around(delta: float) -> void:
	_idle_wiggle_time += delta
	var wiggle := sin(_idle_wiggle_time * 0.6) * 0.35
	rotation.y = lerp_angle(rotation.y, _idle_base_rotation + wiggle, 2.0 * delta)

func _face_player(delta: float) -> void:
	if player == null:
		return
	var direction := player.global_position - position
	direction.y = 0.0
	if direction.length() <= 0.05:
		return
	var facing := atan2(direction.x, -direction.z)
	rotation.y = lerp_angle(rotation.y, facing, turn_speed * 0.5 * delta)

func _move_toward(target: Vector3, speed: float, delta: float) -> void:
	var direction := target - position
	direction.y = 0.0
	var detour := _keep_out_detour(direction)
	if detour != Vector3.ZERO:
		direction = detour
		target = position + detour * speed * delta
	if direction.length() > 0.01:
		# Node3D's local forward is -Z, so solve sin(a)=dx, cos(a)=-dz.
		var facing := atan2(direction.x, -direction.z)
		rotation.y = lerp_angle(rotation.y, facing, turn_speed * delta)
	position = position.move_toward(target, speed * delta)

## Zero when the straight path is clear (or no keep-out is set); otherwise
## the unit direction that slides along the keep-out circle's edge toward
## the side the path was heading — never into it. Pure geometry, no
## physics: a creature already inside steps straight out.
func _keep_out_detour(direction: Vector3) -> Vector3:
	if keep_out_radius <= 0.0:
		return Vector3.ZERO
	var to_zone := keep_out_center - position
	to_zone.y = 0.0
	var gap := to_zone.length()
	if gap < 0.01:
		return Vector3.ZERO
	var toward := to_zone / gap
	if gap < keep_out_radius:
		return -toward
	var reach := direction.length()
	if reach < 0.01:
		return Vector3.ZERO
	var heading := direction / reach
	var closest := heading * clampf(to_zone.dot(heading), 0.0, reach)
	if (to_zone - closest).length() >= keep_out_radius:
		return Vector3.ZERO
	var slide := heading - toward * heading.dot(toward)
	if slide.length() < 0.01:
		slide = Vector3(-toward.z, 0.0, toward.x)
	return slide.normalized()

func _is_kept_out(point: Vector3) -> bool:
	if keep_out_radius <= 0.0:
		return false
	var offset := point - keep_out_center
	offset.y = 0.0
	return offset.length() < keep_out_radius

func _flee_target() -> Vector3:
	if player == null:
		return position
	var away := position - player.global_position
	away.y = 0.0
	if away.length() < 0.01:
		away = Vector3(1.0, 0.0, 0.0)
	return position + away.normalized() * flee_distance * 2.0

## Forces an immediate flee reaction even if the player hasn't crossed
## this actor's own flee_distance yet. Used by EnvironmentalEvent so a
## small group of actors can react together the instant the player
## approaches, rather than each one only noticing individually and late.
## Safe to call on an actor that's already fleeing — it's just a no-op.
func startle() -> void:
	if state != "flee":
		_enter_flee()

## Event-driven from WildlifeController (never per frame). Only takes
## effect from the next wander decision onward — no state is interrupted.
func set_attraction(key: String, strength: float) -> void:
	if attraction_key == "" or key != attraction_key:
		return
	_attraction = clampf(strength * attraction_sensitivity, 0.0, 1.0)

## darkness: 0 = daylight, 1 = full night.
func set_darkness(darkness: float) -> void:
	_activity = lerpf(1.0, night_activity, clampf(darkness, 0.0, 1.0))

func _enter_idle() -> void:
	state = "idle"
	_state_timer = randf_range(idle_time_min, idle_time_max) / _activity
	_idle_base_rotation = rotation.y
	_idle_wiggle_time = 0.0

func _enter_pause() -> void:
	# Only a wander that just reached an interest point counts as arriving
	# there (not e.g. a butterfly landing after a lead).
	var arrived_at := _current_interest_index if state == "wander" else -1
	_current_interest_index = -1
	state = "pause"
	_state_timer = randf_range(idle_time_min, idle_time_max) / _activity
	_idle_base_rotation = rotation.y
	_idle_wiggle_time = 0.0
	if arrived_at < 0:
		return
	_state_timer *= maxf(interest_linger, 1.0)
	if arrived_at < interest_look_targets.size():
		var look := interest_look_targets[arrived_at] - position
		look.y = 0.0
		if look.length() > 0.05:
			_idle_base_rotation = atan2(look.x, -look.z)

func _enter_wander() -> void:
	state = "wander"
	_current_interest_index = -1
	var has_attraction_point := attraction_interest_index >= 0 and attraction_interest_index < interest_points.size()
	if has_attraction_point and randf() < _attraction * _activity:
		_current_interest_index = attraction_interest_index
		_target_position = interest_points[_current_interest_index]
	elif not interest_points.is_empty() and randf() < interest_chance:
		_current_interest_index = randi() % interest_points.size()
		_target_position = interest_points[_current_interest_index]
	else:
		var angle := randf_range(0.0, TAU)
		var radius := randf_range(0.3, wander_radius)
		_target_position = _home_position + Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
	if _is_kept_out(_target_position):
		# Never choose a destination inside the keep-out (sliding around
		# its edge would never arrive) — settle for home instead.
		_current_interest_index = -1
		_target_position = _home_position

func _enter_flee() -> void:
	state = "flee"
	_state_timer = randf_range(1.0, 2.0)
