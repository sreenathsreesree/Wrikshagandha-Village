extends Node3D
class_name DiscoveryIndicator

## Gentle bob + spin for the "something is discoverable here" indicator.
## Only animates while visible, so hidden indicators cost nothing.
##
## Also carries the (very subtle) rarity presentation: rare/very_rare/
## legendary items spin and bob a little more, and very_rare/legendary
## items occasionally show a brief unprompted glint even while the player
## is out of range — a reward for paying attention, never a marker.

@export var bob_height: float = 0.12
@export var bob_speed: float = 2.2
@export var spin_speed: float = 1.4

var rarity: String = "common"

var _base_y: float = 0.0
var _time: float = 0.0
var _idle_glint_timer: float = 0.0

func _ready() -> void:
	_base_y = position.y

func set_rarity(value: String) -> void:
	rarity = value
	match rarity:
		"rare":
			spin_speed *= 1.3
		"very_rare", "legendary":
			spin_speed *= 1.6
			bob_height *= 1.3
	if rarity == "very_rare" or rarity == "legendary":
		_idle_glint_timer = randf_range(10.0, 20.0)

func _process(delta: float) -> void:
	if visible:
		_time += delta
		position.y = _base_y + sin(_time * bob_speed) * bob_height
		rotate_y(spin_speed * delta)
		return

	if rarity != "very_rare" and rarity != "legendary":
		return
	_idle_glint_timer -= delta
	if _idle_glint_timer <= 0.0:
		_idle_glint_timer = randf_range(16.0, 30.0)
		_play_idle_glint()

func _play_idle_glint() -> void:
	visible = true
	scale = Vector3.ZERO
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE * 0.6, 0.4).set_trans(Tween.TRANS_SINE)
	tween.tween_property(self, "scale", Vector3.ZERO, 0.4).set_trans(Tween.TRANS_SINE)
	tween.tween_callback(_end_idle_glint)

func _end_idle_glint() -> void:
	visible = false
	scale = Vector3.ONE
