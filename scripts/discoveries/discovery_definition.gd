extends Resource
class_name DiscoveryDefinition

## Data-driven definition for one discoverable thing (plant, flower, fungus,
## mineral, insect, animal, mystery...). Add new content by creating another
## .tres resource in res://data/discoveries/ — no gameplay code changes
## required. Rarity and respawn behavior live here too, so nothing about a
## specific item is ever hardcoded into gameplay scripts.

@export var id: String = ""
@export var display_name: String = ""
@export_multiline var description: String = ""
@export_enum("plant", "flower", "fungus", "mineral", "insect", "animal", "mystery") var category: String = "plant"
@export_enum("common", "uncommon", "rare", "very_rare", "legendary") var rarity: String = "common"
@export var points_value: int = 10
@export var harvestable: bool = true

## Seconds before a harvested instance of this discovery respawns in the
## world. 0 means it never respawns automatically (used for legendary finds
## that should stay unavailable until a future, separate condition unlocks
## them again).
@export var respawn_seconds: float = 60.0
## The Five Elements id (data/elements/, M11.0, D-46) this belongs to; empty = none.
## Schema only: nothing reads it yet.
@export var element_id: String = ""
