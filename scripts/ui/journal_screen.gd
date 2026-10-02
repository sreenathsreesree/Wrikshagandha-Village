extends Control
class_name JournalScreen

## Modal Journal screen: a permanent record of every discovery ever made,
## in the order the player found them, with rarity, description and the
## points earned.
##
## Presentation (M07.4a, D-26 / D-30): the shared theme's sheet, laid out
## for a landscape phone in two columns that scroll on their own — on the
## left where the player has been (Places, then the garden's record), on
## the right what they have found (one card per discovery). Displays only.

## Leaf green for a visited place; an unvisited one stays "???" (secrets
## stay secret).
const VISITED_COLOR := Color(0.22, 0.32, 0.16, 1)

@onready var left_list: VBoxContainer = $Panel/VBoxContainer/Columns/LeftScroll/LeftList
@onready var list_container: VBoxContainer = $Panel/VBoxContainer/Columns/RightScroll/ListContainer
@onready var summary_label: Label = $Panel/VBoxContainer/Header/SummaryLabel
@onready var close_button: Button = $Panel/VBoxContainer/Header/CloseButton

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
	for list in [left_list, list_container]:
		for child in list.get_children():
			list.remove_child(child)
			child.queue_free()

	left_list.add_child(_build_places_section())
	if FarmManager.is_garden_found() or int(FarmManager.get_activity_counts().planted) > 0:
		left_list.add_child(_build_garden_section())

	var entries := JournalManager.get_entries()
	var visited := 0
	var places := ExplorationManager.get_places_progress()
	for place: Dictionary in places:
		if place.visited:
			visited += 1
	summary_label.text = "%d %s · %d of %d places" % [entries.size(), "discovery" if entries.size() == 1 else "discoveries", visited, places.size()]

	list_container.add_child(_build_heading("Discoveries"))
	if entries.is_empty():
		var empty_label := Label.new()
		empty_label.theme_type_variation = &"Caption"
		empty_label.text = "No discoveries yet. Go explore the meadow!"
		empty_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		list_container.add_child(empty_label)
		return
	for entry: Dictionary in entries:
		list_container.add_child(_build_entry_row(entry))

## Small "Exploration Memory" section: places visited this session, in a
## fixed order, session-only (not saved) — reveals its real name once
## visited, stays "???" until then so secret locations stay secret.
func _build_places_section() -> Control:
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	box.add_child(_build_heading("Places"))

	var card := _build_card()
	var rows := VBoxContainer.new()
	rows.add_theme_constant_override("separation", 10)
	for place: Dictionary in ExplorationManager.get_places_progress():
		var row := Label.new()
		var visited: bool = place.visited
		row.text = "✓ %s" % place.display_name if visited else "???"
		if visited:
			row.add_theme_color_override("font_color", VISITED_COLOR)
		else:
			row.modulate.a = 0.45
		rows.add_child(row)
	card.add_child(rows)
	box.add_child(card)

	return box

## The garden's small record (saved with the farm), shown once the garden has been
## found (or something planted). A few compact lines of state, then the
## milestones as one wrapped line. Everything is read from FarmManager —
## the Journal only displays, it never decides progression — and every
## crop-specific line is built from crop data, so a new crop needs no code.
func _build_garden_section() -> Control:
	var section := VBoxContainer.new()
	section.add_theme_constant_override("separation", 12)
	section.add_child(_build_heading(ExplorationManager.get_place_display_name(ExplorationManager.get_garden_place_id())))
	var card := _build_card()
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 12)
	card.add_child(box)
	section.add_child(card)

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

	# The milestones as separate marks that wrap whole (never mid-name).
	var marks := HFlowContainer.new()
	marks.add_theme_constant_override("h_separation", 24)
	marks.add_theme_constant_override("v_separation", 6)
	for milestone: Dictionary in FarmManager.get_milestones():
		var mark := _build_note(("✓ %s" if milestone.reached else "○ %s") % milestone.label)
		mark.autowrap_mode = TextServer.AUTOWRAP_OFF
		if milestone.reached:
			mark.add_theme_color_override("font_color", VISITED_COLOR)
		marks.add_child(mark)
	box.add_child(marks)

	return section

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
	label.theme_type_variation = &"Caption"
	label.add_theme_font_size_override("font_size", 30)
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	return label

## A section title, as the Inventory's: small capitals above its cards.
func _build_heading(title: String) -> Label:
	var heading := Label.new()
	heading.theme_type_variation = &"Caption"
	heading.text = title.to_upper()
	heading.add_theme_font_size_override("font_size", 30)
	return heading

## A row card that lets a drag through to the scrolling column.
func _build_card() -> PanelContainer:
	var card := PanelContainer.new()
	card.theme_type_variation = &"RowCard"
	card.mouse_filter = Control.MOUSE_FILTER_PASS
	return card

## One card per discovery: its name with the rarity beside it, the
## description, the points it earned.
func _build_entry_row(entry: Dictionary) -> Control:
	var card := _build_card()
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 8)
	card.add_child(box)

	var top := HBoxContainer.new()
	top.add_theme_constant_override("separation", 16)
	var name_row := Label.new()
	name_row.text = String(entry["name"])
	name_row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	name_row.add_theme_font_size_override("font_size", 38)
	top.add_child(name_row)
	var rarity_row := Label.new()
	rarity_row.theme_type_variation = &"Caption"
	rarity_row.text = String(entry["rarity"]).replace("_", " ").to_upper()
	top.add_child(rarity_row)
	box.add_child(top)

	var description_row := Label.new()
	description_row.text = String(entry["description"])
	description_row.add_theme_font_size_override("font_size", 30)
	description_row.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(description_row)

	var points_row := Label.new()
	points_row.theme_type_variation = &"Caption"
	points_row.text = "+%d Wriksha Points" % int(entry["points_earned"])
	box.add_child(points_row)

	return card
