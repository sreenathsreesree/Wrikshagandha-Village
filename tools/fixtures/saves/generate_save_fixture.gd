extends SceneTree

## Old-save fixture generator (M15.3). Run inside an exported historical tree
## (tools/fixtures/saves/generate_all.sh does this), never in the current
## project:
##   godot --headless --path <old tree> -s res://generate_save_fixture.gd -- out=<dir>
## It boots that version's own main scene, plays a short scripted session
## through that version's own public API — each call recorded in calls.json —
## and saves with that version's own SaveManager. It writes:
##   save.json      the file that version's SaveManager wrote (the fixture);
##   expected.json  what that version held in memory when it saved — read
##                  back through its own getters, not from the file;
##   calls.json     every public call made, in order, with its result.
## Only what a version has is used (has_node / has_method), so one script
## serves v0..v9 (M14.1a added one species sighting, v9+ only — the has_method
## guard leaves v0..v8's calls exactly as they were generated). Nothing in the
## old tree is changed except adding this file.

const DISCOVERIES := ["blue_mushroom", "golden_leaf"]
const LANDMARK := "overlook"
const SECRET := "secluded_pond_nook"
const NPC := "villager"
const REQUEST := "villager_stones"
const SPECIES := "rabbit"
## Crops grow over 20–34 s of game time; time runs faster so a harvest fits.
const TIME_SCALE := 8.0
const GROW_LIMIT_SECONDS := 60.0

var out_dir := ""
var calls: Array = []
var log_lines: Array = []

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("out="):
			out_dir = arg.substr(4)
	if out_dir == "":
		push_error("FIXTURE_GEN: out=<dir> is required")
		quit(2)
		return
	_run()

func al(name: String) -> Node:
	return root.get_node_or_null(name)

## One recorded public call.
func api(node_name: String, method: String, args: Array = []) -> Variant:
	var node := al(node_name)
	var result: Variant = node.callv(method, args)
	calls.append({"call": "%s.%s" % [node_name, method], "args": _plain(args), "result": _plain(result)})
	return result

func plot_api(plot: Node, method: String, args: Array = []) -> Variant:
	var result: Variant = plot.callv(method, args)
	calls.append({"call": "FarmPlot(%s).%s" % [plot.get("plot_id"), method], "args": _plain(args), "result": _plain(result)})
	return result

func _plain(v: Variant) -> Variant:
	if v is Object:
		return str(v.get("crop_id")) if v.get("crop_id") != null else v.get_class()
	if v is Array:
		var a: Array = []
		for x in v:
			a.append(_plain(x))
		return a
	return v

func wait_real(seconds: float) -> void:
	var end := Time.get_ticks_msec() + int(seconds * 1000.0)
	while Time.get_ticks_msec() < end:
		await process_frame

func _run() -> void:
	var main_scene: String = ProjectSettings.get_setting("application/run/main_scene")
	root.add_child(load(main_scene).instantiate())
	await wait_real(2.0)
	var plot := _first_unlocked_plot()
	if plot == null:
		_fail("no unlocked FarmPlot in the main scene")
		return
	Engine.time_scale = TIME_SCALE
	api("PointsManager", "add_points", [7])
	for id in DISCOVERIES:
		api("DiscoveryManager", "discover", [id])
	api("InputManager", "set_tap_to_move", [true])
	# Farm: prepare the soil, choose a seed, water when thirsty, harvest when ripe.
	var crop: Object = _crop_with_seeds()
	if crop == null:
		_fail("no crop with starting seeds")
		return
	await _plant(plot, crop)
	var t0 := Time.get_ticks_msec()
	while int(plot.get("plot_state")) != 4:  # PlotState.READY
		if (Time.get_ticks_msec() - t0) / 1000.0 * TIME_SCALE > GROW_LIMIT_SECONDS * 4.0:
			_fail("the crop never ripened")
			return
		if bool(plot.get("_needs_water")):
			plot_api(plot, "interact")
		await wait_real(0.6)
	plot_api(plot, "interact")  # harvest
	await wait_real(0.6)
	# A second crop left growing, so a live plot state is saved too.
	var crop2: Object = _crop_with_seeds()
	if crop2 != null:
		await _plant(plot, crop2)
	Engine.time_scale = 1.0
	if al("Market") != null and al("Market").has_method("sell"):
		var produce := _held_produce()
		if produce.size() == 2:
			api("Market", "sell", [produce[0], produce[1], 1])
	elif al("Wallet") != null:
		api("Wallet", "credit", [5, "m15_3_fixture"])  # no v4/v5 gameplay path credited coins; the public API did
	api("ExplorationManager", "mark_landmark_reached", [LANDMARK])
	api("ExplorationManager", "mark_secret_location_found", [SECRET])
	if al("Relationships") != null:
		api("Relationships", "record_completed_conversation", [NPC])
	if al("Requests") != null:
		api("Requests", "accept", [REQUEST])
	if al("WorldClock") != null:
		api("WorldClock", "advance", [30.0])
	if al("JournalManager").has_method("record_sighting"):
		api("JournalManager", "record_sighting", [SPECIES])
	api("SaveManager", "save_game")
	var expected := facts()
	expected["godot"] = Engine.get_version_info().string
	var save_path := "user://save.json"
	var text := FileAccess.get_file_as_string(save_path)
	if text == "":
		_fail("the old SaveManager wrote nothing")
		return
	_write(out_dir.path_join("save.json"), text)
	_write(out_dir.path_join("expected.json"), JSON.stringify(expected, "\t", true))
	_write(out_dir.path_join("calls.json"), JSON.stringify(calls, "\t", false))
	print("FIXTURE_GEN OK %s" % out_dir)
	quit(0)

