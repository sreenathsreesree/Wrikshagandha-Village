extends Resource
class_name WeatherSchedule

## The weather's data (M09.3, D-43): everything that decides when it rains,
## kept out of WeatherController. One file, data/weather/weather_schedule.tres.
## The same seed, day and fraction always give the same weather — the seed is
## fixed (never per save: weather is not saved, only derived from WorldClock).

## The fixed seed every day's slots are hashed with.
@export var weather_seed: int = 0
## Equal weather slots per day (4 = 150 s each in the 600 s day); the weather
## only changes at a slot boundary.
@export var slots_per_day: int = 4
## The chance (0..1) that a slot after always_clear_days rains.
@export_range(0.0, 1.0) var rain_chance: float = 0.25
## How much of a day the rain takes to start or stop at the edge of a rain
## slot (0.01 of the 600 s day = 6 s).
@export_range(0.0, 0.1) var ramp_fraction: float = 0.01
## Days 1 .. always_clear_days are always Clear (a new game opens Clear).
@export var always_clear_days: int = 1
