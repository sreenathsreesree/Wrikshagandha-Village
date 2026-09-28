extends Node3D
class_name HarvestBurst

## A tiny one-shot "particle" burst for the harvest moment: a few small
## glowing dots fly outward and shrink to nothing, then the whole burst
## frees itself. Built from plain MeshInstance3D + Tween rather than a
## particle system — cheaper and safer to hand-author correctly than
## GPUParticles3D for something this small.

@export var burst_radius: float = 0.35
@export var duration: float = 0.4

func _ready() -> void:
	var dots := get_children()
	for i in dots.size():
		var dot: Node3D = dots[i]
		var angle := (TAU / float(dots.size())) * float(i)
		var target := Vector3(cos(angle), 0.6, sin(angle)) * burst_radius
		var tween := create_tween()
		tween.set_parallel(true)
		tween.tween_property(dot, "position", target, duration).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(dot, "scale", Vector3.ZERO, duration).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)

	var cleanup_timer := get_tree().create_timer(duration + 0.1)
	cleanup_timer.timeout.connect(queue_free)
