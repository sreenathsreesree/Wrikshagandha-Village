extends SceneTree

## Organic art (Stage B0, refined in B0.1; D-60): builds the organic prop
## meshes once, offline, and saves them as resources the scenes reference —
## nothing is generated at runtime. Deterministic: every asset has a fixed seed
## (FastNoiseLite, RandomNumberGenerator and fixed direction sets only) and a
## fixed resource id, so a rerun writes byte-identical files.
##   godot --headless --path <project> -s res://tools/art/generate_organic_assets.gd [-- out=<dir>]
## out defaults to res://assets/organic/meshes; tools/art/run_organic_checks.sh
## regenerates into a temporary folder and compares with the committed meshes.
## Each mesh uses the shared materials in res://assets/organic/materials/.
##
## B0.1 techniques (all baked into the mesh, no runtime cost):
## - canopies: every clump's normals are bent towards one shared canopy
##   envelope, so a crown lights as one mass while its outline stays lumpy;
##   occlusion between clumps is baked into the vertex colour (rays from every
##   corner against the other clumps); small leaf clusters on the envelope break
##   the silhouette;
## - trunks: fluted, slightly twisted bark ridges with darker grooves and moss
##   at the base; two levels of branching; roots that curve down into the soil;
## - rocks: chiselled — each lump is cut by a few planes into flat facets, moss
##   on upward faces, darker where it meets the ground.
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
	for m in ["bark", "foliage", "foliage_landmark", "grass", "rock"]:
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
		"great_tree": _great_tree,
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
## normals of corners at the same position are averaged (trunks, branches);
## otherwise each triangle is flat (rocks, blades). Canopies give explicit
## normals (tri_n) — bent towards their envelope.
class Part:
	var material: Material
	var smooth: bool
	var verts := PackedVector3Array()
	var cols := PackedColorArray()
	var nrms := PackedVector3Array()
	func _init(m: Material, is_smooth: bool) -> void:
		material = m
		smooth = is_smooth
	func tri(a: Vector3, b: Vector3, c: Vector3, ca: Color, cb: Color, cc: Color) -> void:
		verts.append_array([a, b, c])
		cols.append_array([ca, cb, cc])
	func tri_n(a: Vector3, b: Vector3, c: Vector3, ca: Color, cb: Color, cc: Color, na: Vector3, nb: Vector3, nc: Vector3) -> void:
		verts.append_array([a, b, c])
		cols.append_array([ca, cb, cc])
		nrms.append_array([na, nb, nc])

## Merges parts that share a material into one surface each, computes normals,
## indexes identical corners, returns the mesh.
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
	if p.nrms.size() == p.verts.size():
		return p.nrms
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

func _ring_dir(angle: float) -> Vector3:
	return Vector3(cos(angle), 0.0, sin(angle))

func _shade(c: Color, k: float) -> Color:
	return Color(c.r * k, c.g * k, c.b * k, 1.0)

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

## A clump spec for _canopy.
func _clump(centre: Vector3, radii: Vector3, subdiv: int, deep: Color, sun: Color, yaw: float = 0.0, offset: float = 0.0,
		amp: float = 0.22, droop: float = 0.0, occluder: bool = true, normal_blend: float = -1.0) -> Dictionary:
	# normal_blend < 0: the canopy's own blend.
	return {"c": centre, "r": radii, "sub": subdiv, "deep": deep, "sun": sun, "yaw": yaw, "off": offset, "amp": amp,
		"droop": droop, "occluder": occluder, "nb": normal_blend}

## Fringe leaf clusters on a canopy envelope (golden spiral, deterministic):
## small clusters just inside the envelope surface, skipping its underside, so
## the silhouette breaks up; their normals follow the envelope almost fully, so
## they shade as part of the crown rather than as separate stickers.
func _fringe(env_c: Vector3, env_r: Vector3, count: int, size: float, min_rel_y: float, deep: Color, sun: Color, offset: float,
		max_reach: float = 1000.0, floor_y: float = -1000.0, subdiv: int = 0) -> Array:
	var out: Array = []
	var golden := PI * (3.0 - sqrt(5.0))
	for i in count * 3:
		if out.size() >= count:
			break
		var y := 1.0 - (i + 0.5) / (count * 3) * 2.0
		var r := sqrt(maxf(0.0, 1.0 - y * y))
		var dir := Vector3(cos(golden * i) * r, y, sin(golden * i) * r)
		if dir.y < min_rel_y:
			continue
		var s := size * (0.8 + 0.4 * fmod(i * 0.618, 1.0))
		var p := env_c + Vector3(dir.x * env_r.x, dir.y * env_r.y, dir.z * env_r.z) * 0.9
		if Vector2(p.x, p.z).length() + s * 1.3 > max_reach or p.y - s * 1.3 < floor_y:
			continue
		out.append(_clump(p, Vector3(s, s * 0.8, s), subdiv, deep, sun, i * 0.7, offset + i * 3.1, 0.25, 0.0, false, 0.88))
	return out

## Distance along a ray to an ellipsoid clump (-1 = no hit); a start inside it counts as a hit.
func _ray_clump(o: Vector3, d: Vector3, cl: Dictionary) -> float:
	var inv := Basis(Vector3.UP, cl.yaw).inverse()
	var r: Vector3 = cl.r
	var lo: Vector3 = inv * (o - (cl.c as Vector3))
	var ld: Vector3 = inv * d
	lo = Vector3(lo.x / r.x, lo.y / r.y, lo.z / r.z)
	ld = Vector3(ld.x / r.x, ld.y / r.y, ld.z / r.z)
	var a := ld.dot(ld)
	var b := 2.0 * lo.dot(ld)
	var c := lo.dot(lo) - 1.0
	var disc := b * b - 4.0 * a * c
	if disc < 0.0:
		return -1.0
	var s := sqrt(disc)
	var t1 := (-b - s) / (2.0 * a)
	var t2 := (-b + s) / (2.0 * a)
	if t1 > 0.001:
		return t1
	if t2 > 0.001:
		return t2
	return -1.0

