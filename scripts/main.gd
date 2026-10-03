extends Node3D

## The persistent runtime shell (M03.1). Player, FollowCamera and HUD live
## here and belong to no area; the current area (a GameArea — the Meadow,
## the home interior) is world content only. Wired once, after every child
## is ready: the camera follows the player, and the area is handed the
## player for its world simulation.
##
## Travel between areas (M08.1): something in the world (an AreaDoor) asks
## AreaRouter; Main is the one place that carries it out — fade, swap, park
## or free, restore, place, reveal — and tells AreaRouter where the player
## now is. load_area() stays the plain swap with no fade, for the remote
## debugger.

@onready var player: Player = $Player
@onready var follow_camera: FollowCamera = $FollowCamera
@onready var transition_fade: TransitionFade = $TransitionFade
@onready var area: GameArea = $Meadow

## Areas kept alive while the player is elsewhere (D-33), out of the tree:
## scene path -> the same GameArea instance, put back when travelled to.
var _parked_areas: Dictionary = {}
## The player's own zoom, kept while an area with a fixed camera distance
## (an interior, D-32) is current; < 0 = none kept.
var _free_zoom_distance: float = -1.0

func _ready() -> void:
	follow_camera.target = player
	_apply_camera_bounds()
	follow_camera.snap_to_target()
	area.attach_player(player)
	InputManager.zoom_requested.connect(follow_camera.zoom_by)
	AreaRouter.travel_requested.connect(_on_travel_requested)
	AreaRouter.notify_arrived(area.area_id)

## Parked areas are out of the tree, so nothing frees them with it.
func _exit_tree() -> void:
	for parked: GameArea in _parked_areas.values():
		parked.free()
	_parked_areas.clear()

## Swaps the current area for `scene` and places the player on its entry
## `entry_id`. Deferred, so it never runs inside a callback from the area
## being unloaded.
func load_area(scene: PackedScene, entry_id: String) -> void:
	if scene == null:
		push_warning("Main.load_area: no scene given")
		return
	_swap_area.call_deferred(scene, entry_id)

## An accepted AreaRouter.travel(): the veil covers the screen (and takes
## every touch), the areas swap behind it — placing the player ends any
## walk — then it lifts. Continues after the door's interact() has
## returned, so the door may be parked or freed by the swap.
func _on_travel_requested(area_id: String, entry_id: String) -> void:
	var definition := AreaRouter.get_definition(area_id)
	var scene: PackedScene = null
	if definition != null:
		scene = load(definition.scene_path) as PackedScene
	if scene == null:
		push_warning("Main: area '%s' has no scene" % area_id)
		AreaRouter.notify_travel_failed()
		return
	await transition_fade.cover()
	if not _swap_area(scene, entry_id):
		AreaRouter.notify_travel_failed()
	await transition_fade.reveal()

## The old area's farm plots are captured first (FarmManager, M03.3) —
## while they still exist — then it leaves the tree: parked as it is if its
## AreaDefinition keeps it alive (D-33), otherwise freed at once, before
## the new one is added, so its groups, plot ids and navigation region are
## gone when the new area's nodes register (and restore). The new area is a
## parked instance put back (its plots registered again, never attached
## twice) or a fresh one. It goes first among
## Main's children, keeping the processing order (area, player, camera,
## HUD, fade). Returns whether the swap happened.
func _swap_area(scene: PackedScene, entry_id: String) -> bool:
	var next: GameArea = _parked_areas.get(scene.resource_path)
	var restored: bool = next != null
	if not restored:
		var instance := scene.instantiate()
		next = instance as GameArea
		if next == null:
			push_warning("Main.load_area: %s is not an area" % scene.resource_path)
			instance.free()
			return false
	FarmManager.cancel_seed_choice()
	var old := area
	FarmManager.release_plots_in(old)
	remove_child(old)
	if _keeps_alive(old):
		_parked_areas[old.scene_file_path] = old
	else:
		old.free()
	_parked_areas.erase(scene.resource_path)
	area = next
	add_child(area)
	move_child(area, 0)
	if restored:
		_reregister_plots(area)
	else:
		area.attach_player(player)
	var entry := _find_entry(area, entry_id)
	if entry != null:
		player.place_at(entry.global_transform)
	else:
		push_warning("Main.load_area: the area has no entry; the player stays put")
		player.place_at(player.global_transform)
	_apply_camera_bounds()
	_apply_camera_distance()
	follow_camera.snap_to_target()
	AreaRouter.notify_arrived(area.area_id)
	return true

## A parked area's farm plots — the same nodes, never freed — are tracked
## again through FarmManager's own register_plot(): each gets back the state
## release_plots_in() captured when the area was left, so no farm time
## passed while it was parked (D-31).
func _reregister_plots(restored_area: GameArea) -> void:
	for node in restored_area.find_children("*", "Area3D", true, false):
		var plot := node as FarmPlot
		if plot != null:
			FarmManager.register_plot(plot)

## Whether a left area is parked rather than freed — its AreaDefinition's
## keep_alive_when_left (data, never a name in code).
func _keeps_alive(left: GameArea) -> bool:
	var definition := AreaRouter.get_definition(left.area_id)
	return definition != null and definition.keep_alive_when_left

## The camera takes the current area's bounds (M03.4) — replacing the
## previous area's, or clearing them if this area has none.
func _apply_camera_bounds() -> void:
	var bounds := _find_camera_bounds(area)
	if bounds != null:
		follow_camera.set_bounds(bounds.get_rect())
	else:
		follow_camera.clear_bounds()

## An area with a fixed camera distance (an interior's close framing, D-32)
## gets it, and the player's own zoom is kept; any other area gets that
## zoom back. The camera itself is unchanged — only its distance is set.
func _apply_camera_distance() -> void:
	var definition := AreaRouter.get_definition(area.area_id)
	var distance := definition.camera_distance if definition != null else 0.0
	if distance > 0.0:
		if _free_zoom_distance < 0.0:
			_free_zoom_distance = follow_camera.get_zoom_distance()
		follow_camera.set_zoom_distance(distance)
	elif _free_zoom_distance >= 0.0:
		follow_camera.set_zoom_distance(_free_zoom_distance)
		_free_zoom_distance = -1.0

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
