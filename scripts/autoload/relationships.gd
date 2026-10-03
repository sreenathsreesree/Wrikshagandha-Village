extends Node

## Friendship with each NPC (M08.5, D-38): one whole number per NPC id
## (NpcDefinition.id — never a node), 0 until earned, at most
## MAX_FRIENDSHIP. A completed conversation (the speech panel's Goodbye)
## earns +1, at most once per calendar day per NPC — the same system date
## DailyDiscoveryManager uses; ending one early never counts. Kept here,
## outside any area, so it outlives the parked Meadow; only SaveManager
## saves and loads it, and GameState saves on friendship_changed. Nothing
## is shown to the player yet, and nothing reads it but the save.
##
## Saved as {npc_id: {"friendship": n, "last_gain_date": "YYYY-MM-DD"}} —
## the date is what keeps the once-a-day rule across a relaunch.

signal friendship_changed(npc_id: String, friendship: int)

const MAX_FRIENDSHIP := 10
const NPCS_PATH := "res://data/npcs/"

var _friendship: Dictionary = {}  # npc_id -> int (absent = 0)
var _last_gain_date: Dictionary = {}  # npc_id -> "YYYY-MM-DD" of the last +1
var _known_ids: PackedStringArray = PackedStringArray()

## The NPCs that exist are the NpcDefinitions in data/npcs/ — read once, so
## the save can be checked before any area (and its NPCs) is loaded.
## ResourceDirectory handles exported builds (".tres.remap" listings).
func _ready() -> void:
	for path in ResourceDirectory.list_tres_paths(NPCS_PATH):
		var definition := load(path) as NpcDefinition
		if definition != null and definition.id != "":
			_known_ids.append(definition.id)

## 0 for an NPC never befriended (or one that doesn't exist).
func get_friendship(npc_id: String) -> int:
	return int(_friendship.get(npc_id, 0))

## A conversation with `npc_id` was completed. +1 friendship unless it was
## already earned today or is at the maximum; an unknown id changes
## nothing. Returns whether friendship rose.
func record_completed_conversation(npc_id: String) -> bool:
	if not _known_ids.has(npc_id):
		push_warning("Relationships: no NPC '%s'; ignored" % npc_id)
		return false
	var today := _today_string()
	if _last_gain_date.get(npc_id, "") == today:
		return false
	var friendship := get_friendship(npc_id)
	if friendship >= MAX_FRIENDSHIP:
		return false
	_friendship[npc_id] = friendship + 1
	_last_gain_date[npc_id] = today
	friendship_changed.emit(npc_id, friendship + 1)
	return true

## For SaveManager only.
func get_save_data() -> Dictionary:
	var data := {}
	for npc_id: String in _friendship:
		data[npc_id] = {"friendship": _friendship[npc_id], "last_gain_date": _last_gain_date.get(npc_id, "")}
	return data

## For SaveManager, at boot. Announces nothing. Only known NPCs are kept;
## friendship is clamped to 0..MAX_FRIENDSHIP; anything malformed is
## dropped with a warning (that NPC starts at 0, or with no gain today).
func apply_save_data(data: Dictionary) -> void:
	_friendship.clear()
	_last_gain_date.clear()
	for npc_id: Variant in data:
		if typeof(npc_id) != TYPE_STRING or not _known_ids.has(npc_id):
			push_warning("Relationships: saved friendship for unknown NPC '%s'; dropped" % str(npc_id))
			continue
		var entry: Variant = data[npc_id]
		if typeof(entry) != TYPE_DICTIONARY:
			push_warning("Relationships: saved friendship for '%s' is not a record; dropped" % npc_id)
			continue
		var value: Variant = entry.get("friendship")
		if typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT:
			push_warning("Relationships: saved friendship for '%s' is not a number; dropped" % npc_id)
			continue
		_friendship[npc_id] = clampi(int(value), 0, MAX_FRIENDSHIP)
		var date: Variant = entry.get("last_gain_date", "")
		if typeof(date) == TYPE_STRING and (date == "" or _is_date(date)):
			_last_gain_date[npc_id] = date
		else:
			push_warning("Relationships: saved gain date for '%s' is malformed; ignored" % npc_id)
			_last_gain_date[npc_id] = ""

## The system date, as DailyDiscoveryManager reads it.
func _today_string() -> String:
	var d := Time.get_date_dict_from_system()
	return "%04d-%02d-%02d" % [d.year, d.month, d.day]

func _is_date(text: String) -> bool:
	return RegEx.create_from_string("^\\d{4}-\\d{2}-\\d{2}$").search(text) != null
