extends Control
class_name InventoryScreen

## Everything the player carries, on one modal screen (M04.5): Seeds,
## Produce (with its Plain / Good / Fine split) and Collectibles — a
## read-only view of the Inventory autoload through get_view(), one section
## per category, only what is held. Seeds and produce follow FarmManager's
## crop order, like the seed picker and the basket; items without a crop
## (collectibles) follow the item data. Keeps no counts of its own:
## rebuilt on open, and on Inventory.items_changed while open. Displays only:
## nothing here sells, buys or changes an item.
##
## Presentation (M06.3, D-26): the Basket's shared theme, sheet and row
## cards. Seeds and produce show their crop's icon and colour; a collectible
## shows a glyph for its discovery's category (read from DiscoveryDatabase),
## so every row has an icon.

const SECTIONS := [["seed", "Seeds"], ["produce", "Produce"], ["collectible", "Collectibles"]]
const ICON_SIZE := 96.0
## A collectible's icon, by its discovery's category (presentation only).
const CATEGORY_GLYPHS := {"plant": "🌿", "flower": "🌸", "fungus": "🍄", "mineral": "🪨", "insect": "🐞", "animal": "🐾", "mystery": "✧"}
const COLLECTIBLE_COLOR := Color(0.62, 0.7, 0.5, 1)

@onready var list_container: VBoxContainer = $Panel/VBoxContainer/ScrollContainer/ListContainer
@onready var close_button: Button = $Panel/VBoxContainer/Header/CloseButton

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	Inventory.items_changed.connect(_on_items_changed)

func open() -> void:
	_refresh()
	visible = true

func _on_close_pressed() -> void:
	visible = false

func _on_items_changed() -> void:
	if visible:
		_refresh()

func _refresh() -> void:
	for child in list_container.get_children():
		list_container.remove_child(child)
		child.queue_free()
	var any_held := false
	for section: Array in SECTIONS:
		var rows := _section_rows(section[0])
		if rows.is_empty():
			continue
		any_held = true
		list_container.add_child(_build_heading(section[1]))
		for row: Dictionary in rows:
			list_container.add_child(_build_row(row))
	if not any_held:
		var empty := Label.new()
		empty.theme_type_variation = &"Caption"
		empty.text = "Nothing carried yet."
		empty.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		list_container.add_child(empty)

## One category's held items, [{item, total, counts, crop}]: items of a
## crop in FarmManager's crop order (crop = its CropDefinition), then items
## without a crop in data order (crop = null).
func _section_rows(category: String) -> Array:
	var by_crop := {}
	var others: Array = []
	for row: Dictionary in Inventory.get_view(category):
		var crop_id := (row.item as ItemDefinition).crop_id
		if crop_id == "":
			row["crop"] = null
			others.append(row)
		else:
			by_crop[crop_id] = row
	var rows: Array = []
	for crop in FarmManager.get_crops():
		if by_crop.has(crop.crop_id):
			var row: Dictionary = by_crop[crop.crop_id]
			row["crop"] = crop
			rows.append(row)
	return rows + others

func _build_heading(title: String) -> Label:
	var heading := Label.new()
	heading.theme_type_variation = &"Caption"
	heading.text = title.to_upper()
	heading.add_theme_font_size_override("font_size", 30)
	return heading

## One card per held item: icon, name and total, and (produce) the quality
## split. No actions.
func _build_row(row: Dictionary) -> Control:
	var item: ItemDefinition = row.item
	var card := PanelContainer.new()
	card.theme_type_variation = &"RowCard"
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", 24)
	if row.crop != null:
		line.add_child(_build_swatch(row.crop.icon_glyph, row.crop.identity_color))
	else:
		line.add_child(_build_swatch(_collectible_glyph(item), COLLECTIBLE_COLOR))
	var text := VBoxContainer.new()
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text.alignment = BoxContainer.ALIGNMENT_CENTER
	var name_label := Label.new()
	name_label.text = "%s  ×%d" % [item.display_name, int(row.total)]
	name_label.add_theme_font_size_override("font_size", 38)
	text.add_child(name_label)
	if item.quality_levels > 1:
		var split := Label.new()
		split.theme_type_variation = &"Caption"
		split.text = _quality_split(row.counts)
		text.add_child(split)
	line.add_child(text)
	card.add_child(line)
	return card

## The collectible's discovery category as a glyph ("✧" if unknown).
func _collectible_glyph(item: ItemDefinition) -> String:
	var definition := DiscoveryDatabase.get_definition(item.discovery_id)
	if definition == null:
		return "✧"
	return CATEGORY_GLYPHS.get(definition.category, "✧")

## "Good 3 · ✦ Fine 1" — only the qualities actually held (as the basket).
func _quality_split(counts: Array) -> String:
	var parts: PackedStringArray = []
	for quality in counts.size():
		var count := int(counts[quality])
		if count <= 0:
			continue
		var label := FarmManager.get_quality_name(quality)
		if quality == FarmManager.QUALITY_FINE:
			label = "✦ " + label
		parts.append("%s %d" % [label, count])
	return " · ".join(parts)

func _build_swatch(icon_glyph: String, color: Color) -> Control:
	var swatch := Panel.new()
	swatch.custom_minimum_size = Vector2(ICON_SIZE, ICON_SIZE)
	swatch.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var style := StyleBoxFlat.new()
	style.bg_color = color
	style.set_corner_radius_all(int(ICON_SIZE / 2.0))
	swatch.add_theme_stylebox_override("panel", style)
	var glyph := Label.new()
	glyph.text = icon_glyph
	glyph.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	glyph.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	glyph.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	glyph.add_theme_font_size_override("font_size", 52)
	swatch.add_child(glyph)
	return swatch
