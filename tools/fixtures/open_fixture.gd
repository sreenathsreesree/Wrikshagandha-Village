extends Interactable

## Verification fixture only — never game content. tools/ is ignored by
## Godot (tools/.gdignore), so this is never imported, placed or loaded.
## Something that can be opened, on the generic Interactable contract
## alone: offers OPEN while closed and nothing once open (a verb list that
## follows the object's state). No door system — the response is a
## deterministic record (open or not, a counter and the last verb).

var is_open: bool = false
var open_count: int = 0
## The last verb performed (a Verb value); 0 = nothing yet.
var last_action: int = 0

func _ready() -> void:
	remove_on_harvest = false

func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	if not is_open:
		verbs.append(Verb.OPEN)
	return verbs

func interact() -> bool:
	if is_open:
		return false
	is_open = true
	open_count += 1
	last_action = Verb.OPEN
	return true

func set_available(value: bool) -> void:
	monitorable = value
