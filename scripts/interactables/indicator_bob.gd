extends Node3D

## Gentle bob + spin for the "something is discoverable here" indicator.
## Only animates while visible, so hidden indicators cost nothing.

@export var bob_height: float = 0.12
@export var bob_speed: float = 2.2
@export var spin_speed: float = 1.4

var _base_y: float = 0.0
var _time: float = 0.0

func _ready() -> void:
	_base_y = position.y

func _process(delta: float) -> void:
	if not visible:
		return
	_time += delta
	position.y = _base_y + sin(_time * bob_speed) * bob_height
	rotate_y(spin_speed * delta)
