extends Control
class_name DiscoveryNotification

## Transient popup shown when the player discovers something new. Fades in,
## holds, fades out, then frees itself — the caller doesn't manage lifetime.

const DISPLAY_TIME := 2.5

@onready var title_label: Label = $Panel/VBoxContainer/TitleLabel
@onready var name_label: Label = $Panel/VBoxContainer/NameLabel
@onready var points_label: Label = $Panel/VBoxContainer/PointsLabel

func show_discovery(definition: DiscoveryDefinition) -> void:
	title_label.text = "New Discovery!"
	name_label.text = definition.display_name
	points_label.text = "+%d Wriksha Points" % definition.points_value

	modulate.a = 0.0
	var tween := create_tween()
	tween.tween_property(self, "modulate:a", 1.0, 0.2)
	tween.tween_interval(DISPLAY_TIME)
	tween.tween_property(self, "modulate:a", 0.0, 0.4)
	tween.tween_callback(queue_free)
