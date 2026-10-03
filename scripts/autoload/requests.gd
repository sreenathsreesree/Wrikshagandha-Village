extends Node

## NPC requests (M08.6, D-39): an NPC has a problem, the player finds what
## solves it and brings it back — no quest log, tracker or marker. Requests
## are data (RequestDefinition, res://data/requests/); this keeps only each
## request's state, outside any area, so it outlives the parked Meadow:
## absent = not offered yet, ACCEPTED, COMPLETED (final). Only SaveManager
## saves and loads it; GameState saves on request_accepted and
## request_completed. NpcTalk asks conversation_for() which whole
## conversation to open and reports how it ended: a completed offer accepts,
## a completed hand-over completes. Ending one early never does either.
##
## Completing is checked, recorded, then paid: accepted → the items held →
## the items removed (all or nothing) → COMPLETED → reward_points paid once
## → announced (the save follows). A request whose item has more than one
## quality level, or with anything else invalid, is ignored with a warning.

signal request_accepted(request_id: String)
signal request_completed(request_id: String, item_id: String, quantity: int, points: int)

const REQUESTS_PATH := "res://data/requests/"
const NPCS_PATH := "res://data/npcs/"
const ACCEPTED := "accepted"
const COMPLETED := "completed"
const STEP_OFFER := "offer"
const STEP_PENDING := "pending"
const STEP_HANDOVER := "handover"
const MAX_QUANTITY := 9

var _definitions: Dictionary = {}  # request_id -> RequestDefinition (valid ones only)
var _states: Dictionary = {}  # request_id -> ACCEPTED / COMPLETED (absent = not offered)

## Reads the requests in data/requests/ once, keeping only valid ones (at
## most one per NPC). ResourceDirectory handles exported builds.
func _ready() -> void:
	var npc_ids: PackedStringArray = PackedStringArray()
	for path in ResourceDirectory.list_tres_paths(NPCS_PATH):
		var npc := load(path) as NpcDefinition
		if npc != null and npc.id != "":
			npc_ids.append(npc.id)
	for path in ResourceDirectory.list_tres_paths(REQUESTS_PATH):
		var definition := load(path) as RequestDefinition
		if not _is_valid(definition, npc_ids):
			push_warning("Requests: %s is not a valid request; ignored" % path)
			continue
		_definitions[definition.id] = definition

## The conversation an NPC's request calls for now, or {} (no request, or
## it is completed): {"request_id", "step" (STEP_*), "lines"}.
func conversation_for(npc_id: String) -> Dictionary:
	for request_id: String in _definitions:
		var definition: RequestDefinition = _definitions[request_id]
		if definition.npc_id != npc_id:
			continue
		var state: String = _states.get(request_id, "")
		if state == "":
			return {"request_id": request_id, "step": STEP_OFFER, "lines": definition.offer_dialogue.lines}
		if state == ACCEPTED:
			if Inventory.has(definition.item_id, definition.quantity, 0):
				return {"request_id": request_id, "step": STEP_HANDOVER, "lines": definition.handover_dialogue.lines}
			return {"request_id": request_id, "step": STEP_PENDING, "lines": definition.pending_dialogue.lines}
	return {}

## "" (not offered), ACCEPTED or COMPLETED.
func get_state(request_id: String) -> String:
	return _states.get(request_id, "")

## The offer was heard to the end. Returns whether it is now accepted.
func accept(request_id: String) -> bool:
	if not _definitions.has(request_id) or _states.has(request_id):
		return false
	_states[request_id] = ACCEPTED
	request_accepted.emit(request_id)
	return true

## The hand-over was completed (Give). Returns whether the request is now
## completed — never twice, never without the items.
func complete(request_id: String) -> bool:
	var definition: RequestDefinition = _definitions.get(request_id)
	if definition == null or _states.get(request_id, "") != ACCEPTED:
		return false
	if not Inventory.has(definition.item_id, definition.quantity, 0):
		return false
	if not Inventory.remove(definition.item_id, definition.quantity, 0):
		return false
	_states[request_id] = COMPLETED
	PointsManager.add_points(definition.reward_points)
	request_completed.emit(request_id, definition.item_id, definition.quantity, definition.reward_points)
	return true

## For SaveManager only: {request_id: ACCEPTED / COMPLETED}.
func get_save_data() -> Dictionary:
	return _states.duplicate()

## For SaveManager, at boot. Announces and pays nothing. Unknown request
## ids are dropped with a warning; a malformed state for a known request
## counts as completed, so its reward can never be paid twice (as a
## malformed exploration bonus counts as paid, D-21).
func apply_save_data(data: Dictionary) -> void:
	_states.clear()
	for request_id: Variant in data:
		if typeof(request_id) != TYPE_STRING or not _definitions.has(request_id):
			push_warning("Requests: saved state for unknown request '%s'; dropped" % str(request_id))
			continue
		var state: Variant = data[request_id]
		if typeof(state) == TYPE_STRING and (state == ACCEPTED or state == COMPLETED):
			_states[request_id] = state
		else:
			push_warning("Requests: saved state for '%s' is malformed; counts as completed" % request_id)
			_states[request_id] = COMPLETED

func _is_valid(definition: RequestDefinition, npc_ids: PackedStringArray) -> bool:
	if definition == null or definition.id == "" or not npc_ids.has(definition.npc_id):
		return false
	var item := Inventory.get_definition(definition.item_id)
	if item == null or item.quality_levels != 1:
		return false
	if definition.quantity < 1 or definition.quantity > MAX_QUANTITY or definition.reward_points < 1:
		return false
	for dialogue: DialogueDefinition in [definition.offer_dialogue, definition.pending_dialogue, definition.handover_dialogue]:
		if dialogue == null or dialogue.lines.is_empty():
			return false
	for other: RequestDefinition in _definitions.values():
		if other.npc_id == definition.npc_id or other.id == definition.id:
			return false
	return true
