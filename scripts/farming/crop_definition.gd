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

## Identity: the one color that means "this crop" everywhere it appears —
## the seed picker's swatch and the plot's indicator gem while it grows.
## The crop's own meshes carry the same accent (carrot shoulder, herb
## buds, sunflower head), so what's growing is readable without labels.
@export var identity_color: Color = Color(0.72, 0.92, 0.5, 1)
## A single glyph shown on the seed picker button beside the color swatch.
@export var icon_glyph: String = "🌱"

## Seeds the player starts each session with. Harvesting returns exactly
## one seed of the harvested crop, so this is also the most of this crop
## that can ever be growing at once — renewable, never accumulating.
## A crop with starting_seeds > 0 is a *starter* crop: FarmManager's
## "all starter crops grown" milestone is derived from this, so no list of
## crop ids is ever written in code.
@export var starting_seeds: int = 1

## Growth personality, read by the shared CropVisual (never by FarmPlot):
## mature_scale sets the silhouette (compact < 1 < tall), sway_amount
## scales how much the crop moves while growing and when ready (stiff < 1
## < willowy), and ready_pulse is a gentle breathing swell once mature
## (0 = none) — how a flower reads as "open".
@export var mature_scale: float = 1.0
@export var sway_amount: float = 1.0
@export var ready_pulse: float = 0.0

## How much a ripe crop of this kind draws the Meadow's attention (0..1).
## FarmManager sums it over the crops currently ready into one garden
## interest level; wildlife configured to notice the garden then visit it
## a little more often. Purely atmospheric — wildlife never touches crops.
## Quiet crops (a carrot's low tops) sit near 0; showy ones (a flower
## head) sit higher.
@export_range(0.0, 1.0) var wildlife_interest: float = 0.2

## Care: how many seconds this crop can wait for water (each time it's
## thirsty) before it counts as neglected. FarmManager rates care from the
## longest wait: within the tolerance is careful, within
## FarmManager.NEGLECT_FACTOR × tolerance is tended, beyond that neglected.
## Hardy crops tolerate more; fussy ones less. Generous on purpose — a
## short exploring trip is never neglect.
@export var thirst_tolerance: float = 90.0

## Optional line for the quiet card when this crop first grows in the
## garden. Empty = the generic "<name> has grown in the garden."
@export var grown_note: String = ""

## Optional exploration reward, granted by FarmManager at most once per
## session: reaching a place (an ExplorationManager place id) or finding a
## discovery (a DiscoveryDefinition id) reveals one extra seed of this crop.
## "none" = no link. found_seed_note is the line shown when it's found.
@export_enum("none", "place", "discovery") var found_seed_source: String = "none"
@export var found_seed_source_id: String = ""
@export var found_seed_note: String = ""

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
