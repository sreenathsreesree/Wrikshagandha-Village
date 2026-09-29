extends Control
class_name SeedPicker

## The small seed choice shown when the player interacts with prepared
## soil. One large, thumb-sized card per crop — its identity color and
## glyph, its name, and how many seeds are left — sitting above the
## joystick so it isn't covered.
##
## Deliberately not a menu screen: no dim, no pause, and the world stays
## playable underneath. It opens and closes entirely on FarmManager's
## signals, and closes on its own when the player walks away from the plot
## (FarmPlot cancels the choice when it leaves interaction range). Built
## from FarmManager.get_known_crops(), so a new crop appears here
## automatically once the player knows it; each card's count is the
## Inventory's seed view (M04.4) — the picker keeps no count of its own.
## It refreshes on FarmManager.seeds_changed, which fires once a planting
## has finished and the picker has closed (never mid-press). Each card also shows what the
## soil would grow for that crop (FarmManager's rating), so the rotation
## rule is visible right where the choice is made.

const CHOICE_SIZE := Vector2(206, 256)
## The panel's inner width; with more crops than fit at full size, cards
## narrow evenly instead of pushing the panel wider than the screen.
const CHOICES_WIDTH := 700.0
const CHOICE_MIN_WIDTH := 128.0
const SWATCH_SIZE := 84.0

@onready var panel: PanelContainer = $Panel
@onready var choices: HBoxContainer = $Panel/VBoxContainer/Choices
@onready var close_button: Button = $Panel/VBoxContainer/Header/CloseButton
@onready var hint_label: Label = $Panel/VBoxContainer/HintLabel

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	FarmManager.seed_choice_requested.connect(open)
	FarmManager.seed_choice_closed.connect(close)
	FarmManager.seeds_changed.connect(_on_seeds_changed)

func open() -> void:
	_rebuild()
	var was_visible := visible
	visible = true
	if was_visible:
		return
	panel.pivot_offset = panel.size / 2.0
	panel.modulate.a = 0.0
	panel.scale = Vector2.ONE * 0.94
	var tween := create_tween().set_parallel(true)
	tween.tween_property(panel, "modulate:a", 1.0, 0.15)
	tween.tween_property(panel, "scale", Vector2.ONE, 0.2) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func close() -> void:
	visible = false

func _on_seeds_changed() -> void:
	if visible:
		_rebuild()

func _on_close_pressed() -> void:
	AmbientAudioManager.play_ui_feedback()
	FarmManager.cancel_seed_choice()

func _on_choice_pressed(crop: CropDefinition) -> void:
	AmbientAudioManager.play_ui_feedback()
	FarmManager.choose_seed(crop)

func _rebuild() -> void:
	for child in choices.get_children():
		# Detach first so the row never briefly lays out old + new cards.
		choices.remove_child(child)
		child.queue_free()
	var any_seeds := false
	var held := {}
	for row: Dictionary in Inventory.get_view("seed"):
		held[(row.item as ItemDefinition).crop_id] = int(row.total)
	var crops := FarmManager.get_known_crops()
	var width := _choice_width(crops.size())
	for crop in crops:
		var count: int = held.get(crop.crop_id, 0)
		any_seeds = any_seeds or count > 0
		choices.add_child(_build_choice(crop, count, width))
	hint_label.visible = not any_seeds

func _choice_width(crop_count: int) -> float:
	if crop_count <= 1:
		return CHOICE_SIZE.x
	var separation := float(choices.get_theme_constant("separation"))
	var fitted := (CHOICES_WIDTH - separation * (crop_count - 1)) / crop_count
	return clampf(fitted, CHOICE_MIN_WIDTH, CHOICE_SIZE.x)

func _build_choice(crop: CropDefinition, count: int, width: float) -> Button:
	var button := Button.new()
	button.custom_minimum_size = Vector2(width, CHOICE_SIZE.y)
	button.focus_mode = Control.FOCUS_NONE
	button.disabled = count <= 0
	button.add_theme_stylebox_override("normal", _card_style(crop.identity_color, 0.6))
	button.add_theme_stylebox_override("hover", _card_style(crop.identity_color, 0.8))
	button.add_theme_stylebox_override("pressed", _card_style(crop.identity_color, 0.95))
	button.add_theme_stylebox_override("disabled", _card_style(crop.identity_color, 0.3))
	if button.disabled:
		button.modulate.a = 0.45
	button.pressed.connect(_on_choice_pressed.bind(crop))

	var column := VBoxContainer.new()
	column.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	column.alignment = BoxContainer.ALIGNMENT_CENTER
	column.mouse_filter = Control.MOUSE_FILTER_IGNORE
	column.add_theme_constant_override("separation", 6)
	button.add_child(column)

	column.add_child(_build_swatch(crop))
	column.add_child(_build_label(crop.display_name, 22))
	column.add_child(_build_label(_seed_count_text(count), 20))
	if count > 0:
		column.add_child(_build_label(FarmManager.get_soil_note(FarmManager.get_soil_rating(crop)), 18))
	return button

## A round swatch in the crop's identity color with its glyph on top — the
## "icon". Still reads by color alone if a device font lacks the glyph.
func _build_swatch(crop: CropDefinition) -> Control:
	var swatch := Panel.new()
	swatch.custom_minimum_size = Vector2(SWATCH_SIZE, SWATCH_SIZE)
	swatch.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	swatch.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var style := StyleBoxFlat.new()
	style.bg_color = crop.identity_color
	style.set_corner_radius_all(int(SWATCH_SIZE / 2.0))
	swatch.add_theme_stylebox_override("panel", style)

	var glyph := Label.new()
	glyph.text = crop.icon_glyph
	glyph.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	glyph.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	glyph.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	glyph.add_theme_font_size_override("font_size", 40)
	glyph.mouse_filter = Control.MOUSE_FILTER_IGNORE
	swatch.add_child(glyph)
	return swatch

func _build_label(text: String, font_size: int) -> Label:
	var label := Label.new()
	label.text = text
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.autowrap_mode = TextServer.AUTOWRAP_WORD
	label.add_theme_font_size_override("font_size", font_size)
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	return label

func _card_style(accent: Color, fill_alpha: float) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(1, 1, 1, fill_alpha)
	style.border_color = accent
	style.set_border_width_all(3)
	style.set_corner_radius_all(18)
	return style

func _seed_count_text(count: int) -> String:
	if count <= 0:
		return "No seeds"
	return "%d seed" % count if count == 1 else "%d seeds" % count
