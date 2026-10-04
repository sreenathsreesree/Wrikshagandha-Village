extends Resource
class_name ServiceDefinition

## One repeatable NPC service as data (M08.7, D-40): a trade of a
## single-quality collectible for coins. Once the request `unlocked_by_request`
## is completed, the NPC (npc_id) pitches it with pitch_dialogue while the
## player holds fewer than `quantity` of `item_id`, and offers it with
## trade_dialogue (its last button reads "Sell") once they hold enough;
## finishing that conversation sells `quantity` of them for `coins` through
## the Market. Data only — no transaction logic here. Add one by creating
## another .tres in res://data/services/.

@export var id: String = ""
@export var npc_id: String = ""
@export var item_id: String = ""
@export var quantity: int = 1
@export var coins: int = 0
@export var unlocked_by_request: String = ""
@export var pitch_dialogue: DialogueDefinition
@export var trade_dialogue: DialogueDefinition
