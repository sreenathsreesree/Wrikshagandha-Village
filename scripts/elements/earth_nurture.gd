extends Interactable
class_name EarthNurture

## Earth — Nurture (M11.1, D-47): a dormant wild plant that answers care.
## Used through the generic interaction flow (Verb.USE), it runs one
## temporary cycle — dormant → awakening (its Growth children grow in,
## staggered) → hold → relax → dormant — and is unavailable for the whole
## cycle, so a second interaction can't restart or stack it. Afterwards it
## can be used again, without limit.
##
## Reusable and self-contained: no place, scene path, autoload, reward,
## save, farming or HUD knowledge, and no element data — it is Earth by
## what it does. Only the Growth children are animated, never this node's
## own scale (the Interactable base sets that every frame for proximity).
## The cycle runs on tweens bound to this node, so it pauses with the
## Meadow while the area is parked and resumes on return.
##
## The scene authors each Growth child at its awake size, as a pivot at
## ground level; the dormant plant is the same plant at dormant_scale.

@export var grow_seconds: float = 0.7
@export var stagger_seconds: float = 0.2
@export var hold_seconds: float = 6.0
@export var relax_seconds: float = 1.5
@export_range(0.05, 1.0) var dormant_scale: float = 0.4

@onready var _growth: Node3D = $Growth

var _awake_scales: Array[Vector3] = []

func _ready() -> void:
	remove_on_harvest = false
	for child in _growth.get_children():
		var part := child as Node3D
		_awake_scales.append(part.scale)
		part.scale = part.scale * dormant_scale

func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	verbs.append(Verb.USE)
	return verbs

## Starts the cycle and returns once the plant has grown in; the hold and
## the relaxation carry on by themselves. Refused while a cycle is running.
func interact() -> bool:
	if not monitorable:
		return false
	monitorable = false
	var parts := _growth.get_children()
	var grow := create_tween().set_parallel(true)
	for i in parts.size():
		grow.tween_property(parts[i], "scale", _awake_scales[i], grow_seconds) \
			.set_delay(i * stagger_seconds).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	await grow.finished
	_hold_then_relax()
	return true

func _hold_then_relax() -> void:
	var parts := _growth.get_children()
	var rest := create_tween()
	rest.tween_interval(hold_seconds)
	for i in parts.size():
		if i > 0:
			rest.parallel()
		rest.tween_property(parts[i], "scale", _awake_scales[i] * dormant_scale, relax_seconds) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	rest.chain().tween_callback(_on_dormant)

func _on_dormant() -> void:
	monitorable = true
