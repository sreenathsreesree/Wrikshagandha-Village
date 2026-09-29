extends Node

## Local, offline "Today's Discovery" — deterministically picks one target
## discovery per calendar day (device clock only, no network) and awards a
## one-time bonus the first time the player finds it that day. Architecture
## is ready for a future backend to supply the target instead; only
## _pick_target_for_date() would need to change. The bonus is reward data
## ("daily_discovery", M05.3). A once-ever discovery already claimed (M05.3,
## D-22) is never today's target: the next one in order is taken instead,
## so every other day's target is unchanged.

signal daily_completed(definition: DiscoveryDefinition, bonus_points: int)

var target_id: String = ""
var target_date: String = ""
var completed_date: String = ""
var _bonus_points: int = 0

func _ready() -> void:
	_bonus_points = RewardRules.new().points("daily_discovery")
	_ensure_today_target()
	# A repeat harvest of today's target still completes it — first-time
	# vs repeat only matters for Journal/Collection/session-exploration.
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	DiscoveryManager.discovery_repeated.connect(_on_discovery_made)

## The points today's discovery pays (reward data).
func get_bonus_points() -> int:
	return _bonus_points

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
	if target_date == today and target_id != "" and not DiscoveryManager.is_claimed(target_id):
		return
	var definitions := DiscoveryDatabase.get_all_definitions()
	if definitions.is_empty():
		return
	var index := absi(_pick_target_for_date(today)) % definitions.size()
	for step in definitions.size():
		var candidate: DiscoveryDefinition = definitions[(index + step) % definitions.size()]
		if not DiscoveryManager.is_claimed(candidate.id):
			target_id = candidate.id
			target_date = today
			return

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
	PointsManager.add_points(_bonus_points)
	daily_completed.emit(definition, _bonus_points)
