extends Control
class_name DiscoveryNotification

## Transient "NEW DISCOVERY" card shown when the player finds something new.
## Slides/scales in, holds, fades out, then frees itself — the caller
## doesn't manage lifetime.

const DISPLAY_TIME := 2.2

@onready var name_label: Label = $Panel/VBoxContainer/NameLabel
@onready var points_label: Label = $Panel/VBoxContainer/PointsLabel

func show_discovery(definition: DiscoveryDefinition) -> void:
	name_label.text = definition.display_name
	points_label.text = "+%d Wriksha Points" % definition.points_value

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
