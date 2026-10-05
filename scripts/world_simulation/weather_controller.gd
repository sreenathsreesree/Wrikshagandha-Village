extends Node
class_name WeatherController

## Simple weather (M09.3, D-43): Clear or Rain, a pure function of the
## WeatherSchedule's seed and the world's day and fraction. Holds no clock and
## saves nothing — WorldSimulation (the only reader of WorldClock) hands it the
## day and fraction every frame through apply_time(), so the parked Meadow (the
## player indoors) pauses the weather with the time, and a relaunch
## reconstructs exactly the same weather and rain intensity.
##
## The weather changes only at a slot boundary; the rain fades in and out over
## the schedule's ramp at the edges of a rain spell. weather_changed fires only
## when the weather changes during play — never for the first resolution (a new
## game, a load, a fresh area). It is the hook for reactions (M09.4); nothing
## here reacts. The rain emitter is kept above the player from apply_time, so
## no frame loop of its own.

signal weather_changed(weather: String)

const CLEAR := "clear"
const RAIN := "rain"
## Where the rain emitter sits above the player.
const RAIN_HEIGHT := 9.0
## The drops' colour at full rain; their alpha follows the intensity.
const RAIN_COLOR := Color(0.78, 0.84, 0.92, 0.55)

@export var schedule: WeatherSchedule
@export var rain_path: NodePath = ^"../Rain"

## Set by WorldSimulation.configure(): the rain falls around it.
var player: Node3D

var _weather: String = ""  # "" until the first apply_time()
var _rain_intensity: float = 0.0

@onready var _rain: CPUParticles3D = get_node_or_null(rain_path) as CPUParticles3D

## "clear" or "rain" — "" before WorldSimulation has given it the time.
func get_weather() -> String:
	return _weather

func is_raining() -> bool:
	return _weather == RAIN

## 0 (Clear) .. 1 (full rain), including the fade at the edges of a spell.
func get_rain_intensity() -> float:
	return _rain_intensity

## For WorldSimulation only, every frame, with WorldClock's day and fraction.
func apply_time(day: int, fraction: float) -> void:
	var weather := weather_at(day, fraction)
	_rain_intensity = rain_intensity_at(day, fraction)
	_show_rain()
	if weather == _weather:
		return
	var first := _weather == ""
	_weather = weather
	if not first:
		weather_changed.emit(weather)

## The weather at a day and fraction — the same answer every time.
func weather_at(day: int, fraction: float) -> String:
	return RAIN if _slot_rains(day, _slot(fraction)) else CLEAR

## The rain intensity at a day and fraction: 0 when Clear; in a rain slot, a
## fade over ramp_fraction at an edge whose neighbour slot is Clear.
func rain_intensity_at(day: int, fraction: float) -> float:
	var slot := _slot(fraction)
	if not _slot_rains(day, slot):
		return 0.0
	var width := 1.0 / schedule.slots_per_day
	var into := fraction - slot * width
	var ramp := maxf(schedule.ramp_fraction, 0.000001)
	var fade_in := 1.0
	var previous_rains := _slot_rains(day, slot - 1) if slot > 0 else _slot_rains(day - 1, schedule.slots_per_day - 1)
	if not previous_rains:
		fade_in = clampf(into / ramp, 0.0, 1.0)
	var fade_out := 1.0
	var next_rains := _slot_rains(day, slot + 1) if slot < schedule.slots_per_day - 1 else _slot_rains(day + 1, 0)
	if not next_rains:
		fade_out = clampf((width - into) / ramp, 0.0, 1.0)
	return minf(fade_in, fade_out)

func _slot(fraction: float) -> int:
	return clampi(floori(fraction * schedule.slots_per_day), 0, schedule.slots_per_day - 1)

func _slot_rains(day: int, slot: int) -> bool:
	if day <= schedule.always_clear_days:
		return false
	return _hash(schedule.weather_seed, day, slot) < int(schedule.rain_chance * 4294967296.0)

## A 32-bit integer hash of (seed, day, slot): the same everywhere, no random
## state. Every product stays below 2^63, so GDScript's integers never wrap.
static func _hash(seed_value: int, day: int, slot: int) -> int:
	var x := ((seed_value * 73856093) ^ (day * 19349663) ^ (slot * 83492791)) & 0xFFFFFFFF
	x = x ^ (x >> 16)
	x = (x * 0x7feb352d) & 0xFFFFFFFF
	x = x ^ (x >> 15)
	x = (x * 0x2c1b3c6d) & 0xFFFFFFFF
	x = x ^ (x >> 16)
	return x

func _show_rain() -> void:
	if _rain == null:
		return
	_rain.emitting = _rain_intensity > 0.0
	_rain.color = Color(RAIN_COLOR, RAIN_COLOR.a * _rain_intensity)
	if player != null:
		_rain.global_position = player.global_position + Vector3(0.0, RAIN_HEIGHT, 0.0)
