#!/usr/bin/env python3
"""Vertical-slice layout (M07.1 plan, M07.2 placement) — a geometry check of
docs/VERTICAL_SLICE_LAYOUT.md against scenes/world/Meadow.tscn. Source only; nothing in the
game is run or changed.
The layout document carries one fenced ```slice-layout block (the machine-readable plan):
  digest <hex>                       the existing Meadow geometry the plan was drawn on
                                     (every node outside VerticalSlice — unchanged by M07.2)
  scene_digest <hex>                 the whole Meadow geometry, VerticalSlice included (M07.2)
  existing <NodeName> <x> <z>        an existing node the plan refers to
  house <cx> <cz> <width_x> <depth_z>   reserved exterior footprint (axis-aligned)
  door <x> <z>                       the house's entry point
  npc <x> <z>                        the reserved NPC spot
  forest <id> <x0> <z0> <x1> <z1>    a forest-edge zone (rectangle)
  trailhead <x> <z>                  where the path meets the forest edge
  path <id> <x>,<z> <x>,<z> ...      a planned path polyline
Checks:
1. Every `existing` coordinate still matches Meadow.tscn (node names are unique there).
2. The existing Meadow's geometry (every node outside `VerticalSlice`: position/rotation/
   scale, the camera bounds, the spawn entry) still hashes to the plan's `digest` — placing
   the slice moved or changed nothing that was there; the whole scene hashes to
   `scene_digest`, so any later scene change updates the plan deliberately.
3. Everything proposed lies inside the Meadow's camera bounds (64×64), 1 m in from the edge.
4. The house and NPC keep clear of existing solid objects (plots, the pond, trees, rocks,
   mounds, spawn points, …) by 1.5 m, of places' trigger zones by 0.5 m, and of small
   decoration by 0.3 m; forest-edge zones contain no existing object; planned paths keep
   0.8 m from solid objects and never enter the pond, a plot or the house (the player spawn is
   kept clear of the house and NPC but, being a point and not an object, not of paths — the
   existing path already starts beside it).
5. Connections: path "to_house" starts on the existing path and ends at the door; path
   "to_forest" starts at the door and ends at the trailhead, which touches a forest zone;
   the NPC stands 1.2–3 m from a planned path and within 4 m of the door; the door is on
   the house's edge.
6. Placement (M07.2) — the `VerticalSlice` node in Meadow.tscn matches the plan:
   - `House` instances HousePlaceholder.tscn at the footprint centre, unrotated, unscaled; its
     collision box and walls are the footprint; its DoorMarker sits on the door and faces out
     along the door's wall normal; the house is a StaticBody3D (so the navigation mesh baked
     from the navigation_source group avoids it) and carries no AreaEntry (the door's entry
     is M08.1's);
   - `NpcSpot` instances NpcSpotPlaceholder.tscn at the NPC spot — a marker only, with no
     collider (it never blocks the player or the navigation mesh);
   - every forest-edge tree (an existing tree prop) stands in a forest zone, inside the
     bounds, its canopy clear of every existing object, the house, the trailhead and the
     planned paths; along each zone the trees leave no gap wider than 5 m between trunks (ends included);
   - path patches (the existing path's mesh and material) are centred on their planned path
     and cover it end to end with no gap (every 0.25 m of the polyline lies inside a patch,
     the first metres of "to_house" inside the existing path), and none lies in the house.
"""
import hashlib, math, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()

# ---------------------------------------------------------------- the scene
SCENE = _src("scenes", "world", "Meadow.tscn")
EXT = {i: p.split("/")[-1] for p, i in re.findall(r'\[ext_resource type="PackedScene"[^\]]*path="res://([^"]+)" id="(\w+)"', SCENE)}
SOLID_R = {"TreeRound.tscn": 1.5, "TreeTall.tscn": 1.2, "TreeWide.tscn": 1.8, "Rock.tscn": 0.8, "Bush.tscn": 1.0, "FallenLog.tscn": 1.5,
           "MushroomCluster.tscn": 0.6, "UnusualFlowerPatch.tscn": 0.8, "Reed.tscn": 0.4, "LilyPad.tscn": 0.5, "DiscoverySpawnPoint.tscn": 1.0,
           "FarmPlot.tscn": 0.6, "TerracedMound.tscn": 4.5, "StoneMonolith.tscn": 1.2, "PondWater.tscn": 4.2, "GardenBloomFlowers.tscn": 0.6}
