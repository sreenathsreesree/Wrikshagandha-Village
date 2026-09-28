extends CharacterBody3D

## Moves the player from InputManager.move_vector (written by the on-screen
## joystick), with acceleration/deceleration and a smoothly-turning visual
## body. Interaction is touch-to-interact: InputManager raycasts a tap and
## names the Interactable that was touched; the player walks toward it and
## interacts the moment it's inside InteractionZone — the same interaction
## range the zone has always defined, for every kind of Interactable. The
## zone also toggles each Interactable's indicator as it enters/leaves range
## and feeds it a live proximity value, so approaching something builds
## anticipation before the harvest itself.
##
## Two sources feed the same movement code: InputManager.move_vector
## (joystick and keyboard), or a tap-started walk, where the
## NavigationAgent3D's path supplies the direction instead. Either way the
## body moves with the same acceleration and move_and_slide(), so obstacles
## block it exactly the same. Joystick/keyboard input always wins over a
## walk; a new tap replaces it.

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
## Tap to Move eases off over the last stretch so arriving isn't a hard stop.
const ARRIVAL_SLOWDOWN_DISTANCE := 1.2
const ARRIVAL_MIN_SPEED := 0.35
## A path that stops making progress (pressed against something the mesh
## didn't know about) is dropped after this long.
const NAVIGATION_STUCK_SECONDS := 1.0
const NAVIGATION_STUCK_SPEED := 0.25
const DEAD_ZONE := 0.12

## Shapes the raw joystick deflection before it becomes a target speed.
## >1 gives finer, easier control near the center of the joystick (slow,
## precise movement) while still reaching full speed at full deflection —
## without the joystick itself needing to know anything about this.
const INPUT_RESPONSE_CURVE := 1.2

@onready var interaction_zone: Area3D = $InteractionZone
@onready var visual: Node3D = $Visual
@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D

var _nearby_interactables: Array[Interactable] = []
var _facing_angle: float = 0.0
var _bob_time: float = 0.0
var _footstep_timer: float = 0.0
## One-shot interactables (discoveries) already harvested and animating
## away — a second tap on the same one mid-animation must not harvest it
## twice. Dropped automatically once the object is freed.
var _spent_interactables: Array[Interactable] = []
var _navigating: bool = false
var _navigation_stuck_time: float = 0.0
## The Interactable a tap asked for, while walking to it: interacted with
## the moment it enters InteractionZone (see _on_interaction_zone_area_entered).
var _approach_target: Interactable

func _ready() -> void:
	interaction_zone.area_entered.connect(_on_interaction_zone_area_entered)
	interaction_zone.area_exited.connect(_on_interaction_zone_area_exited)
	InputManager.interact_requested.connect(_on_interact_requested)
	InputManager.interact_target_requested.connect(_on_interact_target_requested)
	InputManager.move_target_requested.connect(_on_move_target_requested)
	InputManager.stop_requested.connect(_on_stop_requested)
	add_to_group(InputManager.PLAYER_GROUP)
	InputManager.movement_mode_changed.connect(_on_movement_mode_changed)
	_facing_angle = visual.rotation.y

func _physics_process(delta: float) -> void:
	var direction := _shape_input(InputManager.move_vector)
	if direction != Vector3.ZERO:
		_stop_navigation()
	elif _navigating:
		direction = _navigation_direction()

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
	if _navigating:
		_update_navigation_progress(delta, speed)
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

## Shared by proximity feedback and the nearest-object interaction, so the object whose
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
	if interactable == _approach_target:
		_stop_navigation()
		_interact_with(interactable)

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
	_interact_with(target)

## A tap landed on this exact Interactable (see InputManager). Already in
## interaction range: interact now. Otherwise walk toward it (the path ends
## on the walkable ground nearest the object, so the player never needs to
## stand inside it) and interact when it enters InteractionZone.
func _on_interact_target_requested(target: Interactable) -> void:
	if not is_instance_valid(target):
		return
	if _nearby_interactables.has(target):
		_stop_navigation()
		_interact_with(target)
		return
	_start_navigation(target.global_position)
	_approach_target = target

