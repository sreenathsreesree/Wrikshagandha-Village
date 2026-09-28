extends Area3D
class_name Interactable

## The generic interaction contract: anything in the world the player can
## tap, walk up to and interact with. Placed on an Area3D (collision layer
## "interactables") so proximity is detected without blocking movement.
## Player and InputManager only ever use what is declared here — never a
## concrete type — so a new kind of object (a door, a sign, an NPC) is a
## new subclass, not a change to either of them.
##
## The contract:
##   - is_interaction_available(): may it be tapped / interacted with now?
##   - interact() -> bool: the one generic entry point. Subclasses override
##     it; it may await (the caller's INTERACT state lasts until it returns).
##   - remove_on_harvest: one-shot object, gone after a successful interact()
##     (true), or persistent and interacted with again and again (false).
##   - get_available_interaction_verbs(): the verbs it offers right now, as
##     data (Verb) — empty whenever it's unavailable. interact_with_verb()
##     takes a selected verb back and performs it only if offered.
##   - get_interaction_metadata(): optional read-only description; nothing
##     reads it yet.
##   - set_highlighted() / update_proximity(): in-range presentation.
##   - set_tap_selected(): a tap chose this object — the same Indicator shows
##     at once (even out of range) with a small acknowledging pulse.
##
## Object behaviour lives in subclasses: DiscoveryInteractable (collect a
## discovery), FarmPlot (the farming state machine). If the scene has a
## child named "Indicator" it is shown/hidden automatically as the player
## enters/leaves range — no per-object code needed for that.

const HarvestBurstScene := preload("res://scenes/interactables/HarvestBurst.tscn")

## How much stronger a rarity-scaled feedback animation reads at higher
## rarity — still restrained, never a different animation, just a bit more
## of the same one. Shared presentation data (discoveries and crops).
const RARITY_INTENSITY := {
	"common": 1.0,
	"uncommon": 1.1,
	"rare": 1.2,
	"very_rare": 1.3,
	"legendary": 1.4,
}

## The generic interaction verbs (decision D-09): only those an existing
## object performs today; the rest are added with the behaviours that need
## them. Values are explicit and never reused or renumbered, so they stay
## stable if they are ever saved. Never spelled as strings anywhere.
enum Verb { COLLECT = 1, PLANT = 2, WATER = 3, HARVEST = 4 }

@export var remove_on_harvest: bool = true

## The acknowledging swell a tap gives the Indicator (DiscoveryIndicator.pulse).
const TAP_ACK_PULSE := 0.35

## The Indicator shows while the player is in range OR a tap has chosen this
## object and the player is on the way.
var _highlighted: bool = false
var _tap_selected: bool = false

## Availability is monitorable: an object that isn't monitorable is invisible
## to the player's InteractionZone and to tap rays alike, so both ways of
## reaching it agree. Subclasses change availability by toggling monitorable
## (a locked plot, a discovery mid-harvest).
func is_interaction_available() -> bool:
	return monitorable

## Override in a subclass. Returns whether the interaction did anything.
func interact() -> bool:
	return false

## What this object offers right now, in its current state. Nothing while
## it's unavailable. Subclasses describe their state in
## _get_interaction_verbs(); this wrapper is not overridden.
func get_available_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	if is_interaction_available():
		verbs = _get_interaction_verbs()
	return verbs

## Override in a subclass: the verbs its current state offers. Only what
## interact() would really do now — never a promise it can't keep.
func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	return verbs

## A selected verb, passed back generically (e.g. by a future verb UI —
## nothing calls this yet). Performed only if offered right now; returns
## whether anything happened.
func interact_with_verb(verb: Verb) -> bool:
	if not get_available_interaction_verbs().has(verb):
		return false
	@warning_ignore("redundant_await")
	return await _perform_interaction_verb(verb)

## Override when an object offers more than one verb at once. Today every
## object offers at most its default action, which is what interact() does.
func _perform_interaction_verb(_verb: Verb) -> bool:
	@warning_ignore("redundant_await")
	return await interact()

## Optional, read-only facts about this object for future systems (e.g. a
## verb or label). Empty by default; nothing reads it yet.
func get_interaction_metadata() -> Dictionary:
	return {}

func set_highlighted(active: bool) -> void:
	_highlighted = active
	_refresh_indicator()

## Immediate "your tap was recognised": the object's own Indicator, shown
## from the tap (before any walking) with a brief pulse, until the Player
## deselects it (interaction starting, walk cancelled or replaced). An
## unavailable object is never selected.
func set_tap_selected(active: bool) -> void:
	if active and not is_interaction_available():
		return
	_tap_selected = active
	_refresh_indicator()
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if active and indicator:
		indicator.pulse(TAP_ACK_PULSE)

func _refresh_indicator() -> void:
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator:
		indicator.visible = _highlighted or _tap_selected

## t in 0..1: how close the player currently is within interaction range.
## Called every frame by Player while this item is nearby, so approaching
## it visibly builds anticipation before the interaction itself. The whole
## object grows by a barely-perceptible amount on top of whatever its
## indicator does — a subtle "it notices you too" reaction that works for
## every object regardless of its mesh layout.
func update_proximity(t: float) -> void:
	var indicator := get_node_or_null("Indicator") as DiscoveryIndicator
	if indicator:
		indicator.set_proximity(t)
	scale = Vector3.ONE * (1.0 + t * 0.05)

## Placeholder hook for a real harvest SFX, routed through the shared audio
## manager. If no sound asset is assigned there yet, this is a safe no-op —
## the game runs identically either way.
func _play_harvest_sound() -> void:
	AmbientAudioManager.play_harvest_sound()
