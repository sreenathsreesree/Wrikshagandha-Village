extends SceneTree

## Discovery collection smoke test in real Godot (P0.1; nurture and harvest
## cases P0.1b), run by
## run_collect_check.sh in its own data folder, in two launches:
##   mode=act    the real Main scene (Meadow, Player, autoloads). Three
##               collections through the game's own tap path
##               (InputManager.interact_target_requested — what a tap emits):
##                 walk    a discovery out of reach: the Player walks to it and
##                         collects it from the InteractionZone's area_entered
##                         signal (the path where a direct monitorable write is
##                         blocked by Godot);
##                 tap     a discovery already in reach: collected at once,
##                         outside any physics signal;
##                 repeat  the walk discovery again after its respawn (forced
##                         early): a repeat collection — points and an item, no
##                         new Journal entry.
##               During each collection's animation, a rapid repeat: the same
##               tap request again and a direct interact() on the object (a
##               caller without the Player's own one-shot list) — both must do
##               nothing. Each collection must pay its discovery's points once,
##               emit harvested once, start its spawn point's respawn once and
##               add one item; the Journal and Collection change only on a
##               first find; the object is unavailable within two frames.
##               P0.1b — the same walk-up path for the Earth Nurture plant and a
##               farm harvest (one plot set READY by restore() as test setup):
##                 nurture  unavailable within two frames; a second tap and a
##                          direct interact() mid-cycle refused; available
##                          again once, after one grow-in + hold + relax;
##                          nothing paid;
##                 harvest  one crop_harvested; points = the harvest's points
##                          plus any milestone bonus it triggers, once; the
##                          plot unavailable within two frames, a second tap and
##                          a direct interact() mid-harvest pay nothing; the plot
##                          available again (prepared soil) at the end.
##               Then the facts the game holds are written to expect=<file>.
##   mode=check  a new launch loads the save at boot (GameState) and compares
##               (save_version must still be 9).
## Prints COLLECT_CHECK PASS|FAIL lines; the shell also fails on any SCRIPT
## ERROR or "Function blocked during in/out signal" in either log.

const SAVE_VERSION := 9
## How long a walk may take before it counts as stuck.
const WALK_TIMEOUT_FRAMES := 1200

var args := {}
var failures := 0
var _harvested := 0
var _made := 0
var _repeated := 0
var _entries := 0
## Points paid during a collection by rewards other than the discovery itself
## (a landmark or secret place the walk passes, an exploration threshold, a
## farm milestone). Which discovery the walk picks depends on the date (it
## skips the day's Daily Discovery target), so its route may cross one.
var _other_paid := 0
## Collections that ran to their last check (walk, tap, repeat).
var _completed := 0
## The plot the walk-up harvest used — the guard case below prefers another.
var _harvest_plot: Node = null

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var at := arg.find("=")
		if at > 0:
			args[arg.left(at)] = arg.substr(at + 1)
	_run()

func al(name: String) -> Node:
	return root.get_node_or_null(name)

func check(ok: bool, what: String, detail := "") -> void:
	if not ok:
		failures += 1
	print("COLLECT_CHECK %s %s %s" % ["PASS" if ok else "FAIL", what, detail])

func _run() -> void:
	await process_frame
	match str(args.get("mode", "")):
		"act":
			await _act()
			check(_completed == 7, "all seven cases ran (walk, tap, repeat, nurture, locked plot, harvest, harvest without a crop visual)", str(_completed))
			_write(str(args["expect"]), JSON.stringify(facts(), "\t", true))
			for i in 5:
				await process_frame  # GameState's deferred save on a repeat lands
			print("COLLECT_ACT_DONE failures %d" % failures)
			quit(0 if failures == 0 else 1)
		"check":
			var want: Variant = JSON.parse_string(FileAccess.get_file_as_string(str(args["expect"])))
			var got := facts()
			check(want is Dictionary and JSON.stringify(JSON.parse_string(JSON.stringify(got)), "", true) == JSON.stringify(want, "", true),
				"relaunch", "loaded %s ; held before closing %s" % [JSON.stringify(got, "", true), JSON.stringify(want, "", true)])
			var save: Variant = JSON.parse_string(FileAccess.get_file_as_string("user://save.json"))
			check(save is Dictionary and int(save.get("save_version", -1)) == SAVE_VERSION, "save version",
				str(save.get("save_version", "missing")) if save is Dictionary else "no save")
			quit(0 if failures == 0 else 1)
		_:
			check(false, "mode", str(args.get("mode", "")))
			quit(1)

