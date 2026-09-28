extends Node3D
class_name HarvestBurst

## A tiny one-shot "particle" burst: a few small dots fly outward and
## shrink to nothing, then the whole burst frees itself. Built from plain
## MeshInstance3D + Tween rather than a particle system — cheaper and
## safer to hand-author correctly than GPUParticles3D for something this
## small.
##
## Defaults reproduce the original golden harvest burst exactly. Farming
## reuses the same scene for soil dust and water droplets by setting
## tint/vertical/start_height before adding it to the tree.

@export var burst_radius: float = 0.35
@export var duration: float = 0.4
## Upward (positive) or downward (negative) travel, relative to radius.
@export var vertical: float = 0.6
@export var start_height: float = 0.0
## Alpha 0 keeps the scene's own golden material untouched.
@export var tint: Color = Color(0, 0, 0, 0)
@export var tint_emission: float = 0.3

func _ready() -> void:
	var dots := get_children()
	var tinted := _make_tinted_material(dots)
	for i in dots.size():
		var dot := dots[i] as MeshInstance3D
		if dot == null:
			continue
		if tinted:
			dot.set_surface_override_material(0, tinted)
		dot.position = Vector3(0.0, start_height, 0.0)
		var angle := (TAU / float(dots.size())) * float(i)
		var target := Vector3(cos(angle) * burst_radius, start_height + vertical * burst_radius, sin(angle) * burst_radius)
		var tween := create_tween()
		tween.set_parallel(true)
		tween.tween_property(dot, "position", target, duration).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		tween.tween_property(dot, "scale", Vector3.ZERO, duration).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)

	var cleanup_timer := get_tree().create_timer(duration + 0.1)
	cleanup_timer.timeout.connect(queue_free)

## One copy per burst (never per dot), and only when tinted — the shared
## scene material must never be mutated, or every other burst would change.
func _make_tinted_material(dots: Array[Node]) -> StandardMaterial3D:
	if tint.a <= 0.0 or dots.is_empty():
		return null
	var first := dots[0] as MeshInstance3D
	if first == null:
		return null
	var source := first.get_surface_override_material(0) as StandardMaterial3D
	if source == null:
		return null
	var copy := source.duplicate() as StandardMaterial3D
	copy.albedo_color = tint
	copy.emission = tint
	copy.emission_energy_multiplier = tint_emission
	return copy
