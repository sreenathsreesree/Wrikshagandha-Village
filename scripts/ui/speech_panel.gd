extends Control
class_name SpeechPanel

## What someone in the world says (M08.3): the speaker's name and their
## line, in the shared theme's sheet, docked at the bottom centre between
## the thumb zones like the seed picker, with a 120 px ✕; the HUD keeps it
## clear of the safe-area insets. Non-modal: no dim, the root ignores the
## mouse and the world stays playable. It holds the conversation's state
## itself — who is speaking — and closes when that speaker asks (the player
## walked out of range), when the speaker leaves the world (its area was
## parked or freed) or on the ✕. Built to grow: M08.4's dialogue adds lines
## and choices here.

const GROUP := &"speech_panel"

@onready var panel: PanelContainer = $Panel
@onready var name_label: Label = $Panel/VBoxContainer/Row/Text/NameLabel
@onready var line_label: Label = $Panel/VBoxContainer/Row/Text/LineLabel
@onready var close_button: Button = $Panel/VBoxContainer/Row/CloseButton

var _speaker: Node

func _ready() -> void:
	add_to_group(GROUP)
	visible = false
	close_button.pressed.connect(_on_close_pressed)

## Shows `line` from `speaker_name` for `speaker`. Asking again while the
## same speaker is already shown changes nothing. Returns whether the
## panel is now showing this speaker.
func open(speaker: Node, speaker_name: String, line: String) -> bool:
	if speaker == null or line == "":
		return false
	if speaker == _speaker and visible:
		return true
	_release_speaker()
	_speaker = speaker
	_speaker.tree_exiting.connect(close)
	name_label.text = speaker_name
	line_label.text = line
	visible = true
	panel.pivot_offset = panel.size / 2.0
	panel.modulate.a = 0.0
	panel.scale = Vector2.ONE * 0.94
	var tween := create_tween().set_parallel(true)
	tween.tween_property(panel, "modulate:a", 1.0, 0.15)
	tween.tween_property(panel, "scale", Vector2.ONE, 0.2) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	return true

## Closes only if `speaker` is the one shown.
func close_for(speaker: Node) -> void:
	if speaker == _speaker:
		close()

func close() -> void:
	_release_speaker()
	visible = false

func get_speaker() -> Node:
	return _speaker

func _release_speaker() -> void:
	if _speaker != null and is_instance_valid(_speaker) and _speaker.tree_exiting.is_connected(close):
		_speaker.tree_exiting.disconnect(close)
	_speaker = null

func _on_close_pressed() -> void:
	AmbientAudioManager.play_ui_feedback()
	close()
