extends Resource
class_name MemoryDefinition

## Data-driven definition for one player memory (M14.1, D-71): a moment the
## player has already lived, which the Journal's "Memories" list shows once a
## record the game already saves proves it. A memory is never stored: it is
## derived from that record each time the Journal asks
## (JournalManager.get_memories()), so it needs no save section, pays nothing
## and announces nothing. Add one by creating another .tres in
## res://data/memories/ naming its record and the id in it — no script
## changes.

## The saved records a memory can rest on — each kept once ever by its owner:
## FarmManager's milestones reached (save "farm", "milestones").
const FARM_MILESTONE := "farm_milestone"
## ExplorationManager's secret places found (save "exploration", "secrets").
const SECRET_PLACE := "secret_place"
## JournalManager's species seen (save "wildlife_sightings").
const WILDLIFE := "wildlife"

@export var id: String = ""
## One plain line in the past tense: what happened, nothing more.
@export var text: String = ""
## Position in the Journal's "Memories" list (ascending, unique) — a fixed
## order, never a claim about which moment came first.
@export var order: int = 0
## The record that proves it: one of the constants above.
@export var record: String = ""
## The id that must be in that record. Empty only for SECRET_PLACE, where it
## means any secret place found.
@export var fact_id: String = ""