SOFT_R = {"GrassClump.tscn": 0.4, "GlowingMotes.tscn": 0.5, "Footprints.tscn": 0.5, "DriftingLeaf.tscn": 0.3, "Butterfly.tscn": 0.3}
MOVING = ("Wildlife", "Ambient", "EnvironmentalEvents", "WorldSimulation")   # actors that move or carry no footprint
SLICE = "VerticalSlice"
def in_slice(par, name): return par == SLICE or par.startswith(SLICE + "/") or (par == "." and name == SLICE)
NODES, OBJECTS, PATCHES, GEOM, BASE_GEOM, PLACED = {}, [], [], [], [], []
for m in re.finditer(r'^\[node name="([^"]+)"([^\]]*)\]\n(.*?)(?=^\[|\Z)', SCENE, re.M | re.S):
    name, attrs, body = m.groups()
    par = (re.search(r'parent="([^"]*)"', attrs) or [None, ""])[1]
    props = {k: v.strip() for k, v in re.findall(r"^(position|rotation|scale|size|entry_id|radius) = (.+)$", body, re.M)}
    row = f"{par}/{name}|" + "|".join(f"{k}={props[k]}" for k in sorted(props))
    GEOM.append(row)
    if in_slice(par, name):
        PLACED.append((name, par, attrs, body, props))
        continue
    BASE_GEOM.append(row)
    if "position" not in props:
        continue
    x, _, z = (float(v) for v in re.search(r"Vector3\(([^)]*)\)", props["position"]).group(1).split(","))
    NODES.setdefault(name, []).append((x, z))
    if par.startswith(MOVING):
        continue
    sc = float(re.search(r"Vector3\(([^,]*)", props["scale"]).group(1)) if "scale" in props else 1.0
    inst = re.search(r'instance=ExtResource\("(\w+)"\)', attrs)
    kind = EXT.get(inst.group(1)) if inst else None
    if par == "ExplorationLandmarks":
        OBJECTS.append((name, x, z, float(props["radius"]), "zone"))
    elif kind in SOLID_R:
        OBJECTS.append((name, x, z, SOLID_R[kind] * sc, "solid"))
    elif kind in SOFT_R:
        OBJECTS.append((name, x, z, SOFT_R[kind] * sc, "soft"))
    elif name == "PlayerSpawn":
        OBJECTS.append((name, x, z, 1.5, "spawn"))
    elif par == "Terrain/Path":
        sx, _, sz = (float(v) for v in re.search(r"Vector3\(([^)]*)\)", props["scale"]).group(1).split(","))
        PATCHES.append((name, x, z, sx, sz))
BOUNDS = re.search(r'\[node name="CameraBounds"[^\]]*\]\n(?:[^\[]*?)size = Vector2\(([^,]+), ([^)]+)\)', SCENE)
HALF_X, HALF_Z = float(BOUNDS.group(1)) / 2, float(BOUNDS.group(2)) / 2
DIGEST = hashlib.sha256("\n".join(BASE_GEOM).encode()).hexdigest()[:16]
SCENE_DIGEST = hashlib.sha256("\n".join(GEOM).encode()).hexdigest()[:16]

# ---------------------------------------------------------------- the plan
DOC = _src("docs", "VERTICAL_SLICE_LAYOUT.md")
BLOCK = re.findall(r"^```slice-layout\n(.*?)^```", DOC, re.M | re.S)
assert len(BLOCK) == 1, "the layout document has exactly one slice-layout block"
plan = {"existing": {}, "forest": {}, "path": {}}
for line in BLOCK[0].splitlines():
    line = line.split("#")[0].split()
    if not line: continue
    k, a = line[0], line[1:]
    if k == "digest": plan["digest"] = a[0]
    elif k == "scene_digest": plan["scene_digest"] = a[0]
    elif k == "existing": plan["existing"][a[0]] = (float(a[1]), float(a[2]))
    elif k in ("house",): plan[k] = tuple(float(v) for v in a)
    elif k in ("door", "npc", "trailhead"): plan[k] = (float(a[0]), float(a[1]))
    elif k == "forest": plan["forest"][a[0]] = tuple(float(v) for v in a[1:])
    elif k == "path": plan["path"][a[0]] = [tuple(float(c) for c in p.split(",")) for p in a[1:]]
    else: raise AssertionError(f"unknown layout line: {k}")

