extends RefCounted
class_name ItemStore

## Counts of items by ItemDefinition id — the runtime foundation of the
## inventory (M04.1). Only add() and remove() change a count; both refuse
## an unknown id or an amount below 1, and remove() takes all or nothing,
## so a count is never negative. An item with a count of 0 isn't listed.
## Items stack without a limit: no current design caps a stack.
##
## Not an autoload and not saved yet: nothing holds items until M04.2 moves
## seeds and the basket out of FarmManager, which also adds the save
## section and its migration (D-17).

const ITEMS_PATH := "res://data/items/"

var _definitions: Dictionary = {}
var _quantities: Dictionary = {}

## Every usable ItemDefinition in res://data/items/, in file order.
static func load_definitions() -> Array[ItemDefinition]:
	var definitions: Array[ItemDefinition] = []
	for path in ResourceDirectory.list_tres_paths(ITEMS_PATH):
		var definition := load(path) as ItemDefinition
		if definition == null or definition.id == "":
			push_warning("ItemStore: %s is not a usable ItemDefinition" % path)
			continue
		definitions.append(definition)
	return definitions

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

func get_quantity(item_id: String) -> int:
	return int(_quantities.get(item_id, 0))

func has(item_id: String, amount: int = 1) -> bool:
	return amount >= 1 and get_quantity(item_id) >= amount

func add(item_id: String, amount: int = 1) -> bool:
	if not is_valid_item(item_id) or amount < 1:
		push_warning("ItemStore: cannot add %d of '%s'" % [amount, item_id])
		return false
	_quantities[item_id] = get_quantity(item_id) + amount
	return true

func remove(item_id: String, amount: int = 1) -> bool:
	if not is_valid_item(item_id) or amount < 1:
		push_warning("ItemStore: cannot remove %d of '%s'" % [amount, item_id])
		return false
	if get_quantity(item_id) < amount:
		return false
	var left := get_quantity(item_id) - amount
	if left == 0:
		_quantities.erase(item_id)
	else:
		_quantities[item_id] = left
	return true

## A copy: {item_id: count} for every item held (count >= 1).
func get_quantities() -> Dictionary:
	return _quantities.duplicate()
