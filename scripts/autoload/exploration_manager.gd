extends Node

## Rewards exploring broadly during a play session — not saved between
## sessions, and not tied to any specific item, so it never needs to know
## about rarity or category. Thresholds are data (a dictionary), not
## branching logic, so tuning them later is a one-line change.

signal exploration_bonus_awarded(threshold: int, bonus_points: int)

const THRESHOLDS := {3: 20, 5: 40}

var _session_discovery_count: int = 0
var _awarded_thresholds: Array[int] = []

func _ready() -> void:
	DiscoveryManager.discovery_made.connect(_on_discovery_made)

func _on_discovery_made(_definition: DiscoveryDefinition) -> void:
	_session_discovery_count += 1
	if not THRESHOLDS.has(_session_discovery_count):
		return
	if _awarded_thresholds.has(_session_discovery_count):
		return
	_awarded_thresholds.append(_session_discovery_count)
	var bonus: int = THRESHOLDS[_session_discovery_count]
	PointsManager.add_points(bonus)
	exploration_bonus_awarded.emit(_session_discovery_count, bonus)
