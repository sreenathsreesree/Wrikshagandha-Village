extends SceneTree

## Living Pond Edge (W1, D-63): builds the pond's three dressing meshes once,
## offline — nothing is generated at runtime: the shoreline ring, the shore
## stones (the existing rock_a/rock_b meshes, merged) and the ground cover (the
## existing grass tuft, merged), so each is one draw call.
## Deterministic: fixed noise seeds, a fixed RandomNumberGenerator seed and
## fixed resource ids, so a rerun writes byte-identical files.
##   godot --headless --path <project> -s res://tools/art/generate_pond_edge.gd [-- out=<dir>]
## out defaults to res://assets/organic/meshes; tools/art/run_organic_checks.sh
## regenerates into a temporary folder, compares the files with the committed
## ones and checks the shore's shape (tools/art/check_organic_assets.gd
## mode=pond); tools/sims/sim_slice_layout.py checks STONES and TUFTS below
## against the Meadow (paths, the rest spot's view, the southern side).
##
## Both are in the pond's own frame (its centre at the origin): PondEdge.tscn
## sits exactly on the Meadow's Pond node. The figures below are the pond's
## (scenes/world/props/PondWater.tscn, unchanged): water radius 3.6 m, its top
## 0.05 m above the ground, its sine wave at most 0.025 m above that.
##
## The shore is a ring from an irregular inner line inside the water's rim out
## to 5.3 m. Its inner lip stays above the highest wave out past the rim, so
## the lip's outline is the pond's visible edge and the disc's hard circle and
## side are covered. It then steps down to BANK_HEIGHT, just above the path
## patches' highest point (0.03 m), and stays there wherever it shows any earth
## (out to 5.0 m), so no path patch ever pokes through the bank; where a patch
## lies under it the shader draws that patch's own colour. Only beyond 5.0 m,
## where its colour is exactly the ground's or the path's, does it sink to
## RIM_HEIGHT. Vertex colour: r = earth weight, g = wetness (pond_shore.gdshader).

const DEFAULT_OUT := "res://assets/organic/meshes"
const SHORE_MATERIAL := "res://assets/organic/materials/pond_shore.tres"

const WATER_RADIUS := 3.6
const LIP_HEIGHT := 0.085          ## above the water's highest point (0.05 + 0.025)
const LIP_OUT := 3.72              ## the lip stays at LIP_HEIGHT out to here (past the rim and its side)
const SLOPE_OUT := 4.12            ## where the lip has stepped down to BANK_HEIGHT
const BANK_HEIGHT := 0.034         ## above every path patch (their tops are at most 0.03 m)
const EARTH_END := 5.0             ## no earth (weight 0) from here out
const RIM_HEIGHT := 0.004
const OUTER := 5.3                 ## the mesh's outer rim
const INNER_MEAN := 3.3
const INNER_SWING := 0.17          ## inner line 3.13–3.47 m
const EARTH_MEAN := 3.95
const EARTH_SWING := 0.42          ## the earth line 3.53–4.37 m, fading over 0.6 m (ends by 4.97 m)
const EARTH_FADE := 0.6
const SEGMENTS := 96
const RINGS := [0.0, 0.5, 1.0, 3.82, 3.92, 4.02, 4.12, 4.35, 4.6, 4.8, 5.0, 5.15, 5.3]   ## 0..1 = inner line → LIP_OUT; then metres

const ROCK_MESHES := {"a": "res://assets/organic/meshes/rock_a.res", "b": "res://assets/organic/meshes/rock_b.res"}
const GRASS_MESH := "res://assets/organic/meshes/grass_tuft_a.res"

## Shore stones, pond frame: [rock, x, y (sunk), z, yaw degrees, scale]. The four
## north/east stones may stand up to ~0.17 m; the three on the southern half
## (the side the camera looks across) stay under 0.12 m.
const STONES := [["a", 0.93, -0.05, -3.48, 20, 0.42], ["b", 2.31, -0.03, -3.42, 140, 0.5], ["b", 3.34, -0.03, -1.21, 75, 0.42],
	["a", -1.2, -0.04, -3.29, 250, 0.3], ["a", 3.69, -0.04, 0.65, 310, 0.28], ["b", 1.85, -0.02, 3.2, 200, 0.3],
	["a", -3.65, -0.03, 0.0, 95, 0.25]]
