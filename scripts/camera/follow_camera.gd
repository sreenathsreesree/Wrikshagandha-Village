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
@onready var _spring_arm: SpringArm3D = get_node_or_null("SpringArm3D") as SpringArm3D

## Zoom (M03.5) is the spring arm's length — the camera's distance from the
## point it follows (11 m in the scene). Pinch and mouse wheel both come
## through zoom_by() (wired by Main from InputManager.zoom_requested), and
## set_zoom_distance() is the only place the length changes: always within
## these limits (provisional, proposal P-03 — tune at the playtest).
const ZOOM_MIN_DISTANCE := 7.0
const ZOOM_MAX_DISTANCE := 15.0
## Seated view turning (D-62, R3): degrees of yaw per canvas pixel of a
## one-finger drag (300 px turn the full 45°). The world follows the finger:
## a drag to the right turns the view to the left.
const SEATED_YAW_DEGREES_PER_PIXEL := 0.15

var _last_target_position: Vector3
var _has_last_position: bool = false
## The current area's bounds for the camera's focus (M03.4), set by Main when
## an area loads — replaced, or cleared, on every area change.
var _bounds: Rect2
var _has_bounds: bool = false
## The settle (D-49, D1): one transaction from the first settle() until a
## release has finished. The base — the distance and framing offset before
## it — is captured only when a transaction starts, so a settle during a
## release continues from where the camera is and still restores the
## original base. Pinch and wheel zoom are ignored while it eases (settling
## or releasing); between the two — seated — they stay within the zoom range
## settle() was given (D-62), and the release still restores the base.
## Seated, a drag also turns the view about the player (this node's yaw,
## D-62 R3) within settle()'s yaw limit of the base yaw; every settle and
## release eases the yaw back to the base, which the transaction captured.
var _settle_active: bool = false
var _base_distance: float = 0.0
var _base_offset := Vector2.ZERO
var _settle_tween: Tween
var _settle_zoom_range := Vector2(ZOOM_MIN_DISTANCE, ZOOM_MAX_DISTANCE)
var _base_yaw: float = 0.0
var _settle_yaw_limit: float = 0.0
## A settle transaction has ended: the release finished at the exact base
## (at once for release(0.0)). D-62: Main gives movement back only now.
signal settle_ended

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
	var speed_ratio := clampf(horizontal_speed / look_ahead_speed_reference, 0.0, 1.0)

	var look_ahead := Vector3.ZERO
	if horizontal_speed > 0.15:
		look_ahead = Vector3(velocity_estimate.x, 0.0, velocity_estimate.z).normalized() * look_ahead_distance * speed_ratio

	var desired_position := _clamp_to_bounds(target_position + look_ahead)
	var smoothing := 1.0 - exp(-follow_speed * delta)
	global_position = global_position.lerp(desired_position, smoothing)

	if _camera:
		var fov_smoothing := 1.0 - exp(-3.0 * delta)
		_camera.fov = lerp(_camera.fov, base_fov + speed_ratio * fov_boost, fov_smoothing)

## The loaded area's bounds (M03.4): the point the camera follows stays
## inside this X/Z rectangle. Given once per area load, never polled.
func set_bounds(bounds: Rect2) -> void:
	_bounds = bounds
	_has_bounds = true

func clear_bounds() -> void:
	_has_bounds = false

## Straight onto the target (inside the bounds) — at start and after an area
## change, so the camera never glides across the map; the next frame's
## look-ahead starts fresh instead of reading the jump as speed.
func snap_to_target() -> void:
	if target == null:
		return
	global_position = _clamp_to_bounds(target.global_position)
	_has_last_position = false

func _clamp_to_bounds(point: Vector3) -> Vector3:
	if not _has_bounds:
		return point
	point.x = clampf(point.x, _bounds.position.x, _bounds.end.x)
	point.z = clampf(point.z, _bounds.position.y, _bounds.end.y)
	return point

## factor < 1 brings the camera closer, > 1 moves it away; clamped. During a
## settle transaction it is the seated zoom instead (_zoom_seated).
func zoom_by(factor: float) -> void:
	if _settle_active:
		_zoom_seated(factor)
		return
	if _spring_arm == null or not is_finite(factor) or factor <= 0.0:
		return
	set_zoom_distance(_spring_arm.spring_length * factor)

