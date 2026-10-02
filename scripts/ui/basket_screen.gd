extends Control
class_name BasketScreen

## The harvest basket: one compact row per crop harvested this session —
## its identity swatch, how many, and the Plain / Good / Fine split. A
## filtered view of the Inventory (its produce, M04.4) in FarmManager's crop
## order; keeps no counts.
##
## Selling (M06.2, D-25): each quality held has a Sell button showing the
## coins one unit pays. It opens the sell panel — item, quality, a quantity
## stepper from 1 to what is held, the coins the sale pays — and only
## Confirm sells, through the Market, which decides every price and every
## sale. The coin balance sits in the header, apart from the ✿ Wriksha
## Points on the HUD. Refreshed on FarmManager.produce_changed and on
## Inventory.items_changed (a sale changes items, not the farm).
##
## Presentation (M06.3, D-26): the shared Wrikshagandha theme; a sheet
## anchored to the screen's proportions; "BASKET" with the coin chip; one
## card per crop (icon, name and total, the quality split, a wrapping row of
## Sell buttons); the sell panel reads what → how many → how many coins →
## Cancel / Sell. Every touch target is at least TOUCH_TARGET canvas pixels.

## Canvas pixels (1920×1080 landscape design, D-30): the smallest thing a thumb must hit,
## and the crop icon's size.
const TOUCH_TARGET := 120.0
const ICON_SIZE := 104.0

@onready var list_container: VBoxContainer = $Panel/VBoxContainer/ScrollContainer/ListContainer
@onready var close_button: Button = $Panel/VBoxContainer/Header/CloseButton
@onready var coins_label: Label = $Panel/VBoxContainer/Header/CoinChip/CoinsLabel
@onready var scroll_container: ScrollContainer = $Panel/VBoxContainer/ScrollContainer
@onready var sell_panel: VBoxContainer = $Panel/VBoxContainer/SellPanel
@onready var sell_item_label: Label = $Panel/VBoxContainer/SellPanel/ItemLabel
@onready var sell_detail_label: Label = $Panel/VBoxContainer/SellPanel/DetailLabel
@onready var minus_button: Button = $Panel/VBoxContainer/SellPanel/Stepper/MinusButton
@onready var quantity_label: Label = $Panel/VBoxContainer/SellPanel/Stepper/QuantityLabel
@onready var plus_button: Button = $Panel/VBoxContainer/SellPanel/Stepper/PlusButton
@onready var total_label: Label = $Panel/VBoxContainer/SellPanel/TotalLabel
@onready var message_label: Label = $Panel/VBoxContainer/SellPanel/MessageLabel
@onready var cancel_button: Button = $Panel/VBoxContainer/SellPanel/Actions/CancelButton
@onready var confirm_button: Button = $Panel/VBoxContainer/SellPanel/Actions/ConfirmButton

## The sale being chosen — {"item": ItemDefinition, "quality": int,
## "quantity": int} — or empty. Nothing is sold until Confirm.
var _pending: Dictionary = {}

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	FarmManager.produce_changed.connect(_on_produce_changed)
	Inventory.items_changed.connect(_on_produce_changed)
	Wallet.balance_changed.connect(_on_balance_changed)
	minus_button.pressed.connect(_step_quantity.bind(-1))
	plus_button.pressed.connect(_step_quantity.bind(1))
	cancel_button.pressed.connect(_close_sell_panel)
	confirm_button.pressed.connect(_on_confirm_pressed)
	_on_balance_changed(Wallet.get_balance())

func open() -> void:
	_close_sell_panel()
	_refresh()
	visible = true

func _on_close_pressed() -> void:
	_close_sell_panel()
	visible = false

func _on_produce_changed() -> void:
	if visible:
		_refresh()

## Coins, never points: its own label, its own word.
func _on_balance_changed(balance: int) -> void:
	coins_label.text = "Coins %d" % balance

func _refresh() -> void:
	for child in list_container.get_children():
		list_container.remove_child(child)
		child.queue_free()
	var rows := _basket_rows()
	if rows.is_empty():
		list_container.add_child(_build_empty_state())
		return
	for row: Dictionary in rows:
		list_container.add_child(_build_row(row))
	if not _pending.is_empty():
		_update_sell_panel()

## An empty basket is a calm, expected state, not an error.
func _build_empty_state() -> Control:
	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	box.add_theme_constant_override("separation", 12)
	var icon := Label.new()
	icon.text = "🧺"
	icon.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	icon.add_theme_font_size_override("font_size", 120)
	box.add_child(icon)
	var title := Label.new()
	title.text = "Nothing harvested yet."
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	box.add_child(title)
	var hint := Label.new()
	hint.theme_type_variation = &"Caption"
	hint.text = "Ripe crops you harvest in the garden wait here, ready to sell."
	hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	hint.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(hint)
	return box