# ---------------------------------------------------------------- 1-2. existing world
for name, (x, z) in plan["existing"].items():
    assert len(NODES.get(name, [])) == 1, f"the plan refers to {name}, which is not exactly one node in Meadow.tscn"
    assert NODES[name][0] == (x, z), f"{name} moved: plan {(x, z)} vs scene {NODES[name][0]}"
assert plan["digest"] == DIGEST, f"the existing Meadow geometry changed since the plan was drawn (plan {plan['digest']}, scene {DIGEST})"
assert plan.get("scene_digest") == SCENE_DIGEST, \
    f"Meadow.tscn changed since its placement was recorded (plan {plan.get('scene_digest')}, scene {SCENE_DIGEST}) — update the plan deliberately"

# ---------------------------------------------------------------- geometry helpers
def seg_dist(px, pz, a, b):
    (ax, az), (bx, bz) = a, b
    dx, dz = bx - ax, bz - az
    t = 0.0 if dx == dz == 0 else max(0.0, min(1.0, ((px - ax) * dx + (pz - az) * dz) / (dx * dx + dz * dz)))
    return math.hypot(px - (ax + t * dx), pz - (az + t * dz))
def rect_dist(px, pz, cx, cz, w, d):
    return math.hypot(max(abs(px - cx) - w / 2, 0.0), max(abs(pz - cz) - d / 2, 0.0))
