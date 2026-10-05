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

## Game time (M09.2, D-42): WorldClock is the one clock and this is its one
## driver — _process advances it, so a parked area (the player indoors)
## pauses time. TimeOfDay (pinned, unchanged) only presents it: its own
## frame advance is switched off, it is given the clock's fraction, and its
## existing time_updated / phase_changed are emitted from here, so every
## listener (lighting, wildlife, an NPC's routine) keeps its path. The phase
## is read from the fraction; TimeOfDay's cached get_phase() is never used.
var _phase: String = ""

@onready var time_of_day: TimeOfDay = $TimeOfDay
@onready var environment_controller: EnvironmentController = $Environment
@onready var vegetation_controller: VegetationController = $Vegetation
@onready var wildlife_controller: WildlifeController = $Wildlife
@onready var ambient_controller: AmbientController = $Ambient
@onready var environmental_event_controller: EnvironmentalEventController = $EnvironmentalEvents
@onready var exploration_landmark_controller: ExplorationLandmarkController = $ExplorationLandmarks

func _ready() -> void:
	time_of_day.add_to_group(TIME_GROUP)
	time_of_day.set_process(false)
	time_of_day.day_fraction = WorldClock.get_fraction()
	_phase = time_of_day.get_phase_for_fraction(time_of_day.day_fraction)

func _process(delta: float) -> void:
	WorldClock.advance(delta)
	_present_time()

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
	wildlife_controller.set_time_phase(_phase)
	FarmManager.garden_interest_changed.connect(_on_garden_interest_changed)
	_on_garden_interest_changed(FarmManager.get_garden_interest())

## The clock's fraction into TimeOfDay, as its own frame advance used to:
## time_updated every frame, phase_changed when the phase changes.
func _present_time() -> void:
	var fraction := WorldClock.get_fraction()
	time_of_day.day_fraction = fraction
	time_of_day.time_updated.emit(fraction)
	var phase := time_of_day.get_phase_for_fraction(fraction)
	if phase != _phase:
		_phase = phase
		time_of_day.phase_changed.emit(phase)

func _on_time_updated(day_fraction: float) -> void:
	environment_controller.apply_time(day_fraction)

func _on_garden_interest_changed(level: float) -> void:
	wildlife_controller.set_attraction(FarmManager.WILDLIFE_ATTRACTION_KEY, level)
