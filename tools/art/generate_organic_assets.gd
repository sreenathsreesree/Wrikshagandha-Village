extends SceneTree

## Stage B0 organic art (D-60): builds the organic prop meshes once, offline,
## and saves them as resources the scenes reference — nothing is generated at
## runtime. Deterministic: every asset has a fixed seed (FastNoiseLite and
## RandomNumberGenerator only), so a rerun writes the same geometry.
##   godot --headless --path <project> -s res://tools/art/generate_organic_assets.gd [-- out=<dir>]
## out defaults to res://assets/organic/meshes; tools/art/run_organic_checks.sh
## regenerates into a temporary folder and compares the content with the
## committed meshes. Each mesh has at most two surfaces (bark/stone, foliage),
## each with one of the shared materials in res://assets/organic/materials/.
## The bounds every prop must keep (roots, low trunk, canopy) are checked on
## the saved meshes by tools/art/check_organic_assets.gd, not here.

const MAT_DIR := "res://assets/organic/materials/"
const DEFAULT_OUT := "res://assets/organic/meshes"

var out_dir := DEFAULT_OUT
var mats := {}

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("out="):
			out_dir = arg.substr(4)
	for m in ["bark", "foliage", "grass", "rock", "earth"]:
		mats[m] = load(MAT_DIR + "organic_%s.tres" % m)
		if mats[m] == null:
			print("ORGANIC_GEN FAIL material organic_%s.tres missing" % m)
			quit(1)
			return
	if not out_dir.begins_with("res://"):
		DirAccess.make_dir_recursive_absolute(out_dir)
	var builders := {
		"tree_round_a": _tree_round, "tree_tall_a": _tree_tall, "tree_wide_a": _tree_wide,
		"rock_a": _rock_a, "rock_b": _rock_b, "bush_a": _bush, "grass_tuft_a": _grass_tuft,
		"great_tree": _great_tree, "ground_sample": _ground_sample, "path_sample": _path_sample,
	}
	var failed := 0
	for asset_name: String in builders:
		var mesh: ArrayMesh = builders[asset_name].call()
		mesh.resource_name = asset_name
		# A fixed id instead of Godot's random one, so a rerun writes byte-identical files.
		mesh.resource_scene_unique_id = asset_name
		var path := out_dir.path_join(asset_name + ".res")
		var err := ResourceSaver.save(mesh, path)
		var tris := 0
		for s in mesh.get_surface_count():
			tris += mesh.surface_get_arrays(s)[Mesh.ARRAY_INDEX].size() / 3
		if err != OK:
			failed += 1
			print("ORGANIC_GEN FAIL %s (error %d)" % [path, err])
		else:
			print("ORGANIC_GEN %s %d triangles, %d surfaces" % [asset_name, tris, mesh.get_surface_count()])
	print("ORGANIC_GEN %s" % ("OK" if failed == 0 else "FAILED"))
	quit(0 if failed == 0 else 1)

# ---------------------------------------------------------------- mesh building

## One surface being built: triangles with a colour per corner. smooth = the
## normals of corners at the same position are averaged (trunks, canopies);
## otherwise each triangle is flat (rocks, blades).
class Part:
	var material: Material
	var smooth: bool
	var verts := PackedVector3Array()
	var cols := PackedColorArray()
	func _init(m: Material, is_smooth: bool) -> void:
		material = m
		smooth = is_smooth
	func tri(a: Vector3, b: Vector3, c: Vector3, ca: Color, cb: Color, cc: Color) -> void:
		verts.append_array([a, b, c])
		cols.append_array([ca, cb, cc])

## Merges parts that share a material into one surface each (at most two per
## prop), computes normals, indexes identical corners, returns the mesh.
func _build(parts: Array) -> ArrayMesh:
	var mesh := ArrayMesh.new()
	var order: Array = []
	var by_mat := {}
	for p: Part in parts:
		if not by_mat.has(p.material):
			by_mat[p.material] = []
			order.append(p.material)
		by_mat[p.material].append(p)
	for m: Material in order:
		var verts := PackedVector3Array()
		var norms := PackedVector3Array()
		var cols := PackedColorArray()
		var index := PackedInt32Array()
		var seen := {}
		for p: Part in by_mat[m]:
			var corner_normals := _normals(p)
			for i in p.verts.size():
				var key := "%s|%s|%s" % [p.verts[i], corner_normals[i], p.cols[i]]
				if not seen.has(key):
					seen[key] = verts.size()
					verts.append(p.verts[i])
					norms.append(corner_normals[i])
					cols.append(p.cols[i])
				index.append(seen[key])
		var arrays := []
		arrays.resize(Mesh.ARRAY_MAX)
		arrays[Mesh.ARRAY_VERTEX] = verts
		arrays[Mesh.ARRAY_NORMAL] = norms
		arrays[Mesh.ARRAY_COLOR] = cols
		arrays[Mesh.ARRAY_INDEX] = index
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays)
		mesh.surface_set_material(mesh.get_surface_count() - 1, m)
	return mesh

