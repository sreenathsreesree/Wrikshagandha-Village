extends Marker3D
class_name NpcRoutineSpot

## Where an NPC spends part of the day (M09.1, D-41): its NpcDefinition's
## routine names a spot_id for each time-of-day phase, and the NPC wanders
## around that spot while the phase lasts. Data only: the marker sits on
## walkable ground clear of solid objects and doors; nothing else reads it.
## Ids are stable, lower_snake_case, unique within their area and never
## derived from node names or tree order. Not a rest or scenic spot — those
## are a later, separate world-experience milestone.

const GROUP := &"npc_routine_spot"

@export var spot_id: String = ""

func _enter_tree() -> void:
	add_to_group(GROUP)
