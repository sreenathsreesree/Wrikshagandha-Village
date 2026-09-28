extends Node

## Tracks which discoveries the player has already made this game and
## coordinates awarding points the first time something is discovered.

signal discovery_made(definition: DiscoveryDefinition)
signal discovery_repeated(definition: DiscoveryDefinition)

var discovered_ids: Array[String] = []

func discover(id: String) -> bool:
	var definition := DiscoveryDatabase.get_definition(id)
	if definition == null:
		push_warning("DiscoveryManager: unknown discovery id '%s'" % id)
		return false
	if discovered_ids.has(id):
		discovery_repeated.emit(definition)
		return false
	discovered_ids.append(id)
	PointsManager.add_points(definition.points_value)
	AmbientAudioManager.play_discovery_sound()
	discovery_made.emit(definition)
	return true

func is_discovered(id: String) -> bool:
	return discovered_ids.has(id)

func set_discovered_ids(ids: Array) -> void:
	discovered_ids.clear()
	for id in ids:
		discovered_ids.append(String(id))

func get_discovered_ids() -> Array[String]:
	return discovered_ids.duplicate()
