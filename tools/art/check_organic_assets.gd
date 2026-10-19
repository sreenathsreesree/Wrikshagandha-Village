extends SceneTree

## Stage B0 organic art checks in real Godot (D-60), run by
## tools/art/run_organic_checks.sh. Measures the actual meshes the prop scenes
## show — every MeshInstance3D's surfaces, through its node transform, in the
## prop's own space — never the generator's parameters:
##   mode=bounds  [report=<json>]  triangle counts against the budgets; the
##                exact reach (distance from the prop's vertical axis) of the
##                geometry in each height band, found by clipping every
##                triangle to the band: the root band (y <= 0.15 m) and the low
##                band (0.15 m up to the canopy limit, all geometry, so a low
##                branch or a drooping leaf counts); the lowest point and the
##                reach of the foliage; total reach and height.
##   mode=colliders out=<json>      each prop's collision facts as Godot builds
##                them (shape type and size, the collision node's transform,
##                the body's layer and mask) — run here and in the baseline tree
##                and compared by the shell script.
##   mode=hash dir=<dir> out=<json> a canonical content hash of every mesh
##                resource in dir (per surface: primitive, material, the vertex,
##                normal, colour and index arrays, the AABB).
##   mode=pond    the Living Pond Edge's meshes (W1, D-63), measured: the
##                shore's inner line lies inside the water's rim, its lip stays
##                above the water's highest wave out past the rim, every vertex
##                that shows earth or wetness stands above the path patches,
##                the earth weight is 0 from 5.0 m out, all normals point up, all
##                its triangles face the same way (up); the stones and the
##                ground cover use the shared rock and grass materials; the
##                three stay inside their triangle budgets.
## The limits live here and nowhere else. Prints ORGANIC_CHECK PASS|FAIL lines.

const ROOT_BAND_TOP := 0.15
const FOLIAGE_MATERIALS := ["res://assets/organic/materials/organic_foliage.tres", "res://assets/organic/materials/organic_grass.tres",
	"res://assets/organic/materials/organic_foliage_landmark.tres"]
const MESH_DIR := "res://assets/organic/meshes"

## kind tree: low_allow = the existing collider radius + 0.05 m (the low band's
## reach limit), low_top = the placeholder's canopy bottom (the low band's top
## and the foliage's lowest allowed point), root_reach, canopy_r (the layout's
## clearance radius). kind body: reach and height limits (the placeholder's).
## Budgets (B0.1, developer-approved): 2,000 triangles per ordinary tree, 400
## per rock, 12,000 for the Great Tree; bush and grass unchanged.
const PROPS := {
	"res://scenes/world/props/TreeRound.tscn": {"kind": "tree", "budget": 2000, "low_allow": 0.25, "low_top": 1.2, "root_reach": 0.6, "canopy_r": 1.5},
	"res://scenes/world/props/TreeTall.tscn": {"kind": "tree", "budget": 2000, "low_allow": 0.21, "low_top": 1.2, "root_reach": 0.5, "canopy_r": 1.2},
	"res://scenes/world/props/TreeWide.tscn": {"kind": "tree", "budget": 2000, "low_allow": 0.29, "low_top": 1.1, "root_reach": 0.7, "canopy_r": 1.8},
	"res://scenes/world/props/Rock.tscn": {"kind": "body", "budget": 400, "reach": 0.6, "height": 0.6},
	"res://scenes/world/props/Bush.tscn": {"kind": "body", "budget": 600, "reach": 0.5, "height": 0.7},
	"res://scenes/world/props/GrassClump.tscn": {"kind": "body", "budget": 60, "reach": 0.4, "height": 0.45},
	"res://scenes/dev/organic_preview/GreatTree.tscn": {"kind": "landmark", "budget": 12000},
}
## Meshes shown only in the preview (budget only; rock_b keeps rock A's limits).
const PREVIEW_MESHES := {
	"rock_b": {"budget": 400, "reach": 0.6, "height": 0.6},
}

