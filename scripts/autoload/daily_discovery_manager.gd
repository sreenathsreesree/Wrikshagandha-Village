extends Node

## Local, offline "Today's Discovery" — deterministically picks one target
## discovery per calendar day (device clock only, no network) and awards a
## one-time bonus the first time the player finds it that day. Architecture
## is ready for a future backend to supply the target instead; only
## _pick_target_for_date() would need to change.

signal daily_completed(definition: DiscoveryDefinition, bonus_points: int)

const BONUS_POINTS := 25

var target_id: String = ""
var target_date: String = ""
var completed_date: String = ""

func _ready() -> void:
	_ensure_today_target()
	# A repeat harvest of today's target still completes it — first-time
	# vs repeat only matters for Journal/Collection/session-exploration.
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	DiscoveryManager.discovery_repeated.connect(_on_discovery_made)

func is_completed_today() -> bool:
	return completed_date == _today_string()

func get_target_definition() -> DiscoveryDefinition:
	return DiscoveryDatabase.get_definition(target_id)

func get_save_data() -> Dictionary:
	return {
		"target_id": target_id,
		"target_date": target_date,
		"completed_date": completed_date,
	}

func apply_save_data(data: Dictionary) -> void:
	target_id = String(data.get("target_id", ""))
	target_date = String(data.get("target_date", ""))
	completed_date = String(data.get("completed_date", ""))
	_ensure_today_target()

func _ensure_today_target() -> void:
	var today := _today_string()
	if target_date == today and target_id != "":
		return
	var definitions := DiscoveryDatabase.get_all_definitions()
	if definitions.is_empty():
		return
	var index := absi(_pick_target_for_date(today)) % definitions.size()
	target_id = definitions[index].id
	target_date = today

## Deterministic per-day index seed. Swapping this for a server-provided
## value later needs no other changes to this script.
func _pick_target_for_date(date_string: String) -> int:
	return date_string.hash()

func _today_string() -> String:
	var d := Time.get_date_dict_from_system()
	return "%04d-%02d-%02d" % [d.year, d.month, d.day]

func _on_discovery_made(definition: DiscoveryDefinition) -> void:
	if is_completed_today():
		return
	if definition.id != target_id:
		return
	completed_date = _today_string()
	PointsManager.add_points(BONUS_POINTS)
	daily_completed.emit(definition, BONUS_POINTS)
