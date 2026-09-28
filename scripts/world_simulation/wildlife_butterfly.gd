extends WildlifeActor
class_name WildlifeButterfly

## Adds hover height, wing flapping, a "landed" pose, and a one-shot
## "lead" sequence on top of the shared wander/pause/flee state machine —
## the only creature that needs anything beyond the base behavior.
##
## "lead" is a fourth, transient state used by EnvironmentalEvent's
## BUTTERFLY_LEAD events: the butterfly flies straight to a given point,
## lands (re-entering the ordinary "pause" state), and emits
## lead_finished. It is not part of the normal idle/wander/pause/flee
## cycle and nothing else ever puts the butterfly into it, so plain
## wildlife butterflies behave exactly as before unless something calls
## lead_to() directly. The base class's own player-proximity flee check
## still runs first every frame, so a butterfly that's leading still
## flees like normal if the player gets close enough — leading never
## overrides that safety behavior, it only gets interrupted by it.

signal lead_finished

@export var hover_height: float = 0.35
@export var land_height: float = 0.06
@export var flap_speed: float = 12.0

const LEAD_SPEED_MULTIPLIER := 1.6
const LEAD_MAX_DURATION := 8.0
const LEAD_ARRIVAL_DISTANCE := 0.2

@onready var wing_left: Node3D = $WingLeft
@onready var wing_right: Node3D = $WingRight

var _flap_time: float = 0.0
var _leading: bool = false
var _lead_target: Vector3
var _lead_timeout: float = 0.0

func is_leading() -> bool:
	return _leading

## Starts a short, one-shot flight to target_position, then lands and
## emits lead_finished. Refuses if already leading or currently fleeing —
## callers should generally check is_leading() themselves, but this stays
## safe either way so it can never be started twice or clobber a flee.
func lead_to(target_position: Vector3) -> void:
	if _leading or state == "flee":
		return
	_leading = true
	state = "lead"
	_lead_target = target_position
	_lead_timeout = LEAD_MAX_DURATION

func _process(delta: float) -> void:
	var was_leading := state == "lead"
	super._process(delta)
	if was_leading:
		if state == "flee":
			# The base class's own proximity check interrupted the lead —
			# let it, and don't leave the flag stuck so lead_to() can be
			# used again once the actor settles back down.
			_leading = false
		elif state == "lead":
			_process_lead(delta)

	_flap_time += delta * flap_speed
	var flap := sin(_flap_time)
	wing_left.rotation.z = flap * 0.6
	wing_right.rotation.z = -flap * 0.6

	var target_height := land_height if state == "pause" else hover_height
	position.y = lerp(position.y, target_height, 4.0 * delta)

func _process_lead(delta: float) -> void:
	_lead_timeout -= delta
	_move_toward(_lead_target, move_speed * LEAD_SPEED_MULTIPLIER, delta)
	if position.distance_to(_lead_target) < LEAD_ARRIVAL_DISTANCE or _lead_timeout <= 0.0:
		_leading = false
		_enter_pause()
		lead_finished.emit()
