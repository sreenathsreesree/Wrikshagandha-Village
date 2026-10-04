extends Interactable
class_name NpcTalk

## How the player talks to an NPC (M08.3): an ordinary Interactable on the
## Npc — tapped, walked to and interacted with like anything else; Player
## and InputManager know nothing about NPCs. It offers TALK while its NPC
## has something to say; interact() starts the NPC's dialogue (its
## NpcDefinition's DialogueDefinition, M08.4) in the HUD's SpeechPanel,
## which keeps the conversation's state. Walking out of range closes it,
## the same way a farm plot closes its seed picker. A conversation of its
## own that ends completed (Goodbye) is reported to Relationships by the
## NPC's id (M08.5); one ended early never is.
##
## Requests (M08.6): if the NPC has a request, Requests chooses which whole
## conversation to open — the offer, the pending reminder or the hand-over
## (whose last button reads "Give") — otherwise its usual dialogue. The
## choice is locked while that conversation is open; a completed offer
## accepts the request, a completed hand-over completes it.
##
## Services (M08.7): with no unfinished request, Services may choose the
## NPC's service conversation — the pitch, or the trade (whose last button
## reads "Sell"); a completed trade sells through Services and the Market.
## NpcTalk itself never touches the Inventory or the Wallet.

const GIVE_TEXT := "Give"
const SELL_TEXT := "Sell"

var _panel: SpeechPanel
var _request_id: String = ""
var _request_step: String = ""
var _service_id: String = ""
var _service_step: String = ""

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
	if not _panel.conversation_ended.is_connected(_on_conversation_ended):
		_panel.conversation_ended.connect(_on_conversation_ended)
	if _panel.get_speaker() == self and _panel.visible:
		return true
	var npc := get_parent() as Npc
	var request := Requests.conversation_for(npc.definition.id)
	_request_id = request.get("request_id", "")
	_request_step = request.get("step", "")
	_service_id = ""
	_service_step = ""
	if not request.is_empty():
		var end_text := GIVE_TEXT if _request_step == Requests.STEP_HANDOVER else SpeechPanel.END_TEXT
		return _panel.open(self, npc.definition.display_name, request.lines, end_text)
	var service := Services.conversation_for(npc.definition.id)
	_service_id = service.get("service_id", "")
	_service_step = service.get("step", "")
	if not service.is_empty():
		var sell_text := SELL_TEXT if _service_step == Services.STEP_TRADE else SpeechPanel.END_TEXT
		return _panel.open(self, npc.definition.display_name, service.lines, sell_text)
	return _panel.open(self, npc.definition.display_name, npc.definition.dialogue.lines)

func set_highlighted(active: bool) -> void:
	super(active)
	if not active and _panel != null:
		_panel.close_for(self)

func _on_conversation_ended(speaker: Node, completed: bool) -> void:
	if speaker != self:
		return
	var request_id := _request_id
	var step := _request_step
	var service_id := _service_id
	var service_step := _service_step
	_request_id = ""
	_request_step = ""
	_service_id = ""
	_service_step = ""
	if not completed:
		return
	if step == Requests.STEP_OFFER:
		Requests.accept(request_id)
	elif step == Requests.STEP_HANDOVER:
		Requests.complete(request_id)
	elif service_step == Services.STEP_TRADE:
		Services.trade(service_id)
	var npc := get_parent() as Npc
	if npc != null and npc.definition != null:
		Relationships.record_completed_conversation(npc.definition.id)

func _lines() -> PackedStringArray:
	var npc := get_parent() as Npc
	if npc == null or npc.definition == null or npc.definition.dialogue == null:
		return PackedStringArray()
	return npc.definition.dialogue.lines
