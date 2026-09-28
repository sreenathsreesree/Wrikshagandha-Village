extends Node

## The single authority for farming beyond an individual plot. Saved and
## restored through SaveManager (get_save_data / apply_save_data, see
## docs/farming_persistence_plan.md); a player with no farm save starts
## fresh from data. Exploration seed rewards are granted once ever.
##
## Owns:
## - Crops, loaded data-driven from res://data/crops/ (a new crop is a new
##   CropDefinition .tres + CropVisual scene — no code change anywhere).
## - Seeds: each crop's starting_seeds, minus one per planting, plus one
##   back per harvest, plus at most one exploration reward per crop.
##   Invariant (across sessions): seeds in hand + crops in the ground =
##   starting seeds + exploration seeds found (ever). Never negative.
## - Exploration seed rewards (CropDefinition.found_seed_source/_id):
##   granted once per session when ExplorationManager reports a place
##   reached, or DiscoveryManager reports that discovery found.
## - The garden's pull on the Meadow: an aggregate interest level (0..1)
##   summed from the ready crops' CropDefinition.wildlife_interest, pushed
##   out via garden_interest_changed only when it changes. Nothing polls
##   plots; WorldSimulation relays the level to wildlife.
## - Crop quality (Plain / Good / Fine) from two factors, both rated here
##   from facts the plot reports (FarmPlot owns the facts, never the rule):
##   * soil (rotation), rated at planting from the plot's last harvests —
##     tired (same crop again) / good (fresh or partly rotated) / rotated;
##     shown on the seed picker before the choice;
##   * care, rated at ripening from the longest the crop waited thirsty
##     against its CropDefinition.thirst_tolerance — neglected / tended /
##     careful.
##   soil + care (0..4): 4 = Fine, 2-3 = Good, 0-1 = Plain. Fine needs both
##   a rotated bed and careful watering; either factor alone can't carry a
##   crop, and neither alone ruins one.
## - The basket: harvested produce by crop and quality (saved; a
##   foundation — nothing consumes it yet).
## - Farm progression: which crops have grown, and a small fixed set of
##   quiet milestones, announced via milestone_reached.
## - Plots: every FarmPlot registers under its stable plot_id; plots that
##   start unlocked form the starter garden. A locked plot names the
##   milestone that opens it (FarmPlot.unlock_on_milestone) — the garden
##   grows as it's tended, with no cost or menu.
## - Seed-choice coordination between a plot on prepared soil and the HUD's
##   SeedPicker. The HUD only ever talks to FarmManager, never to a plot.
##
## Each FarmPlot still owns its own state, crop, growth and animation; it
## only reports planted/ready/harvested here. HUD and Journal only display.

signal crop_planted(crop_definition: CropDefinition, announced_by_milestone: bool, soil: int)
signal crop_harvested(crop_definition: CropDefinition, points_awarded: int, quality: int, care: int)
signal seeds_changed
signal produce_changed
signal seed_choice_requested
signal seed_choice_closed
## new_crop: this seed introduces a crop the player didn't know yet (an
## exploration-only crop) — presented as a find in its own right.
signal seed_found(crop_definition: CropDefinition, new_crop: bool)
signal milestone_reached(milestone_id: String, message: String, bonus_points: int)
signal garden_interest_changed(level: float)

const CROPS_PATH := "res://data/crops/"
const SAVE_VERSION := 1
## The attraction key garden-noticing wildlife is configured with.
const WILDLIFE_ATTRACTION_KEY := "garden"
## Cap on the summed interest, so a garden full of ripe sunflowers is a
## strong pull, never a certainty — wildlife keeps its own wandering.
const MAX_GARDEN_INTEREST := 0.7
## A garden in bloom keeps a little pull on the Meadow even with nothing
## ripe — butterflies drift by more often. The lasting part of the bloom's
## world change, through the same interest relay (no new system).
const BLOOM_GARDEN_INTEREST := 0.15
## The ExplorationManager place id that is this garden.
const GARDEN_PLACE_ID := "quiet_farm"

