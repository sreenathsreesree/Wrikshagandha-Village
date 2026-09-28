extends Node
class_name TimeOfDay

## Lightweight local day/night clock. Runs on an accelerated, configurable
## clock (day_length_seconds) — never real-world time, never the network.
## Knows nothing about lights or rendering; it just reports a 0..1 fraction
## of the day and which named phase that falls in. EnvironmentController
## (a sibling, wired by WorldSimulation) is the one that turns this into
## visuals, so TimeOfDay stays swappable on its own.

signal time_updated(day_fraction: float)
signal phase_changed(phase: String)

## Seconds for one full day/night cycle. Change this to make days
## longer/shorter without touching any other script.
@export var day_length_seconds: float = 600.0
@export_range(0.0, 1.0) var start_fraction: float = 0.28

var day_fraction: float = 0.0

const PHASE_ORDER := ["dawn", "morning", "afternoon", "evening", "night"]
const PHASE_START := {
	"dawn": 0.0,
	"morning": 0.1,
	"afternoon": 0.35,
	"evening": 0.65,
	"night": 0.85,
}

var _current_phase: String = "morning"

func _ready() -> void:
	day_fraction = start_fraction
	_current_phase = get_phase_for_fraction(day_fraction)

func _process(delta: float) -> void:
	if day_length_seconds <= 0.0:
		return
	day_fraction = fmod(day_fraction + delta / day_length_seconds, 1.0)
	time_updated.emit(day_fraction)
	var phase := get_phase_for_fraction(day_fraction)
	if phase != _current_phase:
		_current_phase = phase
		phase_changed.emit(phase)

func get_phase() -> String:
	return _current_phase

func get_phase_for_fraction(fraction: float) -> String:
	var result: String = PHASE_ORDER[0]
	for phase_name in PHASE_ORDER:
		var start_value: float = PHASE_START[phase_name]
		if fraction >= start_value:
			result = phase_name
	return result
