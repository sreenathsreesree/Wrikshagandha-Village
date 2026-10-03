#!/usr/bin/env python3
"""Home interior layout (M08.2) — a geometry check of scenes/world/HomeInterior.tscn and its
furniture scenes (scenes/world/props/home/). Source only; nothing in the game is run.
1. The room: the floor is 8 x 6 m at the origin; three full walls and a low camera-side (south)
   wall whose collider spans the side, above the capsule's step and under the tap snap height;
   the exit door and the entry inside it.
2. Furniture: every solid piece (a StaticBody3D prop) lies inside the room, overlaps no other,
   and its carving NavigationObstacle3D is exactly its collision footprint, at least as tall as
   its collider (so no furniture top bakes as a walkable island); flat pieces (the rug, the
   window light) have no collider; the window sits on a wall and its light patch on the floor.
3. Walkability (a 5 cm grid with the navigation agent's 0.35 m radius): from the entry the player
   reaches the exit door and every HomeSlot; the free floor is one connected area.
4. HomeSlots: exactly bed, chest, desk, hearth and shelves, each on reachable floor, 0.3-1.0 m
   from its furniture and facing it (within ~25 degrees).
5. Camera framing (the FollowCamera's arm, pitch, pivot, FOV and screen offset read from source,
   the area's distance from data/areas/home.tres, its focus bounds from the scene), at 16:9, 20:9
   and 4:3 landscape: from the entry the whole floor plan, every piece of furniture and the exit
   door are on screen; from every reachable spot the player stands inside the screen's safe band,
   no furniture hides the player from the camera; every slot, the entry and the exit door are
   tappable (from the entry and from where they are); floor hidden behind furniture stays under
   5 %; and a tap on any reachable floor spot never lands on the low wall's collider except low
   and near enough for InputManager's walkable snap (its constants read from
   source) — a full-height invisible collider swallowed taps on the south half of the room
   (found in M08.2); the collider is still taller than the player's capsule can step.
"""
import math, os, re, collections

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def vec(body, key):
    m = re.search(rf"^{key} = Vector3\(([^)]*)\)", body, re.M)
    return tuple(float(v) for v in m.group(1).split(",")) if m else None
def nodes_of(txt):
    return [(m.group(1), m.group(2), m.group(3)) for m in re.finditer(r'^\[node name="([^"]+)"([^\]]*)\]\n(.*?)(?=^\[|\Z)', txt, re.M | re.S)]

HOME = _src("scenes", "world", "HomeInterior.tscn")
EXT = dict((m.group(2), m.group(1)) for m in re.finditer(r'\[ext_resource type="\w+" path="res://([^"]+)" id="([^"]+)"\]', HOME))
NODES = nodes_of(HOME)
def node(name): return next(n for n in NODES if n[0] == name)

# ---------------------------------------------------------------- 1. the room
floor = re.search(r'id="BoxMesh_floor"\]\nsize = Vector3\(([^)]*)\)', HOME).group(1).replace(" ", "")
assert floor == "8,0.2,6", f"the floor is 8 x 6 m ({floor})"
X0, X1, Z0, Z1 = -4.0, 4.0, -3.0, 3.0
low = re.search(r'id="BoxMesh_wall_low"\]\nsize = Vector3\(([^)]*)\)', HOME).group(1).split(",")
assert float(low[1]) <= 0.5, "the camera-side wall is low"
south = re.search(r'id="BoxShape3D_wall_south"\]\nsize = Vector3\(([^)]*)\)', HOME)
SOUTH_W, SOUTH_H, SOUTH_D = (float(v) for v in south.group(1).split(",")) if south else (0, 0, 0)
spos = vec(node("SouthShape")[2], "position")
assert 'shape = SubResource("BoxShape3D_wall_south")' in node("SouthShape")[2] and spos == (0.0, SOUTH_H / 2, 3.1) and SOUTH_W >= 8.0, \
    "the low wall's collider spans the whole side from the floor"
IM = _src("scripts", "autoload", "input_manager.gd")
SNAP_H = float(re.search(r"^const WALKABLE_SNAP_HORIZONTAL := ([0-9.]+)", IM, re.M).group(1))
SNAP_V = float(re.search(r"^const WALKABLE_SNAP_VERTICAL := ([0-9.]+)", IM, re.M).group(1))
CAPSULE_R = float(re.search(r'\[sub_resource type="CapsuleShape3D"[^\]]*\]\nradius = ([0-9.]+)', _src("scenes", "player", "Player.tscn")).group(1))
assert CAPSULE_R + 0.15 <= SOUTH_H <= SNAP_V, \
    f"the low wall's collider stops the player's capsule (>= radius {CAPSULE_R} + 0.15 m, no step-up) and a tap that lands on it still snaps to the floor (<= {SNAP_V} m) ({SOUTH_H})"
