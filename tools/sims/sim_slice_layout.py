#!/usr/bin/env python3
"""Vertical-slice layout plan (M07.1) — a geometry check of docs/VERTICAL_SLICE_LAYOUT.md
against scenes/world/Meadow.tscn. Source only; nothing in the game is run or changed.
The layout document carries one fenced ```slice-layout block (the machine-readable plan):
  digest <hex>                       the Meadow geometry the plan was drawn on
  existing <NodeName> <x> <z>        an existing node the plan refers to
  house <cx> <cz> <width_x> <depth_z>   reserved exterior footprint (axis-aligned)
  door <x> <z>                       the house's entry point
  npc <x> <z>                        the reserved NPC spot
  forest <id> <x0> <z0> <x1> <z1>    a forest-edge zone (rectangle)
  trailhead <x> <z>                  where the path meets the forest edge
  path <id> <x>,<z> <x>,<z> ...      a planned path polyline
Checks:
1. Every `existing` coordinate still matches Meadow.tscn (node names are unique there).
2. The Meadow's geometry (every node's position/rotation/scale, the camera bounds, the
   spawn entry) hashes to the plan's `digest` — the existing world has not been modified;
   a deliberate scene change (M07.2+) must update the plan.
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
NODES, OBJECTS, PATCHES, GEOM = {}, [], [], []
for m in re.finditer(r'^\[node name="([^"]+)"([^\]]*)\]\n(.*?)(?=^\[|\Z)', SCENE, re.M | re.S):
    name, attrs, body = m.groups()
    par = (re.search(r'parent="([^"]*)"', attrs) or [None, ""])[1]
    props = {k: v.strip() for k, v in re.findall(r"^(position|rotation|scale|size|entry_id|radius) = (.+)$", body, re.M)}
    GEOM.append(f"{par}/{name}|" + "|".join(f"{k}={props[k]}" for k in sorted(props)))
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
DIGEST = hashlib.sha256("\n".join(GEOM).encode()).hexdigest()[:16]

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
assert plan["digest"] == DIGEST, f"Meadow.tscn geometry changed since the plan was drawn (plan {plan['digest']}, scene {DIGEST})"

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

print(f"slice layout: {len(plan['existing'])} existing coordinates match Meadow.tscn; geometry digest {DIGEST} unchanged; "
      f"bounds ±{HALF_X:g}×±{HALF_Z:g}; house {w:g}×{d:g} m at ({cx:g}, {cz:g}) clear by ≥{min(clear['house']):.2f} m, "
      f"NPC by ≥{min(clear['npc']):.2f} m, paths by ≥{min(clear['paths']):.2f} m; {len(plan['forest'])} forest zones empty; "
      f"{length:.1f} m of planned path from the existing path to the door and the trailhead; NPC {npc_path:.2f} m off the path")
print("ALL SLICE LAYOUT SIMULATIONS PASSED")
