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
## The limits live here and nowhere else. Prints ORGANIC_CHECK PASS|FAIL lines.

const ROOT_BAND_TOP := 0.15
const FOLIAGE_MATERIALS := ["res://assets/organic/materials/organic_foliage.tres", "res://assets/organic/materials/organic_grass.tres"]
const MESH_DIR := "res://assets/organic/meshes"

## kind tree: low_allow = the existing collider radius + 0.05 m (the low band's
## reach limit), low_top = the placeholder's canopy bottom (the low band's top
## and the foliage's lowest allowed point), root_reach, canopy_r (the layout's
## clearance radius). kind body: reach and height limits (the placeholder's).
const PROPS := {
	"res://scenes/world/props/TreeRound.tscn": {"kind": "tree", "budget": 1500, "low_allow": 0.25, "low_top": 1.2, "root_reach": 0.6, "canopy_r": 1.5},
	"res://scenes/world/props/TreeTall.tscn": {"kind": "tree", "budget": 1500, "low_allow": 0.21, "low_top": 1.2, "root_reach": 0.5, "canopy_r": 1.2},
	"res://scenes/world/props/TreeWide.tscn": {"kind": "tree", "budget": 1500, "low_allow": 0.29, "low_top": 1.1, "root_reach": 0.7, "canopy_r": 1.8},
	"res://scenes/world/props/Rock.tscn": {"kind": "body", "budget": 300, "reach": 0.6, "height": 0.6},
	"res://scenes/world/props/Bush.tscn": {"kind": "body", "budget": 600, "reach": 0.5, "height": 0.7},
	"res://scenes/world/props/GrassClump.tscn": {"kind": "body", "budget": 60, "reach": 0.4, "height": 0.45},
	"res://scenes/dev/organic_preview/GreatTree.tscn": {"kind": "landmark", "budget": 8000},
}
## Meshes shown only in the preview (budget only; rock_b keeps rock A's limits).
const PREVIEW_MESHES := {
	"rock_b": {"budget": 300, "reach": 0.6, "height": 0.6},
	"ground_sample": {"budget": 2000}, "path_sample": {"budget": 600},
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
