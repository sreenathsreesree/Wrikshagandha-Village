extends Node3D

## The persistent runtime shell (M03.1). Player, FollowCamera and HUD live
## here and belong to no area; the current area — today the Meadow — is
## world content only (terrain, navigation, discoveries, farm, wildlife,
## world simulation). Wired once, after every child is ready: the camera
## follows the player, and the area is handed the player for its world
## simulation. Loading or swapping areas is not done here (M03.2).

@onready var player: Player = $Player
@onready var follow_camera: FollowCamera = $FollowCamera
@onready var area: MeadowArea = $Meadow

func _ready() -> void:
	follow_camera.target = player
	follow_camera.global_position = player.global_position
	area.attach_player(player)
