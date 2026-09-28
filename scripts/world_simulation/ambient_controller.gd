extends Node
class_name AmbientController

## Coordination seam for ambient decoration (drifting leaves, pollen motes,
## distant birds). Today's ambient effects — DriftingLeaf, GlowingMotes,
## BirdFlyoverSpawner — are self-contained prop scenes placed directly in
## the world and need no orchestration to just play. This controller exists
## so a future system (e.g. toggling ambient density by time-of-day or a
## later weather system) has one place to plug into without reaching into
## those props directly.

func set_active(active: bool) -> void:
	for node in get_children():
		if node.has_method("set_ambient_active"):
			node.call("set_ambient_active", active)
