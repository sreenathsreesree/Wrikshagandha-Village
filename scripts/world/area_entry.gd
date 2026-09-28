extends Marker3D
class_name AreaEntry

## A named place where the player enters an area (M03.2). Main.load_area()
## places the player on the entry whose entry_id it asks for, facing the
## marker's forward (-Z). Ids are stable, lower_snake_case, unique within
## their area and never derived from node names or tree order.

const GROUP := &"area_entry"

@export var entry_id: String = ""

func _enter_tree() -> void:
	add_to_group(GROUP)
