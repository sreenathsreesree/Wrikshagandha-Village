extends SceneTree

## Old-save compatibility check in real Godot (M15.3). run_save_fixtures.sh
## puts one fixture where the game keeps its save (user://save.json, in an
## isolated data folder) and starts this script in the current project: the
## game's own GameState loads it at boot through SaveManager, exactly as a
## player's save would load. Nothing here loads, migrates or writes a save
## itself except the one SaveManager.save_game() a check asks for.
##   mode=fresh    out=<facts.json>                 no save: the new-game facts
##   mode=fixture  expected=<v/expected.json> fresh=<facts.json> origin=<n>
##                 [resave=1]  the loaded facts equal what the old version held
##                 (sections it never saved equal a new game's); with resave=1
##                 the game then saves: the build's SAVE_VERSION and exactly today's sections
##   mode=newer                                     refused, never overwritten (the "newer" fixture)
##   mode=malformed fresh=<facts.json>              ignored like a damaged file
## Prints FIXTURE_CHECK PASS|FAIL lines; exits 1 on any failure.

const LANDMARK := "overlook"
const SECRET := "secluded_pond_nook"
const NPC := "villager"
const REQUEST := "villager_stones"
const CURRENT_SECTIONS := ["daily_discovery", "discovered_ids", "exploration", "farm", "items", "journal_entries", "points",
		"relationships", "requests", "save_version", "settings", "wallet", "wildlife_sightings", "world_time"]

var args := {}
var failures := 0

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var at := arg.find("=")
		if at > 0:
			args[arg.left(at)] = arg.substr(at + 1)
	_run()

func al(name: String) -> Node:
	return root.get_node_or_null(name)

func check(ok: bool, what: String, detail := "") -> void:
	if ok:
		print("FIXTURE_CHECK PASS %s" % what)
	else:
		failures += 1
		print("FIXTURE_CHECK FAIL %s %s" % [what, detail])

func _run() -> void:
	await process_frame
	match str(args.get("mode", "")):
		"fresh":
			_write(str(args["out"]), JSON.stringify(facts(), "\t", true))
			print("FIXTURE_CHECK PASS fresh facts written")
		"fixture":
			_check_fixture()
		"newer":
			_check_newer()
		"malformed":
			_check_malformed()
		_:
			check(false, "mode", str(args.get("mode", "")))
	quit(1 if failures > 0 else 0)

func _check_fixture() -> void:
	var origin := int(args.get("origin", "-1"))
	var expected: Dictionary = _read_json(str(args["expected"]))
	var fresh: Dictionary = _read_json(str(args["fresh"]))
	var got := facts()
	var tag := "v%d%s" % [origin, " (re-saved)" if args.has("again") else ""]
	check(got["points"] == expected["points"], tag + " points", "%s vs %s" % [got["points"], expected["points"]])
	check(got["discovered_ids"] == expected["discovered_ids"], tag + " discovered ids", "%s vs %s" % [got["discovered_ids"], expected["discovered_ids"]])
	check(got["journal_has_entry"] == expected["journal_has_entry"], tag + " journal entries")
	check(got["movement_mode"] == expected["movement_mode"], tag + " movement mode", "%s vs %s" % [got["movement_mode"], expected["movement_mode"]])
	var seeds_ok := true
	var produce_ok := true
	for crop_id: String in expected["seeds"]:
		seeds_ok = seeds_ok and int(got["seeds"].get(crop_id, -1)) == int(expected["seeds"][crop_id])
		produce_ok = produce_ok and _ints(got["produce"].get(crop_id, [])) == _ints(expected["produce"][crop_id])
	check(seeds_ok, tag + " seeds (v0/v1: moved from farm.seeds into items)", "%s vs %s" % [got["seeds"], expected["seeds"]])
	check(produce_ok, tag + " produce (v0/v1: moved from farm.basket into items)", "%s vs %s" % [got["produce"], expected["produce"]])
	check(_reached(got["milestones"]) == _reached(expected["milestones"]), tag + " farm milestones", "%s vs %s" % [_reached(got["milestones"]), _reached(expected["milestones"])])
	check(_plots_match(got["plots"], expected["plots"]), tag + " farm plots (states, crops, timers)", "%s\nvs %s" % [got["plots"], expected["plots"]])
	if origin >= 3:
		check(_norm(got["inventory"]) == _norm(expected["inventory"]), tag + " inventory", "%s vs %s" % [got["inventory"], expected["inventory"]])
	var source: Dictionary = expected if origin >= 4 else fresh
	check(got["coins"] == source["coins"] and got["ledger_entries"] == source["ledger_entries"], tag + " wallet%s" % ("" if origin >= 4 else " (absent: empty)"), "%s/%s vs %s/%s" % [got["coins"], got["ledger_entries"], source["coins"], source["ledger_entries"]])
	source = expected if origin >= 5 else fresh
	check(got["landmark_reached"] == source["landmark_reached"] and got["secret_found"] == source["secret_found"], tag + " exploration%s" % ("" if origin >= 5 else " (absent: nothing reached)"))
	source = expected if origin >= 6 else fresh
	check(got["friendship"] == source["friendship"], tag + " friendship%s" % ("" if origin >= 6 else " (absent: 0)"), "%s vs %s" % [got["friendship"], source["friendship"]])
	source = expected if origin >= 7 else fresh
	check(got["request_state"] == source["request_state"], tag + " request%s" % ("" if origin >= 7 else " (absent: not offered)"), "%s vs %s" % [got["request_state"], source["request_state"]])
	if origin >= 8:
		check(got["clock"][0] == expected["clock"][0] and absf(float(got["clock"][1]) - float(expected["clock"][1])) < 0.0005, tag + " world time", "%s vs %s" % [got["clock"], expected["clock"]])
	else:
		check(got["clock"][0] == fresh["clock"][0] and absf(float(got["clock"][1]) - float(fresh["clock"][1])) < 0.01, tag + " world time (absent: a new day)", "%s vs %s" % [got["clock"], fresh["clock"]])
	source = expected if origin >= 9 else fresh
	check(got["wildlife_sighted"] == source["wildlife_sighted"], tag + " wildlife sightings%s" % ("" if origin >= 9 else " (absent: none seen)"), "%s vs %s" % [got["wildlife_sighted"], source["wildlife_sighted"]])
	if args.has("resave"):
		al("SaveManager").save_game()
		var saved: Variant = JSON.parse_string(FileAccess.get_file_as_string("user://save.json"))
		var keys: Array = (saved as Dictionary).keys() if saved is Dictionary else []
		keys.sort()
		var current := int(al("SaveManager").get("SAVE_VERSION"))
		check(saved is Dictionary and int(saved.get("save_version", -1)) == current, tag + " re-saved as save_version %d" % current)
		check(keys == CURRENT_SECTIONS, tag + " re-saved with exactly today's sections", str(keys))