const QUALITY_PLAIN := 0
const QUALITY_GOOD := 1
const QUALITY_FINE := 2
const QUALITY_NAMES := ["Plain", "Good", "Fine"]
## Soil ratings share the 0..2 scale: tired / good / rotated. Shown where
## the player chooses (seed picker, planting note), so the rotation rule is
## learned by seeing it, not reading it.
const SOIL_NOTES := ["Tired soil", "Good soil", "✦ Rotated soil"]
const CARE_NEGLECTED := 0
const CARE_TENDED := 1
const CARE_CAREFUL := 2
## Shown under the crop's name on the harvest card, so care is learned the
## same way.
const CARE_NOTES := ["left thirsty", "watered", "watered with care"]
## Beyond this many times a crop's thirst_tolerance, a wait is neglect.
const NEGLECT_FACTOR := 3.0
## Harvest points relative to the crop's points_value (Good = unchanged).
const QUALITY_POINT_SCALE := [0.75, 1.0, 1.5]
## Mature size relative to the crop's own mature_scale — quality is visible
## in the garden itself, no label needed.
const QUALITY_SIZE := [0.9, 1.0, 1.1]
## How many past harvests a plot's soil remembers.
const SOIL_MEMORY := 2

const FIRST_SEED := "first_seed"
const FIRST_HARVEST := "first_harvest"
const FIRST_FINE := "first_fine"
const GARDEN_IN_BLOOM := "garden_in_bloom"
const ALL_STARTER_CROPS := "all_starter_crops"
const GARDEN_COMPLETE := "garden_complete"
const CROP_GROWN_PREFIX := "grown:"

const FIRST_HARVEST_BONUS := 10
const ALL_STARTER_CROPS_BONUS := 40
const GARDEN_COMPLETE_BONUS := 30
const GARDEN_IN_BLOOM_BONUS := 50

const NUMBER_WORDS := ["No", "One", "Two", "Three", "Four", "Five", "Six", "Seven", "Eight", "Nine", "Ten"]

var _crops: Array[CropDefinition] = []
var _seeds: Dictionary = {}
var _found_seed_crop_ids: Array[String] = []
var _grown_crop_ids: Array[String] = []
## crop_id -> [plain, good, fine] counts harvested this session.
var _produce: Dictionary = {}
var _milestones_reached: Array[String] = []
var _planted_count: int = 0
var _harvested_count: int = 0
## crop_id -> how many of that crop are READY right now (exact, no float
## drift): the source of has_ready_crops() and the garden interest level.
var _ready_by_crop: Dictionary = {}
var _garden_interest: float = 0.0
## Time.get_ticks_msec() of the most recent ripening, -1 if none yet —
## lets the garden tell "ripened while you were away" from "was already
## ripe when you left".
var _last_ripened_msec: int = -1
## crop_id -> {"source": "place"/"discovery", "source_id": String}
var _found_seed_origins: Dictionary = {}
var _garden_found: bool = false

var _plots: Dictionary = {}
var _starter_plot_ids: Array[String] = []
var _harvested_plot_ids: Array[String] = []
var _pending_plot: FarmPlot
## Saved plot states waiting for their FarmPlot to register (the save is
## loaded by an autoload, before the world scene exists). Carried forward
## into the next save untouched if a plot never shows up.
var _saved_plot_states: Dictionary = {}

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

## Crops the player knows about: starter crops, plus any crop whose seed
## has been found. An exploration-only crop stays a secret (absent from the
## seed picker and Journal) until its seed turns up.
func get_known_crops() -> Array[CropDefinition]:
	var known: Array[CropDefinition] = []
	for crop in _crops:
		if _is_known(crop):
			known.append(crop)
	return known

