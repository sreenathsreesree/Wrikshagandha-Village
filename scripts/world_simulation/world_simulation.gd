extends Node3D
class_name WorldSimulation

## Coordinates independent environmental systems without letting them know
## about each other: TimeOfDay only knows "what fraction of the day is it",
## EnvironmentController only knows "how do I paint that", VegetationController
## only publishes player position, WildlifeController only wires actors
## and relays phase/attraction changes to them, and
## Ambient is a seam for future effects. Any one of these can be swapped or
## removed without touching the others. configure() is called once by the
## owning world scene (e.g. meadow.gd) after everything else is ready.

## The area's day clock joins this group so things living in the same area
## (an NPC's routine, M09.1) can find it without a path into this scene.
const TIME_GROUP := &"time_of_day"

@onready var time_of_day: TimeOfDay = $TimeOfDay
@onready var environment_controller: EnvironmentController = $Environment
@onready var vegetation_controller: VegetationController = $Vegetation
@onready var wildlife_controller: WildlifeController = $Wildlife
@onready var ambient_controller: AmbientController = $Ambient
@onready var environmental_event_controller: EnvironmentalEventController = $EnvironmentalEvents
@onready var exploration_landmark_controller: ExplorationLandmarkController = $ExplorationLandmarks

func _ready() -> void:
	time_of_day.add_to_group(TIME_GROUP)

func configure(player: Node3D, directional_light: DirectionalLight3D, world_environment: WorldEnvironment) -> void:
	environment_controller.directional_light = directional_light
	environment_controller.world_environment = world_environment
	vegetation_controller.player = player
	wildlife_controller.player = player
	wildlife_controller.wire_actors()
	environmental_event_controller.player = player
	exploration_landmark_controller.player = player

	time_of_day.time_updated.connect(_on_time_updated)
	_on_time_updated(time_of_day.day_fraction)

	# Wildlife hears about the day's phase and the garden's pull only when
	# either changes — two relays, no polling. FarmManager owns what the
	# garden is worth; wildlife only ever sees a key and a strength.
	time_of_day.phase_changed.connect(wildlife_controller.set_time_phase)
	wildlife_controller.set_time_phase(time_of_day.get_phase())
	FarmManager.garden_interest_changed.connect(_on_garden_interest_changed)
	_on_garden_interest_changed(FarmManager.get_garden_interest())

func _on_time_updated(day_fraction: float) -> void:
	environment_controller.apply_time(day_fraction)

func _on_garden_interest_changed(level: float) -> void:
	wildlife_controller.set_attraction(FarmManager.WILDLIFE_ATTRACTION_KEY, level)
