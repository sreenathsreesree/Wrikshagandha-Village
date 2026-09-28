extends Node

## Single source of truth for player intent. UI (virtual joystick, interact
## button) writes into this; Player reads from it. Keeps input decoupled
## from both the UI scene tree and the player controller.

signal interact_requested

var move_vector: Vector2 = Vector2.ZERO

func set_move_vector(vector: Vector2) -> void:
	move_vector = vector

func request_interact() -> void:
	interact_requested.emit()
