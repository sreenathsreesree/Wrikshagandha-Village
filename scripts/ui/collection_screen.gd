extends Control
class_name CollectionScreen

## Modal Collection screen: one card per category showing found/total, with
## a placeholder "???" for anything not yet discovered so nothing is
## spoiled early. Reads CollectionManager and DiscoveryManager only; keeps
## no state and changes nothing.
##
## Presentation (M07.4a, D-26 / D-30): the shared theme's sheet (as the
## Basket and Inventory); the categories are a grid of cards — three
## columns on a 16:9 landscape phone, more or fewer as the sheet is wider
## or narrower — that scrolls vertically. Each card: the category, "n of N
## found", a small progress bar, then the entries (or a calm empty line).

## Canvas pixels: the narrowest a category card may get before the grid
## drops a column, and the most columns it ever shows.
const CARD_MIN_WIDTH := 520.0
const MAX_COLUMNS := 4
const LEAF := Color(0.42, 0.6, 0.3, 1)
const LEAF_TRACK := Color(0.42, 0.6, 0.3, 0.18)

@onready var grid: GridContainer = $Panel/VBoxContainer/ScrollContainer/Grid
@onready var scroll_container: ScrollContainer = $Panel/VBoxContainer/ScrollContainer
@onready var progress_label: Label = $Panel/VBoxContainer/Header/ProgressLabel
@onready var close_button: Button = $Panel/VBoxContainer/Header/CloseButton

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	scroll_container.resized.connect(_fit_columns)
	_refresh()

func open() -> void:
	_refresh()
	visible = true

func _on_close_pressed() -> void:
	visible = false

func _on_discovery_made(_definition: DiscoveryDefinition) -> void:
	_refresh()

## As many card columns as fit the sheet (landscape: 3 at 16:9).
func _fit_columns() -> void:
	grid.columns = clampi(int(scroll_container.size.x / CARD_MIN_WIDTH), 1, MAX_COLUMNS)

func _refresh() -> void:
	for child in grid.get_children():
		grid.remove_child(child)
		child.queue_free()
	var found := 0
	var total := 0
	for row: Dictionary in CollectionManager.get_all_category_progress():
		found += int(row["found"])
		total += int(row["total"])
		grid.add_child(_build_category_card(row))
	progress_label.text = "%d of %d found" % [found, total]
	_fit_columns()

## One card per category: name and count, a progress bar, then each entry —
## its name once discovered, "???" until then.
func _build_category_card(row: Dictionary) -> Control:
	var card := PanelContainer.new()
	card.theme_type_variation = &"RowCard"
	card.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	card.mouse_filter = Control.MOUSE_FILTER_PASS
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 12)
	card.add_child(column)

	var found := int(row["found"])
	var total := int(row["total"])
	var title := Label.new()
	title.text = String(row["label"])
	title.add_theme_font_size_override("font_size", 38)
	column.add_child(title)
	var count := Label.new()
	count.theme_type_variation = &"Caption"
	if total == 0:
		count.text = "Nothing to find here yet."
	elif found == total:
		count.text = "✦ Complete · %d of %d" % [found, total]
	else:
		count.text = "%d of %d found" % [found, total]
	column.add_child(count)
	if total > 0:
		column.add_child(_build_meter(float(found) / float(total)))

	var category: String = row["category"]
	for definition: DiscoveryDefinition in CollectionManager.get_entries_for_category(category):
		var entry := Label.new()
		var discovered := DiscoveryManager.is_discovered(definition.id)
		entry.text = definition.display_name if discovered else "???"
		entry.add_theme_font_size_override("font_size", 32)
		entry.modulate.a = 1.0 if discovered else 0.45
		column.add_child(entry)
	return card

## A thin leaf-green bar: how much of the category is found.
func _build_meter(ratio: float) -> Control:
	var track := Panel.new()
	track.custom_minimum_size = Vector2(0, 12)
	track.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var track_style := StyleBoxFlat.new()
	track_style.bg_color = LEAF_TRACK
	track_style.set_corner_radius_all(6)
	track.add_theme_stylebox_override("panel", track_style)
	var fill := Panel.new()
	fill.mouse_filter = Control.MOUSE_FILTER_IGNORE
	fill.anchor_bottom = 1.0
	fill.anchor_right = clampf(ratio, 0.0, 1.0)
	var fill_style := StyleBoxFlat.new()
	fill_style.bg_color = LEAF
	fill_style.set_corner_radius_all(6)
	fill.add_theme_stylebox_override("panel", fill_style)
	track.add_child(fill)
	return track
