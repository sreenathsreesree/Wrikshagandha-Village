extends Node3D

## Wires the world's follow camera and WorldSimulation to the player/light/
## environment nodes that live in this scene. Kept deliberately tiny —
## world-building itself lives entirely in the scene tree (Meadow.tscn).

@onready var player: Node3D = $Player
@onready var follow_camera: FollowCamera = $FollowCamera
@onready var world_simulation: WorldSimulation = $WorldSimulation
@onready var directional_light: DirectionalLight3D = $DirectionalLight3D
@onready var world_environment: WorldEnvironment = $WorldEnvironment

func _ready() -> void:
	follow_camera.target = player
	follow_camera.global_position = player.global_position
	world_simulation.configure(player, directional_light, world_environment)
