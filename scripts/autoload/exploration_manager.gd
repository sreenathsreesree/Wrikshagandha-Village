extends Node

## Rewards exploring — not tied to any specific item, so it never needs to
## know about rarity or category beyond the "is this rare?" check below.
##
## Saved (M05.2, P-02, D-21): which places were reached and which secret
## places found, and whether the "every secret found" and curiosity bonuses
## were paid — each of those rewards is once ever, so a relaunch never pays
## them again. Session-only, as before: the discovery-count thresholds
## (they count first-ever discoveries, which are themselves saved, so they
## are bounded), the first/rare discovery beats and the session summary.
## Every bonus amount and the discovery-count thresholds are reward data
## (data/rewards/, M05.3), not constants; places — their
## names, order, secret/garden roles and curiosity pairings — are
## PlaceDefinition resources in res://data/places/ (M03.6), never script
## constants.
##
## Everything here is deliberately calm, not an XP/level system: most
## signals carry no points at all (first discovery, first rare find) and
## the ones that do are small, one-time flats — recognition that something
## happened, not a score to grind.
##
## "Places" (get_places_progress()) is the small "Exploration Memory" the
## Journal screen reads from: a fixed, ordered list of named locations,
## each simply visited-or-not (ever, since M05.2). It reuses the same
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

const RARE_RARITIES := ["rare", "very_rare", "legendary"]

## Where the place definitions live (the Journal's "Places" list, arrival
## names, curiosity pairings, which places are secrets, which is the garden).
## Loaded once at startup, ordered by PlaceDefinition.order.
const PLACES_PATH := "res://data/places/"

var _places: Array[PlaceDefinition] = []
## Reward amounts (M05.3): {count: points} for the discovery-count
## thresholds; the session summary shows at the highest one.
var _rewards: RewardRules
var _thresholds: Dictionary = {}
var _summary_threshold: int = 0
var _secret_place_count: int = 0
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
	_load_places()
	_rewards = RewardRules.new()
	_thresholds = _rewards.thresholds()
	_summary_threshold = _thresholds.keys().max() if not _thresholds.is_empty() else 0
	DiscoveryManager.discovery_made.connect(_on_discovery_made)

## ResourceDirectory handles exported builds (".tres.remap" listings).
func _load_places() -> void:
	_places.clear()
	for path in ResourceDirectory.list_tres_paths(PLACES_PATH):
		var resource: Resource = load(path)
		if resource is PlaceDefinition:
			var place: PlaceDefinition = resource
			if place.id == "":
				push_warning("ExplorationManager: %s has an empty id" % path)
			else:
				_places.append(place)
	_places.sort_custom(func(a: PlaceDefinition, b: PlaceDefinition) -> bool: return a.order < b.order)
	_secret_place_count = 0
	for place in _places:
		if place.secret:
			_secret_place_count += 1

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

	if _thresholds.has(_session_discovery_count) and not _awarded_thresholds.has(_session_discovery_count):
		_awarded_thresholds.append(_session_discovery_count)
		var bonus: int = _thresholds[_session_discovery_count]
		PointsManager.add_points(bonus)
		exploration_bonus_awarded.emit(_session_discovery_count, bonus)
		if _session_discovery_count == _summary_threshold:
			_show_session_summary()

func has_reached_landmark(landmark_id: String) -> bool:
	return _reached_landmarks.has(landmark_id)

func mark_landmark_reached(landmark_id: String) -> void:
	if _reached_landmarks.has(landmark_id):
		return
	_reached_landmarks.append(landmark_id)
	var bonus := _rewards.points("landmark")
	PointsManager.add_points(bonus)
	landmark_reached.emit(landmark_id, bonus)
	FarmManager.notify_place_reached(landmark_id)

func has_found_secret_location(location_id: String) -> bool:
	return _found_secret_locations.has(location_id)

func mark_secret_location_found(location_id: String) -> void:
	if _found_secret_locations.has(location_id):
		return
	_found_secret_locations.append(location_id)
	var bonus := _rewards.points("secret_location")
	PointsManager.add_points(bonus)
	secret_location_found.emit(location_id, bonus)
	FarmManager.notify_place_reached(location_id)

	_maybe_award_curiosity_bonus(location_id)

	if _secret_place_count > 0 and _found_secret_locations.size() >= _secret_place_count and not _all_secrets_bonus_awarded:
		_all_secrets_bonus_awarded = true
		var all_bonus := _rewards.points("all_secret_locations")
		PointsManager.add_points(all_bonus)
		all_secret_locations_found.emit(all_bonus)