SOUTH_BOX = ((-SOUTH_W / 2, 3.1 - SOUTH_D / 2, SOUTH_W / 2, 3.1 + SOUTH_D / 2), SOUTH_H)
ENTRY = vec(node("HomeDoorEntry")[2], "position"); DOOR = vec(node("ExitDoor")[2], "position")
assert X0 < ENTRY[0] < X1 and Z0 < ENTRY[2] < Z1 and Z0 < DOOR[2] < Z1, "entry and exit door inside the room"

# ---------------------------------------------------------------- 2. furniture
def rot_y(p, deg):
    a = math.radians(deg); c, s = round(math.cos(a), 9), round(math.sin(a), 9)
    return (p[0] * c + p[2] * s, p[1], -p[0] * s + p[2] * c)
def footprint(cx, cz, hx, hz, deg):
    pts = [rot_y((sx * hx, 0, sz * hz), deg) for sx in (-1, 1) for sz in (-1, 1)]
    xs, zs = [cx + p[0] for p in pts], [cz + p[2] for p in pts]
    return (min(xs), min(zs), max(xs), max(zs))
SOLIDS, FLATS, PROPS = {}, {}, {}
for name, attrs, body in NODES:
    if 'parent="Furniture"' not in attrs: continue
    path = EXT[re.search(r'instance=ExtResource\("([^"]+)"\)', attrs).group(1)]
    assert path.startswith("scenes/world/props/home/"), f"{name}: furniture comes from scenes/world/props/home/ ({path})"
    ptxt = _src(*path.split("/")); PROPS[name] = ptxt
    pos = vec(body, "position") or (0.0, 0.0, 0.0); rot = (vec(body, "rotation_degrees") or (0, 0, 0))[1]
    assert rot in (0.0, 90.0, -90.0, 180.0) and pos[1] == 0.0, f"{name}: on the floor, axis-aligned"
    assert "script" not in ptxt and "Area3D" not in ptxt, f"{name}: furniture has no script and nothing to interact with"
    root_type = re.search(r'^\[node name="[^"]+" type="(\w+)"\]', ptxt, re.M).group(1)
    if root_type == "StaticBody3D":
        shapes = re.findall(r'\[sub_resource type="BoxShape3D" id="(\w+)"\]\nsize = Vector3\(([^)]*)\)', ptxt)
        cols = [(s, b) for n, a, b in nodes_of(ptxt) if 'type="CollisionShape3D"' in a for s in [re.search(r'SubResource\("(\w+)"\)', b).group(1)]]
        assert len(cols) == 1 and len(shapes) == 1, f"{name}: one box collider"
        sx, sy, sz = (float(v) for v in shapes[0][1].split(","))
        cpos = vec(cols[0][1], "position")
        assert cpos[0] == 0 and cpos[2] == 0, f"{name}: collider centred on the prop"
        obs = [b for n, a, b in nodes_of(ptxt) if 'type="NavigationObstacle3D"' in a]
        assert len(obs) == 1 and "affect_navigation_mesh = true" in obs[0] and "carve_navigation_mesh = true" in obs[0] and "avoidance_enabled = false" in obs[0], \
            f"{name}: one carving NavigationObstacle3D (affect + carve, no avoidance)"
        verts = [float(v) for v in re.search(r"vertices = PackedVector3Array\(([^)]*)\)", obs[0]).group(1).split(",")]
        ox = sorted({round(abs(verts[i]), 4) for i in range(0, len(verts), 3)}); oz = sorted({round(abs(verts[i + 2]), 4) for i in range(0, len(verts), 3)})
        assert ox == [round(sx / 2, 4)] and oz == [round(sz / 2, 4)], f"{name}: the carve is exactly the collider's footprint ({ox}, {oz} vs {sx}x{sz})"
        oh = float(re.search(r"^height = ([0-9.]+)", obs[0], re.M).group(1))
        top = cpos[1] + sy / 2
        assert oh >= top, f"{name}: the carve ({oh} m) is at least as tall as the collider ({top} m)"
        fp = footprint(pos[0], pos[2], sx / 2, sz / 2, rot)
        assert fp[0] >= X0 - 1e-6 and fp[2] <= X1 + 1e-6 and fp[1] >= Z0 - 1e-6 and fp[3] <= Z1 + 1e-6, f"{name}: inside the room {fp}"
        SOLIDS[name] = (fp, top)
    else:
        assert "CollisionShape3D" not in ptxt and "Body3D" not in ptxt, f"{name}: a flat piece has no collider"
        FLATS[name] = (pos, rot)
