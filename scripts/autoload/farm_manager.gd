extends Node

## The single authority for farming beyond an individual plot. Session-only
## by design: everything here starts fresh at launch from data and is never
## saved (there is no scene reload anywhere, so a session = an app launch).
##
## Owns:
## - Crops, loaded data-driven from res://data/crops/ (a new crop is a new
##   CropDefinition .tres + CropVisual scene — no code change anywhere).
## - Seeds: each crop's starting_seeds, minus one per planting, plus one
##   back per harvest, plus at most one exploration reward per crop.
##   Invariant: seeds in hand + crops in the ground =
##   starting seeds + exploration seeds found. Never negative.
## - Exploration seed rewards (CropDefinition.found_seed_source/_id):
##   granted once per session when ExplorationManager reports a place
##   reached, or DiscoveryManager reports that discovery found.
## - Farm progression: which crops have grown/been harvested, and a small
##   fixed set of quiet milestones, announced via milestone_reached.
## - Plots: every FarmPlot registers under its stable plot_id; plots that
##   start unlocked form the starter garden. A future plot is just another
##   FarmPlot with a new plot_id (and unlocked = false until unlock_plot()).
## - Seed-choice coordination between a plot on prepared soil and the HUD's
##   SeedPicker. The HUD only ever talks to FarmManager, never to a plot.
##
## Each FarmPlot still owns its own state, crop, growth and animation; it
## only reports planted/ready/harvested here. HUD and Journal only display.

signal crop_planted(crop_definition: CropDefinition, announced_by_milestone: bool)
signal crop_harvested(crop_definition: CropDefinition, points_awarded: int)
signal seeds_changed
signal seed_choice_requested
signal seed_choice_closed
signal seed_found(crop_definition: CropDefinition)
signal milestone_reached(milestone_id: String, message: String, bonus_points: int)

const CROPS_PATH := "res://data/crops/"
## The ExplorationManager place id that is this garden.
const GARDEN_PLACE_ID := "quiet_farm"

const FIRST_SEED := "first_seed"
const FIRST_HARVEST := "first_harvest"
const ALL_STARTER_CROPS := "all_starter_crops"
const GARDEN_COMPLETE := "garden_complete"
const CROP_GROWN_PREFIX := "grown:"

const FIRST_HARVEST_BONUS := 10
const ALL_STARTER_CROPS_BONUS := 40
const GARDEN_COMPLETE_BONUS := 30

const NUMBER_WORDS := ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]

var _crops: Array[CropDefinition] = []
var _seeds: Dictionary = {}
var _found_seed_crop_ids: Array[String] = []
var _grown_crop_ids: Array[String] = []
var _harvested_crop_ids: Array[String] = []
var _milestones_reached: Array[String] = []
var _planted_count: int = 0
var _harvested_count: int = 0
var _ready_crop_count: int = 0
var _garden_found: bool = false

var _plots: Dictionary = {}
var _starter_plot_ids: Array[String] = []
var _harvested_plot_ids: Array[String] = []
var _pending_plot: FarmPlot

func _ready() -> void:
	_load_crops()
	for crop in _crops:
		_seeds[crop.crop_id] = maxi(crop.starting_seeds, 0)
	# Discoveries are exploration too. Both signals count — discovery_made
	# only fires the first time *ever* (it's saved), and a seed reward is
	# once per session, so a returning player can still find it.
	DiscoveryManager.discovery_made.connect(_on_discovery_found)
	DiscoveryManager.discovery_repeated.connect(_on_discovery_found)

# --- Crops & seeds ----------------------------------------------------------

## Crops in a stable, gentle order: cheapest/fastest first.
func get_crops() -> Array[CropDefinition]:
	return _crops.duplicate()

func get_seed_count(crop_id: String) -> int:
	return int(_seeds.get(crop_id, 0))

func get_found_seed_names() -> PackedStringArray:
	var names: PackedStringArray = []
	for crop in _crops:
		if _found_seed_crop_ids.has(crop.crop_id):
			names.append(crop.display_name)
	return names