## Ground-cover tufts, pond frame: [x, z, yaw degrees, scale, tint]. Chosen once
## with RandomNumberGenerator seed 6302 by the rule: the north half of the bank
## (z < -0.5), 3.95–4.9 m from the centre, 1.6 m clear of the line from the Pond
## Rest Spot to the pond centre, 0.6 m from every stone, reed and existing prop
## near the shore, 0.55 m apart. tint = a small per-tuft colour shift (-1..1) baked
## into the vertex colour (set by hand), since the merged mesh has one origin.
const TUFTS := [[4.06, -0.88, 45, 0.77, 0.4], [0.92, -4.29, 286, 0.98, -0.7], [0.48, -4.75, 158, 0.99, 0.1],
	[-2.42, -3.84, 122, 0.66, 0.8], [1.45, -3.94, 243, 0.7, -0.3], [-0.81, -4.4, 203, 0.77, 0.6],
	[-1.81, -4.23, 222, 0.95, -0.9], [4.06, -2.37, 62, 0.83, 0.2], [4.61, -1.53, 160, 0.72, -0.5],
	[1.38, -4.64, 250, 0.98, 0.9], [2.28, -4.21, 34, 0.99, -0.2], [3.44, -2.27, 223, 0.77, 0.5],
	[3.96, -1.47, 78, 0.83, -0.8], [-4.76, -0.65, 110, 0.76, 0.3], [-1.22, -4.03, 89, 0.7, -0.4],
	[0.16, -4.3, 8, 0.82, 0.7]]
const TINT_VARIATION := 0.08

var out_dir := DEFAULT_OUT

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("out="):
			out_dir = arg.substr(4)
	if not out_dir.begins_with("res://"):
		DirAccess.make_dir_recursive_absolute(out_dir)
	var failed := 0
	var shore := _shore()
	shore.resource_name = "pond_shore"
	shore.resource_scene_unique_id = "pond_shore"
	failed += _save(shore, "pond_shore.res", "%d triangles" % (shore.surface_get_arrays(0)[Mesh.ARRAY_INDEX].size() / 3))
	var stones := _merged(_stone_parts())
	stones.resource_name = "pond_stones"
	stones.resource_scene_unique_id = "pond_stones"
	failed += _save(stones, "pond_stones.res", "%d stones" % STONES.size())
	var cover := _merged(_tuft_parts())
	cover.resource_name = "pond_ground_cover"
	cover.resource_scene_unique_id = "pond_ground_cover"
	failed += _save(cover, "pond_ground_cover.res", "%d tufts" % TUFTS.size())
	print("POND_GEN %s" % ("OK" if failed == 0 else "FAILED"))
	quit(0 if failed == 0 else 1)

func _save(res: Resource, file: String, info: String) -> int:
	var path := out_dir.path_join(file)
	var err := ResourceSaver.save(res, path)
	if err != OK:
		print("POND_GEN FAIL %s (error %d)" % [path, err])
		return 1
	print("POND_GEN %s %s" % [file, info])
	return 0

func _noise(seed_value: int) -> FastNoiseLite:
	var n := FastNoiseLite.new()
	n.seed = seed_value
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	n.frequency = 1.0
	return n

## A smooth value in -1..1 round the circle (sampled on a circle, so it closes).
func _around(n: FastNoiseLite, angle: float, size: float) -> float:
	return clampf(n.get_noise_2d(cos(angle) * size, sin(angle) * size) * 1.6, -1.0, 1.0)

func _shore() -> ArrayMesh:
	var inner_n := _noise(6303)
	var earth_n := _noise(6304)
	var wet_n := _noise(6305)
	var verts := PackedVector3Array()
	var norms := PackedVector3Array()
	var cols := PackedColorArray()
	var index := PackedInt32Array()
	var rows := RINGS.size()
	for s in SEGMENTS:
		var a := TAU * s / SEGMENTS
		var r_in := INNER_MEAN + INNER_SWING * _around(inner_n, a, 1.3)
		var r_earth := EARTH_MEAN + EARTH_SWING * _around(earth_n, a, 1.7)
		var wet_w := 0.45 + 0.15 * _around(wet_n, a, 2.1)
		for k in rows:
			var t: float = RINGS[k]
			var r: float = lerpf(r_in, LIP_OUT, t) if t <= 1.0 else t
			var y := shore_height(r)
			var earth := 1.0 - smoothstep(r_earth, r_earth + EARTH_FADE, r)
			if r >= EARTH_END:
				earth = 0.0
			var wet := 1.0 - clampf((r - r_in) / wet_w, 0.0, 1.0)
			verts.append(Vector3(cos(a) * r, y, sin(a) * r))
			norms.append(Vector3.UP)
			cols.append(Color(earth, wet, 0.0, 1.0))
	for s in SEGMENTS:
		var s2 := (s + 1) % SEGMENTS
		for k in rows - 1:
			var a0: int = s * rows + k
			var a1: int = s * rows + k + 1
			var b0: int = s2 * rows + k
			var b1: int = s2 * rows + k + 1
			# Clockwise seen from above (Godot's front faces), so the top shows under cull_back.
			index.append_array([a0, a1, b0, a1, b1, b0])
	var arrays := []
	arrays.resize(Mesh.ARRAY_MAX)
	arrays[Mesh.ARRAY_VERTEX] = verts
	arrays[Mesh.ARRAY_NORMAL] = norms
	arrays[Mesh.ARRAY_COLOR] = cols
	arrays[Mesh.ARRAY_INDEX] = index
	var mesh := ArrayMesh.new()
	mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
	mesh.surface_set_material(0, load(SHORE_MATERIAL))
	return mesh

