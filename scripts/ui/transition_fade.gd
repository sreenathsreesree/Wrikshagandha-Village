extends CanvasLayer
class_name TransitionFade

## The fade between areas (M08.1), owned by Main. cover() fades to the
## colour and stays; reveal() fades back. From the start of cover() until
## reveal() has begun, the veil takes every touch above the HUD, so nothing
## is tapped or steered mid-swap; while clear it takes none.

## Above the HUD (layer 1): drawn over it and handed touches before it.
const LAYER := 10
const COVER_SECONDS := 0.25
const REVEAL_SECONDS := 0.3

@onready var _veil: ColorRect = $Veil

var _tween: Tween

func _ready() -> void:
	layer = LAYER
	_veil.modulate.a = 0.0
	_veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_veil.visible = false

func cover() -> void:
	_veil.visible = true
	_veil.mouse_filter = Control.MOUSE_FILTER_STOP
	await _fade_to(1.0, COVER_SECONDS)

func reveal() -> void:
	_veil.mouse_filter = Control.MOUSE_FILTER_IGNORE
	await _fade_to(0.0, REVEAL_SECONDS)
	_veil.visible = false

func is_covering() -> bool:
	return _veil.mouse_filter == Control.MOUSE_FILTER_STOP

func _fade_to(alpha: float, seconds: float) -> void:
	if _tween and _tween.is_valid():
		_tween.kill()
	_tween = create_tween()
	_tween.tween_property(_veil, "modulate:a", alpha, seconds)
	await _tween.finished
