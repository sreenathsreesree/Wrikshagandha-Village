extends Node3D

## Wires the world's follow camera and WorldSimulation to the player/light/
## environment nodes that live in this scene. Kept deliberately tiny —
## world-building itself lives entirely in the scene tree (Meadow.tscn).

@onready var player: Node3D = $Player
@onready var follow_camera: FollowCamera = $FollowCamera
@onready var world_simulation: WorldSimulation = $WorldSimulation
@onready var directional_light: DirectionalLight3D = $DirectionalLight3D
@onready var world_environment: WorldEnvironment = $WorldEnvironment
@onready var navigation_region: NavigationRegion3D = $NavigationRegion3D

func _ready() -> void:
	follow_camera.target = player
	follow_camera.global_position = player.global_position
	world_simulation.configure(player, directional_light, world_environment)
	_bake_navigation()

## Tap-to-move walks on a navigation mesh built from the world's own
## static colliders (ground, mounds, trees, rocks, bushes, logs, the
## monolith — everything that already blocks the player), so paths respect
## exactly what the joystick respects. Baked once at load on a background
## thread; skipped if a mesh was baked into the scene in the editor.
func _bake_navigation() -> void:
	if navigation_region.navigation_mesh == null:
		return
	if navigation_region.navigation_mesh.get_polygon_count() > 0:
		return
	navigation_region.bake_navigation_mesh(true)
