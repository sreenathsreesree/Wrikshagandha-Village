extends Node

## Records a permanent entry for every discovery the player has ever made —
## name, category, rarity, description, points earned, and whether it was
## the first time. Independent of DiscoveryManager (which only tracks *that*
## something was found); the Journal is what makes each discovery feel
## remembered rather than just counted.

## Wildlife Journal (M14.1a, D-59): the species in WILDLIFE_PATH and which of
## them the player has seen — once ever, the first time a creature of that
## species has the player within its alert distance (WildlifeController
## relays it). A sighting is only remembered: it pays no points, coins or
## items. Saved as its own section, "wildlife_sightings" (save v9).

signal entry_added(entry: Dictionary)
## A species seen for the first time ever (never again for that species).
signal wildlife_sighted(species_id: String)

const WILDLIFE_PATH := "res://data/wildlife/"

var _entries: Dictionary = {}
## WildlifeDefinition resources, in their Journal order.
var _species: Array = []
## Ids of the species seen, in the order first seen.
var _sighted_species: Array = []

func _ready() -> void:
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	_load_species()

func _on_discovery_made(definition: DiscoveryDefinition) -> void:
	var entry := {
		"id": definition.id,
		"name": definition.display_name,
		"category": definition.category,
		"rarity": definition.rarity,
		"description": definition.description,
		"points_earned": definition.points_value,
		"first_discovery": not _entries.has(definition.id),
	}
	_entries[definition.id] = entry
	entry_added.emit(entry)

func get_entries() -> Array:
	return _entries.values()

func get_entry(id: String) -> Dictionary:
	return _entries.get(id, {})

func has_entry(id: String) -> bool:
	return _entries.has(id)

func get_save_data() -> Dictionary:
	return _entries.duplicate(true)

func apply_save_data(data: Dictionary) -> void:
	_entries = data.duplicate(true)

func _load_species() -> void:
	_species.clear()
	for path in ResourceDirectory.list_tres_paths(WILDLIFE_PATH):
		var resource: Resource = load(path)
		if resource is WildlifeDefinition and (resource as WildlifeDefinition).id != "":
			_species.append(resource)
		else:
			push_warning("JournalManager: %s is not a wildlife definition with an id" % path)
	_species.sort_custom(func(a: WildlifeDefinition, b: WildlifeDefinition) -> bool: return a.order < b.order)

## Records a known species the first time it is seen; false (and nothing
## happens) for one already seen or not in the wildlife data.
func record_sighting(species_id: String) -> bool:
	if _sighted_species.has(species_id) or get_species(species_id) == null:
		return false
	_sighted_species.append(species_id)
	wildlife_sighted.emit(species_id)
	return true

func has_sighted(species_id: String) -> bool:
	return _sighted_species.has(species_id)

func get_sighted_ids() -> Array:
	return _sighted_species.duplicate()

## Every species, in Journal order, seen or not.
func get_all_species() -> Array:
	return _species.duplicate()

func get_species(species_id: String) -> WildlifeDefinition:
	for definition: WildlifeDefinition in _species:
		if definition.id == species_id:
			return definition
	return null

func get_sightings_save_data() -> Array:
	return _sighted_species.duplicate()

## Each id once, strings only. An id no longer in the data is kept (and
## saved again), so a species removed and later restored is still seen.
func apply_sightings_save_data(data: Array) -> void:
	_sighted_species = []
	for value: Variant in data:
		if typeof(value) == TYPE_STRING and not _sighted_species.has(value):
			_sighted_species.append(value)
