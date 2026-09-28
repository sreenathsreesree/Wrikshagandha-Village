extends Node3D
class_name ExplorationLandmark

## A tiny, stateless marker: placed at a landmark or secret location,
## found by ExplorationLandmarkController via the "exploration_landmark"
## group (the same pattern WildlifeController and EnvironmentalEvent use
## for their own groups). Holds no "have I fired yet" flag of its own -
## that bookkeeping already lives in ExplorationManager, so this stays a
## plain position + id + which bonus bucket it belongs to.

enum Kind { LANDMARK, SECRET_LOCATION }

@export var location_id: String = ""
@export var kind: Kind = Kind.LANDMARK
@export var radius: float = 3.0

func _ready() -> void:
	add_to_group("exploration_landmark")

func is_reached() -> bool:
	if kind == Kind.SECRET_LOCATION:
		return ExplorationManager.has_found_secret_location(location_id)
	return ExplorationManager.has_reached_landmark(location_id)

func mark_reached() -> void:
	if kind == Kind.SECRET_LOCATION:
		ExplorationManager.mark_secret_location_found(location_id)
	else:
		ExplorationManager.mark_landmark_reached(location_id)
