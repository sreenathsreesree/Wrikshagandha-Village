extends Control
class_name DiscoveryNotification

## Transient card used for "NEW DISCOVERY", repeat harvests, exploration
## bonuses, and daily discovery completion — same calm slide/scale/fade
## animation each time so the player learns one visual language for
## "something good just happened," rather than a different popup per
## system. Compact mode (repeat harvests) is quieter and smaller so it
## never competes with a genuine first-time discovery.
##
## Phone scale (M06.3, D-26): sized in 1080×1920 canvas pixels; the card's
## height follows its text, so a card never clips a line. Lines, top to
## bottom: title, name, an optional small note (e.g. how a crop was cared
## for), the amount, an optional detail (e.g. "+1 Seed"). A line with no
## text isn't shown.

const DISPLAY_TIME := 2.2
const REPEAT_DISPLAY_TIME := 1.3

## Card widths (canvas pixels); heights follow the text.
const FULL_WIDTH := 640.0
const COMPACT_WIDTH := 520.0

@onready var panel: PanelContainer = $Panel
@onready var title_label: Label = $Panel/VBoxContainer/TitleLabel
@onready var name_label: Label = $Panel/VBoxContainer/NameLabel
@onready var note_label: Label = $Panel/VBoxContainer/NoteLabel
@onready var points_label: Label = $Panel/VBoxContainer/PointsLabel
@onready var detail_label: Label = $Panel/VBoxContainer/DetailLabel

## First-time discovery: full card with rarity, held a normal length.
func show_discovery(definition: DiscoveryDefinition) -> void:
	var rarity_text := String(definition.rarity).replace("_", " ").to_upper()
	_fill("✦ NEW DISCOVERY ✦", "%s\n%s" % [definition.display_name, rarity_text], "", "+%d Wriksha Points" % definition.points_value, "")
	_fit(FULL_WIDTH)
	_play_entry_animation(DISPLAY_TIME)

## Repeat harvest of something already known: small, quiet, points-only —
## never the full "NEW DISCOVERY" presentation.
func show_repeat(definition: DiscoveryDefinition) -> void:
	show_compact(definition.display_name, "+%d" % definition.points_value)

## The same quiet, small card as a repeat harvest, for any short everyday
## note (e.g. "Wild Carrot planted" / "1 seed left").
func show_compact(name_text: String, detail_text: String) -> void:
	_fill("", name_text, "", detail_text, "")
	_fit(COMPACT_WIDTH)
	_play_entry_animation(REPEAT_DISPLAY_TIME, 0.92)

## Generic path used by exploration bonuses, daily-discovery completion,
## harvests (with the care note and "+1 Seed") and sales.
func show_message(title: String, name_text: String, points_text: String, detail_text: String = "", note_text: String = "") -> void:
	_fill(title, name_text, note_text, points_text, detail_text)
	_fit(FULL_WIDTH)
	_play_entry_animation(DISPLAY_TIME)

func _fill(title: String, name_text: String, note_text: String, points_text: String, detail_text: String) -> void:
	for pair: Array in [[title_label, title], [name_label, name_text], [note_label, note_text], [points_label, points_text], [detail_label, detail_text]]:
		var label: Label = pair[0]
		label.text = pair[1]
		label.visible = pair[1] != ""

## Horizontal space the card's own padding takes (the panel's content margins).
const CARD_PADDING := 80.0

func _ready() -> void:
	panel.minimum_size_changed.connect(_sync_height)

## The card is as wide as its kind; each line wraps inside it.
func _fit(width: float) -> void:
	for label: Label in [title_label, name_label, note_label, points_label, detail_label]:
		label.custom_minimum_size = Vector2(width - CARD_PADDING, 0.0)
	custom_minimum_size = Vector2(width, 0.0)
	_sync_height()

## ...and as tall as its text needs, once the wrapped lines are laid out.
func _sync_height() -> void:
	custom_minimum_size.y = panel.get_combined_minimum_size().y

func _play_entry_animation(display_time: float, start_scale: float = 0.85) -> void:
	modulate.a = 0.0
	scale = Vector2.ONE * start_scale
	pivot_offset = custom_minimum_size / 2.0
	position.y += 10.0

	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(self, "modulate:a", 1.0, 0.2)
	tween.tween_property(self, "scale", Vector2.ONE, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.tween_property(self, "position:y", position.y - 10.0, 0.25).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
	tween.chain().tween_interval(display_time)
	tween.chain().tween_property(self, "modulate:a", 0.0, 0.3)
	tween.chain().tween_callback(queue_free)