func _plant(plot: Node, crop: Object) -> void:
	var guard := 0
	while int(plot.get("plot_state")) == 0 and guard < 5:  # EMPTY -> SOIL
		plot_api(plot, "interact")
		await wait_real(0.6)
		guard += 1
	plot_api(plot, "interact")  # SOIL -> the seed choice
	await wait_real(0.2)
	api("FarmManager", "choose_seed", [crop])
	await wait_real(0.6)

func _first_unlocked_plot() -> Node:
	for node in root.find_children("*", "Area3D", true, false):
		var script: Script = node.get_script()
		if script != null and script.resource_path.ends_with("farm_plot.gd") and bool(node.get("unlocked")):
			return node
	return null

func _crop_with_seeds() -> Object:
	for crop: Object in al("FarmManager").get_crops():
		if int(al("FarmManager").get_seed_count(str(crop.get("crop_id")))) > 0:
			return crop
	return null

## [produce item id, quality] of one held produce, read through the item store (v2+).
func _held_produce() -> Array:
	var data: Dictionary = al("Inventory").get_save_data() if al("Inventory") != null else {}
	for item_id: String in data:
		var counts: Variant = data[item_id]
		if item_id.ends_with("_seed") or typeof(counts) != TYPE_ARRAY:
			continue
		for q in (counts as Array).size():
			if int(counts[q]) > 0 and (counts as Array).size() == 3:
				return [item_id, q]
	return []

## What this version holds, read through its own getters (only those it has).
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
	var milestones: Array = Array(fm.get_milestones())
	milestones.sort()
	var journal: Array = []
	for id: String in discovered:
		journal.append([id, al("JournalManager").has_entry(id)])
	var f := {
		"save_version_written": _written_version(),
		"points": int(al("PointsManager").get_points()),
		"discovered_ids": discovered,
		"journal_has_entry": journal,
		"movement_mode": al("InputManager").get_movement_mode_name(),
		"seeds": seeds,
		"produce": produce,
		"milestones": milestones,
		"plots": fm.get_save_data().get("plots", {}),
		"landmark_reached": al("ExplorationManager").has_reached_landmark(LANDMARK),
		"secret_found": al("ExplorationManager").has_found_secret_location(SECRET),
	}
	if al("Inventory") != null:
		f["inventory"] = al("Inventory").get_save_data()
	if al("Wallet") != null:
		f["coins"] = int(al("Wallet").get_balance())
		f["ledger_entries"] = al("Wallet").get_ledger().size()
	if al("Relationships") != null:
		f["friendship"] = int(al("Relationships").get_friendship(NPC))
	if al("Requests") != null:
		f["request_state"] = str(al("Requests").get_state(REQUEST))
	if al("WorldClock") != null:
		f["clock"] = [int(al("WorldClock").get_day()), float(al("WorldClock").get_fraction())]
	if al("JournalManager").has_method("get_sighted_ids"):
		var sighted: Array = Array(al("JournalManager").get_sighted_ids())
		sighted.sort()
		f["wildlife_sighted"] = sighted
	return f

func _written_version() -> int:
	var sm := al("SaveManager")
	var v: Variant = sm.get("SAVE_VERSION")
	return int(v) if v != null else 0

func _write(path: String, text: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()

func _fail(why: String) -> void:
	print("FIXTURE_GEN FAIL %s" % why)
	quit(1)
