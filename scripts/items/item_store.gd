extends RefCounted
class_name ItemStore

## The player's held items, counted by ItemDefinition id (M04.1, M04.2).
## An item may keep quality levels apart (ItemDefinition.quality_levels):
## its count is then one number per level — quality is an attribute of what
## is held, not a separate item (D-18). Only add(), remove() and
## apply_save_data() change a count. add() and remove() refuse an unknown
## id, a level the item doesn't have and an amount below 1; remove() takes
## all or nothing, so no count goes negative. An item holding nothing isn't
## listed. Items stack without a limit: no current design caps a stack.
##
## Not an autoload: FarmManager, the only system holding items so far,
## keeps the player's store (O-14), and the save writes it as "items".

const ITEMS_PATH := "res://data/items/"

var _definitions: Dictionary = {}
var _quantities: Dictionary = {}

## Every usable ItemDefinition in res://data/items/, in file order.
static func load_definitions() -> Array[ItemDefinition]:
	var definitions: Array[ItemDefinition] = []
	for path in ResourceDirectory.list_tres_paths(ITEMS_PATH):
		var definition := load(path) as ItemDefinition
		if definition == null or definition.id == "" or definition.quality_levels < 1:
			push_warning("ItemStore: %s is not a usable ItemDefinition" % path)
			continue
		definitions.append(definition)
	return definitions

## {crop_id: item_id} for the items of one category that belong to a crop.
static func crop_item_ids(definitions: Array[ItemDefinition], category: String) -> Dictionary:
	var ids := {}
	for definition in definitions:
		if definition.category == category and definition.crop_id != "" and not ids.has(definition.crop_id):
			ids[definition.crop_id] = definition.id
	return ids

## A store that knows these items (a duplicate id keeps the first).
func _init(definitions: Array[ItemDefinition]) -> void:
	for definition in definitions:
		if definition == null or definition.id == "" or _definitions.has(definition.id):
			push_warning("ItemStore: ignoring an empty or duplicate item definition")
			continue
		_definitions[definition.id] = definition

func is_valid_item(item_id: String) -> bool:
	return _definitions.has(item_id)

## null for an unknown id.
func get_definition(item_id: String) -> ItemDefinition:
	return _definitions.get(item_id)

## quality < 0 = every level together; an unknown id or level holds 0.
func get_quantity(item_id: String, quality: int = -1) -> int:
	var counts: Array = _quantities.get(item_id, [])
	if quality < 0:
		var total := 0
		for count: int in counts:
			total += count
		return total
	return int(counts[quality]) if quality < counts.size() else 0

func has(item_id: String, amount: int = 1, quality: int = -1) -> bool:
	return amount >= 1 and get_quantity(item_id, quality) >= amount

func add(item_id: String, amount: int = 1, quality: int = 0) -> bool:
	if not _accepts(item_id, quality) or amount < 1:
		push_warning("ItemStore: cannot add %d of '%s' (quality %d)" % [amount, item_id, quality])
		return false
	var counts := _counts_of(item_id)
	counts[quality] = int(counts[quality]) + amount
	_quantities[item_id] = counts
	return true

func remove(item_id: String, amount: int = 1, quality: int = 0) -> bool:
	if not _accepts(item_id, quality) or amount < 1:
		push_warning("ItemStore: cannot remove %d of '%s' (quality %d)" % [amount, item_id, quality])
		return false
	if get_quantity(item_id, quality) < amount:
		return false
	var counts := _counts_of(item_id)
	counts[quality] = int(counts[quality]) - amount
	if counts.max() == 0:
		_quantities.erase(item_id)
	else:
		_quantities[item_id] = counts
	return true

## A copy for the save: {item_id: [count per quality level]}.
func get_save_data() -> Dictionary:
	return _quantities.duplicate(true)

## Replaces every count from a save. An entry is kept only if its id is
## known and it holds one number per quality level (fractions truncated,
## negatives read as 0, as the farm save always did); anything else is
## dropped with a warning — never silently.
func apply_save_data(data: Dictionary) -> void:
	var loaded := {}
	for item_id: String in data:
		var counts := _whole_counts(item_id, data[item_id])
		if counts.is_empty():
			push_warning("ItemStore: ignoring saved item '%s' (unknown id or malformed counts)" % item_id)
			continue
		if counts.max() > 0:
			loaded[item_id] = counts
	_quantities = loaded

func _accepts(item_id: String, quality: int) -> bool:
	return is_valid_item(item_id) and quality >= 0 and quality < get_definition(item_id).quality_levels

## The item's counts, a fresh copy (zeros if nothing is held).
func _counts_of(item_id: String) -> Array:
	if _quantities.has(item_id):
		return (_quantities[item_id] as Array).duplicate()
	var counts := []
	counts.resize(get_definition(item_id).quality_levels)
	counts.fill(0)
	return counts

## [] unless value is an Array of numbers, one per quality level.
func _whole_counts(item_id: String, value: Variant) -> Array:
	if not is_valid_item(item_id) or typeof(value) != TYPE_ARRAY:
		return []
	var entry: Array = value
	if entry.size() != get_definition(item_id).quality_levels:
		return []
	var counts := []
	for count: Variant in entry:
		if typeof(count) != TYPE_INT and typeof(count) != TYPE_FLOAT:
			return []
		counts.append(maxi(int(count), 0))
	return counts
