extends Interactable
class_name DiscoveryInteractable

## A one-shot discovery in the world (plants, herbs, mushrooms, stones,
## mysteries...) on the generic Interactable contract. interact() collects
## it through DiscoveryManager (points, journal, collection, persistence all
## happen there), then it plays its harvest feedback and removes itself.
## The Indicator child is given the discovery's rarity presentation and
## reused for the harvest burst — no per-item code needed for any of that.
##
## Harvest also gets a brief category-flavored "windup" before the pop —
## driven entirely by DiscoveryDefinition.category/.rarity through the two
## data tables below, never by a per-item script.

## Each category's personality: a target scale shape and a small upward
## lift, applied briefly before the shared pop-and-shrink. "flower" blooms
## wide, "fungus" squashes, "mineral" gathers itself (paired with the
## existing indicator sparkle burst), everything else gets a gentle lift.
const CATEGORY_WINDUP := {
	"flower": {"scale": Vector3(1.15, 1.3, 1.15), "lift": 0.02},
	"fungus": {"scale": Vector3(1.2, 0.7, 1.2), "lift": 0.0},
	"mineral": {"scale": Vector3(0.92, 0.92, 0.92), "lift": 0.0},
	"plant": {"scale": Vector3(1.05, 1.15, 1.05), "lift": 0.06},
	"insect": {"scale": Vector3(1.1, 1.1, 1.1), "lift": 0.04},
	"animal": {"scale": Vector3(1.1, 1.1, 1.1), "lift": 0.04},
	"mystery": {"scale": Vector3(1.1, 1.1, 1.1), "lift": 0.05},
}
const DEFAULT_WINDUP := {"scale": Vector3(1.05, 1.15, 1.05), "lift": 0.06}

const WINDUP_DURATION := 0.09

signal harvested(discovery_id: String)

@export var discovery_id: String = ""

var _definition: DiscoveryDefinition

func _ready() -> void:
	_definition = DiscoveryDatabase.get_definition(discovery_id)
	if _definition == null:
		return
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator:
		indicator.set_rarity(_definition.rarity)

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

func get_interaction_metadata() -> Dictionary:
	return {"discovery_id": discovery_id}

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

## APPROACH -> interact() -> (this) tiny anticipation/personality windup ->
## pop -> burst/particles/sound -> shrink away. Kept fast throughout — the
## windup is under a tenth of a second — so it never feels slow on mobile.
func _play_harvest_feedback() -> void:
	monitorable = false
	await _play_category_windup()
	_play_collected_burst()
	_spawn_harvest_particles()
	_play_harvest_sound()
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE * 1.25, 0.1) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "scale", Vector3.ZERO, 0.2) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_IN)
	await tween.finished

func _play_category_windup() -> void:
	var category: String = _definition.category if _definition else "plant"
	var rarity: String = _definition.rarity if _definition else "common"
	var preset: Dictionary = CATEGORY_WINDUP.get(category, DEFAULT_WINDUP)
	var intensity: float = RARITY_INTENSITY.get(rarity, 1.0)

	var preset_scale: Vector3 = preset["scale"]
	var windup_scale := Vector3.ONE + (preset_scale - Vector3.ONE) * intensity
	var lift: float = preset["lift"] * intensity

	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(self, "scale", windup_scale, WINDUP_DURATION) \
		.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	if lift > 0.0:
		tween.tween_property(self, "position:y", position.y + lift, WINDUP_DURATION) \
			.set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
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
