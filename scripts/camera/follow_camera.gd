extends Node3D
class_name FollowCamera

## Smoothly follows a target (the player) at a fixed elevated offset —
## the 2.5D "camera" module, kept independent of Player so the camera
## never spins with the player's facing direction.

@export var target: Node3D
@export var follow_speed: float = 6.0

func _physics_process(delta: float) -> void:
	if target == null:
		return
	var target_position := target.global_position
	var smoothing := 1.0 - exp(-follow_speed * delta)
	global_position = global_position.lerp(target_position, smoothing)
