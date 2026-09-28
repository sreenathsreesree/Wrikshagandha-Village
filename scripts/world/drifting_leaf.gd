extends Node3D

## Purely decorative: a leaf drifts down in a gentle zigzag and loops back
## to its start height. Cheap (one sin + linear fall per frame) and there
## are only ever a couple of these in the world at once.

@export var fall_speed: float = 0.12
@export var sway_amount: float = 0.25
@export var sway_speed: float = 1.1
@export var fall_height: float = 3.0
@export var spin_speed: float = 0.6

var _start_position: Vector3
var _time: float = 0.0

func _ready() -> void:
	_start_position = position
	_time = randf_range(0.0, TAU)

func _process(delta: float) -> void:
	_time += delta
	position.y -= fall_speed * delta
	position.x = _start_position.x + sin(_time * sway_speed) * sway_amount
	position.z = _start_position.z + cos(_time * sway_speed * 0.7) * sway_amount * 0.6
	rotation.y += spin_speed * delta
	if position.y < _start_position.y - fall_height:
		position.y = _start_position.y
