extends Resource
class_name DialogueDefinition

## One conversation as data (M08.4): the lines an NPC says, in order — the
## player steps through them with the speech panel's Next and ends on the
## last. No branches, conditions or outcomes yet; an NPC refers to its
## dialogue from its NpcDefinition, so a later milestone can choose between
## dialogues without changing how one is shown. Add one by creating another
## .tres in res://data/dialogues/.

@export var id: String = ""
@export_multiline var lines: PackedStringArray = PackedStringArray()
