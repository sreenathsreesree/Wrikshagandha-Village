extends Interactable
class_name RestSpot

## A rest spot (Group E, D-48; first instance E1): somewhere to sit and let
## the world carry on. Used through the generic interaction flow with D-09's
## Use verb, it only asks to be sat on — Main walks the player to its
## SeatPoint, settles the camera with this spot's preset (D-49) and quiets
## the HUD (D-50, D-56). It stays available while the player walks to it (a
## second tap repeats the request, D3) and is occupied only while the player
## is seated (Main sets that). Occupied, it stays tappable — so a tap on it
## reaches the Player, which ignores a tap on its own seat (D-56) — but
## offers nothing and refuses interact().
##
## Self-contained and peaceful: no reward, progression, save, audio or HUD
## knowledge, and no reference to the Player, camera or Main.

signal sit_requested(rest_spot: RestSpot)

## Main finds the rest spots of an area through this group.
const GROUP := &"rest_spot"

## The camera preset while seated (D-49, D-62): the seated start distance
## (8 m, inside the seated zoom range), a screen-space framing offset
## (Camera3D h/v offset, metres), the range pinch and wheel stay within while
## seated (7–10 m, inside the 7–15 m zoom limits), how far a drag may turn
## the view either side of its default while seated (45°, D-62 R3) and the
## ease times (1–2 s).
@export_range(7.0, 10.0) var settle_distance: float = 8.0
@export var framing_offset := Vector2(2.0, -2.0)
@export var seated_zoom_range := Vector2(7.0, 10.0)
@export_range(0.0, 45.0) var seated_yaw_limit_degrees: float = 45.0
@export_range(1.0, 2.0) var settle_seconds: float = 1.5
@export_range(1.0, 2.0) var release_seconds: float = 1.5

@onready var _seat_point: Marker3D = $SeatPoint

var _occupied: bool = false

func _ready() -> void:
	remove_on_harvest = false
	add_to_group(GROUP)

func _get_interaction_verbs() -> Array[Verb]:
	var verbs: Array[Verb] = []
	if not _occupied:
		verbs.append(Verb.USE)
	return verbs

## Asks to be sat on; refused while occupied.
func interact() -> bool:
	if _occupied:
		return false
	sit_requested.emit(self)
	return true

## Where the player sits and the way they face (-Z): the view.
func get_seat_transform() -> Transform3D:
	return _seat_point.global_transform

## Occupied while the player is seated. Availability (monitorable) is left
## alone: a tap on the occupied seat must still name it, not fall through to
## the player sitting on it (D-56: tapping the same seat is a no-op).
func set_occupied(occupied: bool) -> void:
	_occupied = occupied
