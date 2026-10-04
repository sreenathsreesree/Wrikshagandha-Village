extends Node

## Selling produce for coins (M06.2, D-25) — the one place coins are
## earned, and the only caller of Wallet.credit(). A sale is one confirmed
## choice of the player: an item, a quality and a quantity they hold. Since
## M08.7 (D-40) it also carries out NPC trades: trade() takes a
## single-quality collectible from the Inventory for coins — the Basket's
## sell() still sells produce only.
##
## Only produce with a sell_value sells; seeds and collectibles never do.
## One unit's price is the item's sell_value scaled by the quality's
## percentage (data/market/sell_rules.tres), rounded half up in whole
## numbers; a sale pays that times the quantity. Nothing here knows points:
## coins and Wriksha Points are independent (D-24).
##
## A sale is all or nothing: every check first, then the items leave the
## Inventory and the coins enter the Wallet as one ledger entry
## "sell:<item_id>:<quality>"; if the credit were refused the items are put
## back. produce_sold then fires, and GameState saves — items and wallet in
## the same save. The Market holds no state of its own beyond the rules.

signal produce_sold(item_id: String, quality: int, quantity: int, coins: int)
signal items_traded(item_id: String, quantity: int, coins: int)

const SELL_RULES_PATH := "res://data/market/sell_rules.tres"

## Percent per quality level, from the sell rules.
var _quality_percents: Array[int] = []

func _ready() -> void:
	var rules := load(SELL_RULES_PATH) as SellRules
	if rules == null:
		push_warning("Market: %s is not a SellRules resource; nothing can be sold" % SELL_RULES_PATH)
		return
	_quality_percents = rules.quality_percents.duplicate()

## Coins one unit sells for at this quality; 0 if it can't be sold.
func get_unit_price(item_id: String, quality: int) -> int:
	var item := Inventory.get_definition(item_id)
	if item == null or item.category != "produce" or item.sell_value < 1:
		return 0
	if quality < 0 or quality >= item.quality_levels:
		return 0
	return _unit_coins(item, quality)

## Sells quantity of the item at this quality; the coins paid, or 0 if
## nothing happened.
func sell(item_id: String, quality: int, quantity: int) -> int:
	var item := Inventory.get_definition(item_id)
	if item == null:
		return 0
	if item.category != "produce":
		return 0
	if item.sell_value < 1:
		return 0
	if quality < 0 or quality >= item.quality_levels:
		return 0
	if quantity < 1:
		return 0
	if not Inventory.has(item_id, quantity, quality):
		return 0
	var coins := _unit_coins(item, quality) * quantity
	if coins < 1:
		return 0
	if not Inventory.remove(item_id, quantity, quality):
		return 0
	if not Wallet.credit(coins, "sell:%s:%d" % [item_id, quality]):
		Inventory.add(item_id, quantity, quality)
		return 0
	produce_sold.emit(item_id, quality, quantity, coins)
	return coins

## sell_value x the quality's percent / 100, rounded half up (whole numbers).
func _unit_coins(item: ItemDefinition, quality: int) -> int:
	if quality >= _quality_percents.size():
		return 0
	@warning_ignore("integer_division")
	return (item.sell_value * _quality_percents[quality] + 50) / 100

## An NPC trade (M08.7, D-40; asked only by Services): quantity of a
## single-quality collectible for coins. Every check first, then the items
## leave the Inventory and the coins enter the Wallet as one ledger entry
## "trade:<service_id>"; if the credit were refused the exact items are put
## back. items_traded then fires (GameState saves). Returns the coins paid,
## or 0 if nothing happened. No points: coins and points are independent.
func trade(item_id: String, quantity: int, coins: int, service_id: String) -> int:
	var item := Inventory.get_definition(item_id)
	if item == null:
		return 0
	if item.category != "collectible":
		return 0
	if item.quality_levels != 1:
		return 0
	if quantity < 1 or coins < 1:
		return 0
	if not Inventory.has(item_id, quantity, 0):
		return 0
	if not Inventory.remove(item_id, quantity, 0):
		return 0
	if not Wallet.credit(coins, "trade:%s" % service_id):
		Inventory.add(item_id, quantity, 0)
		return 0
	items_traded.emit(item_id, quantity, coins)
	return coins
