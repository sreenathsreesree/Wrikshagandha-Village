extends WildlifeActor
class_name WildlifeButterfly

## Adds hover height, wing flapping, and a "landed" pose on top of the
## shared wander/pause/flee state machine — the only creature that needs
## anything beyond the base behavior.

@export var hover_height: float = 0.35
@export var land_height: float = 0.06
@export var flap_speed: float = 12.0

@onready var wing_left: Node3D = $WingLeft
@onready var wing_right: Node3D = $WingRight

var _flap_time: float = 0.0

func _process(delta: float) -> void:
	super._process(delta)

	_flap_time += delta * flap_speed
	var flap := sin(_flap_time)
	wing_left.rotation.z = flap * 0.6
	wing_right.rotation.z = -flap * 0.6

	var target_height := land_height if state == "pause" else hover_height
	position.y = lerp(position.y, target_height, 4.0 * delta)
