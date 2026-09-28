extends Node3D
class_name AreaCameraBounds

## The rectangle on the ground plane (X/Z, metres) that the camera's focus
## may move within while this area is loaded (M03.4). Centred on this node,
## axis-aligned; one per area. Main hands it to the FollowCamera whenever
## the area is loaded, so the camera itself knows no area's size. A zero
## size means "no bounds".

const GROUP := &"area_camera_bounds"

@export var size: Vector2 = Vector2.ZERO

func _enter_tree() -> void:
	add_to_group(GROUP)

func get_rect() -> Rect2:
	return Rect2(Vector2(global_position.x, global_position.z) - size * 0.5, size)
