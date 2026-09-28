extends Node3D
class_name CropVisual

## Generic per-stage presentation shared by every crop scene (Wild Carrot,
## Meadow Herb, Golden Sunflower, and any future crop). Growth is shown by
## scaling the whole visual up through each stage — no new meshes, shaders,
## or particle systems needed per stage. Only the mesh/material differ per
## crop scene; adding a new crop later means a new .tscn + .tres pair, not
## new presentation logic.

const STAGE_SCALES := [0.28, 0.55, 0.8, 1.0]
const STAGE_TWEEN_DURATION := 0.4

func _ready() -> void:
	scale = Vector3.ONE * STAGE_SCALES[0]

func set_stage(stage_index: int) -> void:
	var clamped: int = clamp(stage_index, 0, STAGE_SCALES.size() - 1)
	var tween := create_tween()
	tween.tween_property(self, "scale", Vector3.ONE * STAGE_SCALES[clamped], STAGE_TWEEN_DURATION) \
		.set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

## A brief, restrained "responds to water" bounce — used by FarmPlot right
## after watering, on top of whatever stage-scale tween is already running.
func play_water_response() -> void:
	var current_scale := scale
	var tween := create_tween()
	tween.tween_property(self, "scale", current_scale * 1.12, 0.15).set_trans(Tween.TRANS_SINE)
	tween.tween_property(self, "scale", current_scale, 0.25).set_trans(Tween.TRANS_SINE)
