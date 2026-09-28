extends Node

## Owns the player's Wriksha Points total. No other system should mutate
## points directly — always go through add_points()/set_points().

signal points_changed(total: int)

var points: int = 0

func add_points(amount: int) -> void:
	if amount == 0:
		return
	points += amount
	points_changed.emit(points)

func set_points(value: int) -> void:
	points = value
	points_changed.emit(points)

func get_points() -> int:
	return points
