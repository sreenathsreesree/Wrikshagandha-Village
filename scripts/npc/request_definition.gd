extends Resource
class_name RequestDefinition

## One NPC request as data (M08.6, D-39): someone in the world has a
## problem, the player finds what solves it and brings it back — no quest
## log, tracker or marker. The NPC (npc_id) asks with offer_dialogue,
## reminds with pending_dialogue while the player holds fewer than
## `quantity` of `item_id`, and takes them with handover_dialogue (its last
## button reads "Give"). Completing it pays reward_points once. The item has
## a single quality level. Add one by creating another .tres in
## res://data/requests/ (at most one per NPC).

@export var id: String = ""
@export var npc_id: String = ""
@export var item_id: String = ""
@export var quantity: int = 1
@export var reward_points: int = 0
@export var offer_dialogue: DialogueDefinition
@export var pending_dialogue: DialogueDefinition
@export var handover_dialogue: DialogueDefinition
