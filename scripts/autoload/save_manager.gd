extends Node

## Local save/load only. Reads and writes a single JSON file under the
## platform-specific user:// directory (app-private storage on Android).
## Every section is read with a default, so a save written before Journal /
## Daily Discovery existed still loads cleanly.
##
## Versioning (M04.0, P-01): the file carries a top-level save_version.
## - absent: written before M04.0 (version 0) — same sections, migrated up;
## - older than SAVE_VERSION: migrated one step at a time (_migrate);
## - newer than this build: neither loaded nor overwritten this session —
##   an older build would drop what it doesn't know;
## - not a whole number >= 0: malformed, treated like a corrupted file.
## A section of the wrong type is ignored (its default is used) instead of
## reaching a system's apply function. Bump SAVE_VERSION whenever what is
## saved changes (a new section, a renamed or reshaped field) and add its
## step to _migrate() (a step that changes nothing is fine when old data
## needs no rewrite): the bump is what stops an older build from loading a
## newer save and dropping what it doesn't know on its next save.
##
## Versions: 1 = M04.0 (the six sections, now stamped). 2 = M04.2: the
## player's seeds and basket moved from farm.seeds / farm.basket into
## "items" (ItemStore save data, a count per quality level); the farm keeps
## "starter_seeds", the crops whose starting seeds were given.
## 3 = M04.3: "items" is the Inventory's and may hold collectibles (one per
## discovery collected) — an older build would drop those, so the bump;
## nothing to rewrite.
## 4 = M05.1: a "wallet" section (the coin ledger); older saves have none
## and start with an empty wallet — nothing to rewrite.
## 5 = M05.2: an "exploration" section (places reached, secrets found, the
## two once-ever bonuses); older saves have none — nothing reached yet,
## nothing to rewrite.

const SAVE_PATH := "user://save.json"
const SAVE_VERSION := 5
const VERSION_KEY := "save_version"
## Every section and the JSON types it may have; anything else is ignored.
const SECTION_TYPES := {
	"points": [TYPE_INT, TYPE_FLOAT],
	"discovered_ids": [TYPE_ARRAY],
	"journal_entries": [TYPE_DICTIONARY],
	"daily_discovery": [TYPE_DICTIONARY],
	"farm": [TYPE_DICTIONARY],
	"settings": [TYPE_DICTIONARY],
	"items": [TYPE_DICTIONARY],
	"wallet": [TYPE_DICTIONARY],
	"exploration": [TYPE_DICTIONARY],
}

## Set when the file on disk is newer than this build: saving is refused for
## the rest of the session so that file survives.
var _saving_blocked: bool = false

func save_game() -> void:
	if _saving_blocked:
		push_warning("SaveManager: the save file is from a newer version; not overwriting it")
		return
	var data := {
		VERSION_KEY: SAVE_VERSION,
		"points": PointsManager.get_points(),
		"discovered_ids": DiscoveryManager.get_discovered_ids(),
		"journal_entries": JournalManager.get_save_data(),
		"daily_discovery": DailyDiscoveryManager.get_save_data(),
		"farm": FarmManager.get_save_data(),
		"settings": InputManager.get_settings_data(),
		"items": Inventory.get_save_data(),
		"wallet": Wallet.get_save_data(),
		"exploration": ExplorationManager.get_save_data(),
	}
	var file := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if file == null:
		push_warning("SaveManager: failed to open save file for writing")
		return
	file.store_string(JSON.stringify(data))
	file.close()

func load_game() -> bool:
	if not FileAccess.file_exists(SAVE_PATH):
		return false
	var file := FileAccess.open(SAVE_PATH, FileAccess.READ)
	if file == null:
		push_warning("SaveManager: failed to open save file for reading")
		return false
	var text := file.get_as_text()
	file.close()
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		push_warning("SaveManager: save file corrupted, ignoring")
		return false
	var version := read_version(parsed)
	if version < 0:
		push_warning("SaveManager: save file has a malformed save_version, ignoring")
		return false
	if version > SAVE_VERSION:
		_saving_blocked = true
		push_warning("SaveManager: save_version %d is newer than this build (%d); not loading or overwriting it" % [version, SAVE_VERSION])
		return false
	var data := _migrate(parsed, version)
	if data.is_empty():
		return false
	data = _valid_sections(data)
	PointsManager.set_points(int(data.get("points", 0)))
	DiscoveryManager.set_discovered_ids(data.get("discovered_ids", []))
	JournalManager.apply_save_data(data.get("journal_entries", {}))
	DailyDiscoveryManager.apply_save_data(data.get("daily_discovery", {}))
	Inventory.apply_save_data(data.get("items", {}))
	FarmManager.apply_save_data(data.get("farm", {}))
	InputManager.apply_settings_data(data.get("settings", {}))
	Wallet.apply_save_data(data.get("wallet", {}))
	ExplorationManager.apply_save_data(data.get("exploration", {}))
	return true