func _is_known(crop: CropDefinition) -> bool:
	return crop.starting_seeds > 0 or _found_seed_crop_ids.has(crop.crop_id) or get_seed_count(crop.crop_id) > 0

# --- Quality & basket --------------------------------------------------------

## The soil rule. recent_crop_ids: the plot's past harvests, oldest first.
func rate_soil(recent_crop_ids: Array[String], crop_id: String) -> int:
	if recent_crop_ids.is_empty():
		return QUALITY_GOOD
	if recent_crop_ids.back() == crop_id:
		return QUALITY_PLAIN
	if recent_crop_ids.has(crop_id):
		return QUALITY_GOOD
	return QUALITY_FINE

## The soil this crop would get in the plot waiting for a seed — read by
## the seed picker to show on each card.
func get_soil_rating(crop: CropDefinition) -> int:
	if crop == null or not is_choosing_seed():
		return QUALITY_GOOD
	return rate_soil(_pending_plot.get_recent_crop_ids(), crop.crop_id)

## The care rule: the longest single wait for water, in seconds.
func rate_care(crop: CropDefinition, longest_thirst_seconds: float) -> int:
	var tolerance := maxf(crop.thirst_tolerance, 1.0)
	if longest_thirst_seconds <= tolerance:
		return CARE_CAREFUL
	if longest_thirst_seconds <= tolerance * NEGLECT_FACTOR:
		return CARE_TENDED
	return CARE_NEGLECTED

## Soil and care together decide the harvest quality.
func combine_quality(soil: int, care: int) -> int:
	var score := clampi(soil, 0, 2) + clampi(care, 0, 2)
	if score >= 4:
		return QUALITY_FINE
	if score >= 2:
		return QUALITY_GOOD
	return QUALITY_PLAIN

func get_care_note(care: int) -> String:
	return CARE_NOTES[clampi(care, 0, CARE_NOTES.size() - 1)]

func get_quality_name(quality: int) -> String:
	return QUALITY_NAMES[clampi(quality, 0, QUALITY_NAMES.size() - 1)]

func get_soil_note(quality: int) -> String:
	return SOIL_NOTES[clampi(quality, 0, SOIL_NOTES.size() - 1)]

func get_quality_size(quality: int) -> float:
	return QUALITY_SIZE[clampi(quality, 0, QUALITY_SIZE.size() - 1)]

func get_harvest_points(crop: CropDefinition, quality: int) -> int:
	var factor: float = QUALITY_POINT_SCALE[clampi(quality, 0, QUALITY_POINT_SCALE.size() - 1)]
	return maxi(roundi(crop.points_value * factor), 1)

## quality < 0 = all qualities.
func get_produce_count(crop_id: String, quality: int = -1) -> int:
	var counts: Array = _produce.get(crop_id, [0, 0, 0])
	if quality < 0:
		return int(counts[0]) + int(counts[1]) + int(counts[2])
	return int(counts[clampi(quality, 0, 2)])

func get_produce_total(quality: int = -1) -> int:
	var total := 0
	for crop in _crops:
		total += get_produce_count(crop.crop_id, quality)
	return total

## The basket in crop order, only crops with something in it:
## [{crop, total, plain, good, fine}].
func get_basket() -> Array:
	var rows: Array = []
	for crop in _crops:
		var total := get_produce_count(crop.crop_id)
		if total <= 0:
			continue
		rows.append({
			"crop": crop,
			"total": total,
			"plain": get_produce_count(crop.crop_id, QUALITY_PLAIN),
			"good": get_produce_count(crop.crop_id, QUALITY_GOOD),
			"fine": get_produce_count(crop.crop_id, QUALITY_FINE),
		})
	return rows

## Where each exploration seed was found, in crop order:
## [{crop, source, source_id}]. The Journal turns ids into place/discovery
## names; nothing here knows how they're displayed.
func get_found_seed_origins() -> Array:
	var rows: Array = []
	for crop in _crops:
		if _found_seed_origins.has(crop.crop_id):
			var origin: Dictionary = _found_seed_origins[crop.crop_id]
			rows.append({"crop": crop, "source": origin.source, "source_id": origin.source_id})
	return rows

