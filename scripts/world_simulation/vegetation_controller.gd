extends Node
class_name VegetationController

## Publishes the player's position to a single global shader uniform
## (wg_player_position, declared in shaders/sway.gdshader and registered in
## project.godot's [shader_globals]). Every grass/flower material using
## that shader reads it for free to bend away from the player — one CPU
## update per frame regardless of how many blades are on screen, no
## per-instance scripts or physics needed.

var player: Node3D

func _process(_delta: float) -> void:
	if player == null:
		return
	RenderingServer.global_shader_parameter_set("wg_player_position", player.global_position)
