extends Node

## Thin coordination relay so FarmPlot (a 3D world node) can tell the HUD a
## crop was harvested, without either needing a reference to the other —
## the same World -> autoload -> UI shape DiscoveryManager already provides
## for discoveries. Holds no farm state of its own: every FarmPlot owns its
## own state entirely, and points are awarded directly by FarmPlot through
## the existing PointsManager. This is a signal relay, not a registry.

signal crop_harvested(crop_definition: CropDefinition, points_awarded: int)

func notify_crop_harvested(crop_definition: CropDefinition, points_awarded: int) -> void:
	crop_harvested.emit(crop_definition, points_awarded)
