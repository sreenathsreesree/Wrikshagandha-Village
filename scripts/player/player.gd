extends CharacterBody3D

## Moves the player from InputManager.move_vector (written by the on-screen
## joystick) and resolves interaction against whatever Interactable is
## currently inside InteractionZone.

const SPEED := 4.0
const GRAVITY := 12.0

@onready var interaction_zone: Area3D = $InteractionZone

var _nearby_interactables: Array[Interactable] = []

func _ready() -> void:
	interaction_zone.area_entered.connect(_on_interaction_zone_area_entered)
	interaction_zone.area_exited.connect(_on_interaction_zone_area_exited)
	InputManager.interact_requested.connect(_on_interact_requested)

func _physics_process(delta: float) -> void:
	var move_vector: Vector2 = InputManager.move_vector

	if is_on_floor():
		velocity.y = 0.0
	else:
		velocity.y -= GRAVITY * delta

	var direction := Vector3(move_vector.x, 0.0, move_vector.y)
	if direction.length_squared() > 1.0:
		direction = direction.normalized()

	velocity.x = direction.x * SPEED
	velocity.z = direction.z * SPEED

	move_and_slide()

func _on_interaction_zone_area_entered(area: Area3D) -> void:
	if area is Interactable and not _nearby_interactables.has(area):
		_nearby_interactables.append(area)

func _on_interaction_zone_area_exited(area: Area3D) -> void:
	if area is Interactable:
		_nearby_interactables.erase(area)

func _on_interact_requested() -> void:
	_nearby_interactables = _nearby_interactables.filter(
		func(interactable: Interactable) -> bool: return is_instance_valid(interactable)
	)
	if _nearby_interactables.is_empty():
		return
	var target: Interactable = _nearby_interactables[0]
	target.interact()
	_nearby_interactables.erase(target)
