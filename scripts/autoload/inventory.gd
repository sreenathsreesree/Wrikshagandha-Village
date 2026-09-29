extends Node

## The player's inventory (M04.3, resolves O-14): the one ItemStore holding
## everything the player carries — seeds, harvested produce (a count per
## quality, D-18) and collectibles. Saved by SaveManager as "items".
##
## Screens read it through get_view(category) (M04.4): the seed picker and
## the basket are filtered views of this one store, holding no counts of
## their own.
##
## Who changes it: FarmManager (the seed and basket rules: starting seeds,
## planting, harvests, found seeds) and Inventory itself (a collectible for
## each discovery collected). Anything may read it. The store is never
## handed out; only these methods reach it.
##
## Discovery rewards are data: an ItemDefinition of category "collectible"
## whose discovery_id names the discovery. Every collection — first or
## repeat — gives one; a discovery with no such item gives nothing.
##
## Autoload order matters: after DiscoveryManager (connected here) and
## before FarmManager (gives starting seeds from its _ready) and GameState
## (so a first discovery's item is in before that discovery's autosave).

## Emitted after every change to the player's items — whoever made it
## (FarmManager's rules, a discovery reward, a load). The Inventory screen
## refreshes on it (M04.5); the seed picker and basket keep FarmManager's
## seeds_changed / produce_changed, which fire only after a planting has
## finished.
signal items_changed

var _store: ItemStore
## discovery_id -> the collectible item it gives.
var _collectible_item_ids: Dictionary = {}
## Every item definition, in data order (for get_view()).
var _definitions: Array[ItemDefinition] = []

func _ready() -> void:
	var definitions := ItemStore.load_definitions()
	_store = ItemStore.new(definitions)
	_definitions = definitions
	for definition in definitions:
		if definition.category == "collectible" and definition.discovery_id != "" \
				and not _collectible_item_ids.has(definition.discovery_id):
			_collectible_item_ids[definition.discovery_id] = definition.id
	DiscoveryManager.discovery_made.connect(_on_discovery_collected)
	DiscoveryManager.discovery_repeated.connect(_on_discovery_collected)

func is_valid_item(item_id: String) -> bool:
	return _store.is_valid_item(item_id)

func get_definition(item_id: String) -> ItemDefinition:
	return _store.get_definition(item_id)

## quality < 0 = every level together.
func get_quantity(item_id: String, quality: int = -1) -> int:
	return _store.get_quantity(item_id, quality)

func has(item_id: String, amount: int = 1, quality: int = -1) -> bool:
	return _store.has(item_id, amount, quality)

func add(item_id: String, amount: int = 1, quality: int = 0) -> bool:
	if not _store.add(item_id, amount, quality):
		return false
	items_changed.emit()
	return true

func remove(item_id: String, amount: int = 1, quality: int = 0) -> bool:
	if not _store.remove(item_id, amount, quality):
		return false
	items_changed.emit()
	return true

## A filtered view for the screens (M04.4): one row per item of this
## category the player holds, in data order —
## {"item": ItemDefinition, "total": int, "counts": [count per quality level]}.
## Built fresh from the store on every call; nothing is kept.
func get_view(category: String) -> Array:
	var rows: Array = []
	for definition in _definitions:
		if definition.category != category:
			continue
		var total := _store.get_quantity(definition.id)
		if total <= 0:
			continue
		var counts: Array = []
		for quality in definition.quality_levels:
			counts.append(_store.get_quantity(definition.id, quality))
		rows.append({"item": definition, "total": total, "counts": counts})
	return rows

## For SaveManager: {item_id: [count per quality level]}.
func get_save_data() -> Dictionary:
	return _store.get_save_data()

## For SaveManager, before FarmManager.apply_save_data().
func apply_save_data(data: Dictionary) -> void:
	_store.apply_save_data(data)
	items_changed.emit()

func _on_discovery_collected(definition: DiscoveryDefinition) -> void:
	var item_id: String = _collectible_item_ids.get(definition.id, "")
	if item_id != "" and _store.add(item_id):
		items_changed.emit()
