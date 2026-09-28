extends Area3D
class_name Interactable

## Base script for anything in the world the player can walk up to and
## interact with (plants, herbs, mushrooms, stones, mysteries...). Placed on
## an Area3D so proximity is detected without blocking movement. If the
## scene has a child named "Indicator" it is shown/hidden automatically as
## the player enters/leaves range, reused for the harvest burst, and given
## its rarity presentation — no per-item code needed for any of that.

const HarvestBurstScene := preload("res://scenes/interactables/HarvestBurst.tscn")

signal harvested(discovery_id: String)

@export var discovery_id: String = ""
@export var remove_on_harvest: bool = true

func _ready() -> void:
	var definition := DiscoveryDatabase.get_definition(discovery_id)
	if definition == null:
		return
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator:
		indicator.set_rarity(definition.rarity)

func set_highlighted(active: bool) -> void:
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator:
		indicator.visible = active

## t in 0..1: how close the player currently is within interaction range.
## Called every frame by Player while this item is nearby, so approaching
## it visibly builds anticipation before the harvest itself. The whole
## object grows by a barely-perceptible amount on top of whatever its
## indicator does — a subtle "it notices you too" reaction that works for
## every item regardless of its mesh layout.
func update_proximity(t: float) -> void:
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator:
		indicator.set_proximity(t)
	scale = Vector3.ONE * (1.0 + t * 0.05)

func interact() -> bool:
	if discovery_id == "":
		push_warning("Interactable: no discovery_id set on %s" % name)
		return false
	var success := DiscoveryManager.discover(discovery_id)
	if success:
		harvested.emit(discovery_id)
		if remove_on_harvest:
			await _play_harvest_feedback()
			queue_free()
	return success

## Called by DiscoverySpawnPoint right after instantiating a fresh copy —
## a small scale-up plus a brief glow on the shared indicator, then back to
## normal. Existing discovery logic is untouched; this is presentation only.
func play_spawn_animation() -> void:
	scale = Vector3.ZERO
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE, 0.35) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	_play_spawn_glow()

func _play_spawn_glow() -> void:
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator == null:
		return
	indicator.visible = true
	indicator.scale = Vector3.ZERO
	var glow_tween := create_tween()
	glow_tween.tween_property(indicator, "scale", Vector3.ONE * 1.2, 0.25).set_trans(Tween.TRANS_SINE)
	glow_tween.tween_property(indicator, "scale", Vector3.ZERO, 0.3).set_trans(Tween.TRANS_SINE)
	glow_tween.tween_callback(_hide_indicator.bind(indicator))

func _hide_indicator(indicator: DiscoveryIndicator) -> void:
	indicator.visible = false
	indicator.scale = Vector3.ONE

func _play_harvest_feedback() -> void:
	monitorable = false
	_play_collected_burst()
	_spawn_harvest_particles()
	_play_harvest_sound()
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE * 1.25, 0.1) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "scale", Vector3.ZERO, 0.2) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	await tween.finished

## A quick sparkle "pop" on the shared indicator gem — reuses an object
## that already exists on every interactable instead of spawning a whole
## second effect for the same purpose.
func _play_collected_burst() -> void:
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator == null:
		return
	indicator.visible = true
	var burst := create_tween()
	burst.tween_property(indicator, "scale", Vector3.ONE * 1.8, 0.12) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	burst.tween_property(indicator, "scale", Vector3.ZERO, 0.18) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)

## A handful of small glowing dots scattering outward — the "small
## particles" moment. Spawned as a sibling (not a child of self) so it
## isn't squashed by this node's own shrink-to-zero tween.
func _spawn_harvest_particles() -> void:
	var parent := get_parent()
	if parent == null:
		return
	var burst: Node3D = HarvestBurstScene.instantiate()
	parent.add_child(burst)
	burst.global_position = global_position

## Placeholder hook for a real harvest SFX, routed through the shared audio
## manager. If no sound asset is assigned there yet, this is a safe no-op —
## the game runs identically either way.
func _play_harvest_sound() -> void:
	AmbientAudioManager.play_harvest_sound()