func _check_newer() -> void:
	var got := facts()
	check(got["points"] == 0 and got["discovered_ids"].is_empty(), "newer save not loaded", "points %s" % got["points"])
	al("SaveManager").save_game()
	print("FIXTURE_CHECK INFO newer save_game() attempted (the harness compares the file's bytes)")

func _check_malformed() -> void:
	var got := facts()
	var fresh: Dictionary = _read_json(str(args["fresh"]))
	check(got["points"] == fresh["points"] and _norm(got["discovered_ids"]) == _norm(fresh["discovered_ids"]) and _norm(got["seeds"]) == _norm(fresh["seeds"]), "malformed save ignored (a new game)", "%s / %s vs %s / %s" % [got["points"], got["seeds"], fresh["points"], fresh["seeds"]])

## The same facts the generator recorded, read through the current getters.
func facts() -> Dictionary:
	var fm := al("FarmManager")
	var seeds := {}
	var produce := {}
	for crop: Object in fm.get_crops():
		var id := str(crop.get("crop_id"))
		seeds[id] = int(fm.get_seed_count(id))
		produce[id] = [int(fm.get_produce_count(id, 0)), int(fm.get_produce_count(id, 1)), int(fm.get_produce_count(id, 2))]
	var discovered: Array = Array(al("DiscoveryManager").get_discovered_ids())
	discovered.sort()
	var journal: Array = []
	for id: String in discovered:
		journal.append([id, al("JournalManager").has_entry(id)])
	var sighted: Array = Array(al("JournalManager").get_sighted_ids())
	sighted.sort()
	return {
		"points": int(al("PointsManager").get_points()),
		"discovered_ids": discovered,
		"journal_has_entry": journal,
		"movement_mode": al("InputManager").get_movement_mode_name(),
		"seeds": seeds,
		"produce": produce,
		"milestones": fm.get_milestones(),
		"plots": fm.get_save_data().get("plots", {}),
		"inventory": al("Inventory").get_save_data(),
		"coins": int(al("Wallet").get_balance()),
		"ledger_entries": al("Wallet").get_ledger().size(),
		"landmark_reached": al("ExplorationManager").has_reached_landmark(LANDMARK),
		"secret_found": al("ExplorationManager").has_found_secret_location(SECRET),
		"friendship": int(al("Relationships").get_friendship(NPC)),
		"request_state": str(al("Requests").get_state(REQUEST)),
		"clock": [int(al("WorldClock").get_day()), float(al("WorldClock").get_fraction())],
		"wildlife_sighted": sighted,
	}

## Every plot field exactly, except the three read from the clock when a plot
## is captured (seconds left in a stage, seconds thirsty, the longest thirst):
## the generator read the old game's memory a moment after it saved, so those
## may differ by a few milliseconds — within 0.05 s they are the same moment.
const CLOCK_FIELDS := ["stage_time_left", "thirsty_for", "longest_thirst"]
func _plots_match(got: Variant, want: Variant) -> bool:
	var a: Variant = _norm(got)
	var b: Variant = _norm(want)
	if not (a is Dictionary and b is Dictionary) or (a as Dictionary).keys().size() != (b as Dictionary).keys().size():
		return false
	for plot_id: String in b:
		if not (a as Dictionary).has(plot_id):
			return false
		var pa: Dictionary = a[plot_id]
		var pb: Dictionary = b[plot_id]
		var ka: Array = pa.keys()
		var kb: Array = pb.keys()
		ka.sort()
		kb.sort()
		if ka != kb:
			return false
		for k: String in pb:
			if k in CLOCK_FIELDS:
				if absf(float(pa[k]) - float(pb[k])) > 0.05:
					return false
			elif pa[k] != pb[k]:
				return false
	return true

func _reached(milestones: Variant) -> Array:
	var ids: Array = []
	for m: Variant in milestones:
		if m is Dictionary and bool(m.get("reached", false)):
			ids.append(str(m["id"]))
	ids.sort()
	return ids

func _ints(a: Variant) -> Array:
	var out: Array = []
	for x: Variant in a:
		out.append(int(x))
	return out

## JSON-normalised (every number a float, as a save file reads back) so a value
## restored from the file compares with the one the old version held.
func _norm(v: Variant) -> Variant:
	return JSON.parse_string(JSON.stringify(v, "", true))

func _read_json(path: String) -> Dictionary:
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path))
	return parsed if parsed is Dictionary else {}

func _write(path: String, text: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()