func _normals(p: Part) -> PackedVector3Array:
	var out := PackedVector3Array()
	out.resize(p.verts.size())
	var acc := {}
	for t in range(0, p.verts.size(), 3):
		# Godot's front faces wind clockwise seen from outside: the normal is (c - a) x (b - a).
		var n := (p.verts[t + 2] - p.verts[t]).cross(p.verts[t + 1] - p.verts[t])
		if n.length() > 0.0:
			n = n.normalized()
		for k in 3:
			out[t + k] = n
			if p.smooth:
				var key := str(p.verts[t + k])
				acc[key] = acc.get(key, Vector3.ZERO) + n
	if p.smooth:
		for i in p.verts.size():
			var s: Vector3 = acc[str(p.verts[i])]
			out[i] = s.normalized() if s.length() > 0.0 else out[i]
	return out

func _noise(seed_value: int, frequency: float) -> FastNoiseLite:
	var n := FastNoiseLite.new()
	n.seed = seed_value
	n.noise_type = FastNoiseLite.TYPE_SIMPLEX_SMOOTH
	n.frequency = frequency
	return n

# ---------------------------------------------------------------- shapes

var _ico_cache := {}

## Unit icosphere triangles (outward, clockwise from outside), subdivided n times.
func _icosphere(n: int) -> Array:
	if _ico_cache.has(n):
		return _ico_cache[n]
	var t := (1.0 + sqrt(5.0)) / 2.0
	var v := [Vector3(-1, t, 0), Vector3(1, t, 0), Vector3(-1, -t, 0), Vector3(1, -t, 0), Vector3(0, -1, t), Vector3(0, 1, t),
		Vector3(0, -1, -t), Vector3(0, 1, -t), Vector3(t, 0, -1), Vector3(t, 0, 1), Vector3(-t, 0, -1), Vector3(-t, 0, 1)]
	var faces := [[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6],
		[7, 1, 8], [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]]
	var tris: Array = []
	for f: Array in faces:
		tris.append([(v[f[0]] as Vector3).normalized(), (v[f[1]] as Vector3).normalized(), (v[f[2]] as Vector3).normalized()])
	for _i in n:
		var next: Array = []
		for tr: Array in tris:
			var a: Vector3 = tr[0]
			var b: Vector3 = tr[1]
			var c: Vector3 = tr[2]
			var ab := ((a + b) * 0.5).normalized()
			var bc := ((b + c) * 0.5).normalized()
			var ca := ((c + a) * 0.5).normalized()
			next.append_array([[a, ab, ca], [ab, b, bc], [ca, bc, c], [ab, bc, ca]])
		tris = next
	# Godot front faces are clockwise from outside; the table above is counter-clockwise.
	var out: Array = []
	for tr: Array in tris:
		out.append([tr[0], tr[2], tr[1]])
	_ico_cache[n] = out
	return out

## A lumpy clump (canopy, bush, rock): an icosphere pushed in and out by noise,
## scaled, rotated about y, never below floor_y. Colour: dark underneath, light
## on top, with a little noise. Returns nothing; adds to part.
func _blob(part: Part, centre: Vector3, radii: Vector3, subdiv: int, amp: float, noise: FastNoiseLite,
		bottom: Color, top: Color, floor_y: float = -1000.0, yaw: float = 0.0, offset: float = 0.0) -> void:
	var basis := Basis(Vector3.UP, yaw)
	for tr: Array in _icosphere(subdiv):
		var p: Array = []
		var c: Array = []
		for u: Vector3 in tr:
			var k := 1.0 + amp * noise.get_noise_3d(u.x * 1.7 + offset, u.y * 1.7, u.z * 1.7 - offset)
			var q := centre + basis * Vector3(u.x * radii.x, u.y * radii.y, u.z * radii.z) * k
			q.y = maxf(q.y, floor_y)
			p.append(q)
			var shade := clampf(0.5 + 0.5 * u.y + 0.15 * noise.get_noise_3d(u.x * 5.0 + offset, u.y * 5.0, u.z * 5.0), 0.0, 1.0)
			c.append(bottom.lerp(top, shade))
		part.tri(p[0], p[1], p[2], c[0], c[1], c[2])

