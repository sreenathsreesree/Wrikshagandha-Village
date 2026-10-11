extends Node

## Thin orchestrator: loads the save on boot and autosaves whenever the
## player makes a new discovery, after each farming moment (plant, harvest,
## found seed, farm milestone), after each sale (M06.2: the Inventory and
## the Wallet saved together), when an NPC's friendship rises (M08.5), when
## a request is accepted or completed (M08.6), after an NPC trade (M08.7),
## and when the app is backgrounded or closed (which also captures
## watering and growth progress). Game-flow state (pause, current scene, future
## run-level flags) belongs here, not in the individual systems.
##
## Save reliability (M15.4): progress that pays or records something is saved
## when it happens, so a force-stop can't lose it — each once-ever exploration
## reward (a landmark, a secret, the curiosity bonus, every secret found) and
## the daily bonus, at its own signal: the state and points are set before the
## signal fires, and the rewards that follow a secret (curiosity, every secret)
## save again at theirs. A repeat discovery collection saves deferred, after
## every listener of the same signal has finished — the collectible
## (Inventory), any found seed (FarmManager) and the daily bonus are added by
## those listeners. Saving writes state only; it never pays, so no reward can
## be paid twice. The world time still saves with every save (no save of its
## own, by decision).
##
## Wildlife Journal (M14.1a, D-59): a species seen for the first time is saved
## at once (JournalManager.wildlife_sighted, once ever per species), so a
## force-stop can't lose a sighting. A sighting pays nothing.

func _ready() -> void:
	SaveManager.load_game()
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	FarmManager.crop_planted.connect(_save.unbind(3))
	FarmManager.crop_harvested.connect(_save.unbind(4))
	FarmManager.seed_found.connect(_save.unbind(2))
	FarmManager.milestone_reached.connect(_save.unbind(3))
	Market.produce_sold.connect(_save.unbind(4))
	Relationships.friendship_changed.connect(_save.unbind(2))
	Requests.request_accepted.connect(_save.unbind(1))
	Requests.request_completed.connect(_save.unbind(4))
	Market.items_traded.connect(_save.unbind(3))
	InputManager.movement_mode_changed.connect(_save.unbind(1))
	ExplorationManager.landmark_reached.connect(_save.unbind(2))
	ExplorationManager.secret_location_found.connect(_save.unbind(2))
	ExplorationManager.curiosity_bonus_awarded.connect(_save.unbind(2))
	ExplorationManager.all_secret_locations_found.connect(_save.unbind(1))
	DailyDiscoveryManager.daily_completed.connect(_save.unbind(2))
	DiscoveryManager.discovery_repeated.connect(_save.unbind(1), CONNECT_DEFERRED)
	JournalManager.wildlife_sighted.connect(_save.unbind(1))

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_WM_CLOSE_REQUEST:
		_save()

func _save() -> void:
	SaveManager.save_game()

func _on_discovery_made(_definition: DiscoveryDefinition) -> void:
	SaveManager.save_game()
