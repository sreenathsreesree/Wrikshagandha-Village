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
	ExplorationManager.exploration_bonus_awarded.connect(_on_exploration_bonus_awarded)
	DailyDiscoveryManager.daily_completed.connect(_on_daily_completed)

	interact_button.pressed.connect(_on_interact_button_pressed)
	collection_button.pressed.connect(collection_screen.open)
	journal_button.pressed.connect(journal_screen.open)
	daily_button.pressed.connect(daily_screen.open)

	_on_points_changed(PointsManager.get_points())
	_update_discoveries_label()

func _on_points_changed(total: int) -> void:
	points_label.text = "✿ %d" % total

func _on_interact_button_pressed() -> void:
	InputManager.request_interact()

func _on_discovery_made(definition: DiscoveryDefinition) -> void:
	_update_discoveries_label()
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_discovery(definition)

func _on_exploration_bonus_awarded(_threshold: int, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✦ EXPLORATION BONUS ✦", "Keep exploring!", "+%d Wriksha Points" % bonus_points)

func _on_daily_completed(definition: DiscoveryDefinition, bonus_points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_message("✓ Daily Discovery Complete", definition.display_name, "+%d Wriksha Points" % bonus_points)

func _update_discoveries_label() -> void:
	var found := DiscoveryManager.get_discovered_ids().size()
	var total := DiscoveryDatabase.get_all_definitions().size()
	discoveries_label.text = "Discoveries %d/%d" % [found, total]