## Ambient occlusion at a corner: 7 fixed rays over its hemisphere against the
## other clumps (1 = open, lower = enclosed by foliage).
func _occlusion(q: Vector3, n: Vector3, clumps: Array, self_index: int) -> float:
	var t := n.cross(Vector3.UP if absf(n.y) < 0.9 else Vector3.RIGHT).normalized()
	var b := n.cross(t)
	var dirs: Array = [n]
	for k in 6:
		var a := TAU * k / 6.0
		dirs.append((n * 0.6 + (t * cos(a) + b * sin(a)) * 0.8).normalized())
	var hits := 0
	for d: Vector3 in dirs:
		for j in clumps.size():
			if j == self_index or not clumps[j].occluder:
				continue
			if _ray_clump(q + n * 0.02, d, clumps[j]) > 0.0:
				hits += 1
				break
	return 1.0 - float(hits) / dirs.size()

## A canopy: every clump an icosphere displaced by two octaves of noise
## (optionally drooping at its rim), its normals bent towards the envelope
## ellipsoid by blend, its colour lit from the envelope's facing and darkened by
## the occlusion of the other clumps and by depth inside the envelope.
func _canopy(part: Part, clumps: Array, env_c: Vector3, env_r: Vector3, nz: FastNoiseLite, floor_y: float, blend: float) -> void:
	for i in clumps.size():
		var cl: Dictionary = clumps[i]
		var basis := Basis(Vector3.UP, cl.yaw)
		var r: Vector3 = cl.r
		var off: float = cl.off
		for tr: Array in _icosphere(cl.sub):
			var p: Array = []
			var n: Array = []
			var col: Array = []
			for u: Vector3 in tr:
				var k: float = 1.0 + cl.amp * (nz.get_noise_3d(u.x * 1.6 + off, u.y * 1.6, u.z * 1.6 - off)
					+ 0.5 * nz.get_noise_3d(u.x * 4.1 - off, u.y * 4.1 + off, u.z * 4.1))
				var local: Vector3 = Vector3(u.x * r.x, u.y * r.y, u.z * r.z) * k
				if cl.droop > 0.0:
					local.y -= cl.droop * (u.x * u.x + u.z * u.z) * (1.0 if u.y < 0.2 else 0.4)
				var q: Vector3 = (cl.c as Vector3) + basis * local
				q.y = maxf(q.y, floor_y)
				var own := (basis * Vector3(u.x / r.x, u.y / r.y, u.z / r.z)).normalized()
				var rel := q - env_c
				var en := Vector3(rel.x / (env_r.x * env_r.x), rel.y / (env_r.y * env_r.y), rel.z / (env_r.z * env_r.z)).normalized()
				var nn := own.lerp(en, blend if cl.nb < 0.0 else cl.nb).normalized()
				var ao := _occlusion(q, nn, clumps, i)
				var depth := clampf(Vector3(rel.x / env_r.x, rel.y / env_r.y, rel.z / env_r.z).length(), 0.0, 1.0)
				# The renderer lights the crown from its normals; the baked colour adds
				# only a gentle top-to-bottom shift and the occlusion, so the shadow
				# side is not darkened twice.
				var lit := clampf(0.5 + 0.5 * en.y + 0.12 * nz.get_noise_3d(q.x * 3.0, q.y * 3.0, q.z * 3.0), 0.0, 1.0)
				var c := (cl.deep as Color).lerp(cl.sun, 0.3 + 0.6 * lit)
				p.append(q)
				n.append(nn)
				col.append(_shade(c, (0.6 + 0.4 * ao) * (0.8 + 0.2 * depth)))
			part.tri_n(p[0], p[1], p[2], col[0], col[1], col[2], n[0], n[1], n[2])

