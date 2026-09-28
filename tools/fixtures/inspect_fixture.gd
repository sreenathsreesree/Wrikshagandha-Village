extends Interactable

## Verification fixture only — never game content. tools/ is ignored by
## Godot (tools/.gdignore), so this is never imported, placed or loaded.
## Something that can be inspected, on the generic Interactable contract
## alone: offers INSPECT, persistent, inspectable again and again. The
## response is a deterministic record (a counter and the last verb), no UI.

var inspect_count: int = 0
## The last verb performed (a Verb value); 0 = nothing yet.
var last_action: int = 0

func _ready() -> void:
	remove_on_harvest = false

func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	verbs.append(Verb.INSPECT)
	return verbs

func interact() -> bool:
	inspect_count += 1
	last_action = Verb.INSPECT
	return true

func set_available(value: bool) -> void:
	monitorable = value