func _act() -> void:
	root.add_child(load(str(ProjectSettings.get_setting("application/run/main_scene"))).instantiate())
	var dm := al("DiscoveryManager")
	dm.discovery_made.connect(func(_d: Variant) -> void: _made += 1)
	dm.discovery_repeated.connect(func(_d: Variant) -> void: _repeated += 1)
	al("JournalManager").entry_added.connect(func(_e: Variant) -> void: _entries += 1)
	var em := al("ExplorationManager")
	em.landmark_reached.connect(func(_id: String, b: int) -> void: _other_paid += b)
	em.secret_location_found.connect(func(_id: String, b: int) -> void: _other_paid += b)
	em.curiosity_bonus_awarded.connect(func(_id: String, b: int) -> void: _other_paid += b)
	em.exploration_bonus_awarded.connect(func(_t: int, b: int) -> void: _other_paid += b)
	em.all_secret_locations_found.connect(func(b: int) -> void: _other_paid += b)
	al("FarmManager").milestone_reached.connect(func(_id: String, _m: String, b: int) -> void: _other_paid += b)
	# The navigation mesh bakes on a thread at area load.
	var map: RID = root.get_world_3d().navigation_map
	for i in 600:
		await physics_frame
		if NavigationServer3D.map_get_iteration_id(map) > 0 and i > 30:
			break
	var player: Node3D = get_first_node_in_group(&"player")
	check(player != null, "player present")
	if player == null:
		return
	var candidates := _candidates(player)
	check(candidates.size() >= 2, "two collectable discoveries", str(candidates.size()))
	if candidates.size() < 2:
		return
	# walk: the nearest discovery between 4 and 14 m away (out of the 2.2 m zone).
	var walk_target: Node3D = null
	for c: Node3D in candidates:
		var d := player.global_position.distance_to(c.global_position)
		if d > 4.0 and d < 14.0:
			walk_target = c
			break
	check(walk_target != null, "a discovery 4-14 m away to walk to")
	if walk_target == null:
		return
	var walk_spawn := walk_target.get_parent()
	var walk_id := str(walk_target.get("discovery_id"))
	await _collect("walk", walk_target, player, true)
	# tap: another discovery (a different id), the player placed beside it.
	var tap_target: Node3D = null
	for c: Variant in candidates:
		if is_instance_valid(c) and str((c as Node3D).get("discovery_id")) != walk_id:
			tap_target = c
			break
	check(tap_target != null, "a second discovery to tap")
	if tap_target != null:
		var beside := tap_target.global_position + Vector3(0.0, 0.0, 1.0)
		_put(player, beside)
		for i in 10:
			await physics_frame  # the InteractionZone registers it (no interaction: nothing was asked)
		await _collect("tap", tap_target, player, false)
	# repeat: the walk discovery's respawn, forced early, collected after a walk.
	var timer: Timer = walk_spawn.get("_timer")
	timer.stop()
	timer.timeout.emit()
	await process_frame
	var again := _discovery_children(walk_spawn)
	check(again.size() == 1, "respawn makes exactly one new discovery", str(again.size()))
	if again.size() == 1:
		var respawned: Node3D = again[0]
		var away := respawned.global_position + Vector3(0.0, 0.0, 6.0)
		_put(player, away)
		for i in 10:
			await physics_frame
		await _collect("repeat", respawned, player, true)
	await _nurture(player)
	await _locked_plot(player)
	await _harvest(player)
	await _harvest_without_visual(player)

