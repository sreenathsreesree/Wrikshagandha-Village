extends CanvasLayer

## Wires the on-screen HUD (points readout, interact button, discovery
## popups) to the autoload systems. Holds no gameplay state itself.

const DiscoveryNotificationScene := preload("res://scenes/ui/DiscoveryNotification.tscn")

@onready var points_label: Label = $MarginContainer/TopBar/PointsLabel
@onready var interact_button: Button = $InteractButton
@onready var notification_root: Control = $NotificationRoot

func _ready() -> void:
	PointsManager.points_changed.connect(_on_points_changed)
	DiscoveryManager.discovery_made.connect(_on_discovery_made)
	interact_button.pressed.connect(_on_interact_button_pressed)
	_on_points_changed(PointsManager.get_points())

func _on_points_changed(total: int) -> void:
	points_label.text = "Wriksha Points: %d" % total

func _on_interact_button_pressed() -> void:
	InputManager.request_interact()

func _on_discovery_made(definition: DiscoveryDefinition) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	notification.show_discovery(definition)