## A tapered tube along points (trunks, branches, roots), with a little bark
## noise on the radius; an optional cap closes the top end.
func _tube(part: Part, pts: Array, radii: Array, sides: int, noise: FastNoiseLite, base_col: Color, tip_col: Color,
		cap: bool = true, bark: float = 0.04, roll: float = 0.0) -> void:
	var rings: Array = []
	var nrm := Vector3.ZERO
	for i in pts.size():
		var prev: Vector3 = pts[maxi(i - 1, 0)]
		var nxt: Vector3 = pts[mini(i + 1, pts.size() - 1)]
		var tan_v := (nxt - prev).normalized()
		if i == 0:
			nrm = (Vector3.FORWARD if absf(tan_v.dot(Vector3.UP)) > 0.9 else Vector3.UP).cross(tan_v).normalized()
		else:
			nrm = (nrm - tan_v * nrm.dot(tan_v)).normalized()
		var bin := tan_v.cross(nrm)
		var ring: Array = []
		var r: float = radii[i]
		for k in sides:
			var a := TAU * k / sides + roll
			var dir := nrm * cos(a) + bin * sin(a)
			var p: Vector3 = pts[i]
			var j := 1.0 + bark * noise.get_noise_3d(p.x * 6.0 + dir.x, p.y * 6.0, p.z * 6.0 + dir.z)
			ring.append(p + dir * r * j)
		rings.append(ring)
	for i in pts.size() - 1:
		var c0 := base_col.lerp(tip_col, float(i) / (pts.size() - 1))
		var c1 := base_col.lerp(tip_col, float(i + 1) / (pts.size() - 1))
		for k in sides:
			var a: Vector3 = rings[i][k]
			var b: Vector3 = rings[i][(k + 1) % sides]
			var c: Vector3 = rings[i + 1][k]
			var d: Vector3 = rings[i + 1][(k + 1) % sides]
			var s := 0.92 + 0.16 * (0.5 + 0.5 * noise.get_noise_2d(k * 3.1, i * 2.3))
			part.tri(a, c, b, c0 * s, c1 * s, c0 * s)
			part.tri(b, c, d, c0 * s, c1 * s, c1 * s)
	if cap:
		var last: Array = rings[rings.size() - 1]
		var tip: Vector3 = pts[pts.size() - 1]
		for k in sides:
			part.tri(last[k], tip, last[(k + 1) % sides], tip_col, tip_col, tip_col)

## A curved, tapered, double-sided blade or frond from base towards dir.
func _blade(part: Part, base: Vector3, dir: Vector3, height: float, lean: float, width: float, segments: int,
		base_col: Color, tip_col: Color) -> void:
	var side := Vector3(-dir.z, 0.0, dir.x).normalized()
	var left: Array = []
	var right: Array = []
	for i in segments + 1:
		var f := float(i) / segments
		var centre := base + dir * lean * f * f + Vector3.UP * height * sin(f * PI * 0.5)
		var w := width * (1.0 - f) * 0.5
		left.append(centre - side * w)
		right.append(centre + side * w)
	for i in segments:
		var c0 := base_col.lerp(tip_col, float(i) / segments)
		var c1 := base_col.lerp(tip_col, float(i + 1) / segments)
		var a: Vector3 = left[i]
		var b: Vector3 = right[i]
		var c: Vector3 = left[i + 1]
		var d: Vector3 = right[i + 1]
		if i == segments - 1:
			part.tri(a, c, b, c0, c1, c0)
			part.tri(a, b, c, c0, c0, c1)
		else:
			part.tri(a, c, b, c0, c1, c0)
			part.tri(b, c, d, c0, c1, c1)
			part.tri(a, b, c, c0, c0, c1)
			part.tri(b, d, c, c0, c1, c1)

func _ring_dir(angle: float) -> Vector3:
	return Vector3(cos(angle), 0.0, sin(angle))

# ---------------------------------------------------------------- palette

const BARK_DARK := Color(0.27, 0.18, 0.12)
const BARK_MID := Color(0.40, 0.27, 0.18)
const BARK_LIGHT := Color(0.50, 0.36, 0.24)
const LEAF_DEEP := Color(0.10, 0.21, 0.09)
const LEAF_MID := Color(0.21, 0.37, 0.14)
const LEAF_SUN := Color(0.38, 0.50, 0.19)
const STONE_DARK := Color(0.30, 0.27, 0.24)
const STONE_LIGHT := Color(0.55, 0.49, 0.41)

# ---------------------------------------------------------------- props

