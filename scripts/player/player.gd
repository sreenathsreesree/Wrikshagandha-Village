extends CharacterBody3D

## Moves the player from InputManager.move_vector (written by the on-screen
## joystick), with acceleration/deceleration and a smoothly-turning visual
## body. Resolves interaction against whatever Interactable is currently
## inside InteractionZone, toggles that Interactable's indicator as it
## enters/leaves range, and feeds it a live proximity value while nearby so
## approaching something builds anticipation before the harvest itself.

const MAX_SPEED := 4.3
const ACCELERATION := 15.0
const DECELERATION := 19.0
const TURN_SPEED := 11.0
const GRAVITY := 12.0
const BOB_HEIGHT := 0.035
const BOB_SPEED := 8.5
const SQUASH_AMOUNT := 0.045
const FOOTSTEP_INTERVAL := 0.32
const INTERACTION_RADIUS := 2.2
const DEAD_ZONE := 0.12

## Shapes the raw joystick deflection before it becomes a target speed.
## >1 gives finer, easier control near the center of the joystick (slow,
## precise movement) while still reaching full speed at full deflection —
## without the joystick itself needing to know anything about this.
const INPUT_RESPONSE_CURVE := 1.2

@onready var interaction_zone: Area3D = $InteractionZone
@onready var visual: Node3D = $Visual

var _nearby_interactables: Array[Interactable] = []
var _facing_angle: float = 0.0
var _bob_time: float = 0.0
var _footstep_timer: float = 0.0

func _ready() -> void:
	interaction_zone.area_entered.connect(_on_interaction_zone_area_entered)
	interaction_zone.area_exited.connect(_on_interaction_zone_area_exited)
	InputManager.interact_requested.connect(_on_interact_requested)
	_facing_angle = visual.rotation.y

func _physics_process(delta: float) -> void:
	var direction := _shape_input(InputManager.move_vector)

	if is_on_floor():
		velocity.y = 0.0
	else:
		velocity.y -= GRAVITY * delta

	var horizontal_velocity := Vector3(velocity.x, 0.0, velocity.z)
	var target_velocity := direction * MAX_SPEED
	var rate := ACCELERATION if direction.length_squared() > 0.0 else DECELERATION
	horizontal_velocity = horizontal_velocity.move_toward(target_velocity, rate * delta)
	velocity.x = horizontal_velocity.x
	velocity.z = horizontal_velocity.z

	move_and_slide()

	var speed := horizontal_velocity.length()
	_update_facing(direction, delta)
	_update_walk_bob(delta, speed)
	_update_footsteps(delta, speed)
	_update_nearby_proximity()

## Converts the raw (already 0..1, already dead-zoned by the joystick)
## input vector into a movement direction, applying a response curve to
## the magnitude only — direction is untouched, so diagonals stay
## correctly normalized regardless of the curve.
func _shape_input(move_vector: Vector2) -> Vector3:
	var magnitude := move_vector.length()
	if magnitude < DEAD_ZONE:
		return Vector3.ZERO
	var shaped_magnitude := pow(clamp(magnitude, 0.0, 1.0), INPUT_RESPONSE_CURVE)
	var shaped := move_vector.normalized() * shaped_magnitude
	return Vector3(shaped.x, 0.0, shaped.y)

func _update_facing(direction: Vector3, delta: float) -> void:
	if direction.length_squared() > 0.01:
		# Node3D's local forward is -Z, so solve sin(a)=dx, cos(a)=-dz.
		_facing_angle = atan2(direction.x, -direction.z)
	visual.rotation.y = lerp_angle(visual.rotation.y, _facing_angle, TURN_SPEED * delta)

func _update_walk_bob(delta: float, speed: float) -> void:
	var speed_ratio := clampf(speed / MAX_SPEED, 0.0, 1.0)
	if speed > 0.1:
		_bob_time += delta * BOB_SPEED * speed_ratio
		visual.position.y = abs(sin(_bob_time)) * BOB_HEIGHT
	else:
		_bob_time = 0.0
		visual.position.y = lerp(visual.position.y, 0.0, 10.0 * delta)

	# Subtle squash/stretch: a touch shorter and wider while accelerating
	# hard, a touch taller and thinner at full speed — smoothed so it never
	# snaps, and kept gentle so it reads as weight, not cartoon bounce.
	var target_stretch := speed_ratio * SQUASH_AMOUNT
	var target_scale := Vector3(1.0 - target_stretch * 0.5, 1.0 + target_stretch, 1.0 - target_stretch * 0.5)
	visual.scale = visual.scale.lerp(target_scale, 8.0 * delta)

func _update_footsteps(delta: float, speed: float) -> void:
	if speed <= 0.3:
		_footstep_timer = 0.0
		return
	_footstep_timer -= delta * (speed / MAX_SPEED)
	if _footstep_timer <= 0.0:
		_footstep_timer = FOOTSTEP_INTERVAL
		AmbientAudioManager.play_footstep_sound()

func _update_nearby_proximity() -> void:
	if _nearby_interactables.is_empty():
		return
	var nearest := _find_nearest_interactable()
	if nearest == null:
		return
	var distance := global_position.distance_to(nearest.global_position)
	var t := 1.0 - clampf(distance / INTERACTION_RADIUS, 0.0, 1.0)
	nearest.update_proximity(t)

## Shared by proximity feedback and the Interact press, so the object whose
## indicator is visibly responding is always the one that gets interacted
## with. (Previously the press went to whichever object entered range
## first, which could differ from the glowing one when several interactables
## — e.g. neighbouring farm plots — are in range at once.)
func _find_nearest_interactable() -> Interactable:
	var nearest: Interactable = null
	var nearest_distance := INF
	for interactable in _nearby_interactables:
		if not is_instance_valid(interactable):
			continue
		var distance := global_position.distance_to(interactable.global_position)
		if distance < nearest_distance:
			nearest_distance = distance
			nearest = interactable
	return nearest

func _on_interaction_zone_area_entered(area: Area3D) -> void:
	if not (area is Interactable):
		return
	var interactable: Interactable = area
	if not _nearby_interactables.has(interactable):
		_nearby_interactables.append(interactable)
		interactable.set_highlighted(true)

func _on_interaction_zone_area_exited(area: Area3D) -> void:
	if not (area is Interactable):
		return
	var interactable: Interactable = area
	_nearby_interactables.erase(interactable)
	interactable.set_highlighted(false)

func _on_interact_requested() -> void:
	_nearby_interactables = _nearby_interactables.filter(
		func(interactable: Interactable) -> bool: return is_instance_valid(interactable)
	)
	if _nearby_interactables.is_empty():
		return
	var target := _find_nearest_interactable()
	if target == null:
		return
	target.interact()
	# Only stop tracking it if it's actually gone (or about to be) after
	# this interaction — a one-shot discovery with remove_on_harvest still
	# gets dropped immediately so a second press can't double-harvest it
	# mid-animation, but a persistent multi-state interactable (e.g. a
	# FarmPlot cycling through prepare/plant/water/harvest) must stay
	# tracked so the next press keeps landing on it.
	if target.remove_on_harvest:
		_nearby_interactables.erase(target)
