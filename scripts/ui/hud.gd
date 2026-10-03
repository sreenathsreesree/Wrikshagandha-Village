extends CanvasLayer

## Wires the on-screen HUD (points, discovery count, discovery and sale popups, and
## the Collection/Journal/Daily Discovery/Basket/Inventory screens) to the autoload
## systems. Holds no gameplay state itself. There is no Interact button:
## the player taps the world (see InputManager).
##
## Layout (M06.3, D-26): a top bar anchored to the top edge that sizes to its
## content (never stretched) — the ✿ points pill first, the discovery count,
## then the secondary screens (📚 📖 ⭐ 🕹); notifications flow just below
## it; the Basket and Inventory sit in the bottom-right thumb zone. Both
## clusters keep clear of notches through the display's safe area.
##
## Landscape (M07.4, D-30): the canvas is 1920×1080 (short side 1080, so
## every size keeps its physical size); the joystick in the bottom-left
## thumb zone also keeps clear of side cut-outs and the gesture bar, and so
## does every modal sheet (M07.4a) and the seed picker (M07.4b).

const DiscoveryNotificationScene := preload("res://scenes/ui/DiscoveryNotification.tscn")
## A seed that introduces a new crop is shown a beat after the discovery
## that revealed it, so it reads as that discovery's consequence.
const NEW_CROP_CARD_DELAY := 1.1
## Canvas-pixel gap kept between the screen (or its safe area) and the HUD.
const EDGE_MARGIN := 24.0

@onready var top_area: MarginContainer = $TopArea
@onready var points_label: Label = $TopArea/TopColumn/TopBar/PointsPill/PointsLabel
@onready var discoveries_label: Label = $TopArea/TopColumn/TopBar/DiscoveriesLabel
@onready var notification_root: Control = $TopArea/TopColumn/NotificationRoot

@onready var collection_button: Button = $TopArea/TopColumn/TopBar/MenuButtons/CollectionButton
@onready var journal_button: Button = $TopArea/TopColumn/TopBar/MenuButtons/JournalButton
@onready var daily_button: Button = $TopArea/TopColumn/TopBar/MenuButtons/DailyButton
@onready var movement_button: Button = $TopArea/TopColumn/TopBar/MenuButtons/MovementButton
@onready var screen_buttons: Control = $ScreenButtons
@onready var basket_button: Button = $ScreenButtons/BasketButton
@onready var inventory_button: Button = $ScreenButtons/InventoryButton
@onready var mobile_controls: Control = $MobileControls
@onready var joystick: Control = $MobileControls/Joystick
@onready var seed_picker: Control = $SeedPicker
@onready var speech_panel: Control = $SpeechPanel

@onready var collection_screen: CollectionScreen = $CollectionScreen
@onready var journal_screen: JournalScreen = $JournalScreen
@onready var daily_screen: DailyDiscoveryScreen = $DailyDiscoveryScreen
@onready var basket_screen: BasketScreen = $BasketScreen
@onready var inventory_screen: InventoryScreen = $InventoryScreen

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
	FarmManager.produce_changed.connect(_update_basket_button)
	Inventory.items_changed.connect(_update_basket_button)
	Market.produce_sold.connect(_on_produce_sold)
	Requests.request_completed.connect(_on_request_completed)

	collection_button.pressed.connect(collection_screen.open)
	journal_button.pressed.connect(journal_screen.open)
	daily_button.pressed.connect(daily_screen.open)
	basket_button.pressed.connect(basket_screen.open)
	inventory_button.pressed.connect(inventory_screen.open)
	_update_basket_button()
	movement_button.pressed.connect(_on_movement_button_pressed)
	InputManager.movement_mode_changed.connect(_on_movement_mode_changed)
	_on_movement_mode_changed(InputManager.movement_mode)

	_on_points_changed(PointsManager.get_points())
	_update_discoveries_label()
	get_viewport().size_changed.connect(_apply_safe_area)
	_apply_safe_area()