## Round tree: a gently curving tapered trunk with root flares, three
## branches into a layered canopy of six lumpy clumps. Trunk collider r 0.2.
func _tree_round() -> ArrayMesh:
	var nz := _noise(1101, 0.9)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage"], true)
	_tube(bark, [Vector3(0, -0.05, 0), Vector3(0, 0.15, 0), Vector3(0.01, 0.6, 0), Vector3(0.02, 1.15, 0.01),
		Vector3(0.08, 1.7, 0.04), Vector3(0.14, 2.2, 0.02), Vector3(0.1, 2.6, -0.03)],
		[0.27, 0.205, 0.195, 0.18, 0.15, 0.12, 0.07], 7, nz, BARK_DARK, BARK_LIGHT)
	for k in 5:
		var d := _ring_dir(TAU * k / 5.0 + 0.4)
		_tube(bark, [d * 0.15 + Vector3(0, 0.1, 0), d * 0.32 + Vector3(0, 0.05, 0), d * 0.5 + Vector3(0, -0.01, 0)],
			[0.065, 0.045, 0.025], 5, nz, BARK_DARK, BARK_MID)
	for b in [[0.3, 1.55, Vector3(0.75, 2.25, 0.35)], [2.4, 1.75, Vector3(-0.7, 2.35, -0.3)], [4.3, 1.95, Vector3(0.2, 2.55, -0.7)]]:
		var d := _ring_dir(b[0])
		var start := Vector3(0.06, b[1], 0.02)
		var end_p: Vector3 = b[2]
		_tube(bark, [start, start.lerp(end_p, 0.5) + Vector3(0, 0.15, 0) + d * 0.05, end_p], [0.07, 0.05, 0.03], 5, nz, BARK_MID, BARK_LIGHT)
	var clumps := [[Vector3(0.1, 2.4, 0), Vector3(1.0, 0.72, 0.95), 2], [Vector3(0.55, 2.05, 0.3), Vector3(0.6, 0.45, 0.55), 1],
		[Vector3(-0.5, 2.1, -0.25), Vector3(0.6, 0.48, 0.6), 1], [Vector3(0.0, 2.1, -0.6), Vector3(0.5, 0.4, 0.45), 1],
		[Vector3(-0.2, 2.9, 0.2), Vector3(0.6, 0.5, 0.6), 2], [Vector3(0.4, 2.75, -0.35), Vector3(0.5, 0.4, 0.5), 1]]
	for i in clumps.size():
		var cl: Array = clumps[i]
		_blob(leaves, cl[0], cl[1], cl[2], 0.18, nz, LEAF_DEEP, LEAF_SUN.lerp(LEAF_MID, 0.15 * (i % 3)), 1.25, i * 0.9, i * 7.0)
	return _build([bark, leaves])

## Tall tree: a slender, nearly straight trunk under five stacked, drooping
## tiers narrowing upwards — a columnar silhouette (Ashoka-like), clearly unlike
## the round tree. Trunk collider r 0.16.
func _tree_tall() -> ArrayMesh:
	var nz := _noise(2203, 1.1)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage"], true)
	_tube(bark, [Vector3(0, -0.05, 0), Vector3(0, 0.15, 0), Vector3(0.005, 0.7, 0), Vector3(0.01, 1.15, 0),
		Vector3(0.03, 2.0, 0.01), Vector3(0.0, 3.0, 0.02), Vector3(-0.02, 3.95, 0.0)],
		[0.21, 0.165, 0.155, 0.145, 0.12, 0.09, 0.04], 6, nz, BARK_DARK, BARK_MID)
	for k in 4:
		var d := _ring_dir(TAU * k / 4.0 + 0.8)
		_tube(bark, [d * 0.12 + Vector3(0, 0.08, 0), d * 0.25 + Vector3(0, 0.04, 0), d * 0.38 + Vector3(0, -0.01, 0)],
			[0.05, 0.035, 0.02], 5, nz, BARK_DARK, BARK_MID)
	# Tiers narrowing upwards, each a little off-centre and turned, the lower
	# ones split into two lobes so the outline is ragged, not stacked rings.
	var tiers := [[1.95, 0.6, 0.42, 0.34], [2.5, 0.54, 0.4, 0.3], [3.02, 0.62, 0.38, 0.0], [3.48, 0.48, 0.33, 0.0], [3.9, 0.3, 0.3, 0.0]]
	var deep := LEAF_DEEP.lerp(Color(0.09, 0.2, 0.11), 0.5)
	for i in tiers.size():
		var t: Array = tiers[i]
		var split: float = t[3]
		var lobes := 2 if split > 0.0 else 1
		for l in lobes:
			var off := _ring_dir(i * 2.1 + l * PI) * (split if lobes == 2 else 0.05)
			var r: float = t[1] * (1.0 if l == 0 else 0.86)
			_blob(leaves, Vector3(off.x, t[0] - 0.06 * l, off.z), Vector3(r, t[2], r * 0.9), 1, 0.24, nz, deep,
				LEAF_MID.lerp(LEAF_SUN, 0.18 * i), 1.22, i * 1.3 + l, i * 5.0 + l * 17.0)
	return _build([bark, leaves])