## A tapered tube along points (trunks, branches, roots). flutes/depth/twist
## give bark ridges (darker in the grooves); aspect > 1 stretches the section
## vertically (buttress roots); moss tints the lowest 0.6 m on one side.
func _tube(part: Part, pts: Array, radii: Array, sides: int, noise: FastNoiseLite, base_col: Color, tip_col: Color,
		cap: bool = true, bark: float = 0.02, roll: float = 0.0, flutes: int = 0, depth: float = 0.0, twist: float = 0.0,
		aspect: float = 1.0, moss: float = 0.0) -> void:
	var rings: Array = []
	var shades: Array = []
	var nrm := Vector3.ZERO
	var moss_col := Color(0.3, 0.38, 0.17)
	for i in pts.size():
		var prev: Vector3 = pts[maxi(i - 1, 0)]
		var nxt: Vector3 = pts[mini(i + 1, pts.size() - 1)]
		var tan_v := (nxt - prev).normalized()
		if i == 0:
			if absf(tan_v.dot(Vector3.UP)) > 0.9:
				nrm = Vector3.FORWARD.cross(tan_v).normalized()
			else:
				nrm = (Vector3.UP - tan_v * Vector3.UP.dot(tan_v)).normalized()
		else:
			nrm = (nrm - tan_v * nrm.dot(tan_v)).normalized()
		var bin := tan_v.cross(nrm)
		var ring: Array = []
		var shade: Array = []
		var r: float = radii[i]
		var f := float(i) / maxf(pts.size() - 1, 1)
		for k in sides:
			var a := TAU * k / sides + roll
			var dir := nrm * cos(a) * aspect + bin * sin(a)
			var p: Vector3 = pts[i]
			var ridge := cos(flutes * a + twist * f * TAU) if flutes > 0 else 0.0
			var j := (1.0 + depth * ridge) * (1.0 + bark * noise.get_noise_3d(p.x * 6.0 + dir.x, p.y * 6.0, p.z * 6.0 + dir.z))
			var q := p + dir * r * j
			ring.append(q)
			var s := 0.92 + 0.16 * (0.5 + 0.5 * noise.get_noise_2d(k * 3.1, i * 2.3))
			if flutes > 0:
				s = 0.82 + 0.22 * (0.5 + 0.5 * ridge)
			var mossy := moss * clampf(1.0 - q.y / 0.6, 0.0, 1.0) * clampf(-dir.normalized().z + 0.3, 0.0, 1.0)
			shade.append([s, mossy])
		rings.append(ring)
		shades.append(shade)
	for i in pts.size() - 1:
		var c0 := base_col.lerp(tip_col, float(i) / (pts.size() - 1))
		var c1 := base_col.lerp(tip_col, float(i + 1) / (pts.size() - 1))
		for k in sides:
			var k1 := (k + 1) % sides
			var a: Vector3 = rings[i][k]
			var b: Vector3 = rings[i][k1]
			var c: Vector3 = rings[i + 1][k]
			var d: Vector3 = rings[i + 1][k1]
			var ca := _shade(c0.lerp(moss_col, shades[i][k][1]), shades[i][k][0])
			var cb := _shade(c0.lerp(moss_col, shades[i][k1][1]), shades[i][k1][0])
			var cc := _shade(c1.lerp(moss_col, shades[i + 1][k][1]), shades[i + 1][k][0])
			var cd := _shade(c1.lerp(moss_col, shades[i + 1][k1][1]), shades[i + 1][k1][0])
			part.tri(a, c, b, ca, cc, cb)
			part.tri(b, c, d, cb, cc, cd)
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

## A chiselled stone lump: an icosphere deformed by noise, then cut by a few
## planes into flat facets, never below the ground; flat-shaded with moss on
## upward faces and darker low faces.
func _stone(part: Part, centre: Vector3, radii: Vector3, subdiv: int, cuts: int, nz: FastNoiseLite, seed_value: int, yaw: float = 0.0) -> void:
	var rng := RandomNumberGenerator.new()
	rng.seed = seed_value
	var planes: Array = []
	for k in cuts:
		var a := rng.randf_range(0.0, TAU)
		var e := rng.randf_range(-0.2, 1.1)
		var pn := Vector3(cos(a) * cos(e), sin(e), sin(a) * cos(e)).normalized()
		planes.append([pn, rng.randf_range(0.72, 0.9)])
	var basis := Basis(Vector3.UP, yaw)
	for tr: Array in _icosphere(subdiv):
		var p: Array = []
		for u: Vector3 in tr:
			var k := 1.0 + 0.25 * nz.get_noise_3d(u.x * 1.3 + seed_value, u.y * 1.3, u.z * 1.3)
			var local := Vector3(u.x * radii.x, u.y * radii.y, u.z * radii.z) * k
			for pl: Array in planes:
				var pn: Vector3 = pl[0]
				var ext := Vector3(pn.x * radii.x, pn.y * radii.y, pn.z * radii.z).length()
				var over := local.dot(pn) - ext * float(pl[1])
				if over > 0.0:
					local -= pn * over
			var q := centre + basis * local
			q.y = maxf(q.y, 0.0)
			p.append(q)
		var fn := ((p[2] as Vector3) - (p[0] as Vector3)).cross((p[1] as Vector3) - (p[0] as Vector3))
		fn = fn.normalized() if fn.length() > 0.0 else Vector3.UP
		var mid: Vector3 = ((p[0] as Vector3) + (p[1] as Vector3) + (p[2] as Vector3)) / 3.0
		var base := STONE_MID.lerp(STONE_LIGHT, clampf(0.5 + 0.6 * nz.get_noise_3d(mid.x * 7.0, mid.y * 7.0, mid.z * 7.0), 0.0, 1.0))
		base = base.lerp(MOSS, clampf((fn.y - 0.55) * 1.8, 0.0, 0.75))
		var low := clampf(mid.y / 0.12, 0.0, 1.0)
		var c := _shade(base, (0.62 + 0.38 * low) * (0.78 + 0.22 * clampf(fn.y + 0.5, 0.0, 1.0)))
		part.tri(p[0], p[1], p[2], c, c, c)

# ---------------------------------------------------------------- palette

const BARK_DARK := Color(0.24, 0.16, 0.11)
const BARK_MID := Color(0.38, 0.26, 0.17)
const BARK_LIGHT := Color(0.52, 0.38, 0.26)
const BARK_PALE := Color(0.56, 0.47, 0.37)
const LEAF_DEEP := Color(0.09, 0.2, 0.08)
const LEAF_MID := Color(0.19, 0.35, 0.12)
const LEAF_SUN := Color(0.44, 0.56, 0.2)
const LEAF_FRESH := Color(0.45, 0.57, 0.21)
const LEAF_OLIVE := Color(0.36, 0.42, 0.17)
const STONE_DARK := Color(0.28, 0.25, 0.22)
const STONE_MID := Color(0.42, 0.38, 0.32)
const STONE_LIGHT := Color(0.55, 0.5, 0.42)
const MOSS := Color(0.34, 0.42, 0.2)

