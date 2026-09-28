extends Node3D
class_name WorldSimulation

## Coordinates independent environmental systems without letting them know
## about each other: TimeOfDay only knows "what fraction of the day is it",
## EnvironmentController only knows "how do I paint that", VegetationController
## only publishes player position, WildlifeController only wires actors, and
## Ambient is a seam for future effects. Any one of these can be swapped or
## removed without touching the others. configure() is called once by the
## owning world scene (e.g. meadow.gd) after everything else is ready.

@onready var time_of_day: TimeOfDay = $TimeOfDay
@onready var environment_controller: EnvironmentController = $Environment
@onready var vegetation_controller: VegetationController = $Vegetation
@onready var wildlife_controller: WildlifeController = $Wildlife
@onready var ambient_controller: AmbientController = $Ambient

func configure(player: Node3D, directional_light: DirectionalLight3D, world_environment: WorldEnvironment) -> void:
	environment_controller.directional_light = directional_light
	environment_controller.world_environment = world_environment
	vegetation_controller.player = player
	wildlife_controller.player = player
	wildlife_controller.wire_actors()

	time_of_day.time_updated.connect(_on_time_updated)
	_on_time_updated(time_of_day.day_fraction)

func _on_time_updated(day_fraction: float) -> void:
	environment_controller.apply_time(day_fraction)
