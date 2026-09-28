extends Node
class_name WildlifeController

## Finds every wildlife actor placed anywhere in the world (via the
## "wildlife_actor" group — no direct node-path coupling needed) and gives
## each one the player reference it needs to flee. Called once by
## WorldSimulation.configure(), after the whole scene is ready.

## TimeOfDay phase -> how dark it is for wildlife (0 = day, 1 = night).
## Unknown phases read as day.
const PHASE_DARKNESS := {"dawn": 0.5, "evening": 0.5, "night": 1.0}

var player: Node3D

func wire_actors() -> void:
	for node in get_tree().get_nodes_in_group("wildlife_actor"):
		if node is WildlifeActor:
			var actor: WildlifeActor = node
			actor.player = player

## Relays an outside pull (e.g. FarmManager's garden interest) to every
## actor; each decides for itself whether the key concerns it. Called on
## change only, via WorldSimulation — never per frame.
func set_attraction(key: String, strength: float) -> void:
	for node in get_tree().get_nodes_in_group("wildlife_actor"):
		if node is WildlifeActor:
			var actor: WildlifeActor = node
			actor.set_attraction(key, strength)

## Relays TimeOfDay's named phase as a darkness level. Called on phase
## change only (five times a day), via WorldSimulation.
func set_time_phase(phase: String) -> void:
	var darkness: float = PHASE_DARKNESS.get(phase, 0.0)
	for node in get_tree().get_nodes_in_group("wildlife_actor"):
		if node is WildlifeActor:
			var actor: WildlifeActor = node
			actor.set_darkness(darkness)
