extends Node
class_name WildlifeController

## Finds every wildlife actor placed anywhere in the world (via the
## "wildlife_actor" group — no direct node-path coupling needed) and gives
## each one the player reference it needs to flee. Called once by
## WorldSimulation.configure(), after the whole scene is ready.

var player: Node3D

func wire_actors() -> void:
	for node in get_tree().get_nodes_in_group("wildlife_actor"):
		if node is WildlifeActor:
			var actor: WildlifeActor = node
			actor.player = player
