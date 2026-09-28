extends Node

## Thin orchestrator: loads the save on boot and autosaves whenever the
## player makes a new discovery, after each farming moment (plant, harvest,
## found seed, farm milestone), and when the app is backgrounded or closed
## (which also captures watering and growth progress). Game-flow state
## (pause, current scene, future run-level flags) belongs here, not in the
## individual systems.

func _ready() -> void:
	SaveManager.load_game()
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	FarmManager.crop_planted.connect(_save.unbind(3))
	FarmManager.crop_harvested.connect(_save.unbind(4))
	FarmManager.seed_found.connect(_save.unbind(2))
	FarmManager.milestone_reached.connect(_save.unbind(3))
	InputManager.movement_mode_changed.connect(_save.unbind(1))

func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_PAUSED or what == NOTIFICATION_WM_CLOSE_REQUEST:
		_save()

func _save() -> void:
	SaveManager.save_game()

func _on_discovery_made(_definition: DiscoveryDefinition) -> void:
	SaveManager.save_game()
