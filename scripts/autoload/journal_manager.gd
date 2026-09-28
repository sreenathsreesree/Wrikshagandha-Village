extends Node

## Records a permanent entry for every discovery the player has ever made —
## name, category, rarity, description, points earned, and whether it was
## the first time. Independent of DiscoveryManager (which only tracks *that*
## something was found); the Journal is what makes each discovery feel
## remembered rather than just counted.

signal entry_added(entry: Dictionary)

var _entries: Dictionary = {}

func _ready() -> void:
	DiscoveryManager.discovery_made.connect(_on_discovery_made)

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
