extends Control
class_name DailyDiscoveryScreen

## Modal "Today's Discovery" screen. Shows a rarity-based teaser before
## completion ("Find something Rare.") and the real name only once found,
## so it never spoils what to look for.
##
## Presentation (M07.4a, D-26 / D-30): a centred card in the shared theme
## for a landscape phone — a big glyph, the status, the teaser (or the
## find), the reward read from DailyDiscoveryManager (shown before it is
## earned, as an invitation), and a large "Keep exploring" button in thumb
## reach that closes the card, as the ✕ does.

@onready var glyph_label: Label = $Panel/VBoxContainer/GlyphLabel
@onready var status_label: Label = $Panel/VBoxContainer/StatusLabel
@onready var detail_label: Label = $Panel/VBoxContainer/DetailLabel
@onready var reward_label: Label = $Panel/VBoxContainer/RewardLabel
@onready var close_button: Button = $Panel/VBoxContainer/Header/CloseButton
@onready var explore_button: Button = $Panel/VBoxContainer/ExploreButton

func _ready() -> void:
	visible = false
	close_button.pressed.connect(_on_close_pressed)
	explore_button.pressed.connect(_on_close_pressed)
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
	var bonus := DailyDiscoveryManager.get_bonus_points()
	if DailyDiscoveryManager.is_completed_today():
		glyph_label.text = "✓"
		status_label.text = "DAILY DISCOVERY COMPLETE"
		detail_label.text = definition.display_name if definition else "Unknown"
		reward_label.text = "+%d Wriksha Points · a new one tomorrow" % bonus
	else:
		var rarity_text := "new"
		if definition:
			rarity_text = String(definition.rarity).replace("_", " ")
		glyph_label.text = "⭐"
		status_label.text = "TODAY'S DISCOVERY"
		detail_label.text = "Find something %s." % rarity_text
		reward_label.text = "+%d Wriksha Points when you find it" % bonus