## Seated zoom (D-62): ignored while the settle or release eases; otherwise
## kept within the transaction's zoom range. It never touches the base, so
## the release restores the pre-sit distance whatever the pinch did.
func _zoom_seated(factor: float) -> void:
	if _settle_tween != null or _spring_arm == null or not is_finite(factor) or factor <= 0.0:
		return
	set_zoom_distance(clampf(_spring_arm.spring_length * factor, _settle_zoom_range.x, _settle_zoom_range.y))

func set_zoom_distance(distance: float) -> void:
	if _spring_arm == null:
		return
	_spring_arm.spring_length = clampf(distance, ZOOM_MIN_DISTANCE, ZOOM_MAX_DISTANCE)

func get_zoom_distance() -> float:
	return _spring_arm.spring_length if _spring_arm else 0.0

## Eases the distance (through set_zoom_distance(), so within the zoom
## limits) and the existing screen-space framing offset (Camera3D's h/v
## offset) to these values over `seconds`. The follow, look-ahead, bounds
## and FOV are untouched; nothing rotates. Starting a transaction captures
## the base; during one (even mid-release) the base stays as captured.
## `zoom_range` bounds pinch and wheel once the settle has eased in, and
## `yaw_limit_degrees` the seated turning either side of the base yaw, which
## every settle eases back to (D-62).
func settle(distance: float, framing_offset: Vector2, zoom_range: Vector2, yaw_limit_degrees: float, seconds: float) -> void:
	if _camera == null or _spring_arm == null:
		return
	if not _settle_active:
		_settle_active = true
		_base_distance = get_zoom_distance()
		_base_offset = Vector2(_camera.h_offset, _camera.v_offset)
		_base_yaw = rotation.y
	_settle_zoom_range = zoom_range
	_settle_yaw_limit = deg_to_rad(yaw_limit_degrees)
	_ease_to(distance, framing_offset, seconds, false)

## Eases back to exactly the captured base, then ends the transaction;
## seconds <= 0 restores at once. No-op without a transaction.
func release(seconds: float) -> void:
	if not _settle_active:
		return
	_ease_to(_base_distance, _base_offset, seconds, true)

## Replaces any running ease, starting from the current values.
func _ease_to(distance: float, framing_offset: Vector2, seconds: float, ending: bool) -> void:
	if _settle_tween != null:
		_settle_tween.kill()
		_settle_tween = null
	if seconds <= 0.0:
		_finish_ease(distance, framing_offset, ending)
		return
	_settle_tween = create_tween().set_parallel(true).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	_settle_tween.tween_method(set_zoom_distance, get_zoom_distance(), distance, seconds)
	_settle_tween.tween_property(_camera, "h_offset", framing_offset.x, seconds)
	_settle_tween.tween_property(_camera, "v_offset", framing_offset.y, seconds)
	_settle_tween.tween_method(_set_yaw, rotation.y, _base_yaw, seconds)
	_settle_tween.chain().tween_callback(_finish_ease.bind(distance, framing_offset, ending))

## The exact end values (never left to interpolation), and the end of the
## transaction after a release.
func _finish_ease(distance: float, framing_offset: Vector2, ending: bool) -> void:
	_settle_tween = null
	set_zoom_distance(distance)
	_camera.h_offset = framing_offset.x
	_camera.v_offset = framing_offset.y
	_set_yaw(_base_yaw)
	if ending:
		_settle_active = false
		settle_ended.emit()

## A one-finger drag on the world (D-62 R3), in canvas pixels: seated (a
## transaction whose ease has finished) it turns the view about the player
## within the yaw limit of the base yaw; otherwise — standing, settling or
## releasing — it is ignored.
func yaw_by(drag: Vector2) -> void:
	if not _settle_active or _settle_tween != null or not drag.is_finite():
		return
	var turn := clampf(rotation.y - _base_yaw + deg_to_rad(drag.x * SEATED_YAW_DEGREES_PER_PIXEL), -_settle_yaw_limit, _settle_yaw_limit)
	_set_yaw(_base_yaw + turn)

## The one writer of the camera's yaw (this node's rotation about Y).
func _set_yaw(yaw: float) -> void:
	rotation.y = yaw
