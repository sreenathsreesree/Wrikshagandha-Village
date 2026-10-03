extends Resource
class_name AreaDefinition

## Data-driven definition for one area the player can travel to (M08.1):
## its scene and how Main treats it. Add an area by creating another .tres
## in res://data/areas/ and a scene whose root GameArea has the same
## area_id — no script changes. AreaRouter loads them all.

@export var id: String = ""
@export var display_name: String = ""
@export_file("*.tscn") var scene_path: String = ""
## Kept alive while the player is elsewhere (D-33): Main parks the same
## instance out of the tree and puts it back on return, so nothing in it
## resets or advances. false = freed when left, built fresh on return.
@export var keep_alive_when_left: bool = false
## The camera's distance while in this area (an interior's close framing,
## D-32); 0 = the player's own zoom, given back on leaving such an area.
@export var camera_distance: float = 0.0
