extends Resource
class_name ItemDefinition

## Data-driven definition for one kind of item the player can hold. Adding
## an item means a new .tres in res://data/items/ — never new code. The
## ItemStore counts items by id; everything else about an item is here.
##
## Only the fields today's items need (M04.1, M04.2). Seeds and harvested
## produce are the items that exist; both belong to a crop, so their glyph, color
## and value come from its CropDefinition through crop_id rather than being
## copied here. Fields such as a glyph of its own, an element or a coin
## value arrive with the first item that needs them (M04.3 / Phase 05).

## Stable, lower_snake_case, equal to the file name; what saves will store.
@export var id: String = ""
@export var display_name: String = ""
## "seed": what is planted. "produce": what a harvest gives.
@export_enum("seed", "produce") var category: String = "seed"
## The CropDefinition.crop_id this item belongs to.
@export var crop_id: String = ""
## How many quality levels a held item keeps apart (1 = none). Quality is
## an attribute of what is held, not a separate item (D-18): produce keeps
## FarmManager's three (Plain / Good / Fine), one count per level.
@export var quality_levels: int = 1
