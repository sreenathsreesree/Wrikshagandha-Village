extends Node

## Rewards exploring broadly during a play session — not saved between
## sessions, and not tied to any specific item, so it never needs to know
## about rarity or category beyond the "is this rare?" check below.
## Thresholds/places/pairs are data (dictionaries/arrays), not branching
## logic, so tuning them later is a one-line change.
##
## Everything here is deliberately calm, not an XP/level system: most
## signals carry no points at all (first discovery, first rare find) and
## the ones that do are small, one-time-per-session flats — recognition
## that something happened, not a score to grind.
##
## "Places" (get_places_progress()) is the small session-only "Exploration
## Memory" the Journal screen reads from: a fixed, ordered list of named
## locations, each simply visited-or-not this session. It reuses the same
## _reached_landmarks/_found_secret_locations bookkeeping already needed
## for landmark_reached/secret_location_found, so there's no separate
## place-tracking system underneath it.

signal exploration_bonus_awarded(threshold: int, bonus_points: int)
signal landmark_reached(landmark_id: String, bonus_points: int)
signal secret_location_found(location_id: String, bonus_points: int)
signal first_discovery_noted
signal rare_discovery_noted(definition: DiscoveryDefinition)
signal all_secret_locations_found(bonus_points: int)
signal curiosity_bonus_awarded(location_id: String, bonus_points: int)
signal session_summary_ready(summary: Dictionary)

const THRESHOLDS := {3: 20, 5: 40}
const LANDMARK_BONUS := 15
const SECRET_LOCATION_BONUS := 15
const ALL_SECRET_LOCATIONS_BONUS := 50
const CURIOSITY_BONUS := 20
const RARE_RARITIES := ["rare", "very_rare", "legendary"]

## The full "Exploration Memory" — fixed order, each id resolved through
## has_reached_landmark()/has_found_secret_location() so the underlying
## bookkeeping stays in one place. Undiscovered places stay "???" in the UI.
const PLACES := [
	{"id": "overlook", "display_name": "Overlook"},
	{"id": "wildflower_clearing", "display_name": "Wildflower Clearing"},
	{"id": "ancient_grove", "display_name": "Ancient Grove"},
	{"id": "stone_ring", "display_name": "Stone Ring"},
	{"id": "secluded_pond_nook", "display_name": "Secluded Pond Nook"},
	{"id": "mystery_grove_tree", "display_name": "Mystery Grove Tree"},
	{"id": "hidden_flower_pocket", "display_name": "Hidden Flower Pocket"},
]

## A secret location paired with the "intended" discovery near it. If the
## player reaches the location before finding that discovery, they found
## it out of curiosity rather than by following the obvious route to the
## item itself — worth a small one-time nod. Not every secret location
## has a natural pairing, and that's fine; only these two do.
const CURIOSITY_PAIRS := {
	"secluded_pond_nook": "river_stone",
	"mystery_grove_tree": "golden_leaf",
}

var _session_discovery_count: int = 0
var _session_rare_discovery_count: int = 0
var _awarded_thresholds: Array[int] = []
var _reached_landmarks: Array[String] = []
var _found_secret_locations: Array[String] = []
var _first_discovery_announced: bool = false
var _rare_discovery_announced: bool = false
var _all_secrets_bonus_awarded: bool = false
var _curiosity_bonus_given: bool = false
var _summary_shown: bool = false

func _ready() -> void:
	DiscoveryManager.discovery_made.connect(_on_discovery_made)

func _on_discovery_made(definition: DiscoveryDefinition) -> void:
	_session_discovery_count += 1

	if not _first_discovery_announced:
		_first_discovery_announced = true
		first_discovery_noted.emit()

	if RARE_RARITIES.has(definition.rarity):
		_session_rare_discovery_count += 1
		if not _rare_discovery_announced:
			_rare_discovery_announced = true
			rare_discovery_noted.emit(definition)

	if THRESHOLDS.has(_session_discovery_count) and not _awarded_thresholds.has(_session_discovery_count):
		_awarded_thresholds.append(_session_discovery_count)
		var bonus: int = THRESHOLDS[_session_discovery_count]
		PointsManager.add_points(bonus)
		exploration_bonus_awarded.emit(_session_discovery_count, bonus)
		if _session_discovery_count == 5:
			_show_session_summary()

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

	_maybe_award_curiosity_bonus(location_id)

	if _found_secret_locations.size() >= 4 and not _all_secrets_bonus_awarded:
		_all_secrets_bonus_awarded = true
		PointsManager.add_points(ALL_SECRET_LOCATIONS_BONUS)
		all_secret_locations_found.emit(ALL_SECRET_LOCATIONS_BONUS)

## Rewards exploration *order*, not grinding: reaching this secret spot
## before the nearby discovery it's paired with means the player found it
## out of curiosity, not by following the item's own trail. Fires at most
## once per session, whichever qualifying location gets there first.
func _maybe_award_curiosity_bonus(location_id: String) -> void:
	if _curiosity_bonus_given:
		return
	var paired_discovery_id: String = CURIOSITY_PAIRS.get(location_id, "")
	if paired_discovery_id == "" or DiscoveryManager.is_discovered(paired_discovery_id):
		return
	_curiosity_bonus_given = true
	PointsManager.add_points(CURIOSITY_BONUS)
	curiosity_bonus_awarded.emit(location_id, CURIOSITY_BONUS)

## One row per PLACES entry, in a fixed order, with the caller deciding
## how to render "not visited yet" (the Journal screen shows "???").
func get_places_progress() -> Array:
	var rows: Array = []
	for place: Dictionary in PLACES:
		rows.append({
			"id": place.id,
			"display_name": place.display_name,
			"visited": _is_place_visited(place.id),
		})
	return rows

func get_visited_place_count() -> int:
	var count := 0
	for place: Dictionary in PLACES:
		if _is_place_visited(place.id):
			count += 1
	return count

func _is_place_visited(place_id: String) -> bool:
	return _reached_landmarks.has(place_id) or _found_secret_locations.has(place_id)

func get_session_summary() -> Dictionary:
	return {
		"discoveries": _session_discovery_count,
		"places_explored": get_visited_place_count(),
		"rare_discoveries": _session_rare_discovery_count,
		"secret_locations_found": _found_secret_locations.size(),
	}

func _show_session_summary() -> void:
	if _summary_shown:
		return
	_summary_shown = true
	session_summary_ready.emit(get_session_summary())
