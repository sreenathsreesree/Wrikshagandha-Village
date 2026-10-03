extends Node3D
class_name GameArea

## One swappable piece of world content (M08.1): the Meadow, the home
## interior, any later area. Main owns the player, camera and HUD and swaps
## areas in and out; an area only describes itself. area_id names its
## AreaDefinition (res://data/areas/), where everything Main needs to know
## about the area as a destination lives — never in a script.
##
## Tap-to-move walks on the area's own navigation mesh, built from its
## static colliders: baked once at load on a background thread, skipped if
## a mesh was baked into the scene in the editor or the area has none.

@export var area_id: String = ""

func _ready() -> void:
	_bake_navigation()

## Called by Main once, when this instance first enters the shell: anything
## in the area that follows the player is handed it here. A restored
## (parked) area is never attached twice. Nothing to do by default.
func attach_player(_player: Node3D) -> void:
	pass

func _bake_navigation() -> void:
	var navigation_region := get_node_or_null("NavigationRegion3D") as NavigationRegion3D
	if navigation_region == null or navigation_region.navigation_mesh == null:
		return
	if navigation_region.navigation_mesh.get_polygon_count() > 0:
		return
	navigation_region.bake_navigation_mesh(true)