# ---------------------------------------------------------------- props

## Round tree (sal / mango-like): a fluted trunk with root flares, four
## branches each forking twice into a broad domed crown of six clumps and a
## fringe of small leaf clusters. Trunk collider r 0.2.
func _tree_round() -> ArrayMesh:
	var nz := _noise(1101, 0.9)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage"], true)
	_tube(bark, [Vector3(0, -0.05, 0), Vector3(0, 0.15, 0), Vector3(0.01, 0.6, 0), Vector3(0.02, 1.15, 0.01),
		Vector3(0.06, 1.6, 0.03), Vector3(0.1, 2.0, 0.02), Vector3(0.08, 2.35, -0.02)],
		[0.27, 0.205, 0.193, 0.18, 0.15, 0.12, 0.07], 9, nz, BARK_DARK, BARK_LIGHT, true, 0.02, 0.0, 5, 0.06, 0.15, 1.0, 0.8)
	for k in 5:
		var d := _ring_dir(TAU * k / 5.0 + 0.4)
		# Roots start inside the trunk and low, so above the root band they stay within the trunk's footprint.
		_tube(bark, [d * 0.08 + Vector3(0, 0.09, 0), d * 0.3 + Vector3(0, 0.05, 0), d * 0.44 + Vector3(0, 0.01, 0), d * 0.54 + Vector3(0, -0.06, 0)],
			[0.065, 0.05, 0.034, 0.02], 5, nz, BARK_DARK, BARK_MID, false)
	var crown := Vector3(0.05, 2.45, 0.0)
	var ends := [Vector3(0.55, 2.3, 0.4), Vector3(-0.55, 2.35, -0.25), Vector3(0.1, 2.25, -0.6), Vector3(0.5, 2.8, -0.35)]
	var starts := [1.45, 1.6, 1.75, 1.9]
	for b in ends.size():
		var start := Vector3(0.06, starts[b], 0.02)
		var end_p: Vector3 = ends[b]
		var mid := start.lerp(end_p, 0.5) + Vector3(0, 0.12, 0)
		_tube(bark, [start, mid, end_p], [0.075, 0.05, 0.03], 6, nz, BARK_MID, BARK_LIGHT)
		for s in [-1.0, 1.0]:
			var side: Vector3 = (end_p - start).cross(Vector3.UP).normalized() * s
			_tube(bark, [mid, mid + side * 0.32 + Vector3(0, 0.3, 0), mid + side * 0.5 + Vector3(0, 0.55, 0)], [0.035, 0.024, 0.014], 5, nz, BARK_MID, BARK_LIGHT)
	var clumps := [
		_clump(Vector3(0.05, 2.55, 0.0), Vector3(0.85, 0.62, 0.8), 2, LEAF_DEEP, LEAF_SUN, 0.0, 0.0),
		_clump(Vector3(0.45, 2.25, 0.35), Vector3(0.55, 0.42, 0.5), 1, LEAF_DEEP, LEAF_FRESH, 0.8, 7.0),
		_clump(Vector3(-0.5, 2.3, -0.2), Vector3(0.55, 0.45, 0.55), 1, LEAF_DEEP, LEAF_SUN, 1.6, 14.0),
		_clump(Vector3(0.1, 2.2, -0.55), Vector3(0.5, 0.38, 0.45), 1, LEAF_DEEP, LEAF_OLIVE, 2.4, 21.0),
		_clump(Vector3(-0.15, 2.95, 0.15), Vector3(0.55, 0.42, 0.52), 2, LEAF_MID, LEAF_FRESH, 3.2, 28.0),
		_clump(Vector3(0.5, 2.75, -0.3), Vector3(0.45, 0.36, 0.45), 1, LEAF_MID, LEAF_SUN, 4.0, 35.0)]
	clumps.append_array(_fringe(crown, Vector3(1.1, 0.78, 1.05), 14, 0.17, -0.35, LEAF_DEEP, LEAF_MID.lerp(LEAF_SUN, 0.6), 50.0, 1.45, 1.25))
	_canopy(leaves, clumps, crown, Vector3(1.1, 0.78, 1.05), nz, 1.25, 0.6)
	return _build([bark, leaves])

