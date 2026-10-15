extends Node

## Central hook point for all game audio. No audio assets are bundled yet —
## every play_*() method is a safe no-op when its stream is unassigned, so
## the game behaves identically with or without sound. Assign real
## AudioStream resources to the exported fields later (via this node in the
## editor); no calling code anywhere else needs to change.
##
## Rest Mode ambience (D-62, R4): Main fades a location ambience in when the
## player sits and out when they stand, on its own player (one playback at a
## time: sitting again during the fade-out picks it up, never a second one),
## and the HUD's mute toggle silences it. The mute lasts for the session only
## — it is never saved and touches no settings. Until a licensed recording
## is assigned to rest_ambience, a TEMPORARY TECHNICAL PLACEHOLDER generated
## here (a 2.75 s loop of soft filtered noise, no asset) stands in, as D-62's
## first implementation asks — a test stream, not the intended sound (see
## docs/AUDIO_ASSETS.md). Rest Mode is complete in silence either way.

@export var meadow_ambience: AudioStream
@export var pond_ambience: AudioStream
@export var wildlife_sound: AudioStream
@export var discovery_sound: AudioStream
@export var harvest_sound: AudioStream
@export var ui_feedback_sound: AudioStream
@export var footstep_sound: AudioStream
@export var proximity_chime_sound: AudioStream
## Farming actions are world sounds, not UI clicks, so they get their own
## hooks — assigning a UI click later must not make planting "click".
@export var soil_sound: AudioStream
@export var water_sound: AudioStream
## Rest Mode's location ambience (D-62); unassigned, the temporary technical
## placeholder plays (docs/AUDIO_ASSETS.md).
@export var rest_ambience: AudioStream

## Rest ambience levels and fades (provisional, tuned at the playtest).
const REST_AMBIENCE_DB := -14.0
const REST_SILENT_DB := -60.0
const REST_FADE_IN_SECONDS := 2.0
const REST_FADE_OUT_SECONDS := 1.5
const REST_MUTE_FADE_SECONDS := 0.3
## The placeholder: deterministic, mono, looped without a seam.
const PLACEHOLDER_SAMPLE_HZ := 16000
const PLACEHOLDER_SECONDS := 3.0
const PLACEHOLDER_SEAM_SECONDS := 0.25
const PLACEHOLDER_SEED := 62

@onready var _ambience_player: AudioStreamPlayer = _make_player()
@onready var _sfx_player: AudioStreamPlayer = _make_player()
@onready var _rest_player: AudioStreamPlayer = _make_player()

## Seated (between start_rest_ambience() and stop_rest_ambience()); muted by
## the player this session (never saved); the running fade; the placeholder,
## made once when first needed.
var _rest_active: bool = false
var _rest_muted: bool = false
var _rest_tween: Tween
var _rest_placeholder: AudioStreamWAV

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

func play_footstep_sound() -> void:
	_play_once(footstep_sound)

func play_proximity_chime() -> void:
	_play_once(proximity_chime_sound)

## Preparing soil and planting a seed.
func play_soil_sound() -> void:
	_play_once(soil_sound)

func play_water_sound() -> void:
	_play_once(water_sound)

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

# --- Rest Mode ambience (D-62, R4) -----------------------------------------------

## Seated: fades the ambience in (silent if muted). Already playing — sitting
## again while it fades out — it carries on from where it is.
func start_rest_ambience() -> void:
	_rest_active = true
	if not _rest_player.playing:
		_rest_player.stream = rest_ambience if rest_ambience != null else _placeholder_rest_ambience()
		_rest_player.volume_db = REST_SILENT_DB
		_rest_player.play()
	_fade_rest(REST_FADE_IN_SECONDS)

## Standing: fades the ambience out, then stops it.
func stop_rest_ambience() -> void:
	if not _rest_active:
		return
	_rest_active = false
	_fade_rest(REST_FADE_OUT_SECONDS)

## The HUD's mute toggle: for this session only (never saved).
func set_rest_ambience_muted(muted: bool) -> void:
	_rest_muted = muted
	if _rest_active:
		_fade_rest(REST_MUTE_FADE_SECONDS)

func is_rest_ambience_muted() -> bool:
	return _rest_muted

## Eases the ambience to where it belongs now — audible while seated and not
## muted, otherwise silent — and stops it once silent after standing. Replaces
## any running fade.
func _fade_rest(seconds: float) -> void:
	if _rest_tween != null:
		_rest_tween.kill()
	var audible := _rest_active and not _rest_muted
	_rest_tween = create_tween()
	_rest_tween.tween_property(_rest_player, "volume_db", REST_AMBIENCE_DB if audible else REST_SILENT_DB, seconds)
	if not _rest_active:
		_rest_tween.tween_callback(_rest_player.stop)

func _placeholder_rest_ambience() -> AudioStreamWAV:
	if _rest_placeholder == null:
		_rest_placeholder = _make_placeholder_ambience()
	return _rest_placeholder

## Soft low-passed noise (a distant breeze), normalised, with its last
## PLACEHOLDER_SEAM_SECONDS crossfaded into its start so the loop has no seam.
func _make_placeholder_ambience() -> AudioStreamWAV:
	var total := int(PLACEHOLDER_SAMPLE_HZ * PLACEHOLDER_SECONDS)
	var seam := int(PLACEHOLDER_SAMPLE_HZ * PLACEHOLDER_SEAM_SECONDS)
	var rng := RandomNumberGenerator.new()
	rng.seed = PLACEHOLDER_SEED
	var noise := PackedFloat32Array()
	noise.resize(total)
	var low := 0.0
	var peak := 0.0
	for i in total:
		low += (rng.randf_range(-1.0, 1.0) - low) * 0.03
		noise[i] = low
		peak = maxf(peak, absf(low))
	var length := total - seam
	var data := PackedByteArray()
	data.resize(length * 2)
	for i in length:
		var v: float = noise[i]
		if i < seam:
			v = lerpf(noise[length + i], noise[i], float(i) / seam)
		data.encode_s16(i * 2, int(clampf(v / maxf(peak, 0.0001) * 0.5, -1.0, 1.0) * 32767.0))
	var wav := AudioStreamWAV.new()
	wav.format = AudioStreamWAV.FORMAT_16_BITS
	wav.mix_rate = PLACEHOLDER_SAMPLE_HZ
	wav.stereo = false
	wav.data = data
	wav.loop_mode = AudioStreamWAV.LOOP_FORWARD
	wav.loop_begin = 0
	wav.loop_end = length
	return wav
