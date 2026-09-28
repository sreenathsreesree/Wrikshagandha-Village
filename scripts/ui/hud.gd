extends CanvasLayer

## Wires the on-screen HUD (points, discovery count, interact button,
## discovery popups, and the Collection/Journal/Daily Discovery screens) to
## the autoload systems. Holds no gameplay state itself.

const DiscoveryNotificationScene := preload("res://scenes/ui/DiscoveryNotification.tscn")

@onready var points_label: Label = $MarginContainer/TopBar/HBoxContainer/PointsLabel
@onready var discoveries_label: Label = $MarginContainer/TopBar/HBoxContainer/DiscoveriesLabel
@onready var interact_button: Button = $InteractButton
@onready var notification_root: Control = $NotificationRoot

@onready var collection_button: Button = $ScreenButtons/CollectionButton
@onready var journal_button: Button = $ScreenButtons/JournalButton
@onready var daily_button: Button = $ScreenButtons/DailyButton

@onready var collection_screen: CollectionScreen = $CollectionScreen
@onready var journal_screen: JournalScreen = $JournalScreen
@onready var daily_screen: DailyDiscoveryScreen = $DailyDiscoveryScreen

func _ready() -> void:
	PointsManager.points_changed.connect(_on_points_changed)
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	DiscoveryManager.discovery_repeated.connect(_on_discovery_repeated)
	ExplorationManager.exploration_bonus_awarded.connect(_on_exploration_bonus_awarded)
	ExplorationManager.landmark_reached.connect(_on_landmark_reached)
	ExplorationManager.secret_location_found.connect(_on_secret_location_found)
	ExplorationManager.first_discovery_noted.connect(_on_first_discovery_noted)
	ExplorationManager.rare_discovery_noted.connect(_on_rare_discovery_noted)
	ExplorationManager.all_secret_locations_found.connect(_on_all_secret_locations_found)
	ExplorationManager.curiosity_bonus_awarded.connect(_on_curiosity_bonus_awarded)
	ExplorationManager.session_summary_ready.connect(_on_session_summary_ready)
	DailyDiscoveryManager.daily_completed.connect(_on_daily_completed)
	FarmManager.crop_harvested.connect(_on_crop_harvested)
	FarmManager.crop_planted.connect(_on_crop_planted)
	FarmManager.milestone_reached.connect(_on_farm_milestone)
	FarmManager.seed_found.connect(_on_seed_found)

	interact_button.pivot_offset = interact_button.size / 2.0
	interact_button.pressed.connect(_on_interact_button_pressed)
	interact_button.button_down.connect(_on_interact_button_down)
	interact_button.button_up.connect(_on_interact_button_up)

	collection_button.pressed.connect(collection_screen.open)
	journal_button.pressed.connect(journal_screen.open)
	daily_button.pressed.connect(daily_screen.open)

	_on_points_changed(PointsManager.get_points())
	_update_discoveries_label()

func _on_points_changed(total: int) -> void:
	points_label.text = "✿ %d" % total

func _on_interact_button_pressed() -> void:
	AmbientAudioManager.play_ui_feedback()
	InputManager.request_interact()

## Immediate press/release tactile feedback — a mobile button should never
## feel like it might not have registered.
func _on_interact_button_down() -> void:
	var tween := create_tween()
	tween.tween_property(interact_button, "scale", Vector2.ONE * 0.9, 0.05)

func _on_interact_button_up() -> void:
	var tween := create_tween()
	tween.tween_property(interact_button, "scale", Vector2.ONE, 0.12) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

func _on_discovery_made(definition: DiscoveryDefinition) -> void:
	_update_discoveries_label()
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_discovery(definition)

## Repeat harvest of something already known: quiet points-only feedback,
## never the full discovery presentation.
func _on_discovery_repeated(definition: DiscoveryDefinition) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_repeat(definition)

