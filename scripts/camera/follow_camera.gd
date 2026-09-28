extends Node3D
class_name FollowCamera

## Smoothly follows a target (the player) at a fixed elevated offset — the
## 2.5D "camera" module, kept independent of Player so the camera never
## spins with the player's facing direction and never needs to know the
## target's concrete type (it estimates velocity itself by differentiating
## position, rather than reading a CharacterBody3D.velocity property).
##
## Adds a small velocity-based look-ahead (so the world in front of the
## player's movement is a little more visible), a gentle FOV widen at
## speed, and a fixed screen-space offset so the player sits in a
## comfortable exploration-camera position rather than dead-center.

@export var target: Node3D
@export var follow_speed: float = 6.5
@export var look_ahead_distance: float = 1.0
@export var look_ahead_speed_reference: float = 4.3
@export var base_fov: float = 50.0
@export var fov_boost: float = 2.0

## Camera3D's built-in framing offset (viewport-space, not a 3D move) —
## keeps the player a little below and off dead-center so more of the
## world ahead is visible, without touching the actual camera position.
@export var screen_offset := Vector2(0.0, 0.08)

@onready var _camera: Camera3D = get_node_or_null("SpringArm3D/Camera3D") as Camera3D

var _last_target_position: Vector3
var _has_last_position: bool = false

func _ready() -> void:
	if _camera:
		_camera.h_offset = screen_offset.x
		_camera.v_offset = screen_offset.y

func _physics_process(delta: float) -> void:
	if target == null:
		return

	var target_position := target.global_position
	if not _has_last_position:
		_last_target_position = target_position
		_has_last_position = true

	var velocity_estimate := (target_position - _last_target_position) / maxf(delta, 0.0001)
	_last_target_position = target_position

	var horizontal_speed := Vector2(velocity_estimate.x, velocity_estimate.z).length()
	var speed_ratio := clamp(horizontal_speed / look_ahead_speed_reference, 0.0, 1.0)

	var look_ahead := Vector3.ZERO
	if horizontal_speed > 0.15:
		look_ahead = Vector3(velocity_estimate.x, 0.0, velocity_estimate.z).normalized() * look_ahead_distance * speed_ratio

	var desired_position := target_position + look_ahead
	var smoothing := 1.0 - exp(-follow_speed * delta)
	global_position = global_position.lerp(desired_position, smoothing)

	if _camera:
		var fov_smoothing := 1.0 - exp(-3.0 * delta)
		_camera.fov = lerp(_camera.fov, base_fov + speed_ratio * fov_boost, fov_smoothing)