func _on_move_target_requested(destination: Vector3) -> void:
	_start_navigation(destination)
	if _navigating:
		_spawn_destination_marker(destination)

func _on_movement_mode_changed(_mode: int) -> void:
	_stop_navigation()

## Tapping the player: the deliberate stop. Ends a tap-started walk and
## drops any pending interaction; harmless when already standing still.
func _on_stop_requested() -> void:
	_stop_navigation()

# --- Tap to Move -----------------------------------------------------------------

## A new tap simply replaces the destination — the path is recomputed from
## wherever the player is now, mid-walk or not.
func _start_navigation(destination: Vector3) -> void:
	_approach_target = null
	nav_agent.target_position = destination
	_navigating = true
	_navigation_stuck_time = 0.0

func _stop_navigation() -> void:
	_navigating = false
	_approach_target = null
	_navigation_stuck_time = 0.0

## Direction toward the next corner of the agent's path, scaled down over
## the last stretch. Called from _physics_process only while navigating.
## Without a navigation path (the mesh is still being built at load) the
## player heads straight for the target; move_and_slide() still stops it at
## obstacles, and the stall timeout ends the walk.
func _navigation_direction() -> Vector3:
	var next := nav_agent.get_next_path_position()
	var goal := nav_agent.get_final_position()
	if nav_agent.get_current_navigation_path().is_empty():
		next = nav_agent.target_position
		goal = next
		var remaining := next - global_position
		remaining.y = 0.0
		if remaining.length() <= nav_agent.target_desired_distance:
			_stop_navigation()
			return Vector3.ZERO
	elif nav_agent.is_navigation_finished():
		_stop_navigation()
		return Vector3.ZERO
	var to_next := next - global_position
	to_next.y = 0.0
	if to_next.length() < 0.01:
		return Vector3.ZERO
	var to_goal := goal - global_position
	to_goal.y = 0.0
	var pace := clampf(to_goal.length() / ARRIVAL_SLOWDOWN_DISTANCE, ARRIVAL_MIN_SPEED, 1.0)
	return to_next.normalized() * pace

## Giving up on a walk whose target vanished or that has stalled against
## something. (Reaching a tapped Interactable is handled by the zone's
## area_entered signal, not here.)
func _update_navigation_progress(delta: float, speed: float) -> void:
	if _approach_target != null and not is_instance_valid(_approach_target):
		_stop_navigation()
		return
	if speed < NAVIGATION_STUCK_SPEED:
		_navigation_stuck_time += delta
		if _navigation_stuck_time >= NAVIGATION_STUCK_SECONDS:
			_stop_navigation()
	else:
		_navigation_stuck_time = 0.0

## A quiet acknowledgement of where a tap will take the player: the same
## small, self-clearing burst the farm uses for dust, in a pale tint.
func _spawn_destination_marker(destination: Vector3) -> void:
	var burst := Interactable.HarvestBurstScene.instantiate() as HarvestBurst
	if burst == null:
		return
	burst.tint = Color(0.95, 0.95, 0.88, 1.0)
	burst.burst_radius = 0.22
	burst.vertical = 0.25
	burst.start_height = 0.03
	get_parent().add_child(burst)
	burst.global_position = destination

## The one place interact() is called, whichever way it was asked for.
func _interact_with(target: Interactable) -> void:
	_spent_interactables = _spent_interactables.filter(
		func(spent: Interactable) -> bool: return is_instance_valid(spent)
	)
	if _spent_interactables.has(target):
		return
	target.interact()
	# Only stop tracking it if it's actually gone (or about to be) after
	# this interaction — a one-shot discovery with remove_on_harvest still
	# gets dropped immediately so a second press/tap can't double-harvest
	# it mid-animation, but a persistent multi-state interactable (e.g. a
	# FarmPlot cycling through prepare/plant/water/harvest) must stay
	# tracked so the next tap keeps landing on it.
	if target.remove_on_harvest:
		_nearby_interactables.erase(target)
		_spent_interactables.append(target)
