extends Resource
class_name WildlifeDefinition

## Data-driven definition for one wildlife species (M14.1a, D-59): what the
## Journal's "Wildlife" list shows once the player has seen one. Add a
## species by creating another .tres in res://data/wildlife/ and setting the
## same id as species_id on its creature scene — no script changes.
## JournalManager loads them all; nothing about a species lives in a script.

@export var id: String = ""
@export var display_name: String = ""
## The Journal's note, shown once the species has been seen.
@export_multiline var description: String = ""
## Position in the Journal's fixed "Wildlife" list (ascending, unique).
@export var order: int = 0
