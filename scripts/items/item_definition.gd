extends Resource
class_name ItemDefinition

## Data-driven definition for one kind of item the player can hold. Adding
## an item means a new .tres in res://data/items/ — never new code. The
## ItemStore counts items by id; everything else about an item is here.
##
## Only the fields today's items need (M04.1–M04.3). Seeds and harvested
## produce belong to a crop, collectibles to a discovery; their glyph,
## color and points live on that CropDefinition / DiscoveryDefinition rather
## than being copied here. Fields such as a glyph of its own arrive with the
## first item that needs them; the element is an explicit field of its own
## (M11.0, D-46) — never derived from the crop or the discovery.

## Stable, lower_snake_case, equal to the file name; what saves will store.
@export var id: String = ""
@export var display_name: String = ""
## "seed": what is planted. "produce": what a harvest gives.
## "collectible": what collecting a discovery in the world gives (M04.3).
@export_enum("seed", "produce", "collectible") var category: String = "seed"
## The CropDefinition.crop_id a seed or produce item belongs to.
@export var crop_id: String = ""
## How many quality levels a held item keeps apart (1 = none). Quality is
## an attribute of what is held, not a separate item (D-18): produce keeps
## FarmManager's three (Plain / Good / Fine), one count per level.
@export var quality_levels: int = 1
## The DiscoveryDefinition.id a collectible comes from: each time that
## discovery is collected, Inventory gives one (M04.3).
@export var discovery_id: String = ""
## Coins one unit of this item sells for at Good quality (M06.2, D-25): the
## Market's base price, set independently of any points value. 0 = not
## sellable; only produce may have one (seeds and collectibles never sell).
@export var sell_value: int = 0
## The Five Elements id (data/elements/, M11.0, D-46) this belongs to; empty = none.
## Schema only: nothing reads it yet.
@export var element_id: String = ""