## Keeps the top bar and the thumb buttons inside the display's safe area
## (notches, rounded corners, system bars): the safe area's insets, converted
## from screen pixels to canvas pixels, are added to the edge margin. Where
## the whole window is safe (desktop) only the edge margin applies.
func _apply_safe_area() -> void:
	var window_size := Vector2(DisplayServer.window_get_size())
	var canvas_size: Vector2 = get_viewport().get_visible_rect().size
	var insets := [0.0, 0.0, 0.0, 0.0]  # left, top, right, bottom (canvas pixels)
	if window_size.x > 0.0 and window_size.y > 0.0:
		var window := Rect2(Vector2(DisplayServer.window_get_position()), window_size)
		var safe := Rect2(DisplayServer.get_display_safe_area()).intersection(window)
		if safe.has_area():
			var to_canvas: Vector2 = canvas_size / window_size
			insets = [
				maxf(safe.position.x - window.position.x, 0.0) * to_canvas.x,
				maxf(safe.position.y - window.position.y, 0.0) * to_canvas.y,
				maxf(window.end.x - safe.end.x, 0.0) * to_canvas.x,
				maxf(window.end.y - safe.end.y, 0.0) * to_canvas.y,
			]
	top_area.add_theme_constant_override("margin_left", int(EDGE_MARGIN + insets[0]))
	top_area.add_theme_constant_override("margin_top", int(EDGE_MARGIN + insets[1]))
	top_area.add_theme_constant_override("margin_right", int(EDGE_MARGIN + insets[2]))
	screen_buttons.offset_right = -(EDGE_MARGIN + insets[2])
	screen_buttons.offset_bottom = -(EDGE_MARGIN + insets[3])
	# The joystick's touch zone (its own size, its base inset inside it)
	# moves in by the left and bottom insets only — on a desktop window or a
	# phone without cut-outs it stays exactly where the scene puts it.
	var joystick_size := Vector2(joystick.offset_right - joystick.offset_left, joystick.offset_bottom - joystick.offset_top)
	joystick.offset_left = insets[0]
	joystick.offset_right = insets[0] + joystick_size.x
	joystick.offset_bottom = -insets[3]
	joystick.offset_top = -insets[3] - joystick_size.y
	# Modal sheets (M07.4a): each keeps its designed margin, and moves in
	# only as far as a cut-out reaches past it (plus the edge margin).
	for screen: Control in [collection_screen, journal_screen, daily_screen, basket_screen, inventory_screen]:
		var sheet: Control = screen.get_node("Panel")
		sheet.offset_left = maxf(insets[0] + EDGE_MARGIN - sheet.anchor_left * canvas_size.x, 0.0)
		sheet.offset_top = maxf(insets[1] + EDGE_MARGIN - sheet.anchor_top * canvas_size.y, 0.0)
		sheet.offset_right = -maxf(insets[2] + EDGE_MARGIN - (1.0 - sheet.anchor_right) * canvas_size.x, 0.0)
		sheet.offset_bottom = -maxf(insets[3] + EDGE_MARGIN - (1.0 - sheet.anchor_bottom) * canvas_size.y, 0.0)
	# The seed picker (M07.4b), docked at the bottom centre: above the
	# gesture bar, centred between the side insets; it grows upward.
	var picker_panel: Control = seed_picker.get_node("Panel")
	picker_panel.offset_bottom = -(EDGE_MARGIN + insets[3])
	picker_panel.offset_top = picker_panel.offset_bottom
	picker_panel.offset_left = (insets[0] - insets[2]) / 2.0
	picker_panel.offset_right = picker_panel.offset_left
	# The speech panel (M08.3) docks the same way: bottom centre, above the
	# gesture bar, centred between the side insets.
	var speech: Control = speech_panel.get_node("Panel")
	speech.offset_bottom = -(EDGE_MARGIN + insets[3])
	speech.offset_top = speech.offset_bottom
	speech.offset_left = (insets[0] - insets[2]) / 2.0
	speech.offset_right = speech.offset_left

