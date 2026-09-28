extends Node3D
class_name DiscoveryIndicator

## Gentle bob + spin for the "something is discoverable here" indicator.
## Only animates while visible, so hidden indicators cost nothing.
##
## Carries two kinds of subtlety:
## - Rarity presentation: rare/very_rare/legendary items spin and bob a
##   little more, and very_rare/legendary items occasionally show a brief
##   unprompted glint even while the player is out of range — a reward for
##   paying attention, never a marker.
## - Proximity presentation: while visible, the gem brightens and speeds up
##   as the player gets closer (set_proximity, driven by Player each
##   frame), with a one-time chime the first time they get close — so
##   approaching something feels rewarding before the harvest itself.

@export var bob_height: float = 0.12
@export var bob_speed: float = 2.2
@export var spin_speed: float = 1.4

var rarity: String = "common"

@onready var _gem: MeshInstance3D = get_node_or_null("Gem") as MeshInstance3D

var _base_y: float = 0.0
var _time: float = 0.0
var _idle_glint_timer: float = 0.0
var _proximity: float = 0.0
var _base_emission_energy: float = 1.0
var _chime_played: bool = false

const CHIME_THRESHOLD := 0.85

func _ready() -> void:
	_base_y = position.y
	var material := _get_gem_material()
	if material:
		_base_emission_energy = material.emission_energy_multiplier

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

## t in 0..1, 0 = just entered range, 1 = right on top of it. Called every
## frame by Player only while at least one interactable is nearby, so this
## costs nothing the rest of the time.
func set_proximity(t: float) -> void:
	_proximity = clamp(t, 0.0, 1.0)
	var material := _get_gem_material()
	if material:
		material.emission_energy_multiplier = _base_emission_energy * (1.0 + _proximity * 1.2)
	if _proximity >= CHIME_THRESHOLD and not _chime_played:
		_chime_played = true
		AmbientAudioManager.play_proximity_chime()
	elif _proximity < CHIME_THRESHOLD * 0.6:
		_chime_played = false

func _process(delta: float) -> void:
	if visible:
		_time += delta
		var speed_boost := 1.0 + _proximity * 0.8
		position.y = _base_y + sin(_time * bob_speed * speed_boost) * bob_height
		rotate_y(spin_speed * speed_boost * delta)
		scale = Vector3.ONE * (1.0 + _proximity * 0.25)
		return

	if rarity != "very_rare" and rarity != "legendary":
		return
	_idle_glint_timer -= delta
	if _idle_glint_timer <= 0.0:
		_idle_glint_timer = randf_range(16.0, 30.0)
		_play_idle_glint()

func _get_gem_material() -> StandardMaterial3D:
	if _gem == null:
		return null
	return _gem.get_surface_override_material(0) as StandardMaterial3D

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