var args := {}
var failures := 0

func _initialize() -> void:
	for arg in OS.get_cmdline_user_args():
		var at := arg.find("=")
		if at > 0:
			args[arg.left(at)] = arg.substr(at + 1)
	match str(args.get("mode", "")):
		"bounds":
			_bounds()
		"colliders":
			_colliders()
		"hash":
			_hashes()
		"pond":
			_pond()
		_:
			check(false, "mode", str(args.get("mode", "")))
	quit(1 if failures > 0 else 0)

func check(ok: bool, what: String, detail := "") -> void:
	if ok:
		print("ORGANIC_CHECK PASS %s %s" % [what, detail])
	else:
		failures += 1
		print("ORGANIC_CHECK FAIL %s %s" % [what, detail])

# ---------------------------------------------------------------- geometry

## Triangles of a node tree in the root's space: [[a, b, c, is_foliage], ...].
func _triangles(root: Node) -> Array:
	var out: Array = []
	for node in [root] + root.find_children("*", "MeshInstance3D", true, false):
		if not node is MeshInstance3D:
			continue
		var mi: MeshInstance3D = node
		if mi.mesh == null:
			continue
		var xf := _to_root(mi, root)
		for s in mi.mesh.get_surface_count():
			var mat := mi.get_active_material(s)
			var foliage := mat != null and FOLIAGE_MATERIALS.has(mat.resource_path)
			out.append_array(_surface_triangles(mi.mesh, s, xf, foliage))
	return out

func _surface_triangles(mesh: Mesh, s: int, xf: Transform3D, foliage: bool) -> Array:
	var out: Array = []
	var arrays := mesh.surface_get_arrays(s)
	var v: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
	var idx: PackedInt32Array = arrays[Mesh.ARRAY_INDEX] if arrays[Mesh.ARRAY_INDEX] != null else PackedInt32Array()
	var n := idx.size() if idx.size() > 0 else v.size()
	for t in range(0, n, 3):
		var ia := idx[t] if idx.size() > 0 else t
		var ib := idx[t + 1] if idx.size() > 0 else t + 1
		var ic := idx[t + 2] if idx.size() > 0 else t + 2
		out.append([xf * v[ia], xf * v[ib], xf * v[ic], foliage])
	return out

func _to_root(node: Node3D, root: Node) -> Transform3D:
	var xf := Transform3D.IDENTITY
	var n: Node = node
	while n != root and n != null:
		if n is Node3D:
			xf = (n as Node3D).transform * xf
		n = n.get_parent()
	return xf

## The part of a triangle with lo <= y <= hi (Sutherland–Hodgman on two planes).
func _clip(tri: Array, lo: float, hi: float) -> Array:
	var poly: Array = [tri[0], tri[1], tri[2]]
	poly = _clip_plane(poly, lo, true)
	poly = _clip_plane(poly, hi, false)
	return poly

func _clip_plane(poly: Array, y: float, keep_above: bool) -> Array:
	var out: Array = []
	for i in poly.size():
		var a: Vector3 = poly[i]
		var b: Vector3 = poly[(i + 1) % poly.size()]
		var ina := a.y >= y if keep_above else a.y <= y
		var inb := b.y >= y if keep_above else b.y <= y
		if ina:
			out.append(a)
		if ina != inb and absf(b.y - a.y) > 1e-9:
			out.append(a.lerp(b, (y - a.y) / (b.y - a.y)))
	return out

## Distance from the vertical axis is convex, so its maximum over a (clipped)
## polygon is at a corner — this is exact, not sampled.
func _reach(points: Array) -> float:
	var r := 0.0
	for p: Vector3 in points:
		r = maxf(r, Vector2(p.x, p.z).length())
	return r