## Wide tree: a short thick trunk with six root flares and four limbs spreading
## almost level into a broad, flat umbrella canopy (banyan-like, without aerial
## roots — those stay on the Great Tree, never on a prop). Trunk collider r 0.24.
func _tree_wide() -> ArrayMesh:
	var nz := _noise(3307, 0.8)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage"], true)
	_tube(bark, [Vector3(0, -0.05, 0), Vector3(0, 0.15, 0), Vector3(0.01, 0.6, 0), Vector3(0.02, 1.05, 0.01),
		Vector3(0.05, 1.4, 0.02), Vector3(0.03, 1.7, 0.0)],
		[0.33, 0.25, 0.235, 0.22, 0.2, 0.15], 8, nz, BARK_DARK, BARK_LIGHT)
	for k in 6:
		var d := _ring_dir(TAU * k / 6.0 + 0.2)
		_tube(bark, [d * 0.2 + Vector3(0, 0.1, 0), d * 0.42 + Vector3(0, 0.04, 0), d * 0.62 + Vector3(0, -0.01, 0)],
			[0.07, 0.05, 0.03], 5, nz, BARK_DARK, BARK_MID)
	for k in 4:
		var d := _ring_dir(TAU * k / 4.0 + 0.6)
		var start := Vector3(0.03, 1.38, 0.01)
		_tube(bark, [start, start + d * 0.55 + Vector3(0, 0.16, 0), start + d * 1.1 + Vector3(0, 0.38, 0)], [0.1, 0.07, 0.04], 5, nz, BARK_MID, BARK_LIGHT)
	_blob(leaves, Vector3(0, 2.2, 0), Vector3(1.15, 0.5, 1.1), 2, 0.15, nz, LEAF_DEEP, LEAF_SUN, 1.15, 0.0, 0.0)
	for k in 6:
		var d := _ring_dir(TAU * k / 6.0)
		_blob(leaves, d * 0.95 + Vector3(0, 1.8 + 0.08 * (k % 2), 0), Vector3(0.6, 0.38, 0.6), 1, 0.15, nz, LEAF_DEEP,
			LEAF_MID.lerp(LEAF_SUN, 0.5 + 0.1 * (k % 3)), 1.15, k * 1.1, k * 3.0 + 11.0)
	return _build([bark, leaves])

## Rock A: a faceted boulder with a side stone and a pebble, flat on the ground.
## Collider: sphere r 0.42 at (0.1, 0.28, 0.05).
func _rock_a() -> ArrayMesh:
	var nz := _noise(4409, 1.0)
	var stone := Part.new(mats["rock"], false)
	_blob(stone, Vector3(0.09, 0.2, 0.04), Vector3(0.38, 0.28, 0.34), 1, 0.22, nz, STONE_DARK, STONE_LIGHT, 0.0, 0.3, 0.0)
	_blob(stone, Vector3(0.3, 0.09, 0.18), Vector3(0.16, 0.12, 0.15), 1, 0.22, nz, STONE_DARK, STONE_LIGHT, 0.0, 1.2, 4.0)
	_blob(stone, Vector3(-0.28, 0.05, 0.2), Vector3(0.09, 0.07, 0.08), 1, 0.2, nz, STONE_DARK, STONE_LIGHT, 0.0, 2.0, 9.0)
	return _build([stone])

## Rock B: a low tilted slab with a leaning shard — a second silhouette for the
## preview (the Meadow's rocks all use Rock.tscn, so it appears in-game only
## once Stage A can place it).
func _rock_b() -> ArrayMesh:
	var nz := _noise(5501, 1.2)
	var stone := Part.new(mats["rock"], false)
	_blob(stone, Vector3(0.02, 0.14, 0.0), Vector3(0.46, 0.17, 0.32), 1, 0.2, nz, STONE_DARK, STONE_LIGHT, 0.0, 0.6, 2.0)
	_blob(stone, Vector3(-0.18, 0.18, -0.2), Vector3(0.17, 0.2, 0.14), 1, 0.22, nz, STONE_DARK, STONE_LIGHT, 0.0, 2.2, 6.0)
	_blob(stone, Vector3(0.3, 0.05, 0.2), Vector3(0.1, 0.06, 0.09), 1, 0.2, nz, STONE_DARK, STONE_LIGHT, 0.0, 1.0, 13.0)
	return _build([stone])

## Bush: four overlapping clumps with fern-like fronds arching out at the base.
## Collider: sphere r 0.38 at y 0.32.
func _bush() -> ArrayMesh:
	var nz := _noise(6607, 1.3)
	var leaves := Part.new(mats["foliage"], true)
	var fronds := Part.new(mats["foliage"], false)
	var deep := Color(0.11, 0.24, 0.1)
	for cl in [[Vector3(0, 0.3, 0), Vector3(0.33, 0.28, 0.32)], [Vector3(0.18, 0.22, 0.12), Vector3(0.2, 0.18, 0.2)],
			[Vector3(-0.17, 0.2, -0.1), Vector3(0.2, 0.17, 0.19)], [Vector3(0.05, 0.45, -0.12), Vector3(0.17, 0.15, 0.16)]]:
		_blob(leaves, cl[0], cl[1], 1, 0.2, nz, deep, LEAF_MID, 0.0, 0.0, (cl[0] as Vector3).x * 20.0)
	for k in 8:
		var d := _ring_dir(TAU * k / 8.0 + 0.2)
		_blade(fronds, d * 0.05 + Vector3(0, 0.02, 0), d, 0.34 + 0.04 * (k % 3), 0.4, 0.09, 3, deep, LEAF_SUN.lerp(LEAF_MID, 0.4))
	return _build([leaves, fronds])

