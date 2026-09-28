extends Node

## Thin orchestrator: loads the save on boot and autosaves whenever the
## player makes a new discovery. Game-flow state (pause, current scene,
## future run-level flags) belongs here, not in the individual systems.

func _ready() -> void:
	SaveManager.load_game()
	DiscoveryManager.discovery_made.connect(_on_discovery_made)

func _on_discovery_made(_definition: DiscoveryDefinition) -> void:
	SaveManager.save_game()
