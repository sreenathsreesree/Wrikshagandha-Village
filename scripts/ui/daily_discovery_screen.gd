extends Control
class_name DailyDiscoveryScreen

## Modal "Today's Discovery" screen. Shows a rarity-based teaser before
## completion ("Find something Rare.") and the real name only once found,
## so it never spoils what to look for.

@onready var status_label: Label = $Panel/MarginContainer/VBoxContainer/StatusLabel
@onready var detail_label: Label = $Panel/MarginContainer/VBoxContainer/DetailLabel
@onready var close_button: Button = $Panel/MarginContainer/VBoxContainer/Header/CloseButton

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	DailyDiscoveryManager.daily_completed.connect(_on_daily_completed)
	_refresh()

func open() -> void:
	_refresh()
	visible = true

func _on_close_pressed() -> void:
	visible = false

func _on_daily_completed(_definition: DiscoveryDefinition, _bonus_points: int) -> void:
	_refresh()

func _refresh() -> void:
	var definition := DailyDiscoveryManager.get_target_definition()
	if DailyDiscoveryManager.is_completed_today():
		status_label.text = "✓ Daily Discovery Complete"
		var name_text := definition.display_name if definition else "Unknown"
		detail_label.text = "%s  •  +%d Wriksha Points" % [name_text, DailyDiscoveryManager.get_bonus_points()]
	else:
		var rarity_text := "something new"
		if definition:
			rarity_text = String(definition.rarity).replace("_", " ")
		status_label.text = "TODAY'S DISCOVERY"
		detail_label.text = "Find %s %s." % ["an" if rarity_text.begins_with("u") else "a", rarity_text]