func has_ready_crops() -> bool:
	for crop_id: String in _ready_by_crop:
		if int(_ready_by_crop[crop_id]) > 0:
			return true
	return false

func get_last_ripened_msec() -> int:
	return _last_ripened_msec

func get_garden_interest() -> float:
	return _garden_interest

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
	elif not plot.unlocked and plot.unlock_on_milestone != "" and _milestones_reached.has(plot.unlock_on_milestone):
		plot.set_unlocked(true)
	if _saved_plot_states.has(plot.plot_id):
		var data: Dictionary = _saved_plot_states[plot.plot_id]
		_saved_plot_states.erase(plot.plot_id)
		var restored := plot.restore(data, _find_crop(String(data.get("crop", ""))))
		if restored and plot.plot_state == FarmPlot.PlotState.READY:
			# Counted quietly — no ripening moment or milestone replay. It
			# did ripen while the player was away, so the garden may greet
			# them on their first visit this session.
			_ready_by_crop[restored.crop_id] = int(_ready_by_crop.get(restored.crop_id, 0)) + 1
			_last_ripened_msec = maxi(_last_ripened_msec, 0)
			_update_garden_interest()

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
	var soil := rate_soil(_pending_plot.get_recent_crop_ids(), crop.crop_id)
	if not _pending_plot.plant(crop, soil):
		return false
	_seeds[crop.crop_id] = get_seed_count(crop.crop_id) - 1
	_pending_plot = null
	_planted_count += 1
	seed_choice_closed.emit()
	seeds_changed.emit()
	var announced := _reach(FIRST_SEED, "The garden has its first seed.", 0)
	crop_planted.emit(crop, announced, soil)
	return true

# --- Reports from FarmPlot --------------------------------------------------

## A crop ripened. Balanced by notify_crop_harvested(), the only way a
## ready crop leaves READY.
func notify_crop_ready(crop_definition: CropDefinition) -> void:
	_ready_by_crop[crop_definition.crop_id] = int(_ready_by_crop.get(crop_definition.crop_id, 0)) + 1
	_last_ripened_msec = Time.get_ticks_msec()
	_update_garden_interest()
	if _grown_crop_ids.has(crop_definition.crop_id):
		return
	_grown_crop_ids.append(crop_definition.crop_id)
	var grown_line := crop_definition.grown_note
	if grown_line == "":
		grown_line = "%s has grown in the garden." % crop_definition.display_name
	_reach(CROP_GROWN_PREFIX + crop_definition.crop_id, grown_line, 0)
	if _all_starter_crops_grown():
		var count := _starter_crops().size()
		_reach(ALL_STARTER_CROPS, "%s different crops have grown here." % _number_word(count), ALL_STARTER_CROPS_BONUS)

