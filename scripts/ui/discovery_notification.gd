extends Control
class_name DiscoveryNotification

## Transient card used for "NEW DISCOVERY", exploration bonuses, and daily
## discovery completion — same calm slide/scale/fade animation each time so
## the player learns one visual language for "something good just
## happened," rather than a different popup per system.

const DISPLAY_TIME := 2.2

@onready var title_label: Label = $Panel/VBoxContainer/TitleLabel
@onready var name_label: Label = $Panel/VBoxContainer/NameLabel
@onready var points_label: Label = $Panel/VBoxContainer/PointsLabel

func show_discovery(definition: DiscoveryDefinition) -> void:
	var rarity_text := String(definition.rarity).replace("_", " ").to_upper()
	show_message("✦ NEW DISCOVERY ✦", "%s\n%s" % [definition.display_name, rarity_text], "+%d Wriksha Points" % definition.points_value)

func show_message(title: String, name_text: String, points_text: String) -> void:
	title_label.text = title
	name_label.text = name_text
	points_label.text = points_text
	_play_entry_animation()

func _play_entry_animation() -> void:
	modulate.a = 0.0
	scale = Vector2(0.85, 0.85)
	pivot_offset = custom_minimum_size / 2.0

	var tween := create_tween()
	tween.set_parallel(true)
	tween.tween_property(self, "modulate:a", 1.0, 0.25)
	tween.tween_property(self, "scale", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	tween.chain().tween_interval(DISPLAY_TIME)
	tween.chain().tween_property(self, "modulate:a", 0.0, 0.4)
	tween.chain().tween_callback(queue_free)
