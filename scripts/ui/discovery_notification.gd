extends Control
class_name DiscoveryNotification

## Transient card used for "NEW DISCOVERY", repeat harvests, exploration
## bonuses, and daily discovery completion — same calm slide/scale/fade
## animation each time so the player learns one visual language for
## "something good just happened," rather than a different popup per
## system. Compact mode (repeat harvests) is quieter and smaller so it
## never competes with a genuine first-time discovery.

const DISPLAY_TIME := 2.2
const REPEAT_DISPLAY_TIME := 1.3

const FULL_SIZE := Vector2(300, 120)
const COMPACT_SIZE := Vector2(220, 74)

@onready var title_label: Label = $Panel/VBoxContainer/TitleLabel
@onready var name_label: Label = $Panel/VBoxContainer/NameLabel
@onready var points_label: Label = $Panel/VBoxContainer/PointsLabel

## First-time discovery: full card with rarity, held a normal length.
func show_discovery(definition: DiscoveryDefinition) -> void:
	custom_minimum_size = FULL_SIZE
	title_label.visible = true
	title_label.text = "✦ NEW DISCOVERY ✦"
	var rarity_text := String(definition.rarity).replace("_", " ").to_upper()
	name_label.text = "%s\n%s" % [definition.display_name, rarity_text]
	points_label.text = "+%d Wriksha Points" % definition.points_value
	_play_entry_animation(DISPLAY_TIME)

## Repeat harvest of something already known: small, quiet, points-only —
## never the full "NEW DISCOVERY" presentation.
func show_repeat(definition: DiscoveryDefinition) -> void:
	show_compact(definition.display_name, "+%d" % definition.points_value)

## The same quiet, small card as a repeat harvest, for any short everyday
## note (e.g. "Wild Carrot planted" / "1 seed left").
func show_compact(name_text: String, detail_text: String) -> void:
	custom_minimum_size = COMPACT_SIZE
	title_label.visible = false
	name_label.text = name_text
	points_label.text = detail_text
	_play_entry_animation(REPEAT_DISPLAY_TIME, 0.92)

## Generic path used by exploration bonuses and daily-discovery completion.
func show_message(title: String, name_text: String, points_text: String) -> void:
	custom_minimum_size = FULL_SIZE
	title_label.visible = true
	title_label.text = title
	name_label.text = name_text
	points_label.text = points_text
	_play_entry_animation(DISPLAY_TIME)

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
