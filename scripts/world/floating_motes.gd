extends Node3D

## Gentle ambient motion for a small cluster of glowing motes used as an
## environmental clue near hidden discoveries. Purely decorative — always
## visible, always processing, but cheap (a few sines on a handful of
## meshes, no particle system).

@export var drift_height: float = 0.15
@export var drift_speed: float = 1.1

var _base_positions: Array[Vector3] = []
var _time: float = 0.0

func _ready() -> void:
	for child in get_children():
		if child is Node3D:
			_base_positions.append(child.position)

func _process(delta: float) -> void:
	_time += delta * drift_speed
	var children := get_children()
	for i in children.size():
		if i >= _base_positions.size():
			continue
		var child: Node3D = children[i]
		var base := _base_positions[i]
		var phase := _time + float(i) * 2.1
		child.position = base + Vector3(sin(phase * 0.7) * 0.05, sin(phase) * drift_height, cos(phase * 0.6) * 0.05)