## One card per crop: icon, name and total, the quality split, then its
## Sell buttons.
func _build_row(row: Dictionary) -> Control:
	var crop: CropDefinition = row.crop
	var card := PanelContainer.new()
	card.theme_type_variation = &"RowCard"
	var column := VBoxContainer.new()
	column.add_theme_constant_override("separation", 16)
	card.add_child(column)

	var line := HBoxContainer.new()
	line.add_theme_constant_override("separation", 24)
	line.add_child(_build_swatch(crop))
	var text := VBoxContainer.new()
	text.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	text.alignment = BoxContainer.ALIGNMENT_CENTER
	var name_label := Label.new()
	name_label.text = "%s  ×%d" % [crop.display_name, int(row.total)]
	name_label.add_theme_font_size_override("font_size", 40)
	text.add_child(name_label)
	var split := Label.new()
	split.theme_type_variation = &"Caption"
	split.text = _quality_split(row)
	text.add_child(split)
	line.add_child(text)
	column.add_child(line)
	column.add_child(_build_sell_buttons(row))
	return card

## One Sell button per quality held that has a price (the Market's); the
## buttons wrap onto a new line when the card is narrow.
func _build_sell_buttons(row: Dictionary) -> Control:
	var item: ItemDefinition = row.item
	var buttons := HFlowContainer.new()
	buttons.add_theme_constant_override("h_separation", 16)
	buttons.add_theme_constant_override("v_separation", 16)
	for quality in [FarmManager.QUALITY_PLAIN, FarmManager.QUALITY_GOOD, FarmManager.QUALITY_FINE]:
		var price := Market.get_unit_price(item.id, quality)
		if int(row.counts[quality]) <= 0 or price < 1:
			continue
		var button := Button.new()
		button.theme_type_variation = &"PrimaryButton"
		button.custom_minimum_size = Vector2(TOUCH_TARGET, TOUCH_TARGET)
		button.text = "Sell %s · %d each" % [FarmManager.get_quality_name(quality), price]
		button.pressed.connect(_open_sell_panel.bind(item, quality))
		buttons.add_child(button)
	return buttons

## The produce the player holds, one row per crop in crop order:
## [{crop, item, total, counts}] (counts: one per quality, Plain / Good / Fine).
func _basket_rows() -> Array:
	var held := {}
	for row: Dictionary in Inventory.get_view("produce"):
		held[(row.item as ItemDefinition).crop_id] = row
	var rows: Array = []
	for crop in FarmManager.get_crops():
		if held.has(crop.crop_id):
			rows.append({"crop": crop, "item": held[crop.crop_id].item, "total": held[crop.crop_id].total, "counts": held[crop.crop_id].counts})
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
	swatch.custom_minimum_size = Vector2(ICON_SIZE, ICON_SIZE)
	swatch.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	var style := StyleBoxFlat.new()
	style.bg_color = crop.identity_color
	style.set_corner_radius_all(int(ICON_SIZE / 2.0))
	swatch.add_theme_stylebox_override("panel", style)
	var glyph := Label.new()
	glyph.text = crop.icon_glyph
	glyph.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	glyph.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	glyph.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	glyph.add_theme_font_size_override("font_size", 56)
	swatch.add_child(glyph)
	return swatch

# --- Selling (M06.2) ---------------------------------------------------------

func _open_sell_panel(item: ItemDefinition, quality: int) -> void:
	_pending = {"item": item, "quality": quality, "quantity": 1}
	message_label.text = ""
	scroll_container.visible = false
	sell_panel.visible = true
	_update_sell_panel()

func _close_sell_panel() -> void:
	_pending = {}
	sell_panel.visible = false
	scroll_container.visible = true

func _step_quantity(step: int) -> void:
	if _pending.is_empty():
		return
	_pending["quantity"] = int(_pending["quantity"]) + step
	_update_sell_panel()

## Keeps the quantity within 1..held and shows what Confirm would pay.
func _update_sell_panel() -> void:
	var item: ItemDefinition = _pending["item"]
	var quality: int = _pending["quality"]
	var held := _held(item.id, quality)
	var quantity := clampi(int(_pending["quantity"]), 1, maxi(held, 1))
	_pending["quantity"] = quantity
	var coins := Market.get_unit_price(item.id, quality) * quantity
	sell_item_label.text = item.display_name
	sell_detail_label.text = "%s%s · %d held" % ["✦ " if quality == FarmManager.QUALITY_FINE else "", FarmManager.get_quality_name(quality), held]
	quantity_label.text = str(quantity)
	total_label.text = "+%d Coins" % coins
	minus_button.disabled = quantity <= 1
	plus_button.disabled = quantity >= held
	confirm_button.disabled = held < quantity or coins < 1
	if held < 1:
		message_label.text = "None of these left to sell."

func _on_confirm_pressed() -> void:
	if _pending.is_empty():
		return
	var item: ItemDefinition = _pending["item"]
	if Market.sell(item.id, int(_pending["quality"]), int(_pending["quantity"])) < 1:
		message_label.text = "That sale couldn't be made."
		_update_sell_panel()
		return
	_close_sell_panel()
	_refresh()

## How many of this item, at this quality, are in the basket.
func _held(item_id: String, quality: int) -> int:
	for row: Dictionary in Inventory.get_view("produce"):
		if (row.item as ItemDefinition).id == item_id:
			return int(row.counts[quality])
	return 0