## Tall tree (ashoka-like): a slender fluted trunk under five drooping tiers
## narrowing upwards, the lower three split into two lobes, short branches
## reaching into each tier, small clusters hanging at the tier rims — a
## columnar silhouette, clearly unlike the round tree. Trunk collider r 0.16.
func _tree_tall() -> ArrayMesh:
	var nz := _noise(2203, 1.1)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage"], true)
	_tube(bark, [Vector3(0, -0.05, 0), Vector3(0, 0.15, 0), Vector3(0.005, 0.7, 0), Vector3(0.01, 1.15, 0),
		Vector3(0.03, 2.0, 0.01), Vector3(0.0, 3.0, 0.02), Vector3(-0.02, 3.95, 0.0)],
		[0.21, 0.165, 0.152, 0.142, 0.12, 0.09, 0.04], 7, nz, BARK_DARK, BARK_PALE, true, 0.02, 0.0, 4, 0.05, 0.1, 1.0, 0.6)
	for k in 4:
		var d := _ring_dir(TAU * k / 4.0 + 0.8)
		_tube(bark, [d * 0.1 + Vector3(0, 0.1, 0), d * 0.22 + Vector3(0, 0.06, 0), d * 0.34 + Vector3(0, 0.0, 0), d * 0.42 + Vector3(0, -0.06, 0)],
			[0.055, 0.04, 0.026, 0.015], 5, nz, BARK_DARK, BARK_MID, false)
	var tiers := [[1.98, 0.6, 0.4, 0.3], [2.48, 0.55, 0.38, 0.27], [2.98, 0.62, 0.36, 0.0], [3.43, 0.48, 0.32, 0.0], [3.86, 0.3, 0.28, 0.0]]
	var deep := Color(0.06, 0.16, 0.08)
	var clumps: Array = []
	for i in tiers.size():
		var t: Array = tiers[i]
		var split: float = t[3]
		var lobes := 2 if split > 0.0 else 1
		for l in lobes:
			var off := _ring_dir(i * 2.1 + l * PI) * (split if lobes == 2 else 0.05)
			var r: float = t[1] * (1.0 if l == 0 else 0.86)
			clumps.append(_clump(Vector3(off.x, t[0] - 0.06 * l, off.z), Vector3(r, t[2], r * 0.9), 1, deep,
				LEAF_MID.lerp(LEAF_SUN, 0.2 * i), i * 1.3 + l, i * 5.0 + l * 17.0, 0.22, 0.14))
		if i < 4:
			var d := _ring_dir(i * 1.9 + 0.5)
			var start := Vector3(0.01, t[0] - 0.35, 0.0)
			_tube(bark, [start, start + d * 0.25 + Vector3(0, 0.18, 0), start + d * 0.45 + Vector3(0, 0.3, 0)], [0.045, 0.03, 0.015], 5, nz, BARK_MID, BARK_LIGHT)
		if i < 3:
			for k in 3:
				var a := TAU * k / 3.0 + i * 0.9
				var rim: Vector3 = _ring_dir(a) * (t[1] * 0.92 + split * 0.4)
				clumps.append(_clump(Vector3(rim.x, t[0] - 0.22, rim.z), Vector3(0.14, 0.16, 0.14), 0, deep, LEAF_FRESH, a, i * 9.0 + k, 0.25, 0.0, false))
	_canopy(leaves, clumps, Vector3(0, 2.9, 0), Vector3(0.85, 1.3, 0.85), nz, 1.24, 0.45)
	return _build([bark, leaves])

## Wide tree (neem / banyan-like): a short thick fluted trunk with six root
## flares, five limbs spreading almost level and forking, a broad flat-topped
## layered crown with a fringe round its rim. Trunk collider r 0.24.
func _tree_wide() -> ArrayMesh:
	var nz := _noise(3307, 0.8)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage"], true)
	_tube(bark, [Vector3(0, -0.05, 0), Vector3(0, 0.15, 0), Vector3(0.01, 0.6, 0), Vector3(0.02, 1.05, 0.01),
		Vector3(0.05, 1.4, 0.02), Vector3(0.03, 1.65, 0.0)],
		[0.33, 0.25, 0.232, 0.22, 0.2, 0.15], 10, nz, BARK_DARK, BARK_LIGHT, true, 0.02, 0.0, 6, 0.07, 0.2, 1.0, 0.9)
	for k in 6:
		var d := _ring_dir(TAU * k / 6.0 + 0.2)
		# Roots start inside the trunk and low, so above the root band they stay within the trunk's footprint.
		_tube(bark, [d * 0.1 + Vector3(0, 0.09, 0), d * 0.38 + Vector3(0, 0.05, 0), d * 0.52 + Vector3(0, 0.01, 0), d * 0.62 + Vector3(0, -0.06, 0)],
			[0.07, 0.05, 0.034, 0.02], 5, nz, BARK_DARK, BARK_MID, false)
	var pads: Array = []
	for k in 5:
		var d := _ring_dir(TAU * k / 5.0 + 0.6)
		var start := Vector3(0.03, 1.36 + 0.04 * (k % 2), 0.01)
		var mid := start + d * 0.55 + Vector3(0, 0.2, 0)
		var end_p := start + d * 1.05 + Vector3(0, 0.42, 0)
		_tube(bark, [start, mid, end_p], [0.1, 0.07, 0.04], 6, nz, BARK_MID, BARK_LIGHT)
		for s in [-1.0, 1.0]:
			var side := d.rotated(Vector3.UP, 0.7 * s)
			_tube(bark, [mid, mid + side * 0.32 + Vector3(0, 0.2, 0), mid + side * 0.52 + Vector3(0, 0.36, 0)], [0.04, 0.026, 0.014], 5, nz, BARK_MID, BARK_LIGHT)
		pads.append(_clump(d * 0.98 + Vector3(0, 1.98 + 0.06 * (k % 2), 0), Vector3(0.58, 0.32, 0.54), 1, LEAF_DEEP,
			LEAF_MID.lerp(LEAF_SUN, 0.5 + 0.1 * (k % 3)), atan2(d.x, d.z), k * 3.0 + 11.0))
	var clumps := [_clump(Vector3(0, 2.18, 0), Vector3(1.0, 0.42, 0.95), 2, LEAF_DEEP, LEAF_SUN, 0.0, 0.0)]
	clumps.append_array(pads)
	clumps.append_array(_fringe(Vector3(0, 2.05, 0), Vector3(1.48, 0.5, 1.42), 16, 0.17, -0.2, LEAF_DEEP, LEAF_MID.lerp(LEAF_SUN, 0.6), 60.0, 1.75, 1.2))
	_canopy(leaves, clumps, Vector3(0, 2.05, 0), Vector3(1.48, 0.5, 1.42), nz, 1.2, 0.65)
	return _build([bark, leaves])