names = sorted(SOLIDS)
for i, a in enumerate(names):
    for b in names[i + 1:]:
        A, B = SOLIDS[a][0], SOLIDS[b][0]
        assert A[2] <= B[0] + 1e-6 or B[2] <= A[0] + 1e-6 or A[3] <= B[1] + 1e-6 or B[3] <= A[1] + 1e-6, f"{a} overlaps {b}"
assert {"Bed", "Hearth", "Shelves", "Desk", "Chest"} <= set(SOLIDS) and {"Rug", "WindowLight"} <= set(FLATS), (sorted(SOLIDS), sorted(FLATS))
wpos, wrot = FLATS["WindowLight"]
assert abs(abs(wpos[0]) - 3.98) <= 0.03 or abs(wpos[2] + 2.98) <= 0.03, "the window sits on a wall"
patch = rot_y((0, 0, 1.0), wrot); px, pz = wpos[0] + patch[0], wpos[2] + patch[2]
assert X0 < px < X1 and Z0 < pz < Z1, "the window's light patch falls inside the room"
rpos, _ = FLATS["Rug"]
assert X0 + 1.4 <= rpos[0] <= X1 - 1.4 and Z0 + 0.9 <= rpos[2] <= Z1 - 0.9, "the rug lies on the open floor"

# ---------------------------------------------------------------- 3. walkability
R_AGENT, STEP = 0.35, 0.05
def free(x, z):
    if not (X0 + R_AGENT <= x <= X1 - R_AGENT and Z0 + R_AGENT <= z <= Z1 - R_AGENT): return False
    for fp, _ in SOLIDS.values():
        dx = max(fp[0] - x, 0, x - fp[2]); dz = max(fp[1] - z, 0, z - fp[3])
        if math.hypot(dx, dz) < R_AGENT: return False
    return True
nx, nz = int(round((X1 - X0) / STEP)), int(round((Z1 - Z0) / STEP))
def cell(x, z): return (int(round((x - X0) / STEP)), int(round((z - Z0) / STEP)))
def pos_of(c): return (X0 + c[0] * STEP, Z0 + c[1] * STEP)
FREE = {(i, j) for i in range(nx + 1) for j in range(nz + 1) if free(*pos_of((i, j)))}
start = cell(ENTRY[0], ENTRY[2]); assert start in FREE, "the entry stands on free floor"
seen, q = {start}, collections.deque([start])
while q:
    c = q.popleft()
    for d in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        n = (c[0] + d[0], c[1] + d[1])
        if n in FREE and n not in seen: seen.add(n); q.append(n)
assert seen == FREE, f"the free floor is one connected area ({len(seen)} of {len(FREE)} cells reached)"
door_reach = min(math.dist(pos_of(c), (DOOR[0], DOOR[2])) for c in seen)
assert door_reach <= 0.5, f"the exit door is reachable ({door_reach:.2f} m)"
free_area = len(FREE) * STEP * STEP

# ---------------------------------------------------------------- 4. home slots
SLOT_OF = {"bed": "Bed", "chest": "Chest", "desk": "Desk", "hearth": "Hearth", "shelves": "Shelves"}
slots = {}
for name, attrs, body in NODES:
    if 'parent="HomeSlots"' in attrs:
        assert 'script = ExtResource("slot")' in body and EXT["slot"] == "scripts/world/home_slot.gd", f"{name}: a HomeSlot"
        sid = re.search(r'^slot_id = "([^"]+)"', body, re.M).group(1)
        assert sid not in slots, f"duplicate slot {sid}"
        slots[sid] = (vec(body, "position"), (vec(body, "rotation_degrees") or (0, 0, 0))[1])