## A harvest paid out: exactly one seed of that crop comes back, so the
## loop renews itself without an economy, and the produce goes into the
## basket at the quality it grew.
func notify_crop_harvested(plot_id: String, crop_definition: CropDefinition, points_awarded: int, quality: int, care: int) -> void:
	_seeds[crop_definition.crop_id] = get_seed_count(crop_definition.crop_id) + 1
	_ready_by_crop[crop_definition.crop_id] = maxi(int(_ready_by_crop.get(crop_definition.crop_id, 0)) - 1, 0)
	_update_garden_interest()
	var counts: Array = _produce.get(crop_definition.crop_id, [0, 0, 0])
	counts[clampi(quality, 0, 2)] = int(counts[clampi(quality, 0, 2)]) + 1
	_produce[crop_definition.crop_id] = counts
	_harvested_count += 1
	if plot_id != "" and not _harvested_plot_ids.has(plot_id):
		_harvested_plot_ids.append(plot_id)
	seeds_changed.emit()
	produce_changed.emit()
	crop_harvested.emit(crop_definition, points_awarded, quality, care)
	_reach(FIRST_HARVEST, "Something you planted has finally come home.", FIRST_HARVEST_BONUS)
	if quality >= QUALITY_FINE:
		_reach(FIRST_FINE, "A rotated bed and a careful hand — this one grew fine.", 0)
	if _is_starter_garden_complete():
		_reach(GARDEN_COMPLETE, "The starter garden feels complete.", GARDEN_COMPLETE_BONUS)
	if _is_garden_in_bloom():
		if _reach(GARDEN_IN_BLOOM, "Every bed has given something back. The Quiet Garden is in bloom.", GARDEN_IN_BLOOM_BONUS):
			_update_garden_interest()

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
		var new_crop := not _is_known(crop)
		_found_seed_crop_ids.append(crop.crop_id)
		_found_seed_origins[crop.crop_id] = {"source": source, "source_id": source_id}
		_seeds[crop.crop_id] = get_seed_count(crop.crop_id) + 1
		granted = true
		seed_found.emit(crop, new_crop)
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
	rows.append(_milestone_row(FIRST_FINE, "A Fine Harvest"))
	for crop in _starter_crops():
		rows.append(_milestone_row(CROP_GROWN_PREFIX + crop.crop_id, "%s Grown" % crop.display_name))
	rows.append(_milestone_row(ALL_STARTER_CROPS, "All %s Crops" % _number_word(_starter_crops().size())))
	rows.append(_milestone_row(GARDEN_COMPLETE, "Starter Garden Complete"))
	rows.append(_milestone_row(GARDEN_IN_BLOOM, "Garden in Bloom"))
	return rows

func is_milestone_reached(milestone_id: String) -> bool:
	return _milestones_reached.has(milestone_id)

func get_grown_crop_names() -> PackedStringArray:
	return _crop_names_for(_grown_crop_ids)

func get_activity_counts() -> Dictionary:
	return {"planted": _planted_count, "harvested": _harvested_count}

# --- Persistence ----------------------------------------------------------------

## Everything the farm needs to come back exactly as it was. Derived state
## (ready counts, garden interest, unlocked plots) is rebuilt, never saved.
func get_save_data() -> Dictionary:
	var plots := _saved_plot_states.duplicate(true)
	for plot_id: String in _plots:
		var plot := _get_plot(plot_id)
		if plot:
			plots[plot_id] = plot.capture()
	var basket := {}
	for crop_id: String in _produce:
		basket[crop_id] = Array(_produce[crop_id])
	return {
		"version": SAVE_VERSION,
		"seeds": _seeds.duplicate(),
		"found_seeds": _found_seed_origins.duplicate(true),
		"grown": Array(_grown_crop_ids),
		"basket": basket,
		"milestones": Array(_milestones_reached),
		"counts": {"planted": _planted_count, "harvested": _harvested_count},
		"harvested_plots": Array(_harvested_plot_ids),
		"garden_found": _garden_found,
		"plots": plots,
	}

