extends Area3D
class_name Interactable

## Base script for anything in the world the player can walk up to and
## interact with (plants, herbs, mushrooms, stones, mysteries...). Placed on
## an Area3D so proximity is detected without blocking movement. If the
## scene has a child named "Indicator" it is shown/hidden automatically as
## the player enters/leaves range, and reused for the harvest burst — no
## per-item code needed.

signal harvested(discovery_id: String)

@export var discovery_id: String = ""
@export var remove_on_harvest: bool = true

func set_highlighted(active: bool) -> void:
	var indicator := get_node_or_null("Indicator") as Node3D
	if indicator:
		indicator.visible = active

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

func _play_harvest_feedback() -> void:
	monitorable = false
	_play_collected_burst()
	_play_harvest_sound()
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE * 1.25, 0.1) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "scale", Vector3.ZERO, 0.2) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	await tween.finished

## A quick sparkle "pop" on the shared indicator gem — the closest thing to
## a particle burst this milestone needs, reusing an object that already
## exists on every interactable instead of spawning a new particle system.
func _play_collected_burst() -> void:
	var indicator := get_node_or_null("Indicator") as Node3D
	if indicator == null:
		return
	indicator.visible = true
	var burst := create_tween()
	burst.tween_property(indicator, "scale", Vector3.ONE * 1.8, 0.12) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	burst.tween_property(indicator, "scale", Vector3.ZERO, 0.18) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)

## Placeholder hook for a real harvest SFX. Left deliberately silent — no
## audio asset exists yet, and referencing a missing one would break the
## project. Wire an AudioStreamPlayer3D here once real sound is added.
func _play_harvest_sound() -> void:
	pass
