extends Node

## Thin coordination relay so FarmPlot (a 3D world node) can tell the rest
## of the game that a crop was planted or harvested, without either side
## needing a reference to the other — the same World -> autoload -> UI shape
## DiscoveryManager already provides for discoveries. The HUD listens for
## notification cards; ExplorationManager listens for session milestones.
##
## Holds no farm state of its own: every FarmPlot owns its own state, and
## points are awarded directly by FarmPlot through PointsManager. This is a
## signal relay, not a registry.

signal crop_planted(crop_definition: CropDefinition)
signal crop_harvested(crop_definition: CropDefinition, points_awarded: int)

func notify_crop_planted(crop_definition: CropDefinition) -> void:
	crop_planted.emit(crop_definition)

func notify_crop_harvested(crop_definition: CropDefinition, points_awarded: int) -> void:
	crop_harvested.emit(crop_definition, points_awarded)
