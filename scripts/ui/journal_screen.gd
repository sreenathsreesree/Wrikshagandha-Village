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

	if FarmManager.is_garden_found() or int(FarmManager.get_activity_counts().planted) > 0:
		list_container.add_child(_build_garden_section())
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

## The garden's small record (saved with the farm), shown once the garden has been
## found (or something planted). A few compact lines of state, then the
## milestones as one wrapped line. Everything is read from FarmManager —
## the Journal only displays, it never decides progression — and every
## crop-specific line is built from crop data, so a new crop needs no code.
func _build_garden_section() -> Control:
	var box := VBoxContainer.new()

	var header := Label.new()
	header.text = ExplorationManager.get_place_display_name(ExplorationManager.get_garden_place_id())
	header.add_theme_font_size_override("font_size", 18)
	header.modulate.a = 0.8
	box.add_child(header)

	var plots := FarmManager.get_plot_counts()
	var garden_line := "%d plots to tend" % int(plots.unlocked)
	if int(plots.total) > int(plots.unlocked):
		garden_line += " · room to grow"
	if FarmManager.is_garden_found():
		garden_line = "Found the Meadow's little growing place. " + garden_line + "."
	if FarmManager.is_milestone_reached(FarmManager.GARDEN_IN_BLOOM):
		garden_line = "The garden is in bloom. " + garden_line
	box.add_child(_build_note(garden_line))

	box.add_child(_build_note("Seeds: %s" % _seed_summary()))
	var origins := FarmManager.get_found_seed_origins()
	if not origins.is_empty():
		var lines: PackedStringArray = ["Found through exploration:"]
		for origin: Dictionary in origins:
			var crop: CropDefinition = origin.crop
			lines.append("  %s — %s" % [crop.display_name, _origin_name(String(origin.source), String(origin.source_id))])
		box.add_child(_build_note("\n".join(lines)))

	var grown := FarmManager.get_grown_crop_names()
	if not grown.is_empty():
		box.add_child(_build_note("Grown: %s" % ", ".join(grown)))
	var basket := _basket_summary()
	if basket != "":
		box.add_child(_build_note("Basket: %s" % basket))
		# The soil rule, said once in words until the player has seen it
		# pay off; the seed picker shows it on every choice anyway.
		if FarmManager.get_produce_total(FarmManager.QUALITY_FINE) == 0:
			box.add_child(_build_note("The soil remembers what grew last, and crops remember how long they waited for water. Both together grow Fine."))

	var marks: PackedStringArray = []
	for milestone: Dictionary in FarmManager.get_milestones():
		var mark := "✓ %s" if milestone.reached else "○ %s"
		marks.append(mark % milestone.label)
	box.add_child(_build_note("  ".join(marks)))

	return box

## "Wild Carrot ×2, Meadow Herb ×1, Golden Sunflower ×0" — read straight
## from FarmManager's session inventory, in its crop order. Only crops the
## player knows, so an exploration-only crop stays a surprise.
func _seed_summary() -> String:
	var parts: PackedStringArray = []
	for crop in FarmManager.get_known_crops():
		parts.append("%s ×%d" % [crop.display_name, FarmManager.get_seed_count(crop.crop_id)])
	return ", ".join(parts)

## "Wild Carrot ×3 (1 Fine), Meadow Herb ×1" — everything harvested this
## session, with the Fine ones called out. Empty string = empty basket.
func _basket_summary() -> String:
	var parts: PackedStringArray = []
	for row: Dictionary in FarmManager.get_basket():
		var crop: CropDefinition = row.crop
		var part := "%s ×%d" % [crop.display_name, int(row.total)]
		if int(row.fine) > 0:
			part += " (%d Fine)" % int(row.fine)
		parts.append(part)
	return ", ".join(parts)

## A found seed's origin as the player knows it: the place's name, or the
## discovery's name. Ids come from FarmManager; names from their owners.
func _origin_name(source: String, source_id: String) -> String:
	if source == "discovery":
		var definition := DiscoveryDatabase.get_definition(source_id)
		if definition != null:
			return definition.display_name
		return source_id.replace("_", " ").capitalize()
	return ExplorationManager.get_place_display_name(source_id)

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