func has_ready_crops() -> bool:
	return _ready_crop_count > 0

func is_garden_found() -> bool:
	return _garden_found

# --- Plots ------------------------------------------------------------------

## Called by every FarmPlot in _ready(). Identity is plot_id, never the node
## name or tree order. Plots that start unlocked are the starter garden.
func register_plot(plot: FarmPlot) -> void:
	if plot.plot_id == "":
		push_warning("FarmManager: a FarmPlot has no plot_id; it can't be tracked")
		return
	var existing: Variant = _plots.get(plot.plot_id)
	if is_instance_valid(existing) and existing != plot:
		push_warning("FarmManager: duplicate plot_id '%s'" % plot.plot_id)
		return
	_plots[plot.plot_id] = plot
	if plot.unlocked and not _starter_plot_ids.has(plot.plot_id):
		_starter_plot_ids.append(plot.plot_id)

## The one entry point a future expansion would use — no UI or cost here.
func unlock_plot(plot_id: String) -> void:
	var plot := _get_plot(plot_id)
	if plot:
		plot.set_unlocked(true)

func get_plot_counts() -> Dictionary:
	var unlocked := 0
	for plot_id: String in _plots:
		var plot := _get_plot(plot_id)
		if plot and plot.unlocked:
			unlocked += 1
	return {"unlocked": unlocked, "total": _plots.size(), "starter": _starter_plot_ids.size()}

# --- Seed choice & planting -------------------------------------------------

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
## left; the seed is consumed only after the plot confirms it planted. The
## pending plot is cleared before anything is announced, so a second tap
## arriving while the picker closes finds nothing to plant into.
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
	_planted_count += 1
	seed_choice_closed.emit()
	seeds_changed.emit()
	var announced := _reach(FIRST_SEED, "The garden has its first seed.", 0)
	crop_planted.emit(crop, announced)
	return true

# --- Reports from FarmPlot --------------------------------------------------

## A crop ripened. Balanced by notify_crop_harvested(), the only way a
## ready crop leaves READY.
func notify_crop_ready(crop_definition: CropDefinition) -> void:
	_ready_crop_count += 1
	if _grown_crop_ids.has(crop_definition.crop_id):
		return
	_grown_crop_ids.append(crop_definition.crop_id)
	_reach(CROP_GROWN_PREFIX + crop_definition.crop_id, "%s has grown in the garden." % crop_definition.display_name, 0)
	if _all_starter_crops_grown():
		var count := _starter_crops().size()
		_reach(ALL_STARTER_CROPS, "%s different crops have grown here." % _number_word(count), ALL_STARTER_CROPS_BONUS)

## A harvest paid out: exactly one seed of that crop comes back, so the
## loop renews itself without an economy.
func notify_crop_harvested(plot_id: String, crop_definition: CropDefinition, points_awarded: int) -> void:
	_seeds[crop_definition.crop_id] = get_seed_count(crop_definition.crop_id) + 1
	_ready_crop_count = maxi(_ready_crop_count - 1, 0)
	_harvested_count += 1
	if not _harvested_crop_ids.has(crop_definition.crop_id):
		_harvested_crop_ids.append(crop_definition.crop_id)
	if plot_id != "" and not _harvested_plot_ids.has(plot_id):
		_harvested_plot_ids.append(plot_id)
	seeds_changed.emit()
	crop_harvested.emit(crop_definition, points_awarded)
	_reach(FIRST_HARVEST, "Something you planted has finally come home.", FIRST_HARVEST_BONUS)
	if _is_starter_garden_complete():
		_reach(GARDEN_COMPLETE, "The garden feels complete.", GARDEN_COMPLETE_BONUS)

# --- Exploration --------------------------------------------------------------

## Called by ExplorationManager the first time a place is reached this
## session. Never touches plots.
func notify_place_reached(place_id: String) -> void:
	if place_id == GARDEN_PLACE_ID:
		_garden_found = true
	_grant_found_seeds("place", place_id)

