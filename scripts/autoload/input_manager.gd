extends Node

## Single source of truth for player intent. The virtual joystick writes
## move_vector; Player reads it. A tap on the game world is resolved here,
## in this order:
##   1. the GUI keeps its own touches (joystick zone, buttons, seed picker,
##      screens) — only unhandled input reaches the world;
##   2. a ray against Interactables: if one is hit,
##      interact_target_requested names that exact object (Player runs its
##      normal interact(), walking to it first in Tap to Move);
##   3. in Tap to Move only, a ray against walkable ground, snapped onto the
##      navigation mesh: move_target_requested gives the destination.
## movement_mode (Joystick / Tap to Move) is the one switch between the two
## control schemes; everything that differs between them reads it here, so
## the two can be compared without touching the movement code.
##
## Taps are read in _unhandled_input, so anything the GUI consumes never
## reaches the world: the joystick's touch zone, HUD buttons, the seed
## picker and every open screen all stop their own touches. Desktop: the
## project emulates touch from the mouse, so a click takes the same path.

enum MovementMode { JOYSTICK, TAP_TO_MOVE }

signal interact_requested
signal interact_target_requested(target: Interactable)
signal move_target_requested(destination: Vector3)
signal movement_mode_changed(mode: MovementMode)

## A tap, not a drag: released close to where it started, and quickly.
const TAP_MAX_MOVE := 24.0
const TAP_MAX_MSEC := 450
const RAY_LENGTH := 100.0
## A ground hit counts as walkable only if the navigation mesh is right
## there: tapping a rock, a tree trunk or off the edge of the world lands
## too far from any walkable surface and is ignored.
const WALKABLE_SNAP_HORIZONTAL := 0.35
const WALKABLE_SNAP_VERTICAL := 0.6
## Stands in for a touch index when a real mouse is used without touch
## emulation.
const MOUSE_TAP_INDEX := -100

var move_vector: Vector2 = Vector2.ZERO
## Joystick stays the default until Tap to Move has been play-tested.
var movement_mode: MovementMode = MovementMode.JOYSTICK

## touch index -> [start position, start msec] for presses the GUI didn't take.
var _tap_starts: Dictionary = {}
var _mouse_emulates_touch: bool = false

func _ready() -> void:
	_mouse_emulates_touch = bool(ProjectSettings.get_setting("input_devices/pointing/emulate_touch_from_mouse", false))

func set_move_vector(vector: Vector2) -> void:
	move_vector = vector

## Interact with whatever is nearest the player (kept for non-touch input).
func request_interact() -> void:
	interact_requested.emit()

func set_movement_mode(mode: MovementMode) -> void:
	if mode == movement_mode:
		return
	movement_mode = mode
	move_vector = Vector2.ZERO
	movement_mode_changed.emit(mode)

func set_tap_to_move(enabled: bool) -> void:
	set_movement_mode(MovementMode.TAP_TO_MOVE if enabled else MovementMode.JOYSTICK)

func is_tap_to_move() -> bool:
	return movement_mode == MovementMode.TAP_TO_MOVE

func get_movement_mode_name() -> String:
	return "tap_to_move" if is_tap_to_move() else "joystick"

## Player settings saved by SaveManager (not game progress).
func get_settings_data() -> Dictionary:
	return {"movement_mode": get_movement_mode_name()}

func apply_settings_data(data: Dictionary) -> void:
	var mode_name := String(data.get("movement_mode", "joystick"))
	set_tap_to_move(mode_name == "tap_to_move")

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		var touch: InputEventScreenTouch = event
		_track_tap(touch.index, touch.pressed, touch.position)
	elif event is InputEventMouseButton and not _mouse_emulates_touch:
		# Only a real mouse: touch-emulated mouse events (Android) are
		# already handled as the touches they came from.
		var click: InputEventMouseButton = event
		if click.button_index == MOUSE_BUTTON_LEFT and click.device != InputEvent.DEVICE_ID_EMULATION:
			_track_tap(MOUSE_TAP_INDEX, click.pressed, click.position)

func _track_tap(index: int, pressed: bool, screen_position: Vector2) -> void:
	if pressed:
		_tap_starts[index] = [screen_position, Time.get_ticks_msec()]
		return
	if not _tap_starts.has(index):
		return
	var start: Array = _tap_starts[index]
	_tap_starts.erase(index)
	var start_position: Vector2 = start[0]
	var start_msec: int = start[1]
	if screen_position.distance_to(start_position) > TAP_MAX_MOVE:
		return
	if Time.get_ticks_msec() - start_msec > TAP_MAX_MSEC:
		return
	_handle_tap(screen_position)

## Rays from the camera through the tapped point. Run on the next physics
## frame, where the space state is safe to query — a one-off await per tap,
## not a per-frame check.
func _handle_tap(screen_position: Vector2) -> void:
	await get_tree().physics_frame
	var camera := get_viewport().get_camera_3d()
	if camera == null:
		return
	var from := camera.project_ray_origin(screen_position)
	var to := from + camera.project_ray_normal(screen_position) * RAY_LENGTH
	var space := camera.get_world_3d().direct_space_state

	# Interactables first (areas only, so terrain and props can't block or
	# be picked).
	var query := PhysicsRayQueryParameters3D.create(from, to, PhysicsLayers.INTERACTABLES)
	query.collide_with_areas = true
	query.collide_with_bodies = false
	var hit := space.intersect_ray(query)
	if not hit.is_empty():
		var target := _find_interactable(hit.get("collider") as Node)
		if target:
			interact_target_requested.emit(target)
			return

	if not is_tap_to_move():
		return
	# Then the world: the first solid surface under the tap, which must sit
	# on the navigation mesh to be a destination.
	var ground_query := PhysicsRayQueryParameters3D.create(from, to, PhysicsLayers.WORLD)
	var ground_hit := space.intersect_ray(ground_query)
	if ground_hit.is_empty():
		return
	var tapped_point: Vector3 = ground_hit.get("position", Vector3.ZERO)
	var destination: Variant = _walkable_point(camera.get_world_3d().navigation_map, tapped_point)
	if destination != null:
		move_target_requested.emit(destination)

## The navigation-mesh point under a tapped world point, or null if there
## is no walkable surface there (an obstacle, or no mesh baked yet).
func _walkable_point(map: RID, point: Vector3) -> Variant:
	if NavigationServer3D.map_get_iteration_id(map) == 0:
		return null
	var closest := NavigationServer3D.map_get_closest_point(map, point)
	var offset := closest - point
	if Vector2(offset.x, offset.z).length() > WALKABLE_SNAP_HORIZONTAL:
		return null
	if absf(offset.y) > WALKABLE_SNAP_VERTICAL:
		return null
	return closest

## The hit collider itself, or the Interactable it belongs to.
func _find_interactable(node: Node) -> Interactable:
	while node:
		if node is Interactable:
			return node as Interactable
		node = node.get_parent()
	return null
