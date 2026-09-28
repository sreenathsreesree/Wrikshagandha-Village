extends Node3D

## Wires the world's follow camera to the player. Kept deliberately tiny —
## world-building itself lives entirely in the scene tree (Meadow.tscn).

@onready var player: Node3D = $Player
@onready var follow_camera: FollowCamera = $FollowCamera

func _ready() -> void:
	follow_camera.target = player
	follow_camera.global_position = player.global_position
