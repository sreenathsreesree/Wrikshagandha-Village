extends Node

## Farming's one piece of shared session state, plus the relay between the
## 3D garden and the UI:
##
## - The crop list, loaded data-driven from res://data/crops/ — adding a
##   crop is a new CropDefinition .tres (plus its CropVisual scene), with
##   no code change here.
## - The session seed inventory: each crop's starting_seeds at launch,
##   minus one per planting, plus one back per harvest, plus at most one
##   "found" seed per crop from exploration (CropDefinition.
##   found_seed_place_id). Never negative, never saved. Invariant: seeds in
##   hand + crops in the ground = starting seeds + found seeds.
## - How many crops are ready right now, so the garden itself can react
##   when the player comes back to ripe crops (EnvironmentalEvent's
##   requires_ready_crops gate).
## - Seed-choice coordination: a FarmPlot on prepared soil asks for a
##   choice; the HUD's seed picker shows it; the player's pick comes back
##   through choose_seed(), which checks and consumes the seed and plants.
##   The HUD only ever talks to FarmManager, never to a 3D plot directly.
##
## Every FarmPlot still owns its own growth state; this holds no plot state
## beyond which plot (if any) is currently waiting for a seed choice.

signal crop_planted(crop_definition: CropDefinition)
signal crop_harvested(crop_definition: CropDefinition, points_awarded: int)
signal seeds_changed
signal seed_choice_requested
signal seed_choice_closed

const CROPS_PATH := "res://data/crops/"

var _crops: Array[CropDefinition] = []
var _seeds: Dictionary = {}
var _pending_plot: FarmPlot
var _ready_crop_count: int = 0
var _found_seed_crop_ids: Array[String] = []

func _ready() -> void:
	_load_crops()
	for crop in _crops:
		_seeds[crop.crop_id] = maxi(crop.starting_seeds, 0)

## Crops in a stable, gentle order: cheapest/fastest first.
func get_crops() -> Array[CropDefinition]:
	return _crops.duplicate()

func get_seed_count(crop_id: String) -> int:
	return int(_seeds.get(crop_id, 0))

func is_choosing_seed() -> bool:
	return _pending_plot != null and is_instance_valid(_pending_plot)

func request_seed_choice(plot: FarmPlot) -> void:
	if plot == null or not plot.can_plant():
		return
	_pending_plot = plot
	seed_choice_requested.emit()

## plot == null cancels whatever is open (e.g. the picker's close button);
## otherwise only cancels if that plot is the one waiting, so an unrelated
## plot leaving range never closes another plot's picker.
func cancel_seed_choice(plot: FarmPlot = null) -> void:
	if _pending_plot == null:
		return
	if plot != null and plot != _pending_plot:
		return
	_pending_plot = null
	seed_choice_closed.emit()

## The only way a seed gets planted. Refuses (and leaves inventory alone)
## if the plot is gone or no longer plantable, or no seed of that crop is
## left; the seed is consumed only after the plot confirms it planted.
func choose_seed(crop: CropDefinition) -> bool:
	if crop == null or get_seed_count(crop.crop_id) <= 0:
		return false
	if not is_choosing_seed() or not _pending_plot.can_plant():
		cancel_seed_choice()
		return false
	if not _pending_plot.plant(crop):
		return false
	_seeds[crop.crop_id] = get_seed_count(crop.crop_id) - 1
	_pending_plot = null
	seed_choice_closed.emit()
	seeds_changed.emit()
	crop_planted.emit(crop)
	return true

## Called by FarmPlot once its harvest pays out: exactly one seed of the
## harvested crop comes back, so the loop renews itself without an economy.
func notify_crop_harvested(crop_definition: CropDefinition, points_awarded: int) -> void:
	_seeds[crop_definition.crop_id] = get_seed_count(crop_definition.crop_id) + 1
	_ready_crop_count = maxi(_ready_crop_count - 1, 0)
	seeds_changed.emit()
	crop_harvested.emit(crop_definition, points_awarded)

## Called by FarmPlot when a crop ripens. Balanced by the decrement in
## notify_crop_harvested(), the only way a ready crop leaves READY.
func notify_crop_ready(_crop_definition: CropDefinition) -> void:
	_ready_crop_count += 1

func has_ready_crops() -> bool:
	return _ready_crop_count > 0

## Exploration link, called by ExplorationManager when a place is reached:
## each crop whose found_seed_place_id matches gets one extra seed, once per
## session. Returns the crops that were granted (usually none).
func grant_found_seeds(place_id: String) -> Array[CropDefinition]:
	var granted: Array[CropDefinition] = []
	if place_id == "":
		return granted
	for crop in _crops:
		if crop.found_seed_place_id != place_id or _found_seed_crop_ids.has(crop.crop_id):
			continue
		_found_seed_crop_ids.append(crop.crop_id)
		_seeds[crop.crop_id] = get_seed_count(crop.crop_id) + 1
		granted.append(crop)
	if not granted.is_empty():
		seeds_changed.emit()
	return granted

func get_found_seed_names() -> PackedStringArray:
	var names: PackedStringArray = []
	for crop in _crops:
		if _found_seed_crop_ids.has(crop.crop_id):
			names.append(crop.display_name)
	return names

func _load_crops() -> void:
	_crops.clear()
	for path in ResourceDirectory.list_tres_paths(CROPS_PATH):
		var crop := load(path) as CropDefinition
		if crop == null or crop.crop_id == "":
			push_warning("FarmManager: %s is not a usable CropDefinition" % path)
			continue
		_crops.append(crop)
	_crops.sort_custom(_sort_crops)

func _sort_crops(a: CropDefinition, b: CropDefinition) -> bool:
	if a.points_value != b.points_value:
		return a.points_value < b.points_value
	return a.crop_id < b.crop_id
