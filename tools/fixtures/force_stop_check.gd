extends SceneTree

## Force-stop persistence check in real Godot (M15.4). run_force_stop.sh runs
## each case in its own data folder, in three launches:
##   mode=setup  the state the case needs before the moment under test, saved
##               (an ordinary save, as the game makes on earlier events);
##   mode=act    the moment under test through the game's public API; what the
##               game then holds in memory is written to expect=<file>; then
##               FORCE_STOP_READY is printed and the process waits to be killed
##               (kill -9: no pause or close notification, so no save from those);
##   mode=check  a new launch loads the save at boot (GameState) and compares.
## Cases: landmark, secret, curiosity, all_secrets, repeat, daily — and control, a
## first-time discovery, which was already saved at once before M15.4 (it shows
## the harness can pass, not only fail). Each moment's
## own state is what is compared, so one trigger cannot stand in for another.
## M14.1a adds sighting: a real Rabbit scene and WildlifeController, the player
## (a bare Node3D) placed inside the rabbit's alert distance — the species is
## seen through the game's own path and must survive the kill; seeing it again
## after the relaunch pays and records nothing more.

const LANDMARK := "overlook"
const SPECIES_SCENE := "res://scenes/wildlife/Rabbit.tscn"

var args := {}

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var at := arg.find("=")
		if at > 0:
			args[arg.left(at)] = arg.substr(at + 1)
	_run()

func al(name: String) -> Node:
	return root.get_node_or_null(name)

func _run() -> void:
	await process_frame
	var case := str(args.get("case", ""))
	match str(args.get("mode", "")):
		"setup":
			_setup(case)
			al("SaveManager").save_game()
			print("FORCE_STOP_SETUP_DONE %s" % case)
			quit(0)
		"act":
			_act(case)
			for i in 5:
				await process_frame  # let anything deferred in this frame finish
			_write(str(args["expect"]), JSON.stringify(facts(case), "\t", true))
			print("FORCE_STOP_READY %s" % case)
			while true:
				await process_frame
		"check":
			var want: Variant = JSON.parse_string(FileAccess.get_file_as_string(str(args["expect"])))
			var got := facts(case)
			# Both sides as a save file reads back (every number a float), then compared.
			var ok := want is Dictionary and JSON.stringify(JSON.parse_string(JSON.stringify(got)), "", true) == JSON.stringify(want, "", true)
			if case == "sighting":  # the moment must have happened: the creature was seen through the game's own path
				ok = ok and want is Dictionary and want.get("sighted", []) == ["rabbit"]
			print("FORCE_STOP_%s %s :: after relaunch %s ; held before the kill %s" % ["PASS" if ok else "FAIL", case, JSON.stringify(got, "", true), JSON.stringify(want, "", true)])
			quit(0 if ok else 1)
		"again":
			# A further launch: the same values load again, and repeating the
			# once-ever moment pays nothing more (the daily target collected again
			# pays its discovery points, never a second bonus).
			var want2: Variant = JSON.parse_string(FileAccess.get_file_as_string(str(args["expect"])))
			var got2 := facts(case)
			var stable := want2 is Dictionary and JSON.stringify(JSON.parse_string(JSON.stringify(got2)), "", true) == JSON.stringify(want2, "", true)
			var before := int(al("PointsManager").get_points())
			var allowed := 0
			match case:
				"landmark", "secret", "curiosity", "all_secrets":
					_act(case)
				"daily":
					allowed = int(al("DiscoveryDatabase").get_definition(str(al("DailyDiscoveryManager").get("target_id"))).points_value)
					_act(case)
				"sighting":
					_act(case)
					for i in 10:
						await process_frame
					stable = stable and JSON.stringify(_norm(facts(case)), "", true) == JSON.stringify(want2, "", true)
			var paid := int(al("PointsManager").get_points()) - before
			var ok2 := stable and paid == allowed
			print("FORCE_STOP_%s %s again :: reload stable %s; repeating the moment paid %d (allowed %d)" % ["PASS" if ok2 else "FAIL", case, stable, paid, allowed])
			quit(0 if ok2 else 1)
		_:
			print("FORCE_STOP_FAIL unknown mode")
			quit(1)

## Secret places, in data order: [id, paired curiosity discovery].
func secrets() -> Array:
	var out: Array = []
	for place: Variant in al("ExplorationManager").get("_places"):
		if bool(place.get("secret")):
			out.append([str(place.get("id")), str(place.get("curiosity_discovery_id"))])
	return out

func secret_without_pair() -> String:
	for s: Array in secrets():
		if s[1] == "":
			return s[0]
	return ""

func secret_with_pair() -> Array:
	for s: Array in secrets():
		if s[1] != "":
			return s
	return []

