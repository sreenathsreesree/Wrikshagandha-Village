extends Interactable

## Verification fixture only — never game content. tools/ is ignored by
## Godot (tools/.gdignore), so this is never imported, placed or loaded.
## Something that can be read, on the generic Interactable contract alone,
## and the multi-verb proof: it offers INSPECT and READ at once. A tap
## (interact()) performs its default action, READ; a verb selected by some
## future UI comes back through Interactable.interact_with_verb(), and
## _perform_interaction_verb() picks the action. No lore or text — the
## response is a deterministic record (counters and the last verb).

var inspect_count: int = 0
var read_count: int = 0
## The last verb performed (a Verb value); 0 = nothing yet.
var last_action: int = 0

func _ready() -> void:
	remove_on_harvest = false

func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	verbs.append(Verb.INSPECT)
	verbs.append(Verb.READ)
	return verbs

func interact() -> bool:
	return _read()

func _perform_interaction_verb(verb: Verb) -> bool:
	if verb == Verb.INSPECT:
		return _inspect()
	return _read()

func _inspect() -> bool:
	inspect_count += 1
	last_action = Verb.INSPECT
	return true

func _read() -> bool:
	read_count += 1
	last_action = Verb.READ
	return true

func set_available(value: bool) -> void:
	monitorable = value
