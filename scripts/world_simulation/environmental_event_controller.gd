extends Node
class_name EnvironmentalEventController

## Sibling of WildlifeController/AmbientController under WorldSimulation.
## Finds every EnvironmentalEvent placed anywhere in the world (via the
## "environmental_event" group — same pattern WildlifeController uses for
## actors) and does one shared proximity check per frame for all of them,
## instead of every event running its own _process or Area3D. Cheap even
## as more events are added later, since the world only ever has a
## handful active at once.
##
## Since M09.4 (D-44) an event can wait for a weather instead of the player:
## the distance loop skips it and on_weather_changed() fires it.

var player: Node3D

func _process(_delta: float) -> void:
	if player == null:
		return
	for node in get_tree().get_nodes_in_group("environmental_event"):
		var event := node as EnvironmentalEvent
		if event == null or event.trigger_weather != "":
			continue
		var distance := event.global_position.distance_to(player.global_position)
		if event.trigger_on_arrival:
			# Presence is tracked every frame so leaving is always noticed,
			# even while the event couldn't fire.
			if event.update_player_presence(distance) and event.can_trigger():
				event.fire()
			continue
		if distance <= event.trigger_radius and event.can_trigger():
			event.fire()

## The weather changed during play (WorldSimulation relays WeatherController's
## weather_changed, M09.4, D-44): every event waiting for that weather fires,
## through the same can_trigger() and fire() as a proximity event.
func on_weather_changed(weather: String) -> void:
	for node in get_tree().get_nodes_in_group("environmental_event"):
		var event := node as EnvironmentalEvent
		if event == null or event.trigger_weather == "" or event.trigger_weather != weather:
			continue
		if event.can_trigger():
			event.fire()