## A respawning discovery (from the discovery data) that is not today's daily
## target — the first by id, so the choice is stable.
func repeatable_discovery() -> String:
	var target := str(al("DailyDiscoveryManager").get("target_id"))
	var ids: Array = []
	for definition: Variant in (al("DiscoveryDatabase").get("_definitions") as Dictionary).values():
		if float(definition.get("respawn_seconds")) > 0.0 and str(definition.get("id")) != target:
			ids.append(str(definition.get("id")))
	ids.sort()
	return str(ids[0]) if not ids.is_empty() else ""

func _setup(case: String) -> void:
	var em := al("ExplorationManager")
	var dm := al("DiscoveryManager")
	match case:
		"secret":
			for s: Array in secrets():  # every curiosity pair already found, so only the secret itself pays
				if s[1] != "":
					dm.discover(s[1])
		"all_secrets":
			for s: Array in secrets():
				if s[1] != "":
					dm.discover(s[1])
			var all := secrets()
			for i in all.size() - 1:
				em.mark_secret_location_found(all[i][0])
		"repeat":
			dm.discover(repeatable_discovery())
		"daily":
			dm.discover(str(al("DailyDiscoveryManager").get("target_id")))

func _act(case: String) -> void:
	var em := al("ExplorationManager")
	var dm := al("DiscoveryManager")
	match case:
		"landmark":
			em.mark_landmark_reached(LANDMARK)
		"secret":
			em.mark_secret_location_found(secret_without_pair())
		"curiosity":
			em.mark_secret_location_found(secret_with_pair()[0])
		"all_secrets":
			var all := secrets()
			em.mark_secret_location_found(all[all.size() - 1][0])
		"repeat":
			dm.discover(repeatable_discovery())
		"daily":
			dm.discover(str(al("DailyDiscoveryManager").get("target_id")))
		"control":
			dm.discover(repeatable_discovery())
		"sighting":
			_see_creature()

## The case's own state, read through the game's getters.
func facts(case: String) -> Dictionary:
	var em := al("ExplorationManager")
	var f := {"points": int(al("PointsManager").get_points())}
	match case:
		"landmark":
			f["landmark_reached"] = em.has_reached_landmark(LANDMARK)
		"secret":
			f["secret_found"] = em.has_found_secret_location(secret_without_pair())
		"curiosity":
			f["secret_found"] = em.has_found_secret_location(secret_with_pair()[0])
			f["curiosity_bonus"] = bool(em.get("_curiosity_bonus_given"))
		"all_secrets":
			var all := secrets()
			f["last_secret_found"] = em.has_found_secret_location(all[all.size() - 1][0])
			f["all_secrets_bonus"] = bool(em.get("_all_secrets_bonus_awarded"))
		"repeat":
			var id := repeatable_discovery()
			f["collectible"] = int(al("Inventory").get_quantity(id))
			f["discovered"] = Array(al("DiscoveryManager").get_discovered_ids()).has(id)
		"control":
			f["discovered"] = Array(al("DiscoveryManager").get_discovered_ids()).has(repeatable_discovery())
			f["collectible"] = int(al("Inventory").get_quantity(repeatable_discovery()))
		"sighting":
			var sighted: Array = Array(al("JournalManager").get_sighted_ids())
			sighted.sort()
			f["sighted"] = sighted
			f["coins"] = int(al("Wallet").get_balance())
		"daily":
			f["daily_completed"] = al("DailyDiscoveryManager").is_completed_today()
			f["collectible"] = int(al("Inventory").get_quantity(str(al("DailyDiscoveryManager").get("target_id"))))
	return f

## The game's own sighting path: the creature's scene, the controller that
## relays its sighting, and the player standing inside its alert distance but
## outside its flee distance; then a few frames.
func _see_creature() -> void:
	# Loaded, not named: in -s mode this script compiles before the autoloads the controller uses exist.
	var controller: Node = load("res://scripts/world_simulation/wildlife_controller.gd").new()
	root.add_child(controller)
	var creature: Node3D = load(SPECIES_SCENE).instantiate()
	root.add_child(creature)
	var player := Node3D.new()
	root.add_child(player)
	player.global_position = creature.global_position + Vector3((float(creature.get("alert_distance")) + float(creature.get("flee_distance"))) * 0.5, 0.0, 0.0)
	controller.set("player", player)
	controller.call("wire_actors")

func _norm(v: Variant) -> Variant:
	return JSON.parse_string(JSON.stringify(v, "", true))

func _write(path: String, text: String) -> void:
	var file := FileAccess.open(path, FileAccess.WRITE)
	file.store_string(text)
	file.close()