func _on_exploration_bonus_awarded(threshold: int, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var title := "✦ Exploration Milestone ✦" if threshold == 3 else "✦ Meadow Explored ✦"
	var subtitle := "Keep exploring!" if threshold == 3 else "You know this meadow well."
	notification.show_message(title, subtitle, "+%d Wriksha Points" % bonus_points)

func _on_daily_completed(definition: DiscoveryDefinition, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✓ Daily Discovery Complete", definition.display_name, "+%d Wriksha Points" % bonus_points)

## Reuses the exact same notification card as a discovery harvest — a
## crop is presented the same way, not a separate farming UI. The seed that
## came back is mentioned in the same line, not as a second card.
func _on_crop_harvested(crop_definition: CropDefinition, points_awarded: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✦ Harvested ✦", crop_definition.display_name, "+%d Wriksha Points · +1 seed" % points_awarded)

func _on_landmark_reached(landmark_id: String, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("◆ Landmark Reached ◆", ExplorationManager.get_place_arrival_text(landmark_id), "+%d Wriksha Points" % bonus_points)

func _on_secret_location_found(location_id: String, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✦ Secret Spot Found ✦", ExplorationManager.get_place_display_name(location_id), "+%d Wriksha Points" % bonus_points)

## A quiet note for an everyday planting. When the planting itself was a
## milestone (the garden's first seed), FarmManager says so and the
## milestone card stands in for this one — one card per moment.
func _on_crop_planted(crop_definition: CropDefinition, announced_by_milestone: bool) -> void:
	if announced_by_milestone:
		return
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var left := FarmManager.get_seed_count(crop_definition.crop_id)
	notification.show_compact("%s planted" % crop_definition.display_name, _seeds_left_text(left))

## Farm milestones are quiet sentences, not "achievements": FarmManager
## decides when and what; the HUD only shows it on the shared card.
func _on_farm_milestone(_milestone_id: String, message: String, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var detail := "+%d Wriksha Points" % bonus_points if bonus_points > 0 else ""
	notification.show_message("🌱", message, detail)

func _seeds_left_text(count: int) -> String:
	if count <= 0:
		return "no seeds left"
	return "1 seed left" if count == 1 else "%d seeds left" % count

## Exploration feeding the garden: a quiet card, no points — the seed is
## the reward.
func _on_seed_found(crop_definition: CropDefinition) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var note := crop_definition.found_seed_note if crop_definition.found_seed_note != "" else "You found a seed here."
	notification.show_message(crop_definition.icon_glyph, note, "+1 %s seed" % crop_definition.display_name)

## The very first discovery of the session — a mood beat, not a reward, so
## it carries no points and no fanfare title.
func _on_first_discovery_noted() -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("🌱", "The Meadow is waking up.", "")

## First rare-or-better discovery this session: deliberately subtle — no
## extra points (the discovery itself already paid out for its rarity),
## just a quiet acknowledgment that this one was different.
func _on_rare_discovery_noted(definition: DiscoveryDefinition) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("☾ Something Rare ☾", definition.display_name, "You don't find this every day.")

func _on_all_secret_locations_found(bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("★ Every Secret Found ★", "You've uncovered every hidden place in the Meadow.", "+%d Wriksha Points" % bonus_points)

## Reaching a secret location before finding the discovery it's paired
## with — curiosity paid off before the obvious route did.
func _on_curiosity_bonus_awarded(_location_id: String, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✧ Curious Explorer ✧", "You found this before you were meant to.", "+%d Wriksha Points" % bonus_points)

## A calm, optional recap once the player has substantially explored the
## Meadow this session — reuses the same notification card as everything
## else, just with a short multi-line body instead of one name.
func _on_session_summary_ready(summary: Dictionary) -> void:
	var lines: Array[String] = []
	lines.append(_pluralized_line(int(summary.get("discoveries", 0)), "discovery", "discoveries"))
	lines.append(_pluralized_line(int(summary.get("places_explored", 0)), "place explored", "places explored"))
	var rare_count: int = int(summary.get("rare_discoveries", 0))
	if rare_count > 0:
		lines.append(_pluralized_line(rare_count, "rare discovery", "rare discoveries"))
	var secret_count: int = int(summary.get("secret_locations_found", 0))
	if secret_count > 0:
		lines.append(_pluralized_line(secret_count, "hidden place found", "hidden places found"))

	var body := ""
	for i in lines.size():
		if i > 0:
			body += "\n"
		body += lines[i]

	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✦ Today's Meadow ✦", body, "")

func _pluralized_line(count: int, singular: String, plural: String) -> String:
	return "%d %s" % [count, singular if count == 1 else plural]

func _update_discoveries_label() -> void:
	var found := DiscoveryManager.get_discovered_ids().size()
	var total := DiscoveryDatabase.get_all_definitions().size()
	discoveries_label.text = "Discoveries %d/%d" % [found, total]
