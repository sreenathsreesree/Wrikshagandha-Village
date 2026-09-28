extends Node

## Tracks which discoveries the player has already made this game and
## always awards points on harvest — first-time or repeat. First-time and
## repeat are still distinguished (via which signal fires) so Journal/
## Collection/session-exploration bookkeeping only cares about first-time,
## while points and Daily Discovery completion work identically either way.

signal discovery_made(definition: DiscoveryDefinition)
signal discovery_repeated(definition: DiscoveryDefinition)

var discovered_ids: Array[String] = []

func discover(id: String) -> bool:
	var definition := DiscoveryDatabase.get_definition(id)
	if definition == null:
		push_warning("DiscoveryManager: unknown discovery id '%s'" % id)
		return false

	var is_first_time := not discovered_ids.has(id)
	if is_first_time:
		discovered_ids.append(id)

	PointsManager.add_points(definition.points_value)
	AmbientAudioManager.play_discovery_sound()

	if is_first_time:
		discovery_made.emit(definition)
	else:
		discovery_repeated.emit(definition)
	return true

func is_discovered(id: String) -> bool:
	return discovered_ids.has(id)

func set_discovered_ids(ids: Array) -> void:
	discovered_ids.clear()
	for id in ids:
		discovered_ids.append(String(id))

func get_discovered_ids() -> Array[String]:
	return discovered_ids.duplicate()