func _measure(tris: Array, low_top: float) -> Dictionary:
	var m := {"triangles": tris.size(), "root_reach": 0.0, "low_reach": 0.0, "canopy_bottom": INF, "canopy_reach": 0.0,
		"reach": 0.0, "height": -INF, "bottom": INF}
	for tri: Array in tris:
		var pts := [tri[0], tri[1], tri[2]]
		m.reach = maxf(m.reach, _reach(pts))
		for p: Vector3 in pts:
			m.height = maxf(m.height, p.y)
			m.bottom = minf(m.bottom, p.y)
		m.root_reach = maxf(m.root_reach, _reach(_clip(tri, -INF, ROOT_BAND_TOP)))
		if low_top > ROOT_BAND_TOP:
			var low := _clip(tri, ROOT_BAND_TOP, low_top)
			# A sliver only touching the band's top edge is not geometry in the band.
			if low.size() >= 3:
				m.low_reach = maxf(m.low_reach, _reach(low))
		if tri[3]:
			m.canopy_reach = maxf(m.canopy_reach, _reach(pts))
			for p: Vector3 in pts:
				m.canopy_bottom = minf(m.canopy_bottom, p.y)
	return m

func _bounds() -> void:
	var report := {}
	for path: String in PROPS:
		var spec: Dictionary = PROPS[path]
		var packed: PackedScene = load(path)
		if packed == null:
			check(false, path, "does not load")
			continue
		var root := packed.instantiate()
		var tris := _triangles(root)
		var m := _measure(tris, float(spec.get("low_top", 0.0)))
		root.free()
		report[path] = m
		var tag := path.get_file().get_basename()
		check(m.triangles <= spec.budget and m.triangles > 0, tag + " triangles", "%d (budget %d)" % [m.triangles, spec.budget])
		match spec.kind:
			"tree":
				check(m.root_reach <= spec.root_reach, tag + " root band reach", "%.3f m (limit %.2f, y <= %.2f)" % [m.root_reach, spec.root_reach, ROOT_BAND_TOP])
				check(m.low_reach <= spec.low_allow, tag + " low band reach (trunk footprint)", "%.3f m (limit %.2f, %.2f < y < %.2f)" % [m.low_reach, spec.low_allow, ROOT_BAND_TOP, spec.low_top])
				check(m.canopy_bottom >= spec.low_top, tag + " canopy bottom", "%.3f m (at least %.2f)" % [m.canopy_bottom, spec.low_top])
				check(m.canopy_reach <= spec.canopy_r and m.reach <= spec.canopy_r, tag + " canopy reach", "%.3f m, overall %.3f (limit %.2f)" % [m.canopy_reach, m.reach, spec.canopy_r])
			"body":
				check(m.reach <= spec.reach, tag + " reach", "%.3f m (limit %.2f)" % [m.reach, spec.reach])
				check(m.height <= spec.height, tag + " height", "%.3f m (limit %.2f)" % [m.height, spec.height])
			"landmark":
				print("ORGANIC_CHECK INFO %s reach %.2f m, height %.2f m, canopy bottom %.2f m" % [tag, m.reach, m.height, m.canopy_bottom])
	for asset_name: String in PREVIEW_MESHES:
		var spec: Dictionary = PREVIEW_MESHES[asset_name]
		var mesh: Mesh = load(MESH_DIR.path_join(asset_name + ".res"))
		if mesh == null:
			check(false, asset_name, "does not load")
			continue
		var tris: Array = []
		for s in mesh.get_surface_count():
			tris.append_array(_surface_triangles(mesh, s, Transform3D.IDENTITY, false))
		var m := _measure(tris, 0.0)
		report[asset_name] = m
		check(m.triangles <= spec.budget and m.triangles > 0, asset_name + " triangles", "%d (budget %d)" % [m.triangles, spec.budget])
		if spec.has("reach"):
			check(m.reach <= spec.reach, asset_name + " reach", "%.3f m (limit %.2f)" % [m.reach, spec.reach])
			check(m.height <= spec.height, asset_name + " height", "%.3f m (limit %.2f)" % [m.height, spec.height])
	if args.has("report"):
		_write(str(args["report"]), JSON.stringify(_plain(report), "\t", true))

