extends Node3D
class_name DiscoverySpawnPoint

## Placed in the world in place of a bare interactable instance. Spawns the
## configured discovery scene, waits for it to be harvested, then respawns
## it after DiscoveryDefinition.respawn_seconds — read from the discovery's
## own data, never hardcoded here. respawn_seconds <= 0 means "does not
## respawn automatically" (used for legendary finds) — and once collected,
## such a discovery is claimed for good (DiscoveryManager.is_claimed, M05.3):
## it isn't spawned again, not even after a relaunch or an area reload.

@export var discovery_scene: PackedScene

var _timer: Timer

func _ready() -> void:
	_timer = Timer.new()
	_timer.one_shot = true
	_timer.timeout.connect(_spawn)
	add_child(_timer)
	_spawn()

func _spawn() -> void:
	if discovery_scene == null:
		return
	var instance: DiscoveryInteractable = discovery_scene.instantiate()
	if DiscoveryManager.is_claimed(instance.discovery_id):
		instance.free()
		return
	instance.harvested.connect(_on_harvested)
	add_child(instance)
	instance.play_spawn_animation()

func _on_harvested(discovery_id: String) -> void:
	var definition := DiscoveryDatabase.get_definition(discovery_id)
	if definition == null or definition.respawn_seconds <= 0.0:
		return
	_timer.start(definition.respawn_seconds)
