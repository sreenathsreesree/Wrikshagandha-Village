extends Area3D
class_name Interactable

## Base script for anything in the world the player can walk up to and
## interact with (plants, herbs, mushrooms, stones now; animals, secrets
## later). Placed on an Area3D so proximity is detected without blocking
## movement. If the scene has a child named "Indicator" it is shown/hidden
## automatically as the player enters/leaves range — no per-item code needed.

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
	if success and remove_on_harvest:
		set_highlighted(false)
		await _play_harvest_feedback()
		queue_free()
	return success

func _play_harvest_feedback() -> void:
	monitorable = false
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE * 1.25, 0.1) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "scale", Vector3.ZERO, 0.2) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	await tween.finished