# ---------------------------------------------------------------- colliders

func _colliders() -> void:
	var out := {}
	for path: String in PROPS:
		if PROPS[path].kind == "landmark":
			continue
		var packed: PackedScene = load(path)
		var root := packed.instantiate()
		var facts := {"root_type": root.get_class(), "shapes": []}
		if root is CollisionObject3D:
			facts["layer"] = (root as CollisionObject3D).collision_layer
			facts["mask"] = (root as CollisionObject3D).collision_mask
		for node in root.find_children("*", "CollisionShape3D", true, false):
			var cs: CollisionShape3D = node
			var shape := {"node": str(root.get_path_to(cs)), "transform": str(cs.transform), "disabled": cs.disabled,
				"type": cs.shape.get_class() if cs.shape != null else "none"}
			for prop in ["radius", "height", "size"]:
				if cs.shape != null and prop in cs.shape:
					shape[prop] = str(cs.shape.get(prop))
			facts.shapes.append(shape)
		root.free()
		out[path] = facts
	_write(str(args["out"]), JSON.stringify(out, "\t", true))
	print("ORGANIC_CHECK INFO colliders written for %d props" % out.size())

# ---------------------------------------------------------------- content hashes

func _hashes() -> void:
	var dir := str(args["dir"])
	var out := {}
	var files := DirAccess.get_files_at(dir)
	var names: Array = []
	for f in files:
		if f.ends_with(".res"):
			names.append(f)
	names.sort()
	for f: String in names:
		var mesh: ArrayMesh = ResourceLoader.load(dir.path_join(f), "", ResourceLoader.CACHE_MODE_IGNORE)
		if mesh == null:
			check(false, "hash " + f, "does not load")
			continue
		var ctx := HashingContext.new()
		ctx.start(HashingContext.HASH_SHA256)
		ctx.update(var_to_bytes([mesh.get_surface_count(), mesh.get_aabb()]))
		for s in mesh.get_surface_count():
			var mat := mesh.surface_get_material(s)
			var arrays := mesh.surface_get_arrays(s)
			ctx.update(var_to_bytes([mesh.surface_get_primitive_type(s), mat.resource_path if mat != null else ""]))
			for a in [Mesh.ARRAY_VERTEX, Mesh.ARRAY_NORMAL, Mesh.ARRAY_COLOR, Mesh.ARRAY_INDEX]:
				ctx.update(var_to_bytes(arrays[a]))
		out[f] = ctx.finish().hex_encode()
	_write(str(args["out"]), JSON.stringify(out, "\t", true))
	print("ORGANIC_CHECK INFO content hashes for %d meshes" % out.size())

## The pond's water (PondWater.tscn: radius 3.6 m, top 0.05 m, wave at most
## 0.025 m) and the path patches' highest point (0.03 m); the budgets.
const POND_WATER_RADIUS := 3.6
const POND_WATER_HIGHEST := 0.075
const POND_PATH_TOP := 0.03
const POND_BUDGETS := {"pond_shore.res": 3000, "pond_stones.res": 3000, "pond_ground_cover.res": 1200}
const POND_MATERIALS := {"pond_shore.res": "res://assets/organic/materials/pond_shore.tres",
	"pond_stones.res": "res://assets/organic/materials/organic_rock.tres", "pond_ground_cover.res": "res://assets/organic/materials/organic_grass.tres"}