## The shore's height at a distance r from the centre (from the inner lip out).
static func shore_height(r: float) -> float:
	if r <= LIP_OUT:
		return LIP_HEIGHT
	if r <= SLOPE_OUT:
		return lerpf(LIP_HEIGHT, BANK_HEIGHT, smoothstep(LIP_OUT, SLOPE_OUT, r))
	if r <= EARTH_END:
		return BANK_HEIGHT
	return lerpf(BANK_HEIGHT, RIM_HEIGHT, smoothstep(EARTH_END, OUTER, r))

func _stone_parts() -> Array:
	var parts := []
	for st: Array in STONES:
		var basis := Basis(Vector3.UP, deg_to_rad(st[4])).scaled(Vector3.ONE * float(st[5]))
		parts.append([load(ROCK_MESHES[st[0]]), Transform3D(basis, Vector3(st[1], st[2], st[3])), Color(1, 1, 1)])
	return parts

func _tuft_parts() -> Array:
	var parts := []
	var mesh: ArrayMesh = load(GRASS_MESH)
	for t: Array in TUFTS:
		var basis := Basis(Vector3.UP, deg_to_rad(t[2])).scaled(Vector3.ONE * float(t[3]))
		var h: float = t[4]
		var k := TINT_VARIATION
		var r := Vector2(t[0], t[1]).length()
		# Standing on the bank, not sunk into it.
		parts.append([mesh, Transform3D(basis, Vector3(t[0], shore_height(r), t[1])), Color(1.0 + h * k, 1.0 + h * k * 0.25, 1.0 - h * k)])
	return parts

## Copies of existing meshes, transformed and merged surface by surface (one
## surface per material), each copy's vertex colour multiplied by its tint.
func _merged(parts: Array) -> ArrayMesh:
	var by_mat := {}
	var order := []
	for part: Array in parts:
		var src: ArrayMesh = part[0]
		var xf: Transform3D = part[1]
		var tint: Color = part[2]
		for si in src.get_surface_count():
			var mat := src.surface_get_material(si)
			if not by_mat.has(mat):
				by_mat[mat] = [PackedVector3Array(), PackedVector3Array(), PackedColorArray(), PackedInt32Array()]
				order.append(mat)
			var acc: Array = by_mat[mat]
			var arr := src.surface_get_arrays(si)
			var base: int = (acc[0] as PackedVector3Array).size()
			var v: PackedVector3Array = arr[Mesh.ARRAY_VERTEX]
			var n: PackedVector3Array = arr[Mesh.ARRAY_NORMAL]
			var c: PackedColorArray = arr[Mesh.ARRAY_COLOR]
			for i in v.size():
				acc[0].append(xf * v[i])
				acc[1].append((xf.basis * n[i]).normalized())
				acc[2].append(Color(c[i].r * tint.r, c[i].g * tint.g, c[i].b * tint.b, c[i].a))
			for i: int in arr[Mesh.ARRAY_INDEX]:
				acc[3].append(base + i)
	var mesh := ArrayMesh.new()
	for mat in order:
		var acc: Array = by_mat[mat]
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = acc[0]
		arrays[Mesh.ARRAY_NORMAL] = acc[1]
		arrays[Mesh.ARRAY_COLOR] = acc[2]
		arrays[Mesh.ARRAY_INDEX] = acc[3]
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		mesh.surface_set_material(mesh.get_surface_count() - 1, mat)
	return mesh
