extends Marker3D
class_name HomeSlot

## A reserved spot in a home (M08.2): where a later system will stand the
## player to use a piece of furniture — the bed, the chest, the desk and its
## journal, the hearth, the shelves. Data only: the marker sits on the floor
## in front of its furniture, facing it (-Z), and nothing reads it yet — no
## rest, storage, crafting or cooking exists until a milestone adds one.
## Ids are stable, lower_snake_case, unique within their area and never
## derived from node names or tree order.

const GROUP := &"home_slot"

@export var slot_id: String = ""

func _enter_tree() -> void:
	add_to_group(GROUP)