assert sorted(slots) == sorted(SLOT_OF), f"HomeSlots are exactly {sorted(SLOT_OF)} ({sorted(slots)})"
slot_report = {}
for sid, (p, ry) in slots.items():
    c = cell(p[0], p[2]); assert c in seen, f"slot {sid} stands on reachable floor"
    fp = SOLIDS[SLOT_OF[sid]][0]
    dx = max(fp[0] - p[0], 0, p[0] - fp[2]); dz = max(fp[1] - p[2], 0, p[2] - fp[3]); edge = math.hypot(dx, dz)
    assert 0.3 <= edge <= 1.0, f"slot {sid} is 0.3-1.0 m from its {SLOT_OF[sid]} ({edge:.2f} m)"
    fwd = rot_y((0, 0, -1), ry); to = ((fp[0] + fp[2]) / 2 - p[0], (fp[1] + fp[3]) / 2 - p[2]); n = math.hypot(*to)
    assert (fwd[0] * to[0] + fwd[2] * to[1]) / n > 0.9, f"slot {sid} faces its {SLOT_OF[sid]}"
    slot_report[sid] = round(edge, 2)

# ---------------------------------------------------------------- 5. camera framing
CAM_TSCN, CAM_GD = _src("scenes", "camera", "FollowCamera.tscn"), _src("scripts", "camera", "follow_camera.gd")
arm = re.search(r'\[node name="SpringArm3D"[^\]]*\]\n(.*?)\n\n', CAM_TSCN, re.S).group(1)
PIVOT = vec(arm, "position")[1]; PITCH = math.radians(-vec(arm, "rotation_degrees")[0])
FOV = math.radians(float(re.search(r"^@export var base_fov: float = ([0-9.]+)", CAM_GD, re.M).group(1)))
VOFF = float(re.search(r"^@export var screen_offset := Vector2\(([-0-9.]+), ([-0-9.]+)\)", CAM_GD, re.M).group(2))
L = float(re.search(r"^camera_distance = ([0-9.]+)", _src("data", "areas", "home.tres"), re.M).group(1))
cb = node("CameraBounds")[2]; bc = vec(cb, "position"); bs = [float(v) for v in re.search(r"size = Vector2\(([^)]*)\)", cb).group(1).split(",")]
BX0, BX1, BZ0, BZ1 = bc[0] - bs[0] / 2, bc[0] + bs[0] / 2, bc[2] - bs[1] / 2, bc[2] + bs[1] / 2
UP, FWD = (0.0, math.cos(PITCH), -math.sin(PITCH)), (0.0, -math.sin(PITCH), -math.cos(PITCH))
def camera_for(px, pz):
    fx, fz = min(max(px, BX0), BX1), min(max(pz, BZ0), BZ1)
    return (fx, PIVOT + L * math.sin(PITCH) + VOFF * UP[1], fz + L * math.cos(PITCH) + VOFF * UP[2])
def project(cam, p, aspect):
    d = (p[0] - cam[0], p[1] - cam[1], p[2] - cam[2])
    z = d[1] * FWD[1] + d[2] * FWD[2]; x = d[0]; y = d[1] * UP[1] + d[2] * UP[2]
    t = math.tan(FOV / 2)
    return (0.5 + x / (z * t * aspect) / 2, 0.5 - y / (z * t) / 2)
END = 0.98
def ray_hits_box(a, b, box, end=None):
    global END
    END = 0.98 if end is None else end
    (x0, z0, x1, z1), top = box
    lo, hi = (x0, 0.0, z0), (x1, top, z1); t0, t1 = 0.0, 1.0
    for k in range(3):
        d = b[k] - a[k]
        if abs(d) < 1e-12:
            if not (lo[k] <= a[k] <= hi[k]): return False
            continue
        u, v = (lo[k] - a[k]) / d, (hi[k] - a[k]) / d
        t0, t1 = max(t0, min(u, v)), min(t1, max(u, v))
        if t0 > t1: return False
    return t1 > 0.0 and t0 < END
def ray_entry(a, b, box):
    """Where the segment a -> b first enters the box, or None."""
    (x0, z0, x1, z1), top = box
    lo, hi = (x0, 0.0, z0), (x1, top, z1); t0, t1 = 0.0, 1.0
    for k in range(3):
        d = b[k] - a[k]
        if abs(d) < 1e-12:
            if not (lo[k] <= a[k] <= hi[k]): return None
            continue
        u, v = (lo[k] - a[k]) / d, (hi[k] - a[k]) / d
        t0, t1 = max(t0, min(u, v)), min(t1, max(u, v))
        if t0 > t1: return None
    if t0 >= 0.999: return None
    return tuple(a[k] + (b[k] - a[k]) * t0 for k in range(3))