## Rock A: a chiselled boulder with a leaning side stone and three pebbles.
## Collider: sphere r 0.42 at (0.1, 0.28, 0.05).
func _rock_a() -> ArrayMesh:
	var nz := _noise(4409, 1.0)
	var stone := Part.new(mats["rock"], false)
	_stone(stone, Vector3(0.09, 0.2, 0.04), Vector3(0.38, 0.29, 0.34), 2, 5, nz, 11, 0.3)
	_stone(stone, Vector3(0.31, 0.1, 0.19), Vector3(0.16, 0.12, 0.15), 0, 2, nz, 12, 1.2)
	_stone(stone, Vector3(-0.28, 0.05, 0.2), Vector3(0.09, 0.07, 0.08), 0, 1, nz, 13, 2.0)
	_stone(stone, Vector3(-0.1, 0.04, -0.3), Vector3(0.07, 0.05, 0.07), 0, 1, nz, 14, 0.5)
	_stone(stone, Vector3(0.38, 0.03, -0.12), Vector3(0.06, 0.04, 0.06), 0, 1, nz, 15, 1.1)
	return _build([stone])

## Rock B: a low tilted slab with a leaning shard and two pebbles — a second
## silhouette (preview only until Stage A can place it in the Meadow).
func _rock_b() -> ArrayMesh:
	var nz := _noise(5501, 1.2)
	var stone := Part.new(mats["rock"], false)
	_stone(stone, Vector3(0.02, 0.14, 0.0), Vector3(0.45, 0.17, 0.31), 2, 4, nz, 21, 0.6)
	_stone(stone, Vector3(-0.18, 0.18, -0.2), Vector3(0.17, 0.2, 0.14), 0, 2, nz, 22, 2.2)
	_stone(stone, Vector3(0.3, 0.05, 0.2), Vector3(0.1, 0.06, 0.09), 0, 1, nz, 23, 1.0)
	_stone(stone, Vector3(-0.32, 0.04, 0.14), Vector3(0.07, 0.05, 0.06), 0, 1, nz, 24, 0.3)
	return _build([stone])

## Bush: five overlapping clumps lit as one rosette, fern-like fronds arching
## out at the base, a few small clusters on top. Collider: sphere r 0.38 at y 0.32.
func _bush() -> ArrayMesh:
	var nz := _noise(6607, 1.3)
	var leaves := Part.new(mats["foliage"], true)
	var fronds := Part.new(mats["foliage"], false)
	var deep := Color(0.06, 0.16, 0.07)
	var clumps := [
		_clump(Vector3(0, 0.3, 0), Vector3(0.3, 0.26, 0.29), 1, deep, LEAF_MID, 0.0, 0.0),
		_clump(Vector3(0.18, 0.22, 0.12), Vector3(0.19, 0.17, 0.18), 1, deep, LEAF_SUN, 0.7, 4.0),
		_clump(Vector3(-0.17, 0.2, -0.1), Vector3(0.19, 0.16, 0.18), 1, deep, LEAF_MID, 1.4, 8.0),
		_clump(Vector3(0.05, 0.45, -0.12), Vector3(0.16, 0.14, 0.15), 1, deep, LEAF_FRESH, 2.1, 12.0),
		_clump(Vector3(-0.08, 0.24, 0.2), Vector3(0.17, 0.15, 0.16), 1, deep, LEAF_OLIVE, 2.8, 16.0)]
	clumps.append_array(_fringe(Vector3(0, 0.32, 0), Vector3(0.36, 0.28, 0.35), 5, 0.07, 0.1, LEAF_DEEP, LEAF_MID.lerp(LEAF_SUN, 0.6), 30.0, 0.48, 0.0))
	_canopy(leaves, clumps, Vector3(0, 0.32, 0), Vector3(0.36, 0.28, 0.35), nz, 0.0, 0.5)
	for k in 8:
		var d := _ring_dir(TAU * k / 8.0 + 0.2)
		_blade(fronds, d * 0.05 + Vector3(0, 0.02, 0), d, 0.32 + 0.04 * (k % 3), 0.38, 0.09, 3, deep, LEAF_SUN.lerp(LEAF_MID, 0.4))
	return _build([leaves, fronds])

## Grass tuft: six bent, tapered, double-sided blades of mixed greens from one
## root — light enough to be scattered later with a MultiMesh. No collider.
func _grass_tuft() -> ArrayMesh:
	var blades := Part.new(mats["grass"], false)
	var rng := RandomNumberGenerator.new()
	rng.seed = 7703
	for k in 6:
		var a := TAU * k / 6.0 + rng.randf_range(-0.3, 0.3)
		var d := _ring_dir(a)
		var base := d * rng.randf_range(0.02, 0.07)
		var tip := Color(0.5, 0.64, 0.25).lerp(Color(0.68, 0.64, 0.32), rng.randf() * 0.5)
		_blade(blades, base, d, rng.randf_range(0.24, 0.4), rng.randf_range(0.08, 0.18), 0.05, 3, Color(0.2, 0.36, 0.12), tip)
	return _build([blades])

# ---------------------------------------------------------------- Great Tree (preview only)

