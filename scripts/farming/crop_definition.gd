extends Resource
class_name CropDefinition

## Data-driven definition for one crop. Adding a new crop later means a new
## .tres resource in res://data/crops/ plus a new visual .tscn (using the
## shared CropVisual script) — never new logic in FarmPlot.
##
## category/rarity reuse the same vocabulary as DiscoveryDefinition; rarity
## also scales the harvest animation through Interactable.RARITY_INTENSITY,
## the same table discoveries use.

@export var crop_id: String = ""
@export var display_name: String = ""
@export_enum("plant", "flower", "fungus", "mineral", "insect", "animal", "mystery") var category: String = "plant"
@export_enum("common", "uncommon", "rare", "very_rare", "legendary") var rarity: String = "common"
@export var points_value: int = 10

## The crop's small harvest personality, played by the shared CropVisual:
## "pull" = braces then pops upward (a root being pulled), "sway" = a soft
## leafy sway then a gentle lift, "bloom" = a scale pulse like opening up.
@export_enum("pull", "sway", "bloom") var harvest_style: String = "pull"

## Seconds spent in each growth stage before it can advance to the next —
## each advance requires the plot to be watered first (see FarmPlot).
## seed_duration is 0 by design: the very first watering sprouts it
## immediately, matching "Seed: immediate" from the farming milestone spec.
@export var seed_duration: float = 0.0
@export var sprout_duration: float = 14.0
@export var growing_duration: float = 24.0

## A CropVisual-scripted scene (see scripts/farming/crop_visual.gd) —
## FarmPlot instances this once when the plot is planted and drives its
## growth stage from here.
@export var visual_scene: PackedScene

## stage_index: 0=seed, 1=sprout, 2=growing. Returns how long the plot
## must stay watered in that stage before advancing to the next one.
## Stage 3 (mature) is terminal — harvestable, no further timer.
func get_stage_duration(stage_index: int) -> float:
	match stage_index:
		0:
			return seed_duration
		1:
			return sprout_duration
		2:
			return growing_duration
	return 0.0
