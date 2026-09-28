extends Control
class_name JournalScreen

## Modal Journal screen: a permanent record of every discovery ever made,
## in the order the player found them, with rarity, description and the
## points earned.

@onready var list_container: VBoxContainer = $Panel/MarginContainer/VBoxContainer/ScrollContainer/ListContainer
@onready var close_button: Button = $Panel/MarginContainer/VBoxContainer/Header/CloseButton

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	JournalManager.entry_added.connect(_on_entry_added)
	_refresh()

func open() -> void:
	_refresh()
	visible = true

func _on_close_pressed() -> void:
	visible = false

func _on_entry_added(_entry: Dictionary) -> void:
	_refresh()

func _refresh() -> void:
	for child in list_container.get_children():
		child.queue_free()
	var entries := JournalManager.get_entries()
	if entries.is_empty():
		var empty_label := Label.new()
		empty_label.text = "No discoveries yet. Go explore the meadow!"
		empty_label.modulate.a = 0.7
		list_container.add_child(empty_label)
		return
	for entry: Dictionary in entries:
		list_container.add_child(_build_entry_row(entry))

func _build_entry_row(entry: Dictionary) -> Control:
	var box := VBoxContainer.new()

	var name_row := Label.new()
	var rarity_text: String = String(entry["rarity"]).replace("_", " ").to_upper()
	name_row.text = "%s  —  %s" % [entry["name"], rarity_text]
	name_row.add_theme_font_size_override("font_size", 20)
	box.add_child(name_row)

	var description_row := Label.new()
	description_row.text = String(entry["description"])
	description_row.autowrap_mode = TextServer.AUTOWRAP_WORD
	description_row.modulate.a = 0.85
	box.add_child(description_row)

	var points_row := Label.new()
	points_row.text = "+%d Wriksha Points" % int(entry["points_earned"])
	points_row.modulate.a = 0.7
	box.add_child(points_row)

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 12)
	box.add_child(spacer)

	return box
