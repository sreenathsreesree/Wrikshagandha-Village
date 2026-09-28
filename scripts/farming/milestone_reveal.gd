extends Node3D
class_name MilestoneReveal

## Holds a few decorative nodes that stay hidden until FarmManager reaches
## milestone_id, then grow in one after another — a lasting, quiet change
## in the world rather than a pop-up. Event-driven (one signal, no
## _process); if the milestone was already reached when this loads, the
## children simply start visible. Optionally gives pulse_node_path's
## reveal_pulse() (e.g. the garden's motes) a swell as it happens.

@export var milestone_id: String = ""
@export var stagger_seconds: float = 0.2
@export var pulse_node_path: NodePath

func _ready() -> void:
	var reached := FarmManager.is_milestone_reached(milestone_id)
	for child in get_children():
		var node := child as Node3D
		if node:
			node.visible = reached
	if not reached:
		FarmManager.milestone_reached.connect(_on_milestone_reached)

func _on_milestone_reached(reached_id: String, _message: String, _bonus_points: int) -> void:
	if reached_id != milestone_id:
		return
	FarmManager.milestone_reached.disconnect(_on_milestone_reached)
	var delay := 0.0
	for child in get_children():
		var node := child as Node3D
		if node == null:
			continue
		var target := node.scale
		node.scale = target * 0.05
		node.visible = true
		var tween := create_tween()
		tween.tween_property(node, "scale", target, 0.7).set_delay(delay) \
			.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		delay += stagger_seconds
	if pulse_node_path != NodePath():
		var pulse_node := get_node_or_null(pulse_node_path)
		if pulse_node and pulse_node.has_method("reveal_pulse"):
			pulse_node.call("reveal_pulse")
