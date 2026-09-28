extends Node3D
class_name EnvironmentalEvent

## A small, data-driven "something just happened here" trigger. Placed
## directly in the world near the actor/prop it orchestrates, it does
## nothing on its own — EnvironmentalEventController finds it via the
## "environmental_event" group and does one shared distance check per
## frame for every event in the scene, calling fire() when the player
## steps inside trigger_radius and can_trigger() allows it.
##
## Deliberately thin: every actual effect (a bird fleeing, a butterfly
## flying to a spot and landing, motes pulsing) is implemented by the
## existing actor/prop it points at via NodePath, so this script never
## grows a parallel wildlife or discovery system — it only decides *when*
## to ask an existing thing to do what it already knows how to do.

enum EventType { WILDLIFE_DISTURBANCE, BUTTERFLY_LEAD, ENVIRONMENTAL_REVEAL }

@export var event_type: EventType = EventType.WILDLIFE_DISTURBANCE
@export var trigger_radius: float = 3.5
@export var cooldown_seconds: float = 75.0
@export var repeatable: bool = true

## Purely informational/gating: if set and DiscoveryManager already has
## this id, the event stops firing — once the player has genuinely found
## what this event was pointing at, the world doesn't need to keep
## drawing attention to it. Reuses DiscoveryManager's existing persisted
## state instead of the event inventing its own.
@export var related_discovery_id: String = ""

## WILDLIFE_DISTURBANCE: every actor in this list is startled at once,
## even if the player isn't within that individual actor's own
## flee_distance yet — reads as a small group reacting together.
@export var actor_paths: Array[NodePath] = []

## BUTTERFLY_LEAD: the one butterfly that leads, and the node whose
## position it flies to before landing again.
@export var lead_actor_path: NodePath
@export var lead_target_path: NodePath

## Shared optional flourish: a node with a reveal_pulse() method (e.g. a
## GlowingMotes instance) that gets a brief, subtle pulse. For
## ENVIRONMENTAL_REVEAL this is the whole effect; for BUTTERFLY_LEAD it
## fires once the butterfly actually lands, not at trigger time.
@export var reveal_node_path: NodePath

var _on_cooldown: bool = false
var _triggered_once: bool = false

func _ready() -> void:
	add_to_group("environmental_event")

func can_trigger() -> bool:
	if _on_cooldown:
		return false
	if not repeatable and _triggered_once:
		return false
	if related_discovery_id != "" and DiscoveryManager.is_discovered(related_discovery_id):
		return false
	return true

## Called by EnvironmentalEventController once the player is within
## trigger_radius and can_trigger() is true.
func fire() -> void:
	_triggered_once = true
	_start_cooldown()
	match event_type:
		EventType.WILDLIFE_DISTURBANCE:
			_fire_wildlife_disturbance()
		EventType.BUTTERFLY_LEAD:
			_fire_butterfly_lead()
		EventType.ENVIRONMENTAL_REVEAL:
			_fire_environmental_reveal()

func _start_cooldown() -> void:
	_on_cooldown = true
	get_tree().create_timer(cooldown_seconds).timeout.connect(_end_cooldown)

func _end_cooldown() -> void:
	_on_cooldown = false

func _fire_wildlife_disturbance() -> void:
	for actor_path in actor_paths:
		var actor := get_node_or_null(actor_path) as WildlifeActor
		if actor == null or not is_instance_valid(actor):
			continue
		actor.startle()

func _fire_butterfly_lead() -> void:
	var butterfly := get_node_or_null(lead_actor_path) as WildlifeButterfly
	if butterfly == null or not is_instance_valid(butterfly):
		return
	if butterfly.is_leading() or butterfly.state == "flee":
		return
	var target := get_node_or_null(lead_target_path) as Node3D
	if target == null or not is_instance_valid(target):
		return
	butterfly.lead_to(target.global_position)
	if reveal_node_path != NodePath():
		butterfly.lead_finished.connect(_fire_environmental_reveal, CONNECT_ONE_SHOT)

func _fire_environmental_reveal() -> void:
	var node := get_node_or_null(reveal_node_path)
	if node == null or not is_instance_valid(node):
		return
	if node.has_method("reveal_pulse"):
		node.call("reveal_pulse")
