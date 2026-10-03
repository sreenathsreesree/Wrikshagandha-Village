extends Interactable
class_name AreaDoor

## A way between areas (M08.1): an ordinary Interactable, reached and used
## like anything else in the world — tapped (or walked up to, then tapped),
## never by walking into it (D-35). Its one action asks AreaRouter for the
## trip; Main does the rest. Which area and entry it leads to, and whether
## it reads as going in or out, are set per door in the scene.

@export var target_area_id: String = ""
@export var target_entry_id: String = ""
## ENTER for a way in, EXIT for a way out — the only verbs a door offers.
@export var verb: Verb = Verb.ENTER

func _ready() -> void:
	remove_on_harvest = false

## Offered only while a trip could start: never mid-transition.
func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	if (verb == Verb.ENTER or verb == Verb.EXIT) and not AreaRouter.is_travelling():
		verbs.append(verb)
	return verbs

func interact() -> bool:
	if _get_interaction_verbs().is_empty():
		return false
	return AreaRouter.travel(target_area_id, target_entry_id)

func get_interaction_metadata() -> Dictionary:
	return {"target_area_id": target_area_id, "target_entry_id": target_entry_id}
