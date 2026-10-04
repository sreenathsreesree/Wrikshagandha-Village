extends Resource
class_name NpcDefinition

## Data for one NPC (M08.3): who it is and what it says. Add an NPC by
## creating another .tres in res://data/npcs/ and placing an Npc scene that
## points at it — no script changes. Where it stands is authored in the
## world (the scene/marker it is placed under), never here.

@export var id: String = ""
@export var display_name: String = ""
## What it says when the player talks to it (M08.4: a short sequence of
## lines, res://data/dialogues/).
@export var dialogue: DialogueDefinition
## How far (m) it may wander from where it was placed (from its current
## routine spot, M09.1).
@export var wander_radius: float = 2.0
## Its daily routine (M09.1, D-41): time-of-day phase -> the spot_id of an
## NpcRoutineSpot in its area. Empty = it stays where it was placed.
@export var routine: Dictionary = {}
