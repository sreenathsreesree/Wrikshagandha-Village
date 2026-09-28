extends Control

## On-screen touch joystick. Writes a normalized Vector2 into InputManager
## on drag; resets to zero on release. Touch is the primary input model —
## "emulate touch from mouse" (enabled in project settings) lets this be
## tested with a mouse in the editor without any separate desktop controls.

@export var knob_max_distance: float = 60.0

@onready var base: Control = $Base
@onready var knob: Control = $Base/Knob

var _touch_index: int = -1
var _base_center: Vector2 = Vector2.ZERO

func _ready() -> void:
	_base_center = base.size / 2.0
	_reset()

func _gui_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed and _touch_index == -1:
			_touch_index = event.index
			_update_knob(event.position)
		elif not event.pressed and event.index == _touch_index:
			_reset()
	elif event is InputEventScreenDrag:
		if event.index == _touch_index:
			_update_knob(event.position)

func _update_knob(local_position: Vector2) -> void:
	var offset := local_position - _base_center
	if offset.length() > knob_max_distance:
		offset = offset.normalized() * knob_max_distance
	knob.position = _base_center + offset - knob.size / 2.0
	InputManager.set_move_vector(offset / knob_max_distance)

func _reset() -> void:
	_touch_index = -1
	knob.position = _base_center - knob.size / 2.0
	InputManager.set_move_vector(Vector2.ZERO)
