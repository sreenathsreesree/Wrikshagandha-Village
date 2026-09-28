extends Control
class_name CollectionScreen

## Modal Collection screen: one row per category showing found/total, with
## a placeholder "???" for anything not yet discovered so nothing is
## spoiled early.

@onready var list_container: VBoxContainer = $Panel/MarginContainer/VBoxContainer/ScrollContainer/ListContainer
@onready var close_button: Button = $Panel/MarginContainer/VBoxContainer/Header/CloseButton

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	_refresh()

func open() -> void:
	_refresh()
	visible = true

func _on_close_pressed() -> void:
	visible = false

func _on_discovery_made(_definition: DiscoveryDefinition) -> void:
	_refresh()

func _refresh() -> void:
	for child in list_container.get_children():
		child.queue_free()
	for row: Dictionary in CollectionManager.get_all_category_progress():
		_add_category_section(row)

func _add_category_section(row: Dictionary) -> void:
	var header := Label.new()
	header.text = "%s   %d / %d" % [row["label"], row["found"], row["total"]]
	header.add_theme_font_size_override("font_size", 20)
	list_container.add_child(header)

	var category: String = row["category"]
	for definition: DiscoveryDefinition in CollectionManager.get_entries_for_category(category):
		var entry_label := Label.new()
		var discovered := DiscoveryManager.is_discovered(definition.id)
		entry_label.text = "   • %s" % (definition.display_name if discovered else "???")
		entry_label.modulate.a = 1.0 if discovered else 0.5
		list_container.add_child(entry_label)

	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 14)
	list_container.add_child(spacer)
