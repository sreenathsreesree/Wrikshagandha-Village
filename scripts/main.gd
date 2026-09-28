extends Node3D

## The persistent runtime shell (M03.1). Player, FollowCamera and HUD live
## here and belong to no area; the current area — today the Meadow — is
## world content only (terrain, navigation, discoveries, farm, wildlife,
## world simulation). Wired once, after every child is ready: the camera
## follows the player, and the area is handed the player for its world
## simulation.
##
## Area loading (M03.2) is infrastructure only: nothing in the game calls
## load_area() yet (no door or transition until M08.1, and area-safe farm
## state is M03.3: farm plots survive a reload). For the playtest it is
## called from the Godot remote debugger.

@onready var player: Player = $Player
@onready var follow_camera: FollowCamera = $FollowCamera
@onready var area: MeadowArea = $Meadow

func _ready() -> void:
	follow_camera.target = player
	_apply_camera_bounds()
	follow_camera.snap_to_target()
	area.attach_player(player)

## Swaps the current area for `scene` and places the player on its entry
## `entry_id`. Deferred, so it never runs inside a callback from the area
## being unloaded.
func load_area(scene: PackedScene, entry_id: String) -> void:
	if scene == null:
		push_warning("Main.load_area: no scene given")
		return
	_swap_area.call_deferred(scene, entry_id)

## The old area's farm plots are captured first (FarmManager, M03.3) —
## while they still exist — then it leaves the tree and is freed at once,
## before the new one is added, so its groups, plot ids and navigation
## region are gone when the new area's nodes register (and restore). The
## new area goes first among Main's children, keeping the processing order
## (area, player, camera, HUD).
func _swap_area(scene: PackedScene, entry_id: String) -> void:
	var instance := scene.instantiate()
	var next := instance as MeadowArea
	if next == null:
		push_warning("Main.load_area: %s is not an area" % scene.resource_path)
		instance.free()
		return
	FarmManager.cancel_seed_choice()
	var old := area
	FarmManager.release_plots_in(old)
	remove_child(old)
	old.free()
	area = next
	add_child(area)
	move_child(area, 0)
	area.attach_player(player)
	var entry := _find_entry(area, entry_id)
	if entry != null:
		player.place_at(entry.global_transform)
	else:
		push_warning("Main.load_area: the area has no entry; the player stays put")
		player.place_at(player.global_transform)
	_apply_camera_bounds()
	follow_camera.snap_to_target()

## The camera takes the current area's bounds (M03.4) — replacing the
## previous area's, or clearing them if this area has none.
func _apply_camera_bounds() -> void:
	var bounds := _find_camera_bounds(area)
	if bounds != null:
		follow_camera.set_bounds(bounds.get_rect())
	else:
		follow_camera.clear_bounds()

## This area's AreaCameraBounds (there is at most one), or null.
func _find_camera_bounds(in_area: Node) -> AreaCameraBounds:
	for node in get_tree().get_nodes_in_group(AreaCameraBounds.GROUP):
		var bounds := node as AreaCameraBounds
		if bounds != null and in_area.is_ancestor_of(bounds) and bounds.size.x > 0.0 and bounds.size.y > 0.0:
			return bounds
	return null

## The area's entry with this id; if there is none, its first entry by id
## (with a warning), so the choice never depends on tree order.
func _find_entry(in_area: Node, entry_id: String) -> AreaEntry:
	var first: AreaEntry = null
	for node in get_tree().get_nodes_in_group(AreaEntry.GROUP):
		var entry := node as AreaEntry
		if entry == null or not in_area.is_ancestor_of(entry):
			continue
		if entry.entry_id == entry_id:
			return entry
		if first == null or entry.entry_id < first.entry_id:
			first = entry
	if first != null:
		push_warning("Main.load_area: no entry '%s'; using '%s'" % [entry_id, first.entry_id])
	return first
