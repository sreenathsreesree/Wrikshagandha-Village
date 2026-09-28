extends Node
class_name EnvironmentController

## Turns a 0..1 day fraction into actual visuals — sun rotation/intensity,
## sky brightness, ambient light. Knows nothing about "dawn" or "night" as
## concepts, only the number; TimeOfDay knows nothing about lights. Wired
## together by WorldSimulation, so either side can change independently.

var directional_light: DirectionalLight3D
var world_environment: WorldEnvironment

const DAY_SKY := Color(0.62, 0.78, 0.9, 1.0)
const NIGHT_SKY := Color(0.04, 0.05, 0.1, 1.0)
const DAY_SUN := Color(1.0, 0.96, 0.85, 1.0)
const HORIZON_SUN := Color(1.0, 0.6, 0.35, 1.0)
const NIGHT_SUN := Color(0.4, 0.45, 0.65, 1.0)
const DAY_AMBIENT := Color(0.85, 0.82, 0.65, 1.0)
const NIGHT_AMBIENT := Color(0.42, 0.48, 0.62, 1.0)

func apply_time(day_fraction: float) -> void:
	# One full sun arc per day: height_factor is 1 at "noon" (0.5) and -1 at
	# "midnight" (0.0 / 1.0).
	var sun_angle := (day_fraction - 0.25) * TAU
	var height_factor := clampf(sin(sun_angle), -1.0, 1.0)

	if directional_light:
		directional_light.rotation.x = -clamp(sin(sun_angle) * 1.1, -1.4, 1.4)
		directional_light.rotation.y = deg_to_rad(35.0)
		directional_light.light_energy = clamp(0.15 + height_factor * 0.95, 0.05, 1.15)
		directional_light.light_color = _sun_color(height_factor)
		directional_light.shadow_enabled = height_factor > -0.15

	if world_environment and world_environment.environment:
		var env := world_environment.environment
		var brightness := clampf(0.5 + height_factor * 0.5, 0.05, 1.0)
		env.background_color = DAY_SKY.lerp(NIGHT_SKY, 1.0 - brightness)
		env.ambient_light_energy = clamp(0.2 + height_factor * 0.55, 0.1, 0.75)
		env.ambient_light_color = DAY_AMBIENT.lerp(NIGHT_AMBIENT, 1.0 - brightness)

func _sun_color(height_factor: float) -> Color:
	if height_factor > 0.3:
		return DAY_SUN
	if height_factor > -0.1:
		var t := clampf((height_factor + 0.1) / 0.4, 0.0, 1.0)
		return HORIZON_SUN.lerp(DAY_SUN, t)
	var t2 := clampf((height_factor + 1.0) / 0.9, 0.0, 1.0)
	return NIGHT_SUN.lerp(HORIZON_SUN, t2)
