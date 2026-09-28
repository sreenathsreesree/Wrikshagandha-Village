extends Node

## Single source of truth for player intent. The virtual joystick writes
## move_vector; Player reads it. Interaction is touch-to-interact: a tap on
## the game world is raycast into the scene, and if it lands on an
## Interactable, interact_target_requested names that exact object —
## Player then runs its normal interact(). Keeps input decoupled from both
## the UI scene tree and the player controller.
##
## Taps are read in _unhandled_input, so anything the GUI consumes never
## reaches the world: the joystick's touch zone, HUD buttons, the seed
## picker and every open screen all stop their own touches. Desktop: the
## project emulates touch from the mouse, so a click takes the same path.

signal interact_requested
signal interact_target_requested(target: Interactable)

## A tap, not a drag: released close to where it started, and quickly.
const TAP_MAX_MOVE := 24.0
const TAP_MAX_MSEC := 450
## The physics layer every Interactable (discoveries, farm plots) is on.
const INTERACTABLE_LAYER_MASK := 4
const RAY_LENGTH := 100.0
## Stands in for a touch index when a real mouse is used without touch
## emulation.
const MOUSE_TAP_INDEX := -100

var move_vector: Vector2 = Vector2.ZERO

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
	_interact_at(screen_position)

## One ray from the camera through the tapped point, against interactable
## areas only (terrain and props can't block or be picked). Run on the next
## physics frame, where the space state is safe to query — a one-off await,
## not a per-frame check.
func _interact_at(screen_position: Vector2) -> void:
	await get_tree().physics_frame
	var camera := get_viewport().get_camera_3d()
	if camera == null:
		return
	var from := camera.project_ray_origin(screen_position)
	var to := from + camera.project_ray_normal(screen_position) * RAY_LENGTH
	var query := PhysicsRayQueryParameters3D.create(from, to, INTERACTABLE_LAYER_MASK)
	query.collide_with_areas = true
	query.collide_with_bodies = false
	var hit := camera.get_world_3d().direct_space_state.intersect_ray(query)
	if hit.is_empty():
		return
	var target := _find_interactable(hit.get("collider") as Node)
	if target:
		interact_target_requested.emit(target)

## The hit collider itself, or the Interactable it belongs to.
func _find_interactable(node: Node) -> Interactable:
	while node:
		if node is Interactable:
			return node as Interactable
		node = node.get_parent()
	return null
