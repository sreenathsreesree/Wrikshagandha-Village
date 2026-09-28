extends Control

## Floating mobile joystick: invisible until the player touches down inside
## a generous capture area, then the base appears centered on that touch so
## it always lands comfortably under the thumb. Includes a dead zone (to
## stop idle drift) and per-frame smoothing (so movement doesn't feel
## twitchy). "Emulate touch from mouse" (project setting) lets this be
## tested with a mouse in the editor.

@export var base_radius: float = 85.0
@export var knob_max_distance: float = 60.0
@export var dead_zone: float = 0.15
@export var smoothing_speed: float = 14.0

@onready var base: Control = $Base
@onready var knob: Control = $Base/Knob

var _touch_index: int = -1
var _raw_vector: Vector2 = Vector2.ZERO
var _smoothed_vector: Vector2 = Vector2.ZERO

func _ready() -> void:
	base.visible = false

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var touch: InputEventScreenTouch = event
		if touch.pressed and _touch_index == -1:
			_touch_index = touch.index
			_activate_at(touch.position)
		elif not touch.pressed and touch.index == _touch_index:
			_release()
	elif event is InputEventScreenDrag:
		var drag: InputEventScreenDrag = event
		if drag.index == _touch_index:
			_update_knob(drag.position)

func _activate_at(local_position: Vector2) -> void:
	var clamped := Vector2(
		clamp(local_position.x, base_radius, size.x - base_radius),
		clamp(local_position.y, base_radius, size.y - base_radius)
	)
	base.position = clamped - Vector2(base_radius, base_radius)
	base.visible = true
	_update_knob(local_position)

func _update_knob(local_position: Vector2) -> void:
	var base_center := base.position + Vector2(base_radius, base_radius)
	var offset := local_position - base_center
	if offset.length() > knob_max_distance:
		offset = offset.normalized() * knob_max_distance
	knob.position = Vector2(base_radius, base_radius) + offset - knob.size / 2.0
	var normalized := offset / knob_max_distance
	_raw_vector = normalized if normalized.length() >= dead_zone else Vector2.ZERO

func _release() -> void:
	_touch_index = -1
	base.visible = false
	knob.position = Vector2(base_radius, base_radius) - knob.size / 2.0
	_raw_vector = Vector2.ZERO

func _process(delta: float) -> void:
	_smoothed_vector = _smoothed_vector.lerp(_raw_vector, clamp(smoothing_speed * delta, 0.0, 1.0))
	InputManager.set_move_vector(_smoothed_vector)
