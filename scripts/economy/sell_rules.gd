extends Resource
class_name SellRules

## How quality moves a produce item's sell price (M06.2, D-25): one whole
## percentage per quality level (Plain, Good, Fine), applied to the item's
## own sell_value by the Market. A coin rule of its own — never the farm's
## points scale, never points. Data only; the one file is
## res://data/market/sell_rules.tres.

@export var quality_percents: Array[int] = []