func _pond() -> void:
	for f: String in POND_BUDGETS:
		var mesh: ArrayMesh = load(MESH_DIR.path_join(f))
		if mesh == null:
			check(false, "pond " + f, "does not load")
			continue
		var tris := 0
		var mats_ok := true
		for si in mesh.get_surface_count():
			tris += mesh.surface_get_arrays(si)[Mesh.ARRAY_INDEX].size() / 3
			var mat := mesh.surface_get_material(si)
			mats_ok = mats_ok and mat != null and mat.resource_path == POND_MATERIALS[f]
		check(mesh.get_surface_count() == 1 and mats_ok, "pond %s material" % f, POND_MATERIALS[f])
		check(tris <= POND_BUDGETS[f], "pond %s triangles" % f, "%d (budget %d)" % [tris, POND_BUDGETS[f]])
	var shore: ArrayMesh = load(MESH_DIR.path_join("pond_shore.res"))
	if shore == null:
		return
	var a := shore.surface_get_arrays(0)
	var v: PackedVector3Array = a[Mesh.ARRAY_VERTEX]
	var n: PackedVector3Array = a[Mesh.ARRAY_NORMAL]
	var c: PackedColorArray = a[Mesh.ARRAY_COLOR]
	var idx: PackedInt32Array = a[Mesh.ARRAY_INDEX]
	var inner_min := INF
	var inner_max := 0.0
	var lip_low := INF          # the lowest point within 0.1 m past the water's rim
	var lip_reach := INF        # the smallest radius at which some direction already drops below the highest wave
	var bank_low := INF         # the lowest vertex that shows earth or wetness
	var earth_far := 0.0        # the largest radius with any earth
	var normals_up := true
	for i in v.size():
		var r := Vector2(v[i].x, v[i].z).length()
		if v[i].y < POND_WATER_HIGHEST + 0.005:
			lip_reach = minf(lip_reach, r)
		if r <= POND_WATER_RADIUS + 0.1:
			lip_low = minf(lip_low, v[i].y)
		if c[i].r > 0.0 or c[i].g > 0.0:
			bank_low = minf(bank_low, v[i].y)
		if c[i].r > 0.0:
			earth_far = maxf(earth_far, r)
		normals_up = normals_up and n[i].dot(Vector3.UP) > 0.999   # stored compressed, so not bit-exact
	# The inner line: the innermost vertex of each direction (the generator's first ring).
	var by_dir := {}
	for i in v.size():
		var key := snappedf(atan2(v[i].z, v[i].x), 0.001)
		var r2 := Vector2(v[i].x, v[i].z).length()
		by_dir[key] = minf(by_dir.get(key, INF), r2)
	for k in by_dir:
		inner_min = minf(inner_min, by_dir[k])
		inner_max = maxf(inner_max, by_dir[k])
	var down := 0
	var up := 0
	for t in range(0, idx.size(), 3):
		var fn: Vector3 = (v[idx[t + 1]] - v[idx[t]]).cross(v[idx[t + 2]] - v[idx[t]])
		if fn.y > 0.0:
			up += 1
		else:
			down += 1
	check(inner_min >= 3.0 and inner_max <= POND_WATER_RADIUS - 0.05, "pond shore inner line inside the rim",
		"%.3f–%.3f m (rim %.2f m)" % [inner_min, inner_max, POND_WATER_RADIUS])
	check(lip_low >= POND_WATER_HIGHEST + 0.005 and lip_reach > POND_WATER_RADIUS + 0.1, "pond shore lip above the water past its rim",
		"lowest %.3f m within %.2f m; first below the wave at %.3f m" % [lip_low, POND_WATER_RADIUS + 0.1, lip_reach])
	check(bank_low >= POND_PATH_TOP + 0.002, "pond shore bank above the path patches wherever it shows earth", "lowest %.3f m" % bank_low)
	check(earth_far < 5.0 + 0.001, "pond shore earth ends by 5.0 m", "%.3f m" % earth_far)
	check(normals_up, "pond shore normals all up")
	# Godot's front faces are clockwise seen from the front; seen from above that gives (b - a) x (c - a) pointing down.
	check(up == 0 and down == idx.size() / 3, "pond shore triangles all face up", "%d of %d" % [down, idx.size() / 3])

func _plain(v: Variant) -> Variant:
	if v is Dictionary:
		var d := {}
		for k in v:
			d[k] = _plain(v[k])
		return d
	if v is float:
		return snappedf(v, 0.0001) if is_finite(v) else str(v)
	return v

func _write(path: String, text: String) -> void:
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(text)
	f.close()