## Grass tuft: five bent, tapered, double-sided blades from one root — light
## enough to be scattered later with a MultiMesh. No collider.
func _grass_tuft() -> ArrayMesh:
	var blades := Part.new(mats["grass"], false)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7703
	for k in 5:
		var a := TAU * k / 5.0 + rng.randf_range(-0.3, 0.3)
		var d := _ring_dir(a)
		var base := d * rng.randf_range(0.02, 0.07)
		_blade(blades, base, d, rng.randf_range(0.26, 0.4), rng.randf_range(0.08, 0.17), 0.05, 2,
			Color(0.24, 0.4, 0.13), Color(0.56, 0.68, 0.28).lerp(Color(0.66, 0.62, 0.3), rng.randf() * 0.4))
	return _build([blades])

# ---------------------------------------------------------------- Great Tree (preview only)

## The Great Tree: an ancient sacred banyan-peepal at the heart of the village.
## Five twisting stems merged round a core, buttress roots creeping over a
## round stone platform (a katte, where people sit in its shade), seven great
## limbs spreading wide, aerial roots dropping to the ground, a broad layered
## canopy — and the kalava threads tied round the trunk with a few clay diyas on
## the platform. Visual only: it lives in scenes/dev/ until Stage A places it.
func _great_tree() -> ArrayMesh:
	var nz := _noise(9001, 0.5)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage"], true)
	var stone := Part.new(mats["rock"], false)
	# Platform: two stepped stone rings round the trunk (flat-shaded blocks).
	_platform_ring(stone, 3.6, 2.9, 0.0, 0.22, 28, nz)
	_platform_ring(stone, 3.1, 1.25, 0.22, 0.48, 28, nz)
	# Core and five twisting stems.
	_tube(bark, [Vector3(0, -0.1, 0), Vector3(0, 1.5, 0), Vector3(0.05, 3.0, 0), Vector3(0.0, 4.2, 0.05), Vector3(0, 5.0, 0)],
		[0.9, 0.8, 0.72, 0.6, 0.45], 10, nz, BARK_DARK, BARK_MID, true, 0.06)
	for k in 5:
		var a0 := TAU * k / 5.0
		var pts: Array = []
		var radii: Array = []
		for i in 7:
			var f := i / 6.0
			var a := a0 + f * 0.9
			var r := lerpf(0.6, 0.35, f)
			pts.append(Vector3(cos(a) * r, -0.1 + f * 4.9, sin(a) * r))
			radii.append(lerpf(0.55, 0.3, f))
		_tube(bark, pts, radii, 8, nz, BARK_DARK, BARK_LIGHT, false, 0.07, a0)
	# Buttress roots spreading over the platform and down its edge.
	for k in 7:
		var d := _ring_dir(TAU * k / 7.0 + 0.25)
		_tube(bark, [d * 0.8 + Vector3(0, 0.7, 0), d * 1.6 + Vector3(0, 0.62, 0), d * 2.7 + Vector3(0, 0.55, 0),
			d * 3.25 + Vector3(0, 0.3, 0), d * 3.7 + Vector3(0, 0.02, 0)], [0.42, 0.26, 0.16, 0.12, 0.07], 6, nz, BARK_DARK, BARK_MID, true, 0.08)
	# Great limbs spreading wide and low, each carrying flat shelves of leaves —
	# an umbrella of layered canopy rather than one round crown; aerial roots
	# drop from three limbs to the ground, short strands hang from the others.
	for k in 7:
		var d := _ring_dir(TAU * k / 7.0 + 0.5)
		var h := 3.2 + 0.25 * (k % 3)
		var reach := 4.6 + 0.7 * ((k * 3) % 4)
		var p0 := Vector3(0, h, 0) + d * 0.4
		var p1 := Vector3(0, h + 0.8, 0) + d * reach * 0.35
		var p2 := Vector3(0, h + 1.5, 0) + d * reach * 0.7
		var p3 := Vector3(0, h + 1.9, 0) + d * reach
		_tube(bark, [p0, p1, p2, p3], [0.45, 0.32, 0.22, 0.12], 7, nz, BARK_MID, BARK_LIGHT)
		for sgn in [-1.0, 1.0]:
			var side := d.rotated(Vector3.UP, 0.65 * sgn)
			_tube(bark, [p2, p2 + side * 1.3 + Vector3(0, 0.5, 0), p2 + side * 2.2 + Vector3(0, 0.8, 0)], [0.12, 0.08, 0.04], 5, nz, BARK_MID, BARK_LIGHT)
		var yaw := atan2(d.x, d.z)
		_blob(leaves, p3 + Vector3(0, 0.45, 0), Vector3(2.4, 0.72, 1.9), 2, 0.24, nz, LEAF_DEEP,
			LEAF_MID.lerp(LEAF_SUN, 0.45 + 0.1 * (k % 3)), -1000.0, yaw, k * 4.0)
		_blob(leaves, p2 + Vector3(0, 1.05, 0) + d.rotated(Vector3.UP, 0.9) * 0.8, Vector3(1.7, 0.6, 1.5), 1, 0.24, nz, LEAF_DEEP,
			LEAF_MID.lerp(LEAF_SUN, 0.3), -1000.0, yaw + 0.7, k * 4.0 + 30.0)
		if k % 2 == 0 and k < 6:
			# An aerial root: thin where it leaves the limb, thicker and flared where it roots.
			var top := p1.lerp(p2, 0.6) + Vector3(0, -0.15, 0)
			var foot := Vector3(top.x, 0.0, top.z) + d * 0.25
			_tube(bark, [top, top.lerp(foot, 0.35) + d.rotated(Vector3.UP, 1.4) * 0.12, top.lerp(foot, 0.7) - d.rotated(Vector3.UP, 1.4) * 0.08,
				foot + Vector3(0, 0.25, 0), foot + Vector3(0, -0.05, 0)], [0.05, 0.065, 0.085, 0.12, 0.2], 5, nz, BARK_MID, BARK_DARK, false, 0.12)
		else:
			for st in 2:
				var top := p1.lerp(p2, 0.3 + 0.4 * st) + Vector3(0, -0.12, 0)
				var length := 1.4 + 0.6 * ((k + st) % 3)
				_tube(bark, [top, top + Vector3(0.05, -length * 0.5, 0.03), top + Vector3(0.02, -length, -0.02)], [0.045, 0.03, 0.015], 4, nz, BARK_MID, BARK_DARK, true, 0.1)
	# A low dome over the trunk and a few sunlit pads on top.
	_blob(leaves, Vector3(0, 7.6, 0), Vector3(3.2, 1.25, 3.0), 2, 0.2, nz, LEAF_DEEP, LEAF_SUN, -1000.0, 0.0, 0.0)
	for k in 3:
		var d := _ring_dir(TAU * k / 3.0 + 0.9)
		_blob(leaves, d * 1.6 + Vector3(0, 8.6, 0), Vector3(1.6, 0.65, 1.5), 1, 0.22, nz, LEAF_MID, LEAF_SUN, -1000.0, k * 0.7, k * 9.0 + 70.0)
	# Kalava: red and saffron threads tied round the trunk.
	for i in 3:
		var y := 1.35 + 0.13 * i
		var col := Color(0.72, 0.1, 0.08) if i != 1 else Color(0.92, 0.62, 0.12)
		var pts: Array = []
		var radii: Array = []
		for s in 25:
			var a := TAU * s / 24.0
			pts.append(Vector3(cos(a) * 1.13, y + 0.03 * sin(a * 3.0), sin(a) * 1.13))
			radii.append(0.035)
		_tube(bark, pts, radii, 4, nz, col, col, false, 0.0)
	# Clay diyas on the platform.
	for k in 5:
		var d := _ring_dir(TAU * k / 5.0 + 0.1)
		_diya(bark, d * 2.3 + Vector3(0, 0.48, 0))
	return _build([bark, leaves, stone])