## The Great Tree: an ancient sacred banyan-peepal at the heart of the village.
## One massive trunk whose deep twisting flutes read as many stems grown
## together, four stems spiralling out of it, eight buttress roots creeping
## over a round stepped stone katte, six great limbs forking into a broad,
## coherent, layered crown, curtains of aerial roots, and the kalava threads,
## cloth tags and clay diyas of a living shrine. Its canopy uses the landmark
## foliage material (able to thin near the player; off by default). Visual only:
## it lives in scenes/dev/ until Stage A places it.
func _great_tree() -> ArrayMesh:
	var nz := _noise(9001, 0.5)
	var bark := Part.new(mats["bark"], true)
	var leaves := Part.new(mats["foliage_landmark"], true)
	var stone := Part.new(mats["rock"], false)
	_platform_ring(stone, 4.0, 3.2, 0.0, 0.24, 36, nz)
	_platform_ring(stone, 3.45, 1.45, 0.24, 0.5, 36, nz)
	# The trunk: deep, twisting flutes — stems grown into one.
	_tube(bark, [Vector3(0, -0.1, 0), Vector3(0, 1.0, 0), Vector3(0.04, 2.0, 0.02), Vector3(0.08, 3.0, 0.05), Vector3(0.1, 4.0, 0.06),
		Vector3(0.12, 4.8, 0.05), Vector3(0.1, 5.4, 0.02)], [1.25, 1.06, 0.96, 0.88, 0.78, 0.66, 0.5], 24, nz, BARK_DARK, BARK_MID,
		true, 0.04, 0.0, 9, 0.22, 0.35, 1.0, 1.0)
	for k in 4:
		var a0 := TAU * k / 4.0 + 0.3
		var pts: Array = []
		var radii: Array = []
		for i in 6:
			var f := i / 5.0
			var a := a0 + f * 1.1
			var r := lerpf(1.0, 0.75, f)
			pts.append(Vector3(cos(a) * r, -0.1 + f * 4.6, sin(a) * r))
			radii.append(lerpf(0.38, 0.22, f))
		_tube(bark, pts, radii, 7, nz, BARK_DARK, BARK_LIGHT, false, 0.06, a0)
	# Buttress roots: tall fins spreading over the platform and down its edge.
	for k in 8:
		var d := _ring_dir(TAU * k / 8.0 + 0.2)
		_tube(bark, [d * 0.95 + Vector3(0, 1.0, 0), d * 1.7 + Vector3(0, 0.66, 0), d * 2.55 + Vector3(0, 0.56, 0), d * 3.2 + Vector3(0, 0.4, 0),
			d * 3.75 + Vector3(0, 0.12, 0), d * 4.1 + Vector3(0, -0.06, 0)], [0.36, 0.22, 0.15, 0.11, 0.07, 0.04], 8, nz, BARK_DARK, BARK_MID,
			false, 0.06, 0.0, 0, 0.0, 0.0, 2.2, 0.6)
	# Six great limbs, each forking twice more; pads of leaves at their ends.
	var clumps: Array = []
	for k in 6:
		var d := _ring_dir(TAU * k / 6.0 + 0.5)
		var h := 3.7 + 0.25 * (k % 3)
		var reach := 4.6 + 0.7 * ((k * 3) % 4)
		var p0 := Vector3(0, h, 0) + d * 0.5
		var p1 := Vector3(0, h + 0.7, 0) + d * reach * 0.32
		var p2 := Vector3(0, h + 1.3, 0) + d * reach * 0.64
		var p3 := Vector3(0, h + 1.7, 0) + d * reach * 0.94
		_tube(bark, [p0, p1, p2, p3], [0.5, 0.36, 0.24, 0.12], 8, nz, BARK_MID, BARK_LIGHT)
		for sgn in [-1.0, 1.0]:
			var side := d.rotated(Vector3.UP, 0.62 * sgn)
			var s1 := p1.lerp(p2, 0.6)
			var s2 := s1 + side * 1.4 + Vector3(0, 0.7, 0)
			var s3 := s1 + side * 2.4 + Vector3(0, 1.1, 0)
			_tube(bark, [s1, s2, s3], [0.16, 0.1, 0.05], 6, nz, BARK_MID, BARK_LIGHT)
			for t in [-1.0, 1.0]:
				var tw := side.rotated(Vector3.UP, 0.5 * t)
				_tube(bark, [s2, s2 + tw * 0.8 + Vector3(0, 0.6, 0)], [0.05, 0.02], 5, nz, BARK_MID, BARK_LIGHT)
		var yaw := atan2(d.x, d.z)
		# Each limb carries a layered cluster, not one pad: a main mass, two
		# shoulders either side, and a lumpy hanging lobe beneath, so from below
		# the crown reads as overlapping tiers instead of flat discs.
		var sun := LEAF_MID.lerp(LEAF_SUN, 0.5 + 0.1 * (k % 3))
		clumps.append(_clump(p3 + Vector3(0, 0.55, 0), Vector3(1.75, 0.85, 1.55), 2, LEAF_DEEP, sun, yaw, k * 4.0, 0.3))
		for sgn in [-1.0, 1.0]:
			var sh := p3 + d.rotated(Vector3.UP, 0.9 * sgn) * 1.1 + Vector3(0, 0.2 + 0.15 * sgn, 0) - d * 0.5
			clumps.append(_clump(sh, Vector3(1.1, 0.7, 1.0), 1, LEAF_DEEP, sun, yaw + sgn, k * 4.0 + 11.0 + sgn, 0.3))
		clumps.append(_clump(p3 + d * 0.3 + Vector3(0, -0.15, 0), Vector3(0.95, 0.6, 0.9), 1, LEAF_DEEP, LEAF_MID, yaw + 2.0, k * 4.0 + 17.0, 0.32, 0.2))
		var between := d.rotated(Vector3.UP, TAU / 12.0)
		clumps.append(_clump(between * 4.0 + Vector3(0, 7.2 + 0.2 * (k % 2), 0), Vector3(1.8, 0.8, 1.7), 1, LEAF_DEEP, LEAF_SUN, yaw + 0.5, k * 4.0 + 30.0, 0.3))
		# Aerial roots: curtains from three limbs to the ground; short strands from the others.
		if k % 2 == 0:
			for st in 4:
				var top := p1.lerp(p2, 0.25 + 0.2 * st) + Vector3(0, -0.2, 0)
				var foot := Vector3(top.x, 0.0, top.z) + d * 0.2
				var sway := d.rotated(Vector3.UP, 1.4) * (0.1 if st % 2 == 0 else -0.08)
				_tube(bark, [top, top.lerp(foot, 0.35) + sway, top.lerp(foot, 0.7) - sway, foot + Vector3(0, 0.25, 0), foot + Vector3(0, -0.05, 0)],
					[0.04, 0.05, 0.065, 0.09, 0.16], 5, nz, BARK_MID, BARK_DARK, false, 0.1)
		else:
			for st in 3:
				var top := p1.lerp(p2, 0.2 + 0.3 * st) + Vector3(0, -0.15, 0)
				var length := 1.3 + 0.5 * ((k + st) % 3)
				_tube(bark, [top, top + Vector3(0.05, -length * 0.5, 0.03), top + Vector3(0.02, -length, -0.02)], [0.045, 0.03, 0.015], 4, nz, BARK_MID, BARK_DARK, true, 0.1)
	clumps.append(_clump(Vector3(0, 7.7, 0), Vector3(3.0, 1.3, 2.9), 2, LEAF_DEEP, LEAF_SUN, 0.0, 0.0))
	for k in 4:
		var d := _ring_dir(TAU * k / 4.0 + 0.9)
		clumps.append(_clump(d * 1.9 + Vector3(0, 8.5, 0), Vector3(1.6, 0.65, 1.5), 1, LEAF_MID, LEAF_SUN, k * 0.7, k * 9.0 + 70.0))
	clumps.append_array(_fringe(Vector3(0, 7.0, 0), Vector3(7.0, 2.3, 6.6), 30, 0.55, -0.3, LEAF_DEEP, LEAF_MID.lerp(LEAF_SUN, 0.7), 120.0, 1000.0, -1000.0, 1))
	_canopy(leaves, clumps, Vector3(0, 7.0, 0), Vector3(7.0, 2.3, 6.6), nz, -1000.0, 0.6)
	# Kalava threads (red, saffron, red) and three cloth tags tied round the trunk.
	for i in 3:
		var y := 1.35 + 0.13 * i
		var col := Color(0.72, 0.1, 0.08) if i != 1 else Color(0.92, 0.62, 0.12)
		var pts: Array = []
		var radii: Array = []
		for s in 29:
			var a := TAU * s / 28.0
			pts.append(Vector3(cos(a) * 1.3, y + 0.03 * sin(a * 3.0), sin(a) * 1.3))
			radii.append(0.035)
		_tube(bark, pts, radii, 4, nz, col, col, false, 0.0)
	for k in 3:
		var d := _ring_dir(TAU * k / 3.0 + 0.4)
		var top := d * 1.32 + Vector3(0, 1.45, 0)
		var side := Vector3(-d.z, 0, d.x) * 0.06
		var cloth := Color(0.78, 0.16, 0.12) if k != 1 else Color(0.95, 0.7, 0.2)
		var low := top + d * 0.04 + Vector3(0, -0.35, 0)
		bark.tri(top - side, low - side, top + side, cloth, cloth, cloth)
		bark.tri(top + side, low - side, low + side, cloth, cloth, cloth)
		bark.tri(top - side, top + side, low - side, cloth, cloth, cloth)
		bark.tri(top + side, low + side, low - side, cloth, cloth, cloth)
	for k in 6:
		var d := _ring_dir(TAU * k / 6.0 + 0.1)
		_diya(bark, d * 2.5 + Vector3(0, 0.5, 0))
	return _build([bark, leaves, stone])

