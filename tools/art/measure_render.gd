extends SceneTree

## Stage B0 render capture and measurement (D-60). Needs a display (xvfb-run
## is fine): godot --rendering-driver opengl3 --path <project> -s res://tools/art/measure_render.gd -- mode=<m> out=<dir>
##   mode=preview  the art preview scene from each of its fixed cameras
##   mode=meadow   the real game (its main scene, so autoloads, WorldSimulation
##                 and the player all run) seen from fixed viewpoints at the
##                 game camera's angle (pitch -42°, 11 m, fov 50)
## For each view: a screenshot (<out>/<view>.png) and, averaged over FRAMES
## frames after a settle, draw calls, primitives and frame time (one line of
## RENDER_STAT per view). Measurements under software rendering are relative
## only (the same machine before vs after) — never a PC GPU or Android figure.

const PREVIEW := "res://scenes/dev/organic_preview/OrganicArtPreview.tscn"
const SETTLE := 30
const FRAMES := 60
## [name, target point]; the camera sits at the follow camera's offset from it.
const MEADOW_VIEWS := [["meadow_start", Vector3(0, 0, 5)], ["meadow_garden", Vector3(12, 0, 2.5)],
	["meadow_pond", Vector3(9, 0, -9)], ["meadow_west_forest", Vector3(-24, 0, -8)]]

var args := {}

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var at := arg.find("=")
		if at > 0:
			args[arg.left(at)] = arg.substr(at + 1)
	_run()

func _run() -> void:
	var out := str(args.get("out", "user://"))
	DirAccess.make_dir_recursive_absolute(out)
	var views: Array = []
	if str(args.get("mode", "")) == "preview":
		var scene: Node = load(PREVIEW).instantiate()
		root.add_child(scene)
		for cam in scene.find_children("*", "Camera3D", true, false):
			views.append([str(cam.name).to_snake_case(), cam])
	else:
		var main_scene: String = ProjectSettings.get_setting("application/run/main_scene")
		root.add_child(load(main_scene).instantiate())
		for i in 20:
			await process_frame
		# The preview's game-angle camera (fov 50, set in the scene) is copied for
		# each view, so this tool never writes a camera's FOV itself.
		var template: Node = load(PREVIEW).instantiate()
		var game_cam: Camera3D = template.get_node("Cameras/GameAngleCamera")
		for v: Array in MEADOW_VIEWS:
			var cam: Camera3D = game_cam.duplicate()
			root.add_child(cam)
			var target: Vector3 = v[1]
			cam.global_position = target + Vector3(0, 1.4 + 11.0 * sin(deg_to_rad(42.0)), 11.0 * cos(deg_to_rad(42.0)))
			cam.rotation_degrees = Vector3(-42, 0, 0)
			views.append([v[0], cam])
		template.queue_free()
	for v: Array in views:
		var cam: Camera3D = v[1]
		cam.make_current()
		for i in SETTLE:
			await process_frame
		var draws := 0.0
		var prims := 0.0
		var t0 := Time.get_ticks_usec()
		for i in FRAMES:
			await process_frame
			draws += RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_DRAW_CALLS_IN_FRAME)
			prims += RenderingServer.get_rendering_info(RenderingServer.RENDERING_INFO_TOTAL_PRIMITIVES_IN_FRAME)
		var ms := (Time.get_ticks_usec() - t0) / 1000.0 / FRAMES
		var img := root.get_viewport().get_texture().get_image()
		img.save_png(out.path_join(str(v[0]) + ".png"))
		print("RENDER_STAT %s draw_calls %.1f primitives %.0f frame_ms %.2f" % [v[0], draws / FRAMES, prims / FRAMES, ms])
	print("RENDER_DONE")
	quit(0)
