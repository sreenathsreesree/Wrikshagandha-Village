extends Node

## Single source of truth for player intent. The virtual joystick and the
## keyboard (desktop fallback) both feed move_vector; Player reads it.
##
## The world itself is the control. A tap on the game world is resolved
## here, the same way in every movement mode:
##   1. the GUI keeps its own touches (joystick zone, buttons, seed picker,
##      screens) — only unhandled input reaches the world;
##   2. a ray against Interactables: if one is hit — or, for small objects,
##      one lies within TAP_SELECT_TOLERANCE of the tapped ground point —
##      interact_target_requested names that exact object (Player walks to
##      it and runs its normal interact() once it's in interaction range);
##   3. otherwise a ray against the world, snapped onto the navigation mesh:
##      move_target_requested gives the destination.
## movement_mode (Joystick / Tap to Move) only chooses whether the joystick
## is shown; taps work in both. Joystick or keyboard input always takes over
## from a tap-started walk (see Player).
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
## A tapped world point becomes the nearest walkable (navigation-mesh)
## point if one is this close — so a tap right beside a rock or tree, where
## the mesh keeps the player's radius clear, still walks up to it. Farther
## (the top of a big obstacle, off the world's edge) is ignored.
const WALKABLE_SNAP_HORIZONTAL := 1.0
const WALKABLE_SNAP_VERTICAL := 0.6
## Small objects (flowers, mushrooms) have small collision shapes; a tap
## that lands on the ground within this distance of one selects it.
const TAP_SELECT_TOLERANCE := 0.45
## Stands in for a touch index when a real mouse is used without touch
## emulation.
const MOUSE_TAP_INDEX := -100
## Keyboard movement actions (project.godot [input]: WASD + arrow keys).
const MOVE_LEFT := &"move_left"
const MOVE_RIGHT := &"move_right"
const MOVE_UP := &"move_up"
const MOVE_DOWN := &"move_down"

## What Player moves by: the joystick's and the keyboard's contributions
## combined (clamped to length 1), so both share one movement path.
var move_vector: Vector2 = Vector2.ZERO
## Joystick stays the default until Tap to Move has been play-tested.
var movement_mode: MovementMode = MovementMode.JOYSTICK

## touch index -> [start position, start msec] for presses the GUI didn't take.
var _tap_starts: Dictionary = {}
var _mouse_emulates_touch: bool = false
var _joystick_vector: Vector2 = Vector2.ZERO
var _tap_select_shape: SphereShape3D
var _keyboard_vector: Vector2 = Vector2.ZERO

func _ready() -> void:
	_mouse_emulates_touch = bool(ProjectSettings.get_setting("input_devices/pointing/emulate_touch_from_mouse", false))

## Called by the virtual joystick every frame with its (smoothed) deflection.
func set_move_vector(vector: Vector2) -> void:
	_joystick_vector = vector
	_update_move_vector()

func _update_move_vector() -> void:
	move_vector = (_joystick_vector + _keyboard_vector).limit_length(1.0)

## Interact with whatever is nearest the player (kept for non-touch input).
func request_interact() -> void:
	interact_requested.emit()

func set_movement_mode(mode: MovementMode) -> void:
	if mode == movement_mode:
		return
	movement_mode = mode
	_joystick_vector = Vector2.ZERO
	_update_move_vector()
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

## Keyboard movement (desktop fallback), event-driven: on any movement key
## press/release, the keyboard vector is re-read from the actions' actual
## state. Read in _input, and never consumed, so a focused HUD button can't
## swallow a key release and leave the player walking.
func _input(event: InputEvent) -> void:
	if not (event is InputEventKey):
		return
	if event.is_action(MOVE_LEFT) or event.is_action(MOVE_RIGHT) or event.is_action(MOVE_UP) or event.is_action(MOVE_DOWN):
		_keyboard_vector = Input.get_vector(MOVE_LEFT, MOVE_RIGHT, MOVE_UP, MOVE_DOWN)
		_update_move_vector()

## Losing window focus can swallow key releases; never keep walking on a
## key that's no longer known to be held.
func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT:
		_keyboard_vector = Vector2.ZERO
		_update_move_vector()

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

	# Then the world: the first solid surface under the tap.
	var ground_query := PhysicsRayQueryParameters3D.create(from, to, PhysicsLayers.WORLD)
	var ground_hit := space.intersect_ray(ground_query)
	if ground_hit.is_empty():
		return
	var tapped_point: Vector3 = ground_hit.get("position", Vector3.ZERO)
	# A near miss on a small object still means that object.
	var near_target := _interactable_near(space, tapped_point)
	if near_target:
		interact_target_requested.emit(near_target)
		return
	var destination: Variant = _walkable_point(camera.get_world_3d().navigation_map, tapped_point)
	if destination != null:
		move_target_requested.emit(destination)

## The closest currently-interactable object whose shape lies within
## TAP_SELECT_TOLERANCE of a tapped ground point, or null.
func _interactable_near(space: PhysicsDirectSpaceState3D, point: Vector3) -> Interactable:
	if _tap_select_shape == null:
		_tap_select_shape = SphereShape3D.new()
		_tap_select_shape.radius = TAP_SELECT_TOLERANCE
	var params := PhysicsShapeQueryParameters3D.new()
	params.shape = _tap_select_shape
	params.transform = Transform3D(Basis.IDENTITY, point)
	params.collision_mask = PhysicsLayers.INTERACTABLES
	params.collide_with_areas = true
	params.collide_with_bodies = false
	var best: Interactable = null
	var best_distance := INF
	for result: Dictionary in space.intersect_shape(params, 8):
		var candidate := _find_interactable(result.get("collider") as Node)
		if candidate == null:
			continue
		var offset := candidate.global_position - point
		var distance := Vector2(offset.x, offset.z).length()
		if distance < best_distance:
			best_distance = distance
			best = candidate
	return best

## The navigation-mesh point for a tapped world point, or null if there is
## no walkable surface close enough. Before the navigation mesh exists (it's
## built at load) the tapped point itself is used: the player then walks
## straight there, and collisions still stop it at obstacles.
func _walkable_point(map: RID, point: Vector3) -> Variant:
	if not NavigationServer3D.map_get_closest_point_owner(map, point).is_valid():
		return point
	var closest := NavigationServer3D.map_get_closest_point(map, point)
	var offset := closest - point
	if Vector2(offset.x, offset.z).length() > WALKABLE_SNAP_HORIZONTAL:
		return null
	if absf(offset.y) > WALKABLE_SNAP_VERTICAL:
		return null
	return closest

## The hit collider itself, or the Interactable it belongs to — if it can
## be interacted with right now. An Interactable that isn't monitorable
## (a locked plot, a discovery mid-harvest) is ignored, so the tap falls
## through to the ground.
func _find_interactable(node: Node) -> Interactable:
	while node:
		if node is Interactable:
			var interactable := node as Interactable
			if not interactable.monitorable:
				return null
			return interactable
		node = node.get_parent()
	return null
