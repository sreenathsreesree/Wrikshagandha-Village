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

	list_container.add_child(_build_places_section())
	list_container.add_child(_build_spacer())

	var garden := ExplorationManager.get_garden_journal()
	if garden.found or garden.first_planted != "":
		list_container.add_child(_build_garden_section(garden))
		list_container.add_child(_build_spacer())

	var discoveries_header := Label.new()
	discoveries_header.text = "Discoveries"
	discoveries_header.add_theme_font_size_override("font_size", 18)
	discoveries_header.modulate.a = 0.8
	list_container.add_child(discoveries_header)

	var entries := JournalManager.get_entries()
	if entries.is_empty():
		var empty_label := Label.new()
		empty_label.text = "No discoveries yet. Go explore the meadow!"
		empty_label.modulate.a = 0.7
		list_container.add_child(empty_label)
		return
	for entry: Dictionary in entries:
		list_container.add_child(_build_entry_row(entry))

## Small "Exploration Memory" section: places visited this session, in a
## fixed order, session-only (not saved) — reveals its real name once
## visited, stays "???" until then so secret locations stay secret.
func _build_places_section() -> Control:
	var box := VBoxContainer.new()

	var header := Label.new()
	header.text = "Places"
	header.add_theme_font_size_override("font_size", 18)
	header.modulate.a = 0.8
	box.add_child(header)

	for place: Dictionary in ExplorationManager.get_places_progress():
		var row := Label.new()
		var visited: bool = place.visited
		row.text = "✓ %s" % place.display_name if visited else "???"
		row.modulate.a = 1.0 if visited else 0.6
		box.add_child(row)

	return box

## The garden's small session-only record — hidden entirely until the
## garden has been found (or something planted), and each line only once
## it has actually happened, so it never reads like a checklist.
func _build_garden_section(garden: Dictionary) -> Control:
	var box := VBoxContainer.new()

	var header := Label.new()
	header.text = String(garden.place_name)
	header.add_theme_font_size_override("font_size", 18)
	header.modulate.a = 0.8
	box.add_child(header)

	if garden.found:
		box.add_child(_build_note("Found the Meadow's little growing place."))
	if garden.first_planted != "":
		var first_line := "Planted the garden's first seed: %s" if garden.first_planted_after_discovery else "First crop planted: %s"
		box.add_child(_build_note(first_line % garden.first_planted))
	if garden.first_harvested != "":
		box.add_child(_build_note("First crop harvested: %s" % garden.first_harvested))

	box.add_child(_build_note("Seeds: %s" % _seed_summary()))
	var found := FarmManager.get_found_seed_names()
	if not found.is_empty():
		box.add_child(_build_note("Found while exploring: %s" % ", ".join(found)))
	box.add_child(_build_note("Crops planted: %d" % int(garden.crops_planted)))
	box.add_child(_build_note("Crops harvested: %d" % int(garden.crops_harvested)))

	return box

## "Wild Carrot ×2, Meadow Herb ×1, Golden Sunflower ×0" — read straight
## from FarmManager's session inventory, in its crop order.
func _seed_summary() -> String:
	var parts: PackedStringArray = []
	for crop in FarmManager.get_crops():
		parts.append("%s ×%d" % [crop.display_name, FarmManager.get_seed_count(crop.crop_id)])
	return ", ".join(parts)

func _build_note(text: String) -> Label:
	var label := Label.new()
	label.text = text
	label.autowrap_mode = TextServer.AUTOWRAP_WORD
	label.modulate.a = 0.85
	return label

func _build_spacer() -> Control:
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(0, 12)
	return spacer

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