func _on_discovery_found(definition: DiscoveryDefinition) -> void:
	_grant_found_seeds("discovery", definition.id)

func _grant_found_seeds(source: String, source_id: String) -> void:
	if source_id == "":
		return
	var granted := false
	for crop in _crops:
		if crop.found_seed_source != source or crop.found_seed_source_id != source_id:
			continue
		if _found_seed_crop_ids.has(crop.crop_id):
			continue
		_found_seed_crop_ids.append(crop.crop_id)
		_seeds[crop.crop_id] = get_seed_count(crop.crop_id) + 1
		granted = true
		seed_found.emit(crop)
	if granted:
		seeds_changed.emit()

# --- Progression (read by the Journal) --------------------------------------

## Milestones in display order, each {id, label, reached}. The per-crop
## entries come from the starter crops' own data, so a new starter crop
## gets its own milestone automatically.
func get_milestones() -> Array:
	var rows: Array = []
	rows.append(_milestone_row(FIRST_SEED, "First Seed"))
	rows.append(_milestone_row(FIRST_HARVEST, "First Harvest"))
	for crop in _starter_crops():
		rows.append(_milestone_row(CROP_GROWN_PREFIX + crop.crop_id, "%s Grown" % crop.display_name))
	rows.append(_milestone_row(ALL_STARTER_CROPS, "All %s Crops" % _number_word(_starter_crops().size())))
	rows.append(_milestone_row(GARDEN_COMPLETE, "Starter Garden Complete"))
	return rows

func get_grown_crop_names() -> PackedStringArray:
	return _crop_names_for(_grown_crop_ids)

func get_harvested_crop_names() -> PackedStringArray:
	return _crop_names_for(_harvested_crop_ids)

func get_activity_counts() -> Dictionary:
	return {"planted": _planted_count, "harvested": _harvested_count}

# --- Internals ----------------------------------------------------------------

## Records a milestone once and announces it. Returns whether it was newly
## reached (so callers can avoid a second card for the same moment).
func _reach(milestone_id: String, message: String, bonus_points: int) -> bool:
	if _milestones_reached.has(milestone_id):
		return false
	_milestones_reached.append(milestone_id)
	if bonus_points > 0:
		PointsManager.add_points(bonus_points)
	milestone_reached.emit(milestone_id, message, bonus_points)
	return true

## Validity is checked before the cast: a stored reference can outlive its
## node, and casting a freed object errors.
func _get_plot(plot_id: String) -> FarmPlot:
	var value: Variant = _plots.get(plot_id)
	if not is_instance_valid(value):
		return null
	return value as FarmPlot

func _milestone_row(milestone_id: String, label: String) -> Dictionary:
	return {"id": milestone_id, "label": label, "reached": _milestones_reached.has(milestone_id)}

func _starter_crops() -> Array[CropDefinition]:
	var starters: Array[CropDefinition] = []
	for crop in _crops:
		if crop.starting_seeds > 0:
			starters.append(crop)
	return starters

func _all_starter_crops_grown() -> bool:
	var starters := _starter_crops()
	if starters.is_empty():
		return false
	for crop in starters:
		if not _grown_crop_ids.has(crop.crop_id):
			return false
	return true

## Every plot the session started with has produced at least one harvest.
func _is_starter_garden_complete() -> bool:
	if _starter_plot_ids.is_empty():
		return false
	for plot_id in _starter_plot_ids:
		if not _harvested_plot_ids.has(plot_id):
			return false
	return true

func _crop_names_for(crop_ids: Array[String]) -> PackedStringArray:
	var names: PackedStringArray = []
	for crop in _crops:
		if crop_ids.has(crop.crop_id):
			names.append(crop.display_name)
	return names

func _number_word(count: int) -> String:
	if count >= 0 and count < NUMBER_WORDS.size():
		return NUMBER_WORDS[count]
	return str(count)

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
