extends CharacterBody3D

## Moves the player from InputManager.move_vector (written by the on-screen
## joystick), with acceleration/deceleration and a smoothly-turning visual
## body. Resolves interaction against whatever Interactable is currently
## inside InteractionZone, and toggles that Interactable's indicator as it
## enters/leaves range.

const MAX_SPEED := 4.2
const ACCELERATION := 16.0
const DECELERATION := 20.0
const TURN_SPEED := 10.0
const GRAVITY := 12.0
const BOB_HEIGHT := 0.045
const BOB_SPEED := 9.0

@onready var interaction_zone: Area3D = $InteractionZone
@onready var visual: Node3D = $Visual

var _nearby_interactables: Array[Interactable] = []
var _facing_angle: float = 0.0
var _bob_time: float = 0.0

func _ready() -> void:
	interaction_zone.area_entered.connect(_on_interaction_zone_area_entered)
	interaction_zone.area_exited.connect(_on_interaction_zone_area_exited)
	InputManager.interact_requested.connect(_on_interact_requested)
	_facing_angle = visual.rotation.y

func _physics_process(delta: float) -> void:
	var move_vector: Vector2 = InputManager.move_vector
	if move_vector.length() < 0.12:
		move_vector = Vector2.ZERO

	if is_on_floor():
		velocity.y = 0.0
	else:
		velocity.y -= GRAVITY * delta

	var direction := Vector3(move_vector.x, 0.0, move_vector.y)
	if direction.length_squared() > 1.0:
		direction = direction.normalized()

	var horizontal_velocity := Vector3(velocity.x, 0.0, velocity.z)
	var target_velocity := direction * MAX_SPEED
	var rate := ACCELERATION if direction.length_squared() > 0.0 else DECELERATION
	horizontal_velocity = horizontal_velocity.move_toward(target_velocity, rate * delta)
	velocity.x = horizontal_velocity.x
	velocity.z = horizontal_velocity.z

	move_and_slide()

	_update_facing(direction, delta)
	_update_walk_bob(delta, horizontal_velocity.length())

func _update_facing(direction: Vector3, delta: float) -> void:
	if direction.length_squared() > 0.01:
		# Node3D's local forward is -Z, so solve sin(a)=dx, cos(a)=-dz.
		_facing_angle = atan2(direction.x, -direction.z)
	visual.rotation.y = lerp_angle(visual.rotation.y, _facing_angle, TURN_SPEED * delta)

func _update_walk_bob(delta: float, speed: float) -> void:
	if speed > 0.1:
		_bob_time += delta * BOB_SPEED * (speed / MAX_SPEED)
		visual.position.y = abs(sin(_bob_time)) * BOB_HEIGHT
	else:
		_bob_time = 0.0
		visual.position.y = lerp(visual.position.y, 0.0, 10.0 * delta)

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
	var target: Interactable = _nearby_interactables[0]
	target.interact()
	_nearby_interactables.erase(target)
