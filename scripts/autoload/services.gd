extends Node

## NPC services (M08.7, D-40): repeatable trades of a collectible for coins.
## Services are data (ServiceDefinition, res://data/services/); this holds
## no state of its own and saves nothing — it only reads the Inventory and
## Requests to choose a conversation, and hands a finished trade to the
## Market, which alone moves the items and the coins. A service exists for
## the player only once its unlocking request is completed.
##
## NpcTalk asks conversation_for() (after its request, which comes first):
## nothing while locked; the pitch while the player holds fewer than the
## service's quantity; the trade (last button "Sell") once they hold
## enough. A completed trade conversation calls trade(); ending it early
## never does. A service whose item is not a single-quality collectible,
## or with anything else invalid, is ignored with a warning.

const SERVICES_PATH := "res://data/services/"
const NPCS_PATH := "res://data/npcs/"
const STEP_PITCH := "pitch"
const STEP_TRADE := "trade"
const MAX_QUANTITY := 9

var _definitions: Dictionary = {}  # service_id -> ServiceDefinition (valid ones only)

## Reads the services in data/services/ once, keeping only valid ones.
## ResourceDirectory handles exported builds.
func _ready() -> void:
	var npc_ids: PackedStringArray = PackedStringArray()
	for path in ResourceDirectory.list_tres_paths(NPCS_PATH):
		var npc := load(path) as NpcDefinition
		if npc != null and npc.id != "":
			npc_ids.append(npc.id)
	for path in ResourceDirectory.list_tres_paths(SERVICES_PATH):
		var definition := load(path) as ServiceDefinition
		if not _is_valid(definition, npc_ids):
			push_warning("Services: %s is not a valid service; ignored" % path)
			continue
		_definitions[definition.id] = definition

## The conversation an NPC's service calls for now, or {} (none, or still
## locked): {"service_id", "step" (STEP_*), "lines"}.
func conversation_for(npc_id: String) -> Dictionary:
	for service_id: String in _definitions:
		var definition: ServiceDefinition = _definitions[service_id]
		if definition.npc_id != npc_id or not _is_unlocked(definition):
			continue
		if Inventory.has(definition.item_id, definition.quantity, 0):
			return {"service_id": service_id, "step": STEP_TRADE, "lines": definition.trade_dialogue.lines}
		return {"service_id": service_id, "step": STEP_PITCH, "lines": definition.pitch_dialogue.lines}
	return {}

## The trade conversation was completed (Sell). The Market does the trade;
## returns the coins paid, or 0 if nothing happened.
func trade(service_id: String) -> int:
	var definition: ServiceDefinition = _definitions.get(service_id)
	if definition == null or not _is_unlocked(definition):
		return 0
	return Market.trade(definition.item_id, definition.quantity, definition.coins, definition.id)

func _is_unlocked(definition: ServiceDefinition) -> bool:
	return Requests.get_state(definition.unlocked_by_request) == Requests.COMPLETED

func _is_valid(definition: ServiceDefinition, npc_ids: PackedStringArray) -> bool:
	if definition == null or definition.id == "" or not npc_ids.has(definition.npc_id) or definition.unlocked_by_request == "":
		return false
	var item := Inventory.get_definition(definition.item_id)
	if item == null or item.category != "collectible" or item.quality_levels != 1:
		return false
	if definition.quantity < 1 or definition.quantity > MAX_QUANTITY or definition.coins < 1:
		return false
	for dialogue: DialogueDefinition in [definition.pitch_dialogue, definition.trade_dialogue]:
		if dialogue == null or dialogue.lines.is_empty():
			return false
	return not _definitions.has(definition.id)
