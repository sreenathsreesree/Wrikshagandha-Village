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
	DailyDiscoveryManager.daily_completed.connect(_on_daily_completed)

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

func _on_landmark_reached(landmark_id: String, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("◆ Landmark Reached ◆", _format_location_name(landmark_id), "+%d Wriksha Points" % bonus_points)

func _on_secret_location_found(location_id: String, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✦ Secret Spot Found ✦", _format_location_name(location_id), "+%d Wriksha Points" % bonus_points)

func _format_location_name(id: String) -> String:
	return id.replace("_", " ").capitalize()

func _update_discoveries_label() -> void:
	var found := DiscoveryManager.get_discovered_ids().size()
	var total := DiscoveryDatabase.get_all_definitions().size()
	discoveries_label.text = "Discoveries %d/%d" % [found, total]
