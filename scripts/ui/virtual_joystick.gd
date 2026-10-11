extends Control

## Floating mobile joystick (D-58): a view only — it takes no touches, so
## the world under it stays tappable. InputManager decides which finger is
## the joystick's (a lone finger on the left half of the screen that has
## dragged past a tap) and reports it; this appears at the point that finger
## first touched, its Thumb follows the drag within knob_max_distance (the
## configurable radius), and it disappears on release. Includes a dead zone
## (stops idle drift) and per-frame smoothing (stops twitchy movement).
## Output goes through InputManager, same as always — player.gd is untouched.
##
## Near a screen edge the ring is moved inward just enough to be seen whole;
## movement is still measured from the real touch-down point, so the
## direction never changes with the ring's position. "Emulate touch from
## mouse" (project setting) lets this be tested with a mouse drag.

@export var knob_max_distance: float = 50.0
@export var dead_zone: float = 0.15
@export var smoothing_speed: float = 14.0

@onready var base: Control = $Base
@onready var thumb: Control = $Base/Thumb

var _active: bool = false
## Where the joystick's finger first touched (canvas pixels): the centre
## every deflection is measured from.
var _origin: Vector2 = Vector2.ZERO
var _raw_vector: Vector2 = Vector2.ZERO
var _smoothed_vector: Vector2 = Vector2.ZERO

func _ready() -> void:
	_release()
	InputManager.joystick_started.connect(_on_joystick_started)
	InputManager.joystick_moved.connect(_on_joystick_moved)
	InputManager.joystick_ended.connect(_release)
	visibility_changed.connect(_on_visibility_changed)

## Hidden (Tap to Move selected): let go of any touch in progress so no
## stale deflection keeps steering the player.
func _on_visibility_changed() -> void:
	if not is_visible_in_tree():
		_release()
		_smoothed_vector = Vector2.ZERO

func _on_joystick_started(origin: Vector2, screen_position: Vector2) -> void:
	if not is_visible_in_tree():
		return
	_active = true
	_origin = origin
	base.global_position = _ring_centre(origin) - base.size / 2.0
	base.visible = true
	_on_joystick_moved(screen_position)

## The ring's centre: the touch-down point, moved inward only as far as it
## takes for the whole ring to be on screen.
func _ring_centre(origin: Vector2) -> Vector2:
	var half := base.size / 2.0
	var screen := get_viewport_rect().size
	return Vector2(clampf(origin.x, half.x, maxf(screen.x - half.x, half.x)),
			clampf(origin.y, half.y, maxf(screen.y - half.y, half.y)))

func _on_joystick_moved(screen_position: Vector2) -> void:
	if not _active:
		return
	var offset := (screen_position - _origin).limit_length(knob_max_distance)
	thumb.position = base.size / 2.0 + offset - thumb.size / 2.0
	var normalized := offset / knob_max_distance
	_raw_vector = normalized if normalized.length() >= dead_zone else Vector2.ZERO

func _release() -> void:
	_active = false
	base.visible = false
	thumb.position = base.size / 2.0 - thumb.size / 2.0
	_raw_vector = Vector2.ZERO

func _process(delta: float) -> void:
	_smoothed_vector = _smoothed_vector.lerp(_raw_vector, clamp(smoothing_speed * delta, 0.0, 1.0))
	InputManager.set_move_vector(_smoothed_vector)