## P0.1b: a locked plot is never harvested or made available by a tap or a
## direct call (run before any harvest, whose milestones can unlock plots).
func _locked_plot(player: Node3D) -> void:
	var plot: Area3D = null
	for p in root.find_children("*", "FarmPlot", true, false):
		if not bool(p.get("unlocked")):
			plot = p
			break
	check(plot != null, "locked plot: one exists before any harvest")
	if plot == null:
		return
	var fm := al("FarmManager")
	var harvests := [0]
	var count := func(_c: Variant, _p: int, _q: int, _care: int) -> void: harvests[0] += 1
	fm.crop_harvested.connect(count)
	var milestones := [0]
	var count_m := func(_id: String, _m: String, _b: int) -> void: milestones[0] += 1
	fm.milestone_reached.connect(count_m)
	var state0 := int(plot.get("plot_state"))
	_put(player, plot.global_position + Vector3(0.0, 0.0, 1.0))
	for i in 10:
		await physics_frame
	al("InputManager").interact_target_requested.emit(plot)
	plot.call("interact")
	for i in 10:
		await physics_frame
	# (Points are not compared here: standing by the garden can complete an
	# exploration place, which pays on its own; the farm's own signals are.)
	check(not plot.monitorable and not bool(plot.get("unlocked")) and harvests[0] == 0 and milestones[0] == 0 and int(plot.get("plot_state")) == state0,
		"locked plot: a tap and a direct call change nothing", "monitorable %s, harvests %d, milestones %d, state %d -> %d"
		% [plot.monitorable, harvests[0], milestones[0], state0, int(plot.get("plot_state"))])
	fm.crop_harvested.disconnect(count)
	fm.milestone_reached.disconnect(count_m)
	_completed += 1

## P0.1b ordering guard: a READY plot whose crop visual is gone (test setup
## only — the game never makes one) runs its whole harvest in one frame; the
## deferred switch-off must not land after the plot is made available again.
## Its one-frame harvest is also the controlled setup for the _is_harvesting
## guard: a test handler on FarmManager.crop_harvested — emitted mid-harvest,
## crop still in the ground — interacts with the plot once more through its
## public interact(). The plot's action cooldown cannot refuse it (the outer
## call records its time only after the harvest returns) and no animation can
## stall it (nothing is awaited), so only the guard stands between that call
## and a second harvest paying again.
func _harvest_without_visual(player: Node3D) -> void:
	# Another unlocked plot than the walk-up harvest's, when there is one, so
	# nothing that case did to its plot (its action cooldown) carries over.
	var plot: Area3D = null
	for p in root.find_children("*", "FarmPlot", true, false):
		if bool(p.get("unlocked")) and not bool(p.get("_is_harvesting")) and (plot == null or plot == _harvest_plot):
			plot = p
	check(plot != null, "harvest without a crop visual: an unlocked plot", str(plot.name) if plot else "")
	if plot == null:
		return
	var crop_files := Array(DirAccess.get_files_at("res://data/crops")).filter(func(f: String) -> bool: return f.ends_with(".tres"))
	crop_files.sort()
	var crop: Resource = load("res://data/crops".path_join(str(crop_files[0])))
	plot.call("restore", {"state": "READY", "crop": str(crop.get("crop_id")), "stage": 3, "soil": 1, "care": 2, "quality": 1}, crop)
	var visual: Node = plot.get("_crop_visual")
	plot.set("_crop_visual", null)
	visual.queue_free()
	_put(player, plot.global_position + Vector3(0.0, 0.0, 1.0))
	for i in 10:
		await physics_frame
	# Past the plot's action cooldown, so the tap below is never refused by it.
	var settle := Time.get_ticks_msec()
	while Time.get_ticks_msec() - settle < int(plot.get("ACTION_COOLDOWN_MSEC")) + 150:
		await process_frame
	var fm := al("FarmManager")
	var harvests := [0]
	var bonus := [0]
	var reentry := {"tried": false, "while_harvesting": false}
	fm.crop_harvested.connect(func(_c: Variant, _p: int, _q: int, _care: int) -> void:
		harvests[0] += 1
		if not reentry["tried"]:
			reentry["tried"] = true
			reentry["while_harvesting"] = bool(plot.get("_is_harvesting"))
			plot.call("interact"))
	fm.milestone_reached.connect(func(_id: String, _m: String, b: int) -> void: bonus[0] += b)
	var expected := int(fm.get_harvest_points(crop, 1))
	var points0 := int(al("PointsManager").get_points())
	al("InputManager").interact_target_requested.emit(plot)
	for i in 10:
		await physics_frame
	var paid := int(al("PointsManager").get_points()) - points0
	check(bool(reentry["tried"]) and bool(reentry["while_harvesting"]) and harvests[0] == 1 and paid == expected + bonus[0],
		"harvest guard: a second interact() while _is_harvesting starts no harvest and pays nothing",
		"tried %s while harvesting %s; harvests %d, paid %d (one harvest %d + bonus %d)" % [reentry["tried"], reentry["while_harvesting"], harvests[0], paid, expected, bonus[0]])
	check(harvests[0] == 1 and paid == expected + bonus[0], "harvest without a crop visual: one harvest, paid once",
		"harvests %d, paid %d (harvest %d + bonus %d)" % [harvests[0], paid, expected, bonus[0]])
	check(not bool(plot.get("_is_harvesting")) and int(plot.get("plot_state")) == 1 and plot.monitorable,
		"harvest without a crop visual: ends available as prepared soil",
		"harvesting %s, state %d, monitorable %s" % [plot.get("_is_harvesting"), int(plot.get("plot_state")), plot.monitorable])
	_completed += 1

