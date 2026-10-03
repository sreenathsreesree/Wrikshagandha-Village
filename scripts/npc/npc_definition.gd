extends Resource
class_name NpcDefinition

## Data for one NPC (M08.3): who it is and what it says. Add an NPC by
## creating another .tres in res://data/npcs/ and placing an Npc scene that
## points at it — no script changes. Where it stands is authored in the
## world (the scene/marker it is placed under), never here.

@export var id: String = ""
@export var display_name: String = ""
## The one line it says when the player talks to it (M08.3 — dialogue M08.4).
@export_multiline var greeting: String = ""
## How far (m) it may wander from where it was placed.
@export var wander_radius: float = 2.0