func _platform_ring(part: Part, outer: float, inner: float, y0: float, y1: float, sides: int, nz: FastNoiseLite) -> void:
	for k in sides:
		var a0 := TAU * k / sides
		var a1 := TAU * (k + 1) / sides
		var o0 := _ring_dir(a0) * outer
		var o1 := _ring_dir(a1) * outer
		var i0 := _ring_dir(a0) * inner
		var i1 := _ring_dir(a1) * inner
		var shade := 0.85 + 0.15 * (0.5 + 0.5 * nz.get_noise_2d(k * 4.0, y0 * 10.0))
		var top := STONE_LIGHT * shade
		var side := STONE_LIGHT.lerp(STONE_DARK, 0.45) * shade
		var up := Vector3(0, y1, 0)
		var dn := Vector3(0, y0, 0)
		part.tri(o0 + up, o1 + up, i0 + up, top, top, top)
		part.tri(o1 + up, i1 + up, i0 + up, top, top, top)
		part.tri(o0 + dn, o1 + dn, o0 + up, side, side, side)
		part.tri(o1 + dn, o1 + up, o0 + up, side, side, side)
		part.tri(i0 + dn, i0 + up, i1 + dn, side, side, side)
		part.tri(i1 + dn, i0 + up, i1 + up, side, side, side)

func _diya(part: Part, at: Vector3) -> void:
	var clay := Color(0.62, 0.3, 0.16)
	var flame := Color(1.0, 0.78, 0.3)
	for k in 6:
		var a0 := TAU * k / 6.0
		var a1 := TAU * (k + 1) / 6.0
		var b0 := at + _ring_dir(a0) * 0.06
		var b1 := at + _ring_dir(a1) * 0.06
		var t0 := at + _ring_dir(a0) * 0.1 + Vector3(0, 0.05, 0)
		var t1 := at + _ring_dir(a1) * 0.1 + Vector3(0, 0.05, 0)
		part.tri(b0, t0, b1, clay, clay, clay)
		part.tri(b1, t0, t1, clay, clay, clay)
		part.tri(t0, at + Vector3(0, 0.03, 0), t1, clay * 0.7, clay * 0.7, clay * 0.7)
	part.tri(at + Vector3(-0.015, 0.04, 0), at + Vector3(0, 0.12, 0), at + Vector3(0.015, 0.04, 0), flame, flame, flame)
	part.tri(at + Vector3(0, 0.04, -0.015), at + Vector3(0, 0.12, 0), at + Vector3(0, 0.04, 0.015), flame, flame, flame)