snapped, behind = 0, {}
ASPECTS = {"16:9": 16 / 9, "20:9": 20 / 9, "4:3": 4 / 3}
SAFE_X, SAFE_Y = (0.06, 0.94), (0.10, 0.86)   # clear of the top bar and the bottom thumb zones' height
worst = {}
for label, aspect in ASPECTS.items():
    cam = camera_for(ENTRY[0], ENTRY[2])
    corners = [(x, 0.0, z) for x in (X0, X1) for z in (Z0, Z1)]
    for name, (fp, top) in SOLIDS.items():
        corners += [(x, y, z) for x in (fp[0], fp[2]) for z in (fp[1], fp[3]) for y in (0.0, top)]
    corners.append((DOOR[0], 0.0, DOOR[2]))
    for p in corners:
        sx, sy = project(cam, p, aspect)
        assert 0.0 <= sx <= 1.0 and 0.0 <= sy <= 1.0, f"{label}: from the entry, {p} is off screen ({sx:.2f}, {sy:.2f})"
    m = [1.0, 1.0, 0.0, 0.0]
    for c in seen:
        x, z = pos_of(c); cam = camera_for(x, z)
        for h in (0.0, 1.3):
            sx, sy = project(cam, (x, h, z), aspect)
            assert SAFE_X[0] <= sx <= SAFE_X[1] and SAFE_Y[0] <= sy <= SAFE_Y[1], f"{label}: the player at ({x:.2f}, {z:.2f}) leaves the safe band ({sx:.2f}, {sy:.2f})"
            m = [min(m[0], sx), min(m[1], sy), max(m[2], sx), max(m[3], sy)]
        for name, box in SOLIDS.items():
            assert not ray_hits_box(cam, (x, 0.9, z), box), f"{label}: {name} hides the player at ({x:.2f}, {z:.2f})"
        # a tap on this floor spot (seen from the entry, and from the spot itself) reaches the floor first
        for viewer in (camera_for(ENTRY[0], ENTRY[2]), cam):
            if any(ray_hits_box(viewer, (x, 0.0, z), box, 0.999) for box in SOLIDS.values()):
                behind.setdefault(label, set()).add(c)   # floor the furniture itself hides from the camera
            hit = ray_entry(viewer, (x, 0.0, z), SOUTH_BOX)
            if hit is not None:   # InputManager snaps a hit this low to the walkable floor nearby
                snapped += 1
                assert hit[1] <= SNAP_V and math.hypot(hit[0] - x, hit[2] - z) <= SNAP_H, \
                    f"{label}: a tap on ({x:.2f}, {z:.2f}) lands on the low wall's collider at {tuple(round(v, 2) for v in hit)}, too far to snap back to the floor"
    worst[label] = tuple(round(v, 2) for v in m)
    targets = {f"slot {sid}": (p[0], p[2]) for sid, (p, _) in slots.items()}
    targets["exit door"] = (DOOR[0], DOOR[2]); targets["entry"] = (ENTRY[0], ENTRY[2])
    for tname, (tx, tz) in targets.items():
        for viewer in (camera_for(ENTRY[0], ENTRY[2]), camera_for(tx, tz)):
            for name, box in SOLIDS.items():
                assert not ray_hits_box(viewer, (tx, 0.0, tz), box, 0.999), f"{label}: a tap on the {tname} hits {name}"
    share = len(behind.get(label, ())) / len(seen)
    assert share <= 0.05, f"{label}: {share:.1%} of the free floor is hidden behind furniture"
hidden_share = {k: "%.1f%%" % (100.0 * len(v) / len(seen)) for k, v in behind.items()}
print(f"home layout: room 8x6 m, low camera-side wall (collider {SOUTH_H:g} m: blocks the {CAPSULE_R} m capsule, taps on it snap to the floor); {len(SOLIDS)} solid pieces {sorted(SOLIDS)} inside, no overlaps, "
      f"carve = collider footprint and >= its height; flat {sorted(FLATS)}; free floor {free_area:.1f} m2, one connected area, exit door reachable")
print(f"home slots (edge distance m): {slot_report}; all reachable and facing their furniture")
print(f"camera: {L} m, pitch {math.degrees(PITCH):.0f}, focus bounds x[{BX0:g},{BX1:g}] z[{BZ0:g},{BZ1:g}]; from the entry the whole room, furniture and exit door on screen; "
      f"player screen extent over {len(seen)} reachable spots {worst}; never hidden by furniture; every slot, the entry and the exit door tappable; floor hidden behind furniture {hidden_share}; "
      f"{snapped} views land on the low wall's collider within snap range")
print("ALL HOME LAYOUT SIMULATIONS PASSED")