## Called by SaveManager.load_game() at boot, before any FarmPlot exists.
## An empty dictionary (no farm in the save yet) keeps the fresh farm.
## Unknown crop ids (crop removed from data) are dropped.
func apply_save_data(data: Dictionary) -> void:
	if data.is_empty():
		return
	for crop in _crops:
		var saved_seeds: Variant = data.get("seeds", {}).get(crop.crop_id)
		_seeds[crop.crop_id] = maxi(int(saved_seeds), 0) if saved_seeds != null else maxi(crop.starting_seeds, 0)
	_found_seed_crop_ids.clear()
	_found_seed_origins.clear()
	var found: Dictionary = data.get("found_seeds", {})
	for crop_id: String in found:
		if _find_crop(crop_id) == null:
			continue
		var origin: Dictionary = found[crop_id]
		_found_seed_crop_ids.append(crop_id)
		_found_seed_origins[crop_id] = {"source": String(origin.get("source", "")), "source_id": String(origin.get("source_id", ""))}
	_grown_crop_ids.clear()
	for crop_id: Variant in data.get("grown", []):
		if _find_crop(String(crop_id)):
			_grown_crop_ids.append(String(crop_id))
	_produce.clear()
	var basket: Dictionary = data.get("basket", {})
	for crop_id: String in basket:
		var counts: Array = basket[crop_id]
		if _find_crop(crop_id) and counts.size() == 3:
			_produce[crop_id] = [maxi(int(counts[0]), 0), maxi(int(counts[1]), 0), maxi(int(counts[2]), 0)]
	_milestones_reached.clear()
	for milestone_id: Variant in data.get("milestones", []):
		_milestones_reached.append(String(milestone_id))
	var counts_data: Dictionary = data.get("counts", {})
	_planted_count = int(counts_data.get("planted", 0))
	_harvested_count = int(counts_data.get("harvested", 0))
	_harvested_plot_ids.clear()
	for plot_id: Variant in data.get("harvested_plots", []):
		_harvested_plot_ids.append(String(plot_id))
	_garden_found = bool(data.get("garden_found", false))
	_saved_plot_states = data.get("plots", {}).duplicate(true)
	_update_garden_interest()
	seeds_changed.emit()
	produce_changed.emit()

func _find_crop(crop_id: String) -> CropDefinition:
	for crop in _crops:
		if crop.crop_id == crop_id:
			return crop
	return null

# --- Internals ----------------------------------------------------------------

## Records a milestone once and announces it. Returns whether it was newly
## reached (so callers can avoid a second card for the same moment).
func _reach(milestone_id: String, message: String, bonus_points: int) -> bool:
	if _milestones_reached.has(milestone_id):
		return false
	_milestones_reached.append(milestone_id)
	if bonus_points > 0:
		PointsManager.add_points(bonus_points)
	if _unlock_plots_for(milestone_id) > 0:
		message += " There's room to grow a little more."
	milestone_reached.emit(milestone_id, message, bonus_points)
	return true

## Opens every locked plot waiting on this milestone. Announced as part of
## the milestone's own card — one card per moment.
func _unlock_plots_for(milestone_id: String) -> int:
	var opened := 0
	for plot_id: String in _plots:
		var plot := _get_plot(plot_id)
		if plot and not plot.unlocked and plot.unlock_on_milestone == milestone_id:
			plot.set_unlocked(true)
			opened += 1
	return opened

## Recomputed only on ripen/harvest events, from crop data — never by
## looking at plots, never per frame. Emits only on an actual change.
func _update_garden_interest() -> void:
	var total := 0.0
	for crop in _crops:
		total += float(_ready_by_crop.get(crop.crop_id, 0)) * crop.wildlife_interest
	if _milestones_reached.has(GARDEN_IN_BLOOM):
		total += BLOOM_GARDEN_INTEREST
	var level := clampf(total, 0.0, MAX_GARDEN_INTEREST)
	if is_equal_approx(level, _garden_interest):
		return
	_garden_interest = level
	garden_interest_changed.emit(level)

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

## The whole garden, not just the start: every plot open and harvested at
## least once, every crop the player knows harvested, and at least one
## Fine harvest. Derived from data — a new plot or found crop simply
## becomes part of it.
func _is_garden_in_bloom() -> bool:
	if _plots.is_empty() or not _milestones_reached.has(FIRST_FINE):
		return false
	for plot_id: String in _plots:
		var plot := _get_plot(plot_id)
		if plot == null or not plot.unlocked or not _harvested_plot_ids.has(plot_id):
			return false
	for crop in get_known_crops():
		if get_produce_count(crop.crop_id) <= 0:
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
