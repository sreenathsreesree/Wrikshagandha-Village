extends Node

## Loads every DiscoveryDefinition resource found under DISCOVERIES_PATH at
## startup. Adding hundreds of plants/animals/resources later means dropping
## more .tres files in that folder — this script never needs to change.

const DISCOVERIES_PATH := "res://data/discoveries/"

var _definitions: Dictionary = {}

func _ready() -> void:
	_load_definitions()

## ResourceDirectory handles exported builds, where these files are listed
## as "*.tres.remap" rather than "*.tres".
func _load_definitions() -> void:
	_definitions.clear()
	for path in ResourceDirectory.list_tres_paths(DISCOVERIES_PATH):
		var resource: Resource = load(path)
		if resource is DiscoveryDefinition:
			var definition: DiscoveryDefinition = resource
			if definition.id == "":
				push_warning("DiscoveryDatabase: %s has an empty id" % path)
			else:
				_definitions[definition.id] = definition

func get_definition(id: String) -> DiscoveryDefinition:
	return _definitions.get(id, null)

func has_definition(id: String) -> bool:
	return _definitions.has(id)

func get_all_definitions() -> Array:
	return _definitions.values()