# ---------------------------------------------------------------- ground and path samples (preview only)

## A 24 m round patch of ground with a ragged edge: warm earth showing through
## grass, in broad soft patches. Preview only — the Meadow's own ground and
## path materials are unchanged in B0.
func _ground_sample() -> ArrayMesh:
	var nz := _noise(8101, 0.12)
	var fine := _noise(8102, 0.6)
	var ground := Part.new(mats["earth"], true)
	var grass := Color(0.32, 0.47, 0.2)
	var earth := Color(0.56, 0.42, 0.27)
	var rings := 12
	var sides := 48
	var pts: Array = [[Vector3.ZERO]]
	for r in range(1, rings + 1):
		var ring: Array = []
		for s in sides:
			var a := TAU * s / sides
			var edge := 1.0 if r < rings else 0.9 + 0.1 * nz.get_noise_2d(cos(a) * 30.0, sin(a) * 30.0)
			ring.append(_ring_dir(a) * r * edge)
		pts.append(ring)
	var col := func(p: Vector3) -> Color:
		var m := clampf(0.5 + 0.9 * nz.get_noise_2d(p.x, p.z) + 0.2 * fine.get_noise_2d(p.x, p.z), 0.0, 1.0)
		return grass.lerp(earth, m * m)
	for s in sides:
		var a: Vector3 = pts[1][s]
		var b: Vector3 = pts[1][(s + 1) % sides]
		ground.tri(Vector3.ZERO, a, b, col.call(Vector3.ZERO), col.call(a), col.call(b))
	for r in range(1, rings):
		for s in sides:
			var a: Vector3 = pts[r][s]
			var b: Vector3 = pts[r][(s + 1) % sides]
			var c: Vector3 = pts[r + 1][s]
			var d: Vector3 = pts[r + 1][(s + 1) % sides]
			ground.tri(a, c, b, col.call(a), col.call(c), col.call(b))
			ground.tri(b, c, d, col.call(b), col.call(c), col.call(d))
	return _build([ground])

## A winding packed-earth path, ochre in the middle and darker at its soft,
## uneven edges, laid a centimetre above the ground sample.
func _path_sample() -> ArrayMesh:
	var nz := _noise(8201, 0.35)
	var path := Part.new(mats["earth"], true)
	var ctrl := [Vector3(-11, 0, 6), Vector3(-7, 0, 3.5), Vector3(-3, 0, 4.5), Vector3(1, 0, 1.5), Vector3(4.5, 0, -1.5),
		Vector3(8, 0, -1.0), Vector3(11, 0, -3.5)]
	var centre := Color(0.72, 0.55, 0.34)
	var edge := Color(0.55, 0.39, 0.24)
	var steps := 48
	var rows: Array = []
	for i in steps + 1:
		var t := float(i) / steps * (ctrl.size() - 1)
		var seg := mini(int(t), ctrl.size() - 2)
		var f := t - seg
		var p0: Vector3 = ctrl[maxi(seg - 1, 0)]
		var p1: Vector3 = ctrl[seg]
		var p2: Vector3 = ctrl[seg + 1]
		var p3: Vector3 = ctrl[mini(seg + 2, ctrl.size() - 1)]
		var c := _catmull(p0, p1, p2, p3, f)
		var c2 := _catmull(p0, p1, p2, p3, minf(f + 0.01, 1.0)) if f < 0.99 else c + (p2 - p1).normalized() * 0.01
		var dir := (c2 - c).normalized()
		var side := Vector3(-dir.z, 0, dir.x)
		var w := 0.8 + 0.18 * nz.get_noise_1d(i * 3.0)
		var y := Vector3(0, 0.012, 0)
		rows.append([c - side * (w + 0.25 + 0.1 * nz.get_noise_1d(i * 5.0)) + y, c - side * w * 0.55 + y, c + side * w * 0.55 + y,
			c + side * (w + 0.25 + 0.1 * nz.get_noise_1d(i * 5.0 + 50.0)) + y])
	for i in steps:
		var a: Array = rows[i]
		var b: Array = rows[i + 1]
		var cols := [edge, centre, centre, edge]
		for k in 3:
			path.tri(a[k], b[k], a[k + 1], cols[k], cols[k], cols[k + 1])
			path.tri(a[k + 1], b[k], b[k + 1], cols[k + 1], cols[k], cols[k + 1])
	return _build([path])

func _catmull(p0: Vector3, p1: Vector3, p2: Vector3, p3: Vector3, t: float) -> Vector3:
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t3)