## P0.1b: the Earth Nurture plant, used by a walk-up tap.
func _nurture(player: Node3D) -> void:
	var found := root.find_children("*", "EarthNurture", true, false)
	check(found.size() == 1, "nurture: one Earth Nurture plant", str(found.size()))
	if found.size() != 1:
		return
	var plant: Area3D = found[0]
	_put(player, plant.global_position + Vector3(0.0, 0.0, 6.0))
	for i in 10:
		await physics_frame
	var points0 := int(al("PointsManager").get_points())
	var start := player.global_position
	# Used = its first Growth child starts growing in (read from the scene, so the
	# case works on any version of the script).
	var part: Node3D = plant.get_node("Growth").get_child(0)
	var dormant := part.scale
	al("InputManager").interact_target_requested.emit(plant)
	var frames := 0
	while part.scale.is_equal_approx(dormant) and frames < WALK_TIMEOUT_FRAMES:
		await physics_frame
		frames += 1
	var used_at := Time.get_ticks_msec()
	check(not part.scale.is_equal_approx(dormant), "nurture used", "after %d frames" % frames)
	check(player.global_position.distance_to(start) > 1.0, "nurture went through a walk", "walked %.1f m" % player.global_position.distance_to(start))
	al("InputManager").interact_target_requested.emit(plant)
	var direct: Variant = await plant.call("interact")
	check(direct == false, "nurture direct interact() mid-cycle refused", str(direct))
	await physics_frame
	await physics_frame
	check(not plant.monitorable, "nurture unavailable within two frames", "monitorable %s" % plant.monitorable)
	var cycle_ms := int(1000.0 * (float(plant.get("grow_seconds")) + float(plant.get("stagger_seconds")) * (plant.get_node("Growth").get_child_count() - 1)
		+ float(plant.get("hold_seconds")) + float(plant.get("relax_seconds"))))
	while not plant.monitorable and Time.get_ticks_msec() - used_at < cycle_ms + 5000:
		await process_frame
		if Time.get_ticks_msec() - used_at > 1500 and Time.get_ticks_msec() - used_at < cycle_ms - 500:
			al("InputManager").interact_target_requested.emit(plant)  # more taps mid-cycle: never a second cycle
	var took := Time.get_ticks_msec() - used_at
	check(plant.monitorable and absi(took - cycle_ms) < 600, "nurture available again after one cycle",
		"%d ms (one cycle %d ms)" % [took, cycle_ms])
	# In reach, a tap runs interact() at once (outside any physics signal); a direct
	# call in that same frame comes before the deferred switch-off has landed, so
	# only the cycle's own guard can refuse it.
	al("InputManager").interact_target_requested.emit(plant)
	var same: Variant = plant.call("interact")
	check(same is bool and same == false, "nurture same-frame direct interact() refused by the guard", str(same))
	var again_at := Time.get_ticks_msec()
	while not plant.monitorable or Time.get_ticks_msec() - again_at < 100:
		await process_frame
		if Time.get_ticks_msec() - again_at > cycle_ms + 5000:
			break
	var took2 := Time.get_ticks_msec() - again_at
	check(plant.monitorable and absi(took2 - cycle_ms) < 600, "nurture in reach: one cycle again", "%d ms (one cycle %d ms)" % [took2, cycle_ms])
	check(int(al("PointsManager").get_points()) == points0, "nurture pays nothing")
	_completed += 1