def path_dist(px, pz, pts): return min(seg_dist(px, pz, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
def inside(x, z, margin=1.0): return abs(x) <= HALF_X - margin and abs(z) <= HALF_Z - margin
NEED = {"solid": 1.5, "zone": 0.5, "soft": 0.3, "spawn": 1.5}   # the spawn is a point the player appears at: kept clear, but a path may start beside it
def on_existing_path(x, z): return any(math.hypot((x - px) / sx, (z - pz) / sz) <= 1.0 + 0.5 / min(sx, sz) for _, px, pz, sx, sz in PATCHES)

# ---------------------------------------------------------------- 3. inside the bounds
cx, cz, w, d = plan["house"]
corners = [(cx + sx * w / 2, cz + sz * d / 2) for sx in (-1, 1) for sz in (-1, 1)]
points = corners + [plan["door"], plan["npc"], plan["trailhead"]] + [p for pts in plan["path"].values() for p in pts] \
    + [(f[0], f[1]) for f in plan["forest"].values()] + [(f[2], f[3]) for f in plan["forest"].values()]
assert all(inside(x, z) for x, z in points), "everything proposed lies inside the 64×64 bounds, 1 m in from the edge"

# ---------------------------------------------------------------- 4. no collisions
clear = {}
for n, x, z, r, k in OBJECTS:
    m = rect_dist(x, z, cx, cz, w, d) - r - NEED[k]
    assert m >= 0, f"the house footprint is too close to {n} ({k}, short by {-m:.2f} m)"
    clear.setdefault("house", []).append(m)
    m2 = math.hypot(x - plan["npc"][0], z - plan["npc"][1]) - 0.5 - r - NEED[k]
    assert m2 >= 0, f"the NPC spot is too close to {n} ({k}, short by {-m2:.2f} m)"
    clear.setdefault("npc", []).append(m2)
    for fid, (x0, z0, x1, z1) in plan["forest"].items():
        fx, fz, fw, fd = (x0 + x1) / 2, (z0 + z1) / 2, abs(x1 - x0), abs(z1 - z0)
        assert rect_dist(x, z, fx, fz, fw, fd) - r >= 0.5, f"forest zone {fid} contains or touches {n}"
    if k == "solid":
        for pid, pts in plan["path"].items():
            m3 = path_dist(x, z, pts) - r - 0.8
            assert m3 >= 0, f"path {pid} runs too close to {n} (short by {-m3:.2f} m)"
            clear.setdefault("paths", []).append(m3)
for fid, (x0, z0, x1, z1) in plan["forest"].items():
    fx, fz, fw, fd = (x0 + x1) / 2, (z0 + z1) / 2, abs(x1 - x0), abs(z1 - z0)
    assert all(rect_dist(px, pz, fx, fz, fw, fd) >= 1.0 for px, pz in corners), f"forest zone {fid} overlaps the house"
for pid, pts in plan["path"].items():
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        steps = max(2, int(math.dist(a, b) / 0.25))
        for s in range(steps + 1):
            px, pz = a[0] + (b[0] - a[0]) * s / steps, a[1] + (b[1] - a[1]) * s / steps
            assert rect_dist(px, pz, cx, cz, w, d) >= 0.4 or math.dist((px, pz), plan["door"]) <= 1.2, f"path {pid} cuts through the house"

# ---------------------------------------------------------------- 5. connections
th, tf = plan["path"]["to_house"], plan["path"]["to_forest"]
assert set(plan["path"]) == {"to_house", "to_forest"}, "two planned paths"
assert on_existing_path(*th[0]), "to_house starts on the existing path"
assert math.dist(th[-1], plan["door"]) <= 1.0 and math.dist(tf[0], plan["door"]) <= 1.0, "both paths meet at the door"
assert math.dist(tf[-1], plan["trailhead"]) <= 1.0, "to_forest ends at the trailhead"
assert min(rect_dist(*plan["trailhead"], (f[0] + f[2]) / 2, (f[1] + f[3]) / 2, abs(f[2] - f[0]), abs(f[3] - f[1])) for f in plan["forest"].values()) <= 2.0, \
    "the trailhead touches the forest edge"
npc_path = min(path_dist(*plan["npc"], pts) for pts in plan["path"].values())
assert 1.2 <= npc_path <= 3.0 and math.dist(plan["npc"], plan["door"]) <= 4.0, f"the NPC stands beside the path ({npc_path:.2f} m) near the door"
assert abs(rect_dist(*plan["door"], cx, cz, w, d)) <= 0.05 and (abs(abs(plan["door"][0] - cx) - w / 2) <= 0.05 or abs(abs(plan["door"][1] - cz) - d / 2) <= 0.05), \
    "the door is on the house's edge"
length = sum(math.dist(p[i], p[i + 1]) for p in plan["path"].values() for i in range(len(p) - 1))

# ---------------------------------------------------------------- 6. placement (M07.2)
def vec(props, key, default=(0.0, 0.0, 0.0)):
    return tuple(float(v) for v in re.search(r"Vector3\(([^)]*)\)", props[key]).group(1).split(",")) if key in props else default
def scene_nodes(rel):
    txt = _src(*rel.split("/"))
    return txt, [(m.group(1), (re.search(r'type="(\w+)"', m.group(2)) or [None, None])[1], (re.search(r'parent="([^"]*)"', m.group(2)) or [None, None])[1],
                  {k: v.strip() for k, v in re.findall(r"^(\w[\w/]*) = (.+)$", m.group(3), re.M)})
                 for m in re.finditer(r'^\[node name="([^"]+)"([^\]]*)\]\n(.*?)(?=^\[|\Z)', txt, re.M | re.S)]
def inst_of(attrs):
    m = re.search(r'instance=ExtResource\("(\w+)"\)', attrs); return EXT.get(m.group(1)) if m else None
placed = {name: (par, attrs, body, props) for name, par, attrs, body, props in PLACED}
assert len(placed) == len(PLACED), "VerticalSlice node names are unique"
root = placed.get(SLICE)
assert root and root[0] == "." and not set(root[3]) & {"position", "rotation", "scale"}, "VerticalSlice sits directly under the Meadow, at the origin, unrotated"
# the house
par, attrs, body, props = placed["House"]
assert par == SLICE and inst_of(attrs) == "HousePlaceholder.tscn", "House instances HousePlaceholder.tscn"
assert vec(props, "position") == (cx, 0.0, cz) and not re.search(r"^(rotation|rotation_degrees|scale|transform) = ", body, re.M), "the house sits on the footprint, unrotated, unscaled"
htxt, hnodes = scene_nodes("scenes/world/props/HousePlaceholder.tscn")
hroot = hnodes[0]
assert hroot[1] == "StaticBody3D" and "script" not in hroot[3], "the house is a plain StaticBody3D (an obstacle the navigation bake sees)"
def sub(id_, key): return re.search(rf'\[sub_resource type="\w+" id="{id_}"\]\n(?:[^\[]*?){key} = Vector3\(([^)]*)\)', htxt).group(1)
hcol = next(n for n in hnodes if n[1] == "CollisionShape3D")
bx, by, bz = (float(v) for v in sub(re.search(r'SubResource\("(\w+)"\)', hcol[3]["shape"]).group(1), "size").split(","))
assert (bx, bz) == (w, d) and vec(hcol[3], "position")[0::2] == (0.0, 0.0), f"the house collider is the footprint ({bx}×{bz})"
walls = next(n for n in hnodes if n[0] == "Walls")
wx, _, wz = (float(v) for v in sub(re.search(r'SubResource\("(\w+)"\)', walls[3]["mesh"]).group(1), "size").split(","))
assert (wx, wz) == (w, d) and vec(walls[3], "position")[0::2] == (0.0, 0.0), "the house walls are the footprint"
dm = next(n for n in hnodes if n[0] == "DoorMarker")
assert dm[1] == "Marker3D" and "script" not in dm[3], "the door is a plain marker — its AreaEntry is M08.1's"
dx_, _, dz_ = vec(dm[3], "position"); yaw = math.radians(vec(dm[3], "rotation_degrees")[1])
assert math.dist((cx + dx_, cz + dz_), plan["door"]) <= 1e-6, "the DoorMarker sits on the door"
fwd = (-math.sin(yaw), -math.cos(yaw))                                  # a Node3D's forward is -Z
out_n = (1.0, 0.0) if abs(abs(plan["door"][0] - cx) - w / 2) <= 0.05 else (0.0, 1.0)
out_n = tuple(c * (1 if (plan["door"][0] - cx) * out_n[0] + (plan["door"][1] - cz) * out_n[1] > 0 else -1) for c in out_n)
assert fwd[0] * out_n[0] + fwd[1] * out_n[1] > 0.999, f"the door faces out of its wall towards the path ({fwd} vs {out_n})"
assert "area_entry.gd" not in htxt and "ExtResource(\"entry\")" not in placed["House"][2], "no AreaEntry at the door before M08.1"
# the NPC spot
par, attrs, body, props = placed["NpcSpot"]
assert par == SLICE and inst_of(attrs) == "NpcSpotPlaceholder.tscn" and vec(props, "position")[0::2] == plan["npc"], "NpcSpot instances NpcSpotPlaceholder.tscn on the NPC spot"
ntxt, nnodes = scene_nodes("scenes/world/props/NpcSpotPlaceholder.tscn")
assert nnodes[0][1] == "Marker3D" and not re.search(r"Body3D|CollisionShape3D|Area3D|script = ", ntxt), "the NPC spot is a marker only — no collider, no behaviour"
# the forest edge
TREES = {"TreeRound.tscn", "TreeTall.tscn", "TreeWide.tscn"}
zones = {fid: ((x0 + x1) / 2, (z0 + z1) / 2, abs(x1 - x0), abs(z1 - z0)) for fid, (x0, z0, x1, z1) in plan["forest"].items()}
trees, tclear = [], []
for name, (par, attrs, body, props) in placed.items():
    kind = inst_of(attrs)
    if kind not in TREES: continue
    assert par == SLICE, f"{name}: forest trees sit directly under VerticalSlice"
    x, _, z = vec(props, "position"); r = SOLID_R[kind] * vec(props, "scale", (1.0, 1.0, 1.0))[0]
    zs = [fid for fid, zz in zones.items() if rect_dist(x, z, *zz) == 0.0]
    assert zs, f"{name} ({x}, {z}) stands outside the forest-edge zones"
    assert inside(x, z), f"{name} lies outside the bounds"
    for n, ox, oz, orr, k in OBJECTS:
        if k in ("solid", "spawn", "zone"):
            assert math.hypot(x - ox, z - oz) - r - orr >= 0, f"{name} overlaps {n}"
            tclear.append(math.hypot(x - ox, z - oz) - r - orr)
    assert rect_dist(x, z, cx, cz, w, d) - r >= 0.3, f"{name} crowds the house"
    assert math.dist((x, z), plan["trailhead"]) - r >= 1.0, f"{name} blocks the trailhead"
    for pid, pts in plan["path"].items():
        assert path_dist(x, z, pts) - r >= 0.8, f"{name} stands on path {pid}"
    trees.append((name, x, z, r, zs))
for fid, (fx, fz, fw, fd) in zones.items():
    along = 0 if fw >= fd else 1
    lo, hi = (fx - fw / 2, fx + fw / 2) if along == 0 else (fz - fd / 2, fz + fd / 2)
    for oid, (ox, oz, ow, od) in zones.items():                         # an end another band already covers (the shared corner)
        o_lo, o_hi = (ox - ow / 2, ox + ow / 2) if along == 0 else (oz - od / 2, oz + od / 2)
        if oid != fid and o_lo <= lo < o_hi and (ow < od if along == 0 else ow > od):
            lo = o_hi
    pos = sorted([(t[1], t[2])[along] for t in trees if fid in t[4]])
    assert pos, f"forest zone {fid} has trees"
    gaps = [b - a for a, b in zip([lo] + pos, pos + [hi])]
    assert max(gaps) <= 5.0, f"forest zone {fid} has a {max(gaps):.2f} m gap (ends included)"
# the path patches
def in_patch(px, pz, x, z, sx, sz, yaw_deg):
    t = math.radians(yaw_deg); dx, dz = px - x, pz - z
    lx, lz = dx * math.cos(t) - dz * math.sin(t), dx * math.sin(t) + dz * math.cos(t)
    return (lx / sx) ** 2 + (lz / sz) ** 2 <= 1.0
PATCH_OF = {"HousePath": "to_house", "ForestPath": "to_forest"}
new_patches = []
for name, (par, attrs, body, props) in placed.items():
    if par != SLICE + "/Path": continue
    assert 'mesh = SubResource("CylinderMesh_path")' in body and 'surface_material_override/0 = SubResource("Material_path")' in body, f"{name} uses the existing path mesh"
    pid = PATCH_OF[re.match(r"[A-Za-z]+", name).group(0)]
    x, y, z = vec(props, "position"); sx, _, sz = vec(props, "scale"); yd = vec(props, "rotation_degrees")[1]
    assert y == 0.015 and path_dist(x, z, plan["path"][pid]) <= 0.1, f"{name} is centred on path {pid}"
    assert rect_dist(x, z, cx, cz, w, d) >= 0.4 or math.dist((x, z), plan["door"]) <= 1.2, f"{name} lies in the house"
    new_patches.append((pid, x, z, sx, sz, yd))
for pid, pts in plan["path"].items():
    covered_from = 0
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        steps = max(2, int(math.dist(a, b) / 0.25))
        for s_ in range(steps + 1):
            px, pz = a[0] + (b[0] - a[0]) * s_ / steps, a[1] + (b[1] - a[1]) * s_ / steps
            ok = any(in_patch(px, pz, x, z, sx, sz, yd) for q, x, z, sx, sz, yd in new_patches if q == pid) or on_existing_path(px, pz) \
                or math.dist((px, pz), plan["door"]) <= 1.2
            assert ok, f"path {pid} has a gap at ({px:.2f}, {pz:.2f})"
n_patches = {pid: sum(1 for p in new_patches if p[0] == pid) for pid in plan["path"]}

print(f"slice layout: {len(plan['existing'])} existing coordinates match Meadow.tscn; existing geometry digest {DIGEST} unchanged; scene digest {SCENE_DIGEST}; "
      f"bounds ±{HALF_X:g}×±{HALF_Z:g}; house {w:g}×{d:g} m at ({cx:g}, {cz:g}) clear by ≥{min(clear['house']):.2f} m, "
      f"NPC by ≥{min(clear['npc']):.2f} m, paths by ≥{min(clear['paths']):.2f} m; {len(plan['forest'])} forest zones empty; "
      f"{length:.1f} m of planned path from the existing path to the door and the trailhead; NPC {npc_path:.2f} m off the path")
print(f"placement: house {w:g}×{d:g} m StaticBody3D on the footprint, door marker on the door facing out, no AreaEntry; NPC marker without collider; "
      f"{len(trees)} forest-edge trees in their zones (canopies clear of existing objects by ≥{min(tclear):.2f} m, no gap > 5 m); "
      f"path patches {n_patches} cover both paths end to end")
print("ALL SLICE LAYOUT SIMULATIONS PASSED")
