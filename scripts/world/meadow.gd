extends Node3D
class_name MeadowArea

## The Meadow area: world content only. The player, camera and HUD belong to
## the persistent Main scene (M03.1), which hands the player over through
## attach_player(). Kept deliberately tiny — world-building itself lives
## entirely in the scene tree (Meadow.tscn).

@onready var world_simulation: WorldSimulation = $WorldSimulation
@onready var directional_light: DirectionalLight3D = $DirectionalLight3D
@onready var world_environment: WorldEnvironment = $WorldEnvironment
@onready var navigation_region: NavigationRegion3D = $NavigationRegion3D

func _ready() -> void:
	_bake_navigation()

## Called once by Main when the shell is ready: the area's world simulation
## (wildlife, vegetation, events, landmarks) follows this player.
func attach_player(player: Node3D) -> void:
	world_simulation.configure(player, directional_light, world_environment)

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