## P0.1b: a farm harvest by a walk-up tap. The plot is set READY with restore() (test setup only).
func _harvest(player: Node3D) -> void:
	var plot: Area3D = null
	for p in root.find_children("*", "FarmPlot", true, false):
		if bool(p.get("unlocked")):
			plot = p
			break
	check(plot != null, "harvest: an unlocked farm plot")
	if plot == null:
		return
	_harvest_plot = plot
	# Any crop from the data (the first by file name) — no crop is named here.
	var crop_files := Array(DirAccess.get_files_at("res://data/crops")).filter(func(f: String) -> bool: return f.ends_with(".tres"))
	crop_files.sort()
	check(not crop_files.is_empty(), "harvest: a crop in data/crops")
	if crop_files.is_empty():
		return
	var crop: Resource = load("res://data/crops".path_join(str(crop_files[0])))
	plot.call("restore", {"state": "READY", "crop": str(crop.get("crop_id")), "stage": 3, "soil": 1, "care": 2, "quality": 1}, crop)
	_put(player, plot.global_position + Vector3(0.0, 0.0, 6.0))
	for i in 10:
		await physics_frame
	var fm := al("FarmManager")
	var harvests := [0]
	var bonus := [0]
	fm.crop_harvested.connect(func(_c: Variant, _p: int, _q: int, _care: int) -> void: harvests[0] += 1)
	fm.milestone_reached.connect(func(_id: String, _m: String, b: int) -> void: bonus[0] += b)
	var expected := int(fm.get_harvest_points(crop, 1))
	var points0 := int(al("PointsManager").get_points())
	var start := player.global_position
	al("InputManager").interact_target_requested.emit(plot)
	var frames := 0
	while not bool(plot.get("_is_harvesting")) and frames < WALK_TIMEOUT_FRAMES:
		await physics_frame
		frames += 1
	check(bool(plot.get("_is_harvesting")), "harvest started", "after %d frames" % frames)
	check(player.global_position.distance_to(start) > 1.0, "harvest went through a walk", "walked %.1f m" % player.global_position.distance_to(start))
	al("InputManager").interact_target_requested.emit(plot)
	plot.call("interact")  # a direct call: refused (nothing awaited here, so it never blocks the case)
	await physics_frame
	await physics_frame
	check(not plot.monitorable, "harvest unavailable within two frames", "monitorable %s" % plot.monitorable)
	var harvest_at := Time.get_ticks_msec()
	var waited := 0
	while bool(plot.get("_is_harvesting")) and waited < 1200:
		await process_frame
		waited += 1
		if waited % 20 == 0:
			# Repeats throughout the harvest, past the plot's short action cooldown, so the
			# harvest's own guard is what is tested: a tap and a direct call.
			al("InputManager").interact_target_requested.emit(plot)
			plot.call("interact")
	var harvest_ms := Time.get_ticks_msec() - harvest_at
	for i in 5:
		await process_frame
	var paid := int(al("PointsManager").get_points()) - points0
	check(harvests[0] == 1, "harvest crop_harvested once", "%d (harvest lasted %d ms; the plot's action cooldown is %d ms)" % [harvests[0], harvest_ms, int(plot.get("ACTION_COOLDOWN_MSEC"))])
	check(paid == expected + bonus[0], "harvest paid once", "%d (harvest %d + milestone bonus %d)" % [paid, expected, bonus[0]])
	check(plot.monitorable and str(plot.get("plot_state")) != "" and int(plot.get("plot_state")) == 1, "harvest plot available again as prepared soil",
		"monitorable %s, state %s" % [plot.monitorable, plot.get("plot_state")])
	_completed += 1

## Moves the idle player (between collections) — test setup only; the game
## itself places the player only through Main's area loader.
func _put(player: Node3D, at: Vector3) -> void:
	player.global_position = Vector3(at.x, player.global_position.y, at.z)
	player.set("velocity", Vector3.ZERO)

