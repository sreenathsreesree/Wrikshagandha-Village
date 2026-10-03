extends Control
class_name SpeechPanel

## What someone in the world says (M08.3; a short dialogue since M08.4): the
## speaker's name and the current line, in the shared theme's sheet, docked
## at the bottom centre between the thumb zones like the seed picker; the
## HUD keeps it clear of the safe-area insets. Non-modal: no dim, the root
## ignores the mouse and the world stays playable (a tap on the sheet itself
## does nothing). It holds the conversation's state itself — who is
## speaking, their lines and which one is shown. Only the Next button moves
## on (it reads "Goodbye" on the last line, which ends the conversation —
## or the label open() was given, e.g. a request's "Give", M08.6);
## the ✕ ends it early, as do the speaker asking (the player walked out of
## range) and the speaker leaving the world (its area parked or freed).
## Every conversation ends exactly once, with conversation_ended — heard
## by the speaking NpcTalk, which reports a completed one to Relationships
## (M08.5); the panel itself knows nothing of friendship.

signal conversation_ended(speaker: Node, completed: bool)

const GROUP := &"speech_panel"
const NEXT_TEXT := "Next ▸"
const END_TEXT := "Goodbye"

@onready var panel: PanelContainer = $Panel
@onready var name_label: Label = $Panel/VBoxContainer/Row/Text/NameLabel
@onready var line_label: Label = $Panel/VBoxContainer/Row/Text/LineLabel
@onready var progress_label: Label = $Panel/VBoxContainer/Row/Text/ProgressLabel
@onready var next_button: Button = $Panel/VBoxContainer/Row/NextButton
@onready var close_button: Button = $Panel/VBoxContainer/Row/CloseButton

var _speaker: Node
var _lines: PackedStringArray = PackedStringArray()
var _index: int = 0
var _end_text: String = END_TEXT

func _ready() -> void:
	add_to_group(GROUP)
	visible = false
	next_button.pressed.connect(_on_next_pressed)
	close_button.pressed.connect(_on_close_pressed)

## Starts `speaker`'s conversation — `lines` from `speaker_name`, from the
## first; the last line's button reads `end_text`. Asking again while the
## same speaker is shown changes nothing (no restart, no skip, no new
## label). Returns whether the panel is now showing this speaker.
func open(speaker: Node, speaker_name: String, lines: PackedStringArray, end_text: String = END_TEXT) -> bool:
	if speaker == null or lines.is_empty():
		return false
	if speaker == _speaker and visible:
		return true
	_end(false)
	_speaker = speaker
	_speaker.tree_exiting.connect(close)
	_lines = lines
	_index = 0
	_end_text = end_text
	name_label.text = speaker_name
	_show_line()
	visible = true
	panel.pivot_offset = panel.size / 2.0
	panel.modulate.a = 0.0
	panel.scale = Vector2.ONE * 0.94
	var tween := create_tween().set_parallel(true)
	tween.tween_property(panel, "modulate:a", 1.0, 0.15)
	tween.tween_property(panel, "scale", Vector2.ONE, 0.2) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	return true

## The next line; past the last, the conversation is complete.
func advance() -> void:
	if _speaker == null:
		return
	if _index >= _lines.size() - 1:
		_end(true)
		return
	_index += 1
	_show_line()

## Closes only if `speaker` is the one shown.
func close_for(speaker: Node) -> void:
	if speaker == _speaker:
		close()

## Ends the conversation early, if there is one.
func close() -> void:
	_end(false)

func get_speaker() -> Node:
	return _speaker

func get_line_index() -> int:
	return _index

func _show_line() -> void:
	line_label.text = _lines[_index]
	progress_label.text = "%d / %d" % [_index + 1, _lines.size()]
	next_button.text = _end_text if _index >= _lines.size() - 1 else NEXT_TEXT

## The one way a conversation ends: once, announced, then hidden.
func _end(completed: bool) -> void:
	if _speaker == null:
		visible = false
		return
	var speaker := _speaker
	if is_instance_valid(speaker) and speaker.tree_exiting.is_connected(close):
		speaker.tree_exiting.disconnect(close)
	_speaker = null
	_lines = PackedStringArray()
	_index = 0
	_end_text = END_TEXT
	visible = false
	conversation_ended.emit(speaker, completed)

func _on_next_pressed() -> void:
	AmbientAudioManager.play_ui_feedback()
	advance()

func _on_close_pressed() -> void:
	AmbientAudioManager.play_ui_feedback()
	close()
