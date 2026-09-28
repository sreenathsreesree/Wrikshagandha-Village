extends Node

## Loads every DiscoveryDefinition resource found under DISCOVERIES_PATH at
## startup. Adding hundreds of plants/animals/resources later means dropping
## more .tres files in that folder — this script never needs to change.

const DISCOVERIES_PATH := "res://data/discoveries/"

var _definitions: Dictionary = {}

func _ready() -> void:
	_load_definitions()

func _load_definitions() -> void:
	_definitions.clear()
	var dir := DirAccess.open(DISCOVERIES_PATH)
	if dir == null:
		push_warning("DiscoveryDatabase: could not open %s" % DISCOVERIES_PATH)
		return
	dir.list_dir_begin()
	var file_name := dir.get_next()
	while file_name != "":
		if not dir.current_is_dir() and file_name.ends_with(".tres"):
			var resource: Resource = load(DISCOVERIES_PATH + file_name)
			if resource is DiscoveryDefinition:
				if resource.id == "":
					push_warning("DiscoveryDatabase: %s has an empty id" % file_name)
				else:
					_definitions[resource.id] = resource
		file_name = dir.get_next()
	dir.list_dir_end()

func get_definition(id: String) -> DiscoveryDefinition:
	return _definitions.get(id, null)

func has_definition(id: String) -> bool:
	return _definitions.has(id)

func get_all_definitions() -> Array:
	return _definitions.values()