## Rewards exploration *order*, not grinding: reaching this secret spot
## before the nearby discovery it's paired with means the player found it
## out of curiosity, not by following the item's own trail. Fires at most
## once ever (saved), whichever qualifying location gets there first.
func _maybe_award_curiosity_bonus(location_id: String) -> void:
	if _curiosity_bonus_given:
		return
	var place := _find_place(location_id)
	var paired_discovery_id := place.curiosity_discovery_id if place else ""
	if paired_discovery_id == "" or DiscoveryManager.is_discovered(paired_discovery_id):
		return
	_curiosity_bonus_given = true
	var bonus := _rewards.points("curiosity")
	PointsManager.add_points(bonus)
	curiosity_bonus_awarded.emit(location_id, bonus)

## One row per place, in its fixed order, with the caller deciding
## how to render "not visited yet" (the Journal screen shows "???").
func get_places_progress() -> Array:
	var rows: Array = []
	for place in _places:
		rows.append({
			"id": place.id,
			"display_name": place.display_name,
			"visited": _is_place_visited(place.id),
		})
	return rows

func get_visited_place_count() -> int:
	var count := 0
	for place in _places:
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

func get_place_display_name(place_id: String) -> String:
	var place := _find_place(place_id)
	if place == null:
		return place_id.replace("_", " ").capitalize()
	return place.display_name

## The line shown on first arrival: a place's own arrival_text if it has
## one (e.g. the garden's "A quiet place to grow."), otherwise its name.
func get_place_arrival_text(place_id: String) -> String:
	var place := _find_place(place_id)
	if place != null and place.arrival_text != "":
		return place.arrival_text
	return get_place_display_name(place_id)

## The garden's place id (the one PlaceDefinition marked garden), or "".
func get_garden_place_id() -> String:
	for place in _places:
		if place.garden:
			return place.id
	return ""

## For SaveManager (M05.2): exploration progress that must survive a
## relaunch so its one-time rewards are never paid twice.
func get_save_data() -> Dictionary:
	return {
		"landmarks": Array(_reached_landmarks),
		"secrets": Array(_found_secret_locations),
		"all_secrets_bonus": _all_secrets_bonus_awarded,
		"curiosity_bonus": _curiosity_bonus_given,
	}

## For SaveManager, at boot, before any landmark exists. Pays nothing and
## announces nothing. Only known places of the right kind are kept (reached
## landmarks = non-secret places, found secrets = secret places), once
## each; anything else is dropped with a warning. A one-time bonus counts
## as paid unless the save plainly says it wasn't (absent — a save from
## before M05.2 — means not paid; a malformed value means paid). ("Every
## secret found" can only pay while finding a new secret, so a list that
## already holds every secret can never pay it again either.)
func apply_save_data(data: Dictionary) -> void:
	_reached_landmarks.clear()
	_found_secret_locations.clear()
	_restore_places(data.get("landmarks", []), false, _reached_landmarks)
	_restore_places(data.get("secrets", []), true, _found_secret_locations)
	_curiosity_bonus_given = _was_paid(data, "curiosity_bonus")
	_all_secrets_bonus_awarded = _was_paid(data, "all_secrets_bonus")

func _restore_places(saved: Variant, secret: bool, into: Array[String]) -> void:
	if typeof(saved) != TYPE_ARRAY:
		push_warning("ExplorationManager: saved places are not a list; ignored")
		return
	for place_id: Variant in saved:
		var place: PlaceDefinition = null
		if typeof(place_id) == TYPE_STRING:
			place = _find_place(place_id)
		if place == null or place.secret != secret or into.has(place.id):
			push_warning("ExplorationManager: ignoring saved place %s" % str(place_id))
			continue
		into.append(place.id)

func _was_paid(data: Dictionary, key: String) -> bool:
	if not data.has(key):
		return false
	var value: Variant = data[key]
	return value if typeof(value) == TYPE_BOOL else true

func _find_place(place_id: String) -> PlaceDefinition:
	for place in _places:
		if place.id == place_id:
			return place
	return null
