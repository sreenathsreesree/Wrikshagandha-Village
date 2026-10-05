extends Node

## The world's time (M09.2, D-42): the one authoritative clock of the game.
## Holds a whole day number (from START_DAY) and the fraction of that day
## (0 <= fraction < 1). Game time only — never the system clock, and no time
## passes while the app is closed.
##
## Only the area's WorldSimulation advances it, once per frame, so while the
## Meadow is parked (the player indoors, D-31/D-33) nothing advances it and
## time pauses. Only SaveManager restores it, at boot. Nothing else sets it:
## there is no time-skip. TimeOfDay (time_of_day.gd, pinned) is only how an
## area presents this clock — WorldSimulation copies the fraction into it.

const DAY_LENGTH_SECONDS := 600.0
const START_DAY := 1
const START_FRACTION := 0.28

var _day: int = START_DAY
var _fraction: float = START_FRACTION

## The current day, from START_DAY.
func get_day() -> int:
	return _day

## How far through the current day, 0 <= fraction < 1.
func get_fraction() -> float:
	return _fraction

## For the area's WorldSimulation only, once per frame. Each crossing of the
## day boundary raises the day by exactly one and wraps the fraction.
func advance(delta: float) -> void:
	if not is_finite(delta) or delta <= 0.0:
		return
	var total := _fraction + delta / DAY_LENGTH_SECONDS
	var whole := floori(total)
	_day += whole
	_fraction = total - whole

## For SaveManager only.
func get_save_data() -> Dictionary:
	return {"day": _day, "fraction": _fraction}

## For SaveManager, at boot. An empty section (a save from before M09.2)
## starts at START_DAY / START_FRACTION, like a new game; a malformed one
## does the same, with a warning — never a half-restored clock.
func apply_save_data(data: Dictionary) -> void:
	_day = START_DAY
	_fraction = START_FRACTION
	if data.is_empty():
		return
	var day: Variant = data.get("day")
	var fraction: Variant = data.get("fraction")
	if not _is_number(day) or not _is_number(fraction):
		push_warning("WorldClock: saved world time is not two numbers; starting at day %d" % START_DAY)
		return
	if float(day) < START_DAY or float(day) != floorf(float(day)) or float(fraction) < 0.0 or float(fraction) >= 1.0:
		push_warning("WorldClock: saved world time is out of range; starting at day %d" % START_DAY)
		return
	_day = int(day)
	_fraction = float(fraction)

func _is_number(value: Variant) -> bool:
	return (typeof(value) == TYPE_INT or typeof(value) == TYPE_FLOAT) and is_finite(float(value))
