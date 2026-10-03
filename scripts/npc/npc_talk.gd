extends Interactable
class_name NpcTalk

## How the player talks to an NPC (M08.3): an ordinary Interactable on the
## Npc — tapped, walked to and interacted with like anything else; Player
## and InputManager know nothing about NPCs. It offers TALK while its NPC
## has something to say; interact() starts the NPC's dialogue (its
## NpcDefinition's DialogueDefinition, M08.4) in the HUD's SpeechPanel,
## which keeps the conversation's state. Walking out of range closes it,
## the same way a farm plot closes its seed picker.

var _panel: SpeechPanel

func _ready() -> void:
	remove_on_harvest = false

func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	if not _lines().is_empty():
		verbs.append(Verb.TALK)
	return verbs

func interact() -> bool:
	if _get_interaction_verbs().is_empty():
		return false
	_panel = get_tree().get_first_node_in_group(SpeechPanel.GROUP) as SpeechPanel
	if _panel == null:
		return false
	var npc := get_parent() as Npc
	return _panel.open(self, npc.definition.display_name, npc.definition.dialogue.lines)

func set_highlighted(active: bool) -> void:
	super(active)
	if not active and _panel != null:
		_panel.close_for(self)

func _lines() -> PackedStringArray:
	var npc := get_parent() as Npc
	if npc == null or npc.definition == null or npc.definition.dialogue == null:
		return PackedStringArray()
	return npc.definition.dialogue.lines
