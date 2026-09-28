extends Node3D

## A small decorative butterfly that hovers in a gentle loop near its spawn
## point and flutters its wings. Purely visual — an environmental clue, not
## an interactable.

@export var loop_radius: float = 0.6
@export var loop_speed: float = 0.8
@export var flutter_speed: float = 14.0

@onready var wing_left: Node3D = $WingLeft
@onready var wing_right: Node3D = $WingRight

var _base_position: Vector3
var _time: float = 0.0

func _ready() -> void:
	_base_position = position

func _process(delta: float) -> void:
	_time += delta
	var loop_angle := _time * loop_speed
	position = _base_position + Vector3(
		sin(loop_angle) * loop_radius,
		0.25 + sin(_time * 1.7) * 0.08,
		cos(loop_angle * 0.8) * loop_radius * 0.6
	)
	rotation.y = loop_angle
	var flutter := sin(_time * flutter_speed)
	wing_left.rotation.z = flutter * 0.6
	wing_right.rotation.z = -flutter * 0.6
