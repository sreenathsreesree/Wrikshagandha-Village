extends GameArea
class_name MeadowArea

## The Meadow area: world content only. The player, camera and HUD belong to
## the persistent Main scene (M03.1), which hands the player over through
## attach_player(). Kept deliberately tiny — world-building itself lives
## entirely in the scene tree (Meadow.tscn). Its navigation is baked by
## GameArea from the world's own static colliders (ground, mounds, trees,
## rocks, bushes, logs, the monolith — everything that already blocks the
## player), so paths respect exactly what the joystick respects.
##
## While the player is indoors the Meadow is parked by Main (M08.1, D-33):
## out of the tree, the same instance, untouched — its time of day,
## discoveries, wildlife and farm wait exactly as they were.

@onready var world_simulation: WorldSimulation = $WorldSimulation
@onready var directional_light: DirectionalLight3D = $DirectionalLight3D
@onready var world_environment: WorldEnvironment = $WorldEnvironment

## Called once by Main when the shell is ready: the area's world simulation
## (wildlife, vegetation, events, landmarks) follows this player.
func attach_player(player: Node3D) -> void:
	world_simulation.configure(player, directional_light, world_environment)
