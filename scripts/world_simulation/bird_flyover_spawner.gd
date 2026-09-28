extends Node3D
class_name BirdFlyoverSpawner

## Purely ambient background detail: every so often, spawns one bird
## silhouette at one edge of the sky and tweens it straight across to the
## opposite edge, then frees it. Timer + Tween driven — no per-frame
## processing at all when nothing is flying, and never more than one bird
## in flight at a time.

@export var bird_scene: PackedScene
@export var min_interval: float = 25.0
@export var max_interval: float = 55.0
@export var flight_height: float = 14.0
@export var flight_radius: float = 26.0
@export var flight_duration_min: float = 7.0
@export var flight_duration_max: float = 12.0

var _timer: Timer

func _ready() -> void:
	_timer = Timer.new()
	_timer.one_shot = true
	_timer.timeout.connect(_spawn_bird)
	add_child(_timer)
	_schedule_next()

func _schedule_next() -> void:
	_timer.start(randf_range(min_interval, max_interval))

func _spawn_bird() -> void:
	if bird_scene == null:
		_schedule_next()
		return
	var bird: Node3D = bird_scene.instantiate()
	var angle := randf_range(0.0, TAU)
	var start := global_position + Vector3(cos(angle), 0.0, sin(angle)) * flight_radius + Vector3(0.0, flight_height, 0.0)
	var end := global_position + Vector3(cos(angle + PI), 0.0, sin(angle + PI)) * flight_radius + Vector3(0.0, flight_height, 0.0)

	get_parent().add_child(bird)
	bird.global_position = start
	bird.look_at(end, Vector3.UP)

	var duration := randf_range(flight_duration_min, flight_duration_max)
	var tween := bird.create_tween()
	tween.tween_property(bird, "global_position", end, duration)
	tween.tween_callback(bird.queue_free)

	_schedule_next()
