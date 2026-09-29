extends Control
class_name BasketScreen

## The harvest basket: one compact row per crop harvested this session —
## its identity swatch, how many, and the Plain / Good / Fine split. A
## filtered view of the Inventory (its produce, M04.4) in FarmManager's crop
## order; keeps no counts, displays only, decides nothing.
## Same modal shape and parchment theme as the Collection screen.

const SWATCH_SIZE := 56.0

@onready var list_container: VBoxContainer = $Panel/MarginContainer/VBoxContainer/ScrollContainer/ListContainer
@onready var close_button: Button = $Panel/MarginContainer/VBoxContainer/Header/CloseButton

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	FarmManager.produce_changed.connect(_on_produce_changed)

func open() -> void:
	_refresh()
	visible = true

func _on_close_pressed() -> void:
	visible = false

func _on_produce_changed() -> void:
	if visible:
		_refresh()

func _refresh() -> void:
	for child in list_container.get_children():
		list_container.remove_child(child)
		child.queue_free()
	var rows := _basket_rows()
	if rows.is_empty():
		var empty := Label.new()
		empty.text = "Nothing harvested yet."
		empty.modulate.a = 0.7
		list_container.add_child(empty)
		return
	for row: Dictionary in rows:
		list_container.add_child(_build_row(row))

func _build_row(row: Dictionary) -> Control:
	var crop: CropDefinition = row.crop
	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", 14)
	line.add_child(_build_swatch(crop))

	var text := VBoxContainer.new()
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text.alignment = BoxContainer.ALIGNMENT_CENTER
	var name_label := Label.new()
	name_label.text = "%s  ×%d" % [crop.display_name, int(row.total)]
	name_label.add_theme_font_size_override("font_size", 22)
	text.add_child(name_label)
	var split := Label.new()
	split.text = _quality_split(row)
	split.modulate.a = 0.8
	text.add_child(split)
	line.add_child(text)
	return line

## The produce the player holds, one row per crop in crop order:
## [{crop, total, counts}] (counts: one per quality, Plain / Good / Fine).
func _basket_rows() -> Array:
	var held := {}
	for row: Dictionary in Inventory.get_view("produce"):
		held[(row.item as ItemDefinition).crop_id] = row
	var rows: Array = []
	for crop in FarmManager.get_crops():
		if held.has(crop.crop_id):
			rows.append({"crop": crop, "total": held[crop.crop_id].total, "counts": held[crop.crop_id].counts})
	return rows

## "Good 3 · ✦ Fine 1" — only the qualities actually in the basket.
func _quality_split(row: Dictionary) -> String:
	var parts: PackedStringArray = []
	for quality in [FarmManager.QUALITY_PLAIN, FarmManager.QUALITY_GOOD, FarmManager.QUALITY_FINE]:
		var count := int(row.counts[quality])
		if count <= 0:
			continue
		var label := FarmManager.get_quality_name(quality)
		if quality == FarmManager.QUALITY_FINE:
			label = "✦ " + label
		parts.append("%s %d" % [label, count])
	return " · ".join(parts)

func _build_swatch(crop: CropDefinition) -> Control:
	var swatch := Panel.new()
	swatch.custom_minimum_size = Vector2(SWATCH_SIZE, SWATCH_SIZE)
	swatch.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var style := StyleBoxFlat.new()
	style.bg_color = crop.identity_color
	style.set_corner_radius_all(int(SWATCH_SIZE / 2.0))
	swatch.add_theme_stylebox_override("panel", style)
	var glyph := Label.new()
	glyph.text = crop.icon_glyph
	glyph.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	glyph.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	glyph.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	glyph.add_theme_font_size_override("font_size", 28)
	swatch.add_child(glyph)
	return swatch