func _platform_ring(part: Part, outer: float, inner: float, y0: float, y1: float, sides: int, nz: FastNoiseLite) -> void:
	for k in sides:
		var a0 := TAU * k / sides
		var a1 := TAU * (k + 1) / sides
		var o0 := _ring_dir(a0) * outer
		var o1 := _ring_dir(a1) * outer
		var i0 := _ring_dir(a0) * inner
		var i1 := _ring_dir(a1) * inner
		# Stone blocks: three segments each, alternating shade, a darker seam line.
		var block := int(k / 3)
		var shade := (0.82 if block % 2 == 0 else 0.95) + 0.08 * nz.get_noise_2d(block * 4.0, y0 * 10.0)
		if k % 3 == 0:
			shade *= 0.86
		var top := _shade(STONE_LIGHT, shade)
		var side := _shade(STONE_LIGHT.lerp(STONE_DARK, 0.45), shade)
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
		var b0 := at + _ring_dir(a0) * 0.07
		var b1 := at + _ring_dir(a1) * 0.07
		var t0 := at + _ring_dir(a0) * 0.12 + Vector3(0, 0.06, 0)
		var t1 := at + _ring_dir(a1) * 0.12 + Vector3(0, 0.06, 0)
		part.tri(b0, t0, b1, clay, clay, clay)
		part.tri(b1, t0, t1, clay, clay, clay)
		part.tri(t0, at + Vector3(0, 0.035, 0), t1, _shade(clay, 0.7), _shade(clay, 0.7), _shade(clay, 0.7))
	part.tri(at + Vector3(-0.02, 0.05, 0), at + Vector3(0, 0.16, 0), at + Vector3(0.02, 0.05, 0), flame, flame, flame)
	part.tri(at + Vector3(0, 0.05, -0.02), at + Vector3(0, 0.16, 0), at + Vector3(0, 0.05, 0.02), flame, flame, flame)
