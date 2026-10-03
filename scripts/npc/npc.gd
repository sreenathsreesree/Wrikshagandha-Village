extends CharacterBody3D
class_name Npc

## A person in the world (M08.3): a solid body that idles and wanders a
## little around where it was placed, on the area's own navigation mesh
## (its NavigationAgent3D on the same map the player walks), and stops to
## face the player once they come close. Who it is and what it says come
## from its NpcDefinition (res://data/npcs/); the talking itself is its
## NpcTalk child, an ordinary Interactable. No schedule, no saved state:
## it starts where it is placed, every launch. A parked area (the Meadow
## while the player is indoors) simply stops processing it.

@export var definition: NpcDefinition

## Close enough (m, flat) that it stops wandering and turns to the player.
## It also holds still from the moment a tap chooses it (its NpcTalk is
## tap-selected), so the player walks to where it really is.
const NOTICE_DISTANCE := 4.0
const WALK_SPEED := 0.9
const TURN_SPEED := 6.0
const IDLE_SECONDS_MIN := 2.5
const IDLE_SECONDS_MAX := 5.5
## A moving player about to bump into it (closer than this, m, heading
## at it) gets a small step aside, so a walk past it never deadlocks on
## its body (it is not in the baked navigation mesh — it moves). Never
## while the player stands still, e.g. talking to it from range.
const YIELD_DISTANCE := 1.0
const YIELD_MIN_PLAYER_SPEED := 0.5
## Touching (m, centre to centre — the two capsules plus a margin): it
## steps aside whatever the player's speed, since a body pressed against it
## head-on has its velocity cancelled by the collision.
const YIELD_CONTACT := 0.75
## How far from home a step aside may take it (beyond the wander radius).
const YIELD_LEASH := 0.75
## Wander targets keep this far (m) from every area entry, so it never
## stands where the player arrives through a door or in the doorway.
const DOOR_CLEARANCE := 1.5
const GRAVITY := 9.8

@onready var nav_agent: NavigationAgent3D = $NavigationAgent3D
@onready var visual: Node3D = $Visual
@onready var talk: NpcTalk = $NpcTalk

var _home: Vector3
var _rng := RandomNumberGenerator.new()
var _idle_left: float = 0.0
var _wandering: bool = false
var _facing_angle: float = 0.0
var _player: Node3D
## The side a step aside committed to (zero when not yielding): kept until
## the player is no longer close, so it never dithers across their line.
var _yield_side: Vector3 = Vector3.ZERO

func _ready() -> void:
	_home = global_position
	_rng.seed = hash(definition.id) if definition else 0
	_idle_left = _rng.randf_range(IDLE_SECONDS_MIN, IDLE_SECONDS_MAX)
	_facing_angle = visual.rotation.y

func _physics_process(delta: float) -> void:
	var direction := Vector3.ZERO
	var player := _find_player()
	if player != null and (talk.is_tap_selected() or _flat_distance(player.global_position) <= NOTICE_DISTANCE):
		_wandering = false
		_turn_toward(player.global_position - global_position, delta)
		direction = _yield_direction(player)
	elif _wandering:
		if nav_agent.is_navigation_finished():
			_wandering = false
			_idle_left = _rng.randf_range(IDLE_SECONDS_MIN, IDLE_SECONDS_MAX)
		else:
			direction = nav_agent.get_next_path_position() - global_position
			direction.y = 0.0
			direction = direction.normalized() if direction.length() > 0.05 else Vector3.ZERO
			_turn_toward(direction, delta)
	else:
		_idle_left -= delta
		if _idle_left <= 0.0:
			_start_wander()
	velocity.x = direction.x * WALK_SPEED
	velocity.z = direction.z * WALK_SPEED
	velocity.y = 0.0 if is_on_floor() else velocity.y - GRAVITY * delta
	move_and_slide()

## Sideways, away from a moving player's line, when they are about to walk
## into it or are pressed against it — the other side if that one is blocked;
## nothing if both would leave its leash or come near a door's entry.
func _yield_direction(player: Node3D) -> Vector3:
	var body := player as CharacterBody3D
	if body == null:
		return Vector3.ZERO
	var motion := Vector3(body.velocity.x, 0.0, body.velocity.z)
	var to_me := global_position - player.global_position
	to_me.y = 0.0
	var touching := to_me.length() <= YIELD_CONTACT
	var heading_at_me := motion.length() >= YIELD_MIN_PLAYER_SPEED and to_me.length() <= YIELD_DISTANCE and motion.dot(to_me) > 0.0
	if not touching and not heading_at_me:
		_yield_side = Vector3.ZERO
		return Vector3.ZERO
	if _yield_side == Vector3.ZERO:
		# Perpendicular to the player's line (or, pressed still, to the
		# contact), on the side it already leans to — then kept.
		var line := motion if motion.length() >= YIELD_MIN_PLAYER_SPEED else to_me
		_yield_side = Vector3(-line.z, 0.0, line.x).normalized()
		if _yield_side.dot(to_me) < 0.0:
			_yield_side = -_yield_side
	# The other side if that one would leave its leash or come near a door.
	for candidate in [_yield_side, -_yield_side]:
		if _step_allowed(global_position + candidate * 0.3):
			_yield_side = candidate
			return candidate
	return Vector3.ZERO

func _step_allowed(step: Vector3) -> bool:
	var leash := (definition.wander_radius if definition else 0.0) + YIELD_LEASH
	return Vector2(step.x - _home.x, step.z - _home.z).length() <= leash and _clear_of_doors(step)

func is_noticing_player() -> bool:
	var player := _find_player()
	return player != null and (talk.is_tap_selected() or _flat_distance(player.global_position) <= NOTICE_DISTANCE)

## A walkable point within its wander radius of home (on the mesh, clear of
## doors and entries); stays idle a while longer if none is found.
func _start_wander() -> void:
	var radius := definition.wander_radius if definition else 0.0
	var map := get_world_3d().navigation_map
	for attempt in 6:
		var angle := _rng.randf_range(0.0, TAU)
		var candidate := _home + Vector3(cos(angle), 0.0, sin(angle)) * _rng.randf_range(0.4, radius)
		var point := NavigationServer3D.map_get_closest_point(map, candidate)
		if Vector2(point.x - _home.x, point.z - _home.z).length() <= radius and _clear_of_doors(point):
			nav_agent.target_position = point
			_wandering = true
			return
	_idle_left = _rng.randf_range(IDLE_SECONDS_MIN, IDLE_SECONDS_MAX)

## Clear of every entry (where the player arrives through a door — the door
## itself stands inside its building's carve, off the mesh).
func _clear_of_doors(point: Vector3) -> bool:
	for node in get_tree().get_nodes_in_group(AreaEntry.GROUP):
		if Vector2((node as Node3D).global_position.x - point.x, (node as Node3D).global_position.z - point.z).length() < DOOR_CLEARANCE:
			return false
	return true

func _turn_toward(direction: Vector3, delta: float) -> void:
	direction.y = 0.0
	if direction.length() < 0.05:
		return
	# Node3D's local forward is -Z, so solve sin(a)=dx, cos(a)=-dz.
	var target := atan2(direction.x, -direction.z)
	_facing_angle = lerp_angle(_facing_angle, target, 1.0 - exp(-TURN_SPEED * delta))
	visual.rotation.y = _facing_angle

func _flat_distance(point: Vector3) -> float:
	return Vector2(point.x - global_position.x, point.z - global_position.z).length()

func _find_player() -> Node3D:
	if _player == null or not is_instance_valid(_player):
		_player = get_tree().get_first_node_in_group(InputManager.PLAYER_GROUP) as Node3D
	return _player
