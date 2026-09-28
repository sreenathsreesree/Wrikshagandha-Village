extends Node

## Central hook point for all game audio. No audio assets are bundled yet —
## every play_*() method is a safe no-op when its stream is unassigned, so
## the game behaves identically with or without sound. Assign real
## AudioStream resources to the exported fields later (via this node in the
## editor); no calling code anywhere else needs to change.

@export var meadow_ambience: AudioStream
@export var pond_ambience: AudioStream
@export var wildlife_sound: AudioStream
@export var discovery_sound: AudioStream
@export var harvest_sound: AudioStream
@export var ui_feedback_sound: AudioStream

@onready var _ambience_player: AudioStreamPlayer = _make_player()
@onready var _sfx_player: AudioStreamPlayer = _make_player()

func _make_player() -> AudioStreamPlayer:
	var player := AudioStreamPlayer.new()
	add_child(player)
	return player

func play_meadow_ambience() -> void:
	_play_looping(meadow_ambience)

func play_pond_ambience() -> void:
	_play_looping(pond_ambience)

func play_wildlife_sound() -> void:
	_play_once(wildlife_sound)

func play_discovery_sound() -> void:
	_play_once(discovery_sound)

func play_harvest_sound() -> void:
	_play_once(harvest_sound)

func play_ui_feedback() -> void:
	_play_once(ui_feedback_sound)

func _play_once(stream: AudioStream) -> void:
	if stream == null:
		return
	_sfx_player.stream = stream
	_sfx_player.play()

func _play_looping(stream: AudioStream) -> void:
	if stream == null:
		return
	_ambience_player.stream = stream
	_ambience_player.play()
