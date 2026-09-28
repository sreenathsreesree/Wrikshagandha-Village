extends Node3D
class_name WildlifeActor

## Generic, lightweight wildlife behavior shared by every ground/hovering
## creature: idle -> wander -> pause -> (flee if the player gets close) ->
## idle. Movement is plain position interpolation, not physics — these are
## decorative, non-interactable actors, so a physics body would be wasted
## cost on Android. Different creatures (Rabbit, Small Bird) reuse this
## script unchanged with different exported tuning; Butterfly subclasses it
## for hover/landing behavior.

signal state_changed(state: String)

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

## Set by WildlifeController once, after every actor in the scene exists —
## never touched by the actor itself.
var player: Node3D

var state: String = "idle"

var _home_position: Vector3
var _target_position: Vector3
var _state_timer: float = 0.0

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
	if direction.length() > 0.01:
		# Node3D's local forward is -Z, so solve sin(a)=dx, cos(a)=-dz.
		var facing := atan2(direction.x, -direction.z)
		rotation.y = lerp_angle(rotation.y, facing, turn_speed * delta)
	position = position.move_toward(target, speed * delta)

func _flee_target() -> Vector3:
	if player == null:
		return position
	var away := position - player.global_position
	away.y = 0.0
	if away.length() < 0.01:
		away = Vector3(1.0, 0.0, 0.0)
	return position + away.normalized() * flee_distance * 2.0

func _enter_idle() -> void:
	state = "idle"
	_state_timer = randf_range(idle_time_min, idle_time_max)
	state_changed.emit(state)

func _enter_pause() -> void:
	state = "pause"
	_state_timer = randf_range(idle_time_min, idle_time_max)
	state_changed.emit(state)

func _enter_wander() -> void:
	state = "wander"
	var angle := randf_range(0.0, TAU)
	var radius := randf_range(0.3, wander_radius)
	_target_position = _home_position + Vector3(cos(angle) * radius, 0.0, sin(angle) * radius)
	state_changed.emit(state)

func _enter_flee() -> void:
	state = "flee"
	_state_timer = randf_range(1.0, 2.0)
	state_changed.emit(state)