func _on_points_changed(total: int) -> void:
	points_label.text = "✿ %d" % total

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
## crop is presented the same way, not a separate farming UI. The quality it
## grew at sits beside its name, how it was cared for just under it (that
## is how the care rule is learned); then the points and the seed that came
## back, on the same card, never a second one.
func _on_crop_harvested(crop_definition: CropDefinition, points_awarded: int, quality: int, care: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var name_line := "%s · %s" % [crop_definition.display_name, FarmManager.get_quality_name(quality)]
	notification.show_message("✦ HARVESTED ✦", name_line, "+%d Wriksha Points" % points_awarded, "+1 Seed", FarmManager.get_care_note(care))

## A sale (M06.2): the coins it paid (as the Market reported them) on the
## shared card — the crop, then quality × quantity, then coins, never
## Wriksha Points.
func _on_produce_sold(item_id: String, quality: int, quantity: int, coins: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var item := Inventory.get_definition(item_id)
	var item_name := item.display_name if item != null else item_id
	notification.show_message(item_name.to_upper(), "%s ×%d" % [FarmManager.get_quality_name(quality), quantity], "+%d Coins" % coins)

## A request completed (M08.6): the items given and the points earned, on
## the same card as every other reward — no tracker, log or marker.
func _on_request_completed(_request_id: String, item_id: String, quantity: int, points: int) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var item := Inventory.get_definition(item_id)
	var item_name := item.display_name if item != null else item_id
	notification.show_message("✓ Request Complete", "%s ×%d" % [item_name, quantity], "+%d Wriksha Points" % points)

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
func _on_crop_planted(crop_definition: CropDefinition, announced_by_milestone: bool, soil: int) -> void:
	if announced_by_milestone:
		return
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var left := FarmManager.get_seed_count(crop_definition.crop_id)
	var detail := "%s · %s" % [FarmManager.get_soil_note(soil), _seeds_left_text(left)]
	notification.show_compact("%s planted" % crop_definition.display_name, detail)

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
## the reward. A seed of a crop the player has never known is its own
## small moment: shown just after the discovery that revealed it, titled
## as a new crop, pointing home to the garden.
func _on_seed_found(crop_definition: CropDefinition, new_crop: bool) -> void:
	if new_crop:
		get_tree().create_timer(NEW_CROP_CARD_DELAY).timeout.connect(_show_new_crop_card.bind(crop_definition))
		return
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var note := crop_definition.found_seed_note if crop_definition.found_seed_note != "" else "You found a seed here."
	notification.show_message(crop_definition.icon_glyph, note, "+1 %s seed" % crop_definition.display_name)

func _show_new_crop_card(crop_definition: CropDefinition) -> void:
	var notification: DiscoveryNotification = DiscoveryNotificationScene.instantiate()
	notification_root.add_child(notification)
	var note := crop_definition.found_seed_note if crop_definition.found_seed_note != "" else "A seed you've never seen before."
	var garden := ExplorationManager.get_place_display_name(ExplorationManager.get_garden_place_id())
	notification.show_message("%s A New Crop %s" % [crop_definition.icon_glyph, crop_definition.icon_glyph], "%s\n%s" % [crop_definition.display_name, note], "Plant it in the %s" % garden)

## The one movement setting: Joystick ↔ Tap to Move. The joystick is only
## shown in Joystick mode; the button shows the current mode.
func _on_movement_button_pressed() -> void:
	AmbientAudioManager.play_ui_feedback()
	InputManager.set_tap_to_move(not InputManager.is_tap_to_move())

func _on_movement_mode_changed(_mode: int) -> void:
	var tap := InputManager.is_tap_to_move()
	mobile_controls.visible = not tap
	movement_button.text = "👆" if tap else "🕹"
	movement_button.tooltip_text = "Movement: Tap to Move" if tap else "Movement: Joystick"

## The basket button only appears once there's something in the basket.
func _update_basket_button() -> void:
	basket_button.visible = FarmManager.get_produce_total() > 0

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