## One collection through the tap path, with the rapid repeats and every count.
func _collect(label: String, target: Node3D, player: Node3D, expect_walk: bool) -> void:
	var id := str(target.get("discovery_id"))
	var definition: Variant = al("DiscoveryDatabase").get_definition(id)
	var item_id := str((al("Inventory").get("_collectible_item_ids") as Dictionary).get(id, ""))
	var first := not bool(al("DiscoveryManager").is_discovered(id))
	var spawn := target.get_parent()
	var timer: Timer = spawn.get("_timer")
	var points0 := int(al("PointsManager").get_points())
	var items0 := int(al("Inventory").get_quantity(item_id)) if item_id != "" else 0
	var found0 := int(al("CollectionManager").get_category_progress(str(definition.get("category"))).get("found"))
	_harvested = 0
	_made = 0
	_repeated = 0
	_entries = 0
	_other_paid = 0
	target.connect("harvested", func(_id: String) -> void: _harvested += 1)
	var start := player.global_position
	var distance := start.distance_to(target.global_position)
	al("InputManager").interact_target_requested.emit(target)
	var frames := 0
	while _harvested == 0 and frames < WALK_TIMEOUT_FRAMES and is_instance_valid(target):
		await physics_frame
		frames += 1
	check(_harvested == 1, label + " collected", "%s after %d frames, %.1f m away" % [id, frames, distance])
	if _harvested == 0:
		return
	if expect_walk:
		check(distance > 2.2 and player.global_position.distance_to(start) > 1.0, label + " went through a walk",
			"started %.1f m away, walked %.1f m" % [distance, player.global_position.distance_to(start)])
	# Rapid repeats during the animation: the tap request again, and a direct call.
	var points1 := int(al("PointsManager").get_points())
	al("InputManager").interact_target_requested.emit(target)
	var direct: Variant = await target.call("interact")
	check(direct == false, label + " direct interact() during the animation refused", str(direct))
	await physics_frame
	await physics_frame
	var still := is_instance_valid(target)
	check(not still or not bool(target.get("monitorable")), label + " unavailable within two frames",
		"monitorable %s" % (str(target.get("monitorable")) if still else "freed"))
	check(still, label + " still animating when checked (the repeats really landed mid-animation)")
	while is_instance_valid(target):
		await process_frame
	for i in 3:
		await process_frame
	# The discovery's own points exactly once; any other reward on the way is
	# counted by its own signal and must account for the rest exactly.
	var paid := int(al("PointsManager").get_points()) - points0 - _other_paid
	check(paid == int(definition.get("points_value")) and int(al("PointsManager").get_points()) == points1, label + " points paid once",
		"%d (value %d; other rewards on the way %d)" % [paid, int(definition.get("points_value")), _other_paid])
	check(_harvested == 1, label + " harvested emitted once", str(_harvested))
	check(_made + _repeated == 1 and (_made == 1) == first, label + " one discovery event", "made %d repeated %d (first %s)" % [_made, _repeated, first])
	check(not timer.is_stopped() and absf(timer.time_left - float(definition.get("respawn_seconds"))) < 2.0, label + " respawn scheduled once",
		"%.1f s left of %.1f" % [timer.time_left, float(definition.get("respawn_seconds"))])
	check(_discovery_children(spawn).is_empty(), label + " nothing respawned early")
	if item_id != "":
		check(int(al("Inventory").get_quantity(item_id)) - items0 == 1, label + " one item added", item_id)
	check(_entries == (1 if first else 0) and bool(al("JournalManager").has_entry(id)), label + " journal", "entries added %d" % _entries)
	var found1 := int(al("CollectionManager").get_category_progress(str(definition.get("category"))).get("found"))
	check(found1 - found0 == (1 if first else 0), label + " collection", "found %d -> %d" % [found0, found1])
	_completed += 1

## Collectable discoveries in the Meadow, nearest the player first: respawning
## (so a repeat exists), not today's daily target (its bonus would add points).
func _candidates(player: Node3D) -> Array:
	var target_id := str(al("DailyDiscoveryManager").get("target_id"))
	var out: Array = []
	for spawn in root.find_children("*", "DiscoverySpawnPoint", true, false):
		for d: Node3D in _discovery_children(spawn):
			var definition: Variant = al("DiscoveryDatabase").get_definition(str(d.get("discovery_id")))
			if definition != null and float(definition.get("respawn_seconds")) > 0.0 and str(d.get("discovery_id")) != target_id:
				out.append(d)
	out.sort_custom(func(a: Node3D, b: Node3D) -> bool:
		return player.global_position.distance_to(a.global_position) < player.global_position.distance_to(b.global_position))
	return out

func _discovery_children(spawn: Node) -> Array:
	var out: Array = []
	for child in spawn.get_children():
		if child is Area3D and child.get("discovery_id") != null and not child.is_queued_for_deletion():
			out.append(child)
	return out

## What collecting changes, as the save holds it.
func facts() -> Dictionary:
	var ids: Array = (al("DiscoveryManager").get("discovered_ids") as Array).duplicate()
	ids.sort()
	var entries: Array = []
	for e: Variant in al("JournalManager").get_entries():
		entries.append(str((e as Dictionary).get("id", "")))
	entries.sort()
	return {
		"points": al("PointsManager").get_points(),
		"discovered": ids,
		"journal": entries,
		"items": al("Inventory").get_save_data(),
	}

func _write(path: String, text: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(text)
	f.close()
