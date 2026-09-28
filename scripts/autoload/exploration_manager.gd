extends Node

## Rewards exploring broadly during a play session — not saved between
## sessions, and not tied to any specific item, so it never needs to know
## about rarity or category. Thresholds are data (a dictionary), not
## branching logic, so tuning them later is a one-line change.
##
## Also tracks two lighter, one-time-per-session touches that previously
## had no reward at all: simply reaching a landmark (e.g. the Overlook)
## and simply finding one of the secret micro-locations (e.g. the Stone
## Ring) — walking there and looking around was already the point, this
## just acknowledges it happened. Both are driven by ExplorationLandmark
## markers placed in the world and checked by ExplorationLandmarkController,
## the same "small controller does the distance check" shape already used
## for wildlife and environmental events.

signal exploration_bonus_awarded(threshold: int, bonus_points: int)
signal landmark_reached(landmark_id: String, bonus_points: int)
signal secret_location_found(location_id: String, bonus_points: int)

const THRESHOLDS := {3: 20, 5: 40}
const LANDMARK_BONUS := 15
const SECRET_LOCATION_BONUS := 15

var _session_discovery_count: int = 0
var _awarded_thresholds: Array[int] = []
var _reached_landmarks: Array[String] = []
var _found_secret_locations: Array[String] = []

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

func has_reached_landmark(landmark_id: String) -> bool:
	return _reached_landmarks.has(landmark_id)

func mark_landmark_reached(landmark_id: String) -> void:
	if _reached_landmarks.has(landmark_id):
		return
	_reached_landmarks.append(landmark_id)
	PointsManager.add_points(LANDMARK_BONUS)
	landmark_reached.emit(landmark_id, LANDMARK_BONUS)

func has_found_secret_location(location_id: String) -> bool:
	return _found_secret_locations.has(location_id)

func mark_secret_location_found(location_id: String) -> void:
	if _found_secret_locations.has(location_id):
		return
	_found_secret_locations.append(location_id)
	PointsManager.add_points(SECRET_LOCATION_BONUS)
	secret_location_found.emit(location_id, SECRET_LOCATION_BONUS)
