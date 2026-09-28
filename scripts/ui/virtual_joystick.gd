extends Control

## Fixed mobile joystick: Base and Thumb are always visible at a fixed
## bottom-left position (never hidden, never repositioned to the touch
## point). This Control itself is only the touch-capture zone — dragging
## anywhere inside it moves the Thumb, clamped to the Base's radius, and
## releasing snaps the Thumb back to center. Includes a dead zone (stops
## idle drift) and per-frame smoothing (stops twitchy movement). Output
## goes through InputManager, same as always — player.gd is untouched.
## "Emulate touch from mouse" (project setting) lets this be tested with a
## mouse in the editor.

@export var knob_max_distance: float = 50.0
@export var dead_zone: float = 0.15
@export var smoothing_speed: float = 14.0

@onready var base: Control = $Base
@onready var thumb: Control = $Base/Thumb

var _touch_index: int = -1
var _base_center: Vector2 = Vector2.ZERO
var _raw_vector: Vector2 = Vector2.ZERO
var _smoothed_vector: Vector2 = Vector2.ZERO

func _ready() -> void:
	_base_center = base.size / 2.0
	_reset_thumb()
	visibility_changed.connect(_on_visibility_changed)

## Hidden (Tap to Move selected): let go of any touch in progress so no
## stale deflection keeps steering the player.
func _on_visibility_changed() -> void:
	if not is_visible_in_tree():
		_release()
		_smoothed_vector = Vector2.ZERO

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var touch: InputEventScreenTouch = event
		if touch.pressed and _touch_index == -1:
			_touch_index = touch.index
			_update_thumb(_to_base_local(touch.position))
		elif not touch.pressed and touch.index == _touch_index:
			_release()
	elif event is InputEventScreenDrag:
		var drag: InputEventScreenDrag = event
		if drag.index == _touch_index:
			_update_thumb(_to_base_local(drag.position))

## event.position arrives relative to this Control (the touch zone); Base
## is a fixed-position child of it, so shift into Base-local space before
## measuring the offset from its center.
func _to_base_local(zone_local_position: Vector2) -> Vector2:
	return zone_local_position - base.position

func _update_thumb(base_local_position: Vector2) -> void:
	var offset := base_local_position - _base_center
	if offset.length() > knob_max_distance:
		offset = offset.normalized() * knob_max_distance
	thumb.position = _base_center + offset - thumb.size / 2.0
	var normalized := offset / knob_max_distance
	_raw_vector = normalized if normalized.length() >= dead_zone else Vector2.ZERO

func _release() -> void:
	_touch_index = -1
	_reset_thumb()
	_raw_vector = Vector2.ZERO

func _reset_thumb() -> void:
	thumb.position = _base_center - thumb.size / 2.0

func _process(delta: float) -> void:
	_smoothed_vector = _smoothed_vector.lerp(_raw_vector, clamp(smoothing_speed * delta, 0.0, 1.0))
	InputManager.set_move_vector(_smoothed_vector)
