extends Node
class_name ExplorationLandmarkController

## Sibling of WildlifeController/EnvironmentalEventController under
## WorldSimulation. One shared per-frame distance check over every
## ExplorationLandmark in the world (there are only a handful), rather
## than each marker running its own _process or Area3D. Already-reached
## markers are skipped before the distance check even runs, so the cost
## only exists for the few landmarks/secret spots still unvisited this
## session.

var player: Node3D

func _process(_delta: float) -> void:
	if player == null:
		return
	for node in get_tree().get_nodes_in_group("exploration_landmark"):
		var landmark := node as ExplorationLandmark
		if landmark == null or landmark.is_reached():
			continue
		if landmark.global_position.distance_to(player.global_position) <= landmark.radius:
			landmark.mark_reached()
