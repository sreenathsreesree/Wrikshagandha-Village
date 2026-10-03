extends Node

## The travel layer between areas (M08.1). Anything that wants the player
## somewhere else — today a door (AreaDoor) — asks here with travel(); Main
## alone carries the request out (fade, swap, park, restore) and reports
## back with notify_arrived(). Everything else asks here which area the
## player is in. The areas themselves are data: one AreaDefinition per
## .tres in res://data/areas/, never named in a script.
##
## Not saved (D-34): a relaunch always starts in the Meadow at its start
## entry, whatever area the player was in.

signal travel_requested(area_id: String, entry_id: String)
signal area_changed(area_id: String)

const AREAS_PATH := "res://data/areas/"

var _definitions: Dictionary = {}
var _current_area_id: String = ""
## True from an accepted travel() until Main reports the arrival: a second
## request meanwhile (a double tap, the other door) is ignored.
var _travelling: bool = false

func _ready() -> void:
	_load_definitions()

## ResourceDirectory handles exported builds (".tres.remap" listings).
func _load_definitions() -> void:
	for path in ResourceDirectory.list_tres_paths(AREAS_PATH):
		var definition := load(path) as AreaDefinition
		if definition == null or definition.id == "":
			push_warning("AreaRouter: %s is not an AreaDefinition with an id" % path)
			continue
		if _definitions.has(definition.id):
			push_warning("AreaRouter: duplicate area id '%s'" % definition.id)
			continue
		_definitions[definition.id] = definition

## Asks for the player to go to `entry_id` in area `area_id`. Returns
## whether the request was accepted (a known area, and no travel already
## under way).
func travel(area_id: String, entry_id: String) -> bool:
	if _travelling:
		return false
	if not _definitions.has(area_id):
		push_warning("AreaRouter: unknown area '%s'" % area_id)
		return false
	_travelling = true
	travel_requested.emit(area_id, entry_id)
	return true

## Main, once the area `area_id` is the current one (also at boot).
func notify_arrived(area_id: String) -> void:
	_travelling = false
	if area_id == _current_area_id:
		return
	_current_area_id = area_id
	area_changed.emit(area_id)

## Main, when an accepted travel could not be carried out.
func notify_travel_failed() -> void:
	_travelling = false

func is_travelling() -> bool:
	return _travelling

func get_current_area_id() -> String:
	return _current_area_id

func get_definition(area_id: String) -> AreaDefinition:
	return _definitions.get(area_id) as AreaDefinition