func has_save_file() -> bool:
	return FileAccess.file_exists(SAVE_PATH)

## The save's schema version: 0 if absent (written before M04.0); -1 if it
## isn't a whole number >= 0 (JSON numbers arrive as floats).
static func read_version(save: Dictionary) -> int:
	if not save.has(VERSION_KEY):
		return 0
	var value: Variant = save[VERSION_KEY]
	if typeof(value) != TYPE_INT and typeof(value) != TYPE_FLOAT:
		return -1
	var number := float(value)
	if number < 0.0 or number != floorf(number):
		return -1
	return int(number)

## Brings a save from an older version up to SAVE_VERSION, one step at a
## time; each step turns version n data into version n + 1 data. An empty
## result means a step is missing (never expected: checked by the toolkit).
func _migrate(save: Dictionary, from_version: int) -> Dictionary:
	var data := save.duplicate(true)
	var version := from_version
	while version < SAVE_VERSION:
		match version:
			0:
				pass  # before M04.0: the same sections, only save_version was missing
			1:
				_move_holdings_to_items(data)  # M04.2
			2:
				pass  # M04.3: items may now hold collectibles; same shape
			3:
				pass  # M05.1: a new "wallet" section; absent = an empty wallet
			4:
				pass  # M05.2: a new "exploration" section; absent = nothing reached yet
			_:
				push_warning("SaveManager: no migration from save_version %d" % version)
				return {}
		version += 1
		data[VERSION_KEY] = version
	return data

## Only sections of an expected type go on to their system; a wrong type is
## dropped (so its default applies) rather than breaking the load halfway.
func _valid_sections(data: Dictionary) -> Dictionary:
	var valid := {}
	for key: String in SECTION_TYPES:
		if not data.has(key):
			continue
		var allowed: Array = SECTION_TYPES[key]
		if allowed.has(typeof(data[key])):
			valid[key] = data[key]
		else:
			push_warning("SaveManager: ignoring save section '%s' of the wrong type" % key)
	return valid

## Step 1 -> 2 (M04.2): the seeds in hand (farm.seeds, crop -> count) and
## the basket (farm.basket, crop -> [plain, good, fine]) become the crops'
## seed and produce items in "items"; the farm records which crops' starting
## seeds were given (the crops farm.seeds listed). Counts are carried over
## as they are (ItemStore validates them on load); an entry for a crop with
## no item is dropped with a warning. No other section is touched.
func _move_holdings_to_items(data: Dictionary) -> void:
	var items := {}
	var farm: Variant = data.get("farm")
	if typeof(farm) == TYPE_DICTIONARY and not (farm as Dictionary).is_empty():
		var definitions := ItemStore.load_definitions()
		var seed_items := ItemStore.crop_item_ids(definitions, "seed")
		var produce_items := ItemStore.crop_item_ids(definitions, "produce")
		var seeds: Variant = farm.get("seeds", {})
		var basket: Variant = farm.get("basket", {})
		farm["starter_seeds"] = []
		if typeof(seeds) == TYPE_DICTIONARY:
			farm["starter_seeds"] = (seeds as Dictionary).keys()
			for crop_id: String in seeds:
				if seed_items.has(crop_id):
					items[seed_items[crop_id]] = [seeds[crop_id]]
				else:
					push_warning("SaveManager: no seed item for saved crop '%s'; dropped" % crop_id)
		if typeof(basket) == TYPE_DICTIONARY:
			for crop_id: String in basket:
				if produce_items.has(crop_id):
					items[produce_items[crop_id]] = basket[crop_id]
				else:
					push_warning("SaveManager: no produce item for saved crop '%s'; dropped" % crop_id)
		farm.erase("seeds")
		farm.erase("basket")
	data["items"] = items
