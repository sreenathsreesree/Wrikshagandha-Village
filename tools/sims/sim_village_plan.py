#!/usr/bin/env python3
"""Village plan model (A0 — Village World Design Lock): checks the planned first-village coordinates against the
existing Meadow and the real camera, before any of it is built. A model only — it reads files, writes nothing and
changes no game behaviour; nothing it accepts is authorised for construction (Stage A waits for the Phase 16 gate).

Reads:
  - docs/VILLAGE_DESIGN_LOCK_A0.md — its one ```village-plan block (the planned coordinates);
  - scenes/world/Meadow.tscn — every existing object, through tools/sims/sim_slice_layout.py's own scene parsing
    (its "the scene" section, executed as written, so both models see the same radii and ground) — the objects it
    counts as the existing world plus the nodes placed since (the forest edge, hidden places, ...), with the same radii;
  - docs/VERTICAL_SLICE_LAYOUT.md — the planned "to_forest" path the village road leaves from, and the house;
  - scenes/camera/FollowCamera.tscn — the spring arm's height, pitch and length and the camera's field of view;
  - scripts/peaceful/rest_spot.gd — the seated distance and framing offset; project.godot — the canvas shape.
  The starting yaw of a sit (0) is assumed, not read.

Plan lines (# comments; a leading "provisional" marks an entry whose design is not locked — checked as a candidate):
  bounds <stage_a|target> x0 z0 x1 z1         the first stage's ground and the long-term target
  band <name> x0 z0 x1 z1                     an edge forest band (where the edge's trees will stand)
  tree <name> x z trunk <r> crown <reach> <bottom> <top> keepclear <r> katte <r>
  clearing <name> x z <radius>
  path <name> <width> <x,z> <x,z> ...         a planned path (the first must start on an existing planned path)
  threshold <name> <width> <x,z> <x,z>        a deliberate narrowing through an existing forest strip
  seat <name> x z yaw <x,y,z> [<x,y,z> ...]   a RestSpot (yaw recorded, not checked) and the subject points its
                                              seated view must frame at yaw 0
  reveal <tree> <metres south of the trunk>   by where, walking north, the crown must be in the frame (default arm)
  house <name> x z <width> <depth>            a placeholder house; its door is the middle of its south wall
  area <name> x z <radius>                    a later-stage place, checked only against the target bounds

Checks:
  1. bounds — Stage A contains the existing 64 × 64 m ground and lies inside the target; bands lie inside Stage A.
  2. Great Tree — its keep-clear circle and crown lie inside Stage A and clear of every band; its keep-clear circle
     is clear of every existing object and every clearing; every path's edge stays 0.3 m off its katte (paths may
     pass under the crown).
  3. paths — the first path starts on the planned "to_forest" path; every path edge keeps each existing object's
     layout radius (sim_slice_layout's radii) and the house footprint, and stays 1.5 m inside Stage A; a threshold
     instead keeps 0.8 m from the existing trunk colliders (the narrowing under the strip's canopies); paths join.
  4. clearings and houses — clear of existing objects (by their layout radii); clearings 1.5 m inside Stage A;
     houses 1.0 m from the clearings, 1.5 m from the bands and 0.8 m from the paths, each south door within 3 m of
     a path (houses are not checked against each other).
  5. seats — at the default seated view (the RestSpot preset, yaw 0) every subject point projects inside the frame
     with a 5 % margin; the seat's own frame bottom lies on Stage A ground; no planned crown lies between the camera
     and the seated player; each seat 0.5 m clear of trunk colliders and 0.8 m off every path. The seat's yaw (which
     way it faces) is not checked.
  6. reveal — walking north towards the tree at the default arm, the crown's underside reaches the frame top by the
     planned distance south of the trunk (reported if it already shows 4 m further south).
  7. later-stage areas — inside the target, outside the existing ground (not checked against Stage A's paths,
     houses or clearings).
Designs shown to break (they must each fail): A0 blueprint's straight road from the door (it crosses the house);
the Great Tree at A0's x = -52 with a 4 m west band; a seat whose subject is out of frame.
"""
import math, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()

# ---------------------------------------------------------------- the existing world (sim_slice_layout's own parsing)
_layout = _src("tools", "sims", "sim_slice_layout.py")
_scene = _layout[_layout.index("# ---------------------------------------------------------------- the scene"):
                 _layout.index("# ---------------------------------------------------------------- the plan")]
_ns = {"_src": _src, "os": os, "re": re, "math": math, "hashlib": __import__("hashlib")}
exec(_scene, _ns)
HALF_X, HALF_Z = _ns["HALF_X"], _ns["HALF_Z"]
SCENE, EXT = _ns["SCENE"], _ns["EXT"]
# sim_slice_layout's OBJECTS leave out the nodes added since the slice plan (its ADDED groups: the forest edge, the
# hidden places, the rest spot, ...); they are existing objects all the same, so they are added here with the same
# radii by kind (solid and soft), each placed node at its position and scale.
OBJECTS = list(_ns["OBJECTS"])
for _name, _par, _attrs, _body, _props in _ns["PLACED"]:
    _inst = re.search(r'instance=ExtResource\("(\w+)"\)', _attrs)
    _kind = EXT.get(_inst.group(1)) if _inst else None
    if "position" not in _props or _par.startswith(_ns["MOVING"]) or not (_kind in _ns["SOLID_R"] or _kind in _ns["SOFT_R"]):
        continue
    _x, _, _z = (float(v) for v in re.search(r"Vector3\(([^)]*)\)", _props["position"]).group(1).split(","))
    _sc = float(re.search(r"Vector3\(([^,]*)", _props["scale"]).group(1)) if "scale" in _props else 1.0
    if _kind in _ns["SOLID_R"]:
        OBJECTS.append((_name, _x, _z, _ns["SOLID_R"][_kind] * _sc, "solid"))
    else:
        OBJECTS.append((_name, _x, _z, _ns["SOFT_R"][_kind] * _sc, "soft"))
# Tree trunk colliders as built (B0: the placeholder colliders kept; radius = check_organic_assets low_allow - 0.05).
TRUNK_R = {"TreeRound.tscn": 0.20, "TreeTall.tscn": 0.16, "TreeWide.tscn": 0.24}
TRUNKS = []
for m in re.finditer(r'^\[node name="([^"]+)"([^\]]*)\]\n(.*?)(?=^\[|\Z)', SCENE, re.M | re.S):
    inst = re.search(r'instance=ExtResource\("(\w+)"\)', m.group(2))
    kind = EXT.get(inst.group(1)) if inst else None
    pos = re.search(r"^position = Vector3\(([^)]*)\)", m.group(3), re.M)
    if kind in TRUNK_R and pos:
        x, _, z = (float(v) for v in pos.group(1).split(","))
        sc = re.search(r"^scale = Vector3\(([^,]*)", m.group(3), re.M)
        TRUNKS.append((m.group(1), x, z, TRUNK_R[kind] * (float(sc.group(1)) if sc else 1.0)))
_slice = re.findall(r"^```slice-layout\n(.*?)^```", _src("docs", "VERTICAL_SLICE_LAYOUT.md"), re.M | re.S)[0]
TO_FOREST = [tuple(float(v) for v in p.split(",")) for p in re.search(r"^path to_forest (.*)$", _slice, re.M).group(1).split()]
hx, hz, hw, hd = (float(v) for v in re.search(r"^house (\S+) (\S+) (\S+) (\S+)$", _slice, re.M).groups())
HOUSE = (hx - hw / 2, hx + hw / 2, hz - hd / 2, hz + hd / 2)

# ---------------------------------------------------------------- the camera, read from its sources
_fc = _src("scenes", "camera", "FollowCamera.tscn")
PIVOT = float(re.search(r'\[node name="SpringArm3D"[^\]]*\]\nposition = Vector3\(0, ([0-9.]+), 0\)', _fc).group(1))
PITCH = float(re.search(r'\[node name="SpringArm3D"[^\]]*\]\n[^\[]*?rotation_degrees = Vector3\((-?[0-9.]+), 0, 0\)', _fc).group(1))
ARM = float(re.search(r"^spring_length = ([0-9.]+)", _fc, re.M).group(1))
FOV = float(re.search(r"^fov = ([0-9.]+)", _fc, re.M).group(1))           # vertical (Camera3D keeps height by default)
_rs = _src("scripts", "peaceful", "rest_spot.gd")
SEAT_ARM = float(re.search(r"var settle_distance: float = ([0-9.]+)", _rs).group(1))
SEAT_OFFSET = tuple(float(v) for v in re.search(r"var framing_offset := Vector2\(([^)]*)\)", _rs).group(1).split(","))
_pg = _src("project.godot")
ASPECT = float(re.search(r"^window/size/viewport_width=(\d+)", _pg, re.M).group(1)) / float(re.search(r"^window/size/viewport_height=(\d+)", _pg, re.M).group(1))

def rig(focus, yaw_deg, arm, offset=(0.0, 0.0)):
    """The camera's position and axes for a player at focus (x, z): FollowCamera at the player, rotated by yaw; the
    SpringArm3D at (0, PIVOT, 0) pitched by PITCH carries the Camera3D arm metres along its +Z; Camera3D's h/v_offset
    move it along its own X/Y (Godot adds them to the camera transform's origin)."""
    th = math.radians(PITCH)
    zax, yax, xax = (0.0, -math.sin(th), math.cos(th)), (0.0, math.cos(th), math.sin(th)), (1.0, 0.0, 0.0)
    cam = [arm * zax[i] + offset[0] * xax[i] + offset[1] * yax[i] for i in range(3)]
    cam[1] += PIVOT
    ps = math.radians(yaw_deg)
    def roty(p): return (p[0] * math.cos(ps) + p[2] * math.sin(ps), p[1], -p[0] * math.sin(ps) + p[2] * math.cos(ps))
    c = roty(cam)
    return (c[0] + focus[0], c[1], c[2] + focus[1]), roty(xax), roty(yax), roty(zax)

def project(pt, focus, yaw_deg, arm, offset=(0.0, 0.0)):
    """Normalised screen position (-1..1, +y up) of a world point, or None behind the camera."""
    c, x, y, z = rig(focus, yaw_deg, arm, offset)
    d = [pt[i] - c[i] for i in range(3)]
    xc, yc, zc = (sum(d[i] * a[i] for i in range(3)) for a in (x, y, z))
    if zc >= 0:
        return None
    f = 1.0 / math.tan(math.radians(FOV / 2))
    return (f * xc / -zc / ASPECT, f * yc / -zc)

def ground_hit(focus, yaw_deg, arm, offset, u, v):
    c, x, y, z = rig(focus, yaw_deg, arm, offset)
    t = math.tan(math.radians(FOV / 2))
    d = [-z[i] + u * t * ASPECT * x[i] + v * t * y[i] for i in range(3)]
    if d[1] >= 0:
        return None
    s = -c[1] / d[1]
    return (c[0] + s * d[0], c[2] + s * d[2])

# ---------------------------------------------------------------- geometry helpers
def seg_dist(p, a, b):
    dx, dz = b[0] - a[0], b[1] - a[1]
    t = max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dz) / (dx * dx + dz * dz)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dz)
def poly_dist(p, pts): return min(seg_dist(p, pts[i], pts[i + 1]) for i in range(len(pts) - 1))
def rect_poly_dist(r, pts):
    best = 9e9
    for i in range(len(pts) - 1):
        for k in range(201):
            t = k / 200
            q = (pts[i][0] + (pts[i + 1][0] - pts[i][0]) * t, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * t)
            best = min(best, math.hypot(max(r[0] - q[0], 0, q[0] - r[1]), max(r[2] - q[1], 0, q[1] - r[3])))
    return best
def circle_rect_gap(c, r, rect):   # distance from a circle's edge to a rectangle (negative = overlap)
    return math.hypot(max(rect[0] - c[0], 0, c[0] - rect[2]), max(rect[1] - c[1], 0, c[1] - rect[3])) - r
def inside_rect(p, rect, margin=0.0):
    return rect[0] + margin <= p[0] <= rect[2] - margin and rect[1] + margin <= p[1] <= rect[3] - margin

# ---------------------------------------------------------------- the plan
def parse(text):
    plan = {"bounds": {}, "band": {}, "tree": {}, "clearing": {}, "path": {}, "threshold": {}, "seat": {}, "reveal": {},
            "house": {}, "area": {}, "provisional": set()}
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line:
            continue
        w = line.split()
        prov = w[0] == "provisional"
        if prov:
            w = w[1:]
        k, name, a = w[0], w[1], w[2:]
        if prov:
            plan["provisional"].add((k, name))
        if k in ("bounds", "band"):
            plan[k][name] = tuple(float(v) for v in a)
        elif k == "tree":
            v = dict(zip(a[2::2], a[3::2]))
            crown = a[a.index("crown") + 1:a.index("crown") + 4]
            plan[k][name] = {"x": float(a[0]), "z": float(a[1]), "trunk": float(v["trunk"]), "crown": tuple(float(c) for c in crown),
                             "keepclear": float(a[a.index("keepclear") + 1]), "katte": float(a[a.index("katte") + 1])}
        elif k in ("clearing", "area"):
            plan[k][name] = (float(a[0]), float(a[1]), float(a[2]))
        elif k in ("path", "threshold"):
            plan[k][name] = (float(a[0]), [tuple(float(c) for c in p.split(",")) for p in a[1:]])
        elif k == "seat":
            plan[k][name] = (float(a[0]), float(a[1]), float(a[2]), [tuple(float(c) for c in p.split(",")) for p in a[3:]])
        elif k == "reveal":
            plan[k][name] = float(a[0])
        elif k == "house":
            plan[k][name] = tuple(float(v) for v in a)
        else:
            raise AssertionError(f"unknown plan line: {line}")
    return plan

def check(plan):
    """Every failed rule, as messages (empty = the plan holds); and the figures worth printing."""
    bad, info = [], []
    A, T = plan["bounds"]["stage_a"], plan["bounds"]["target"]
    ground = (-HALF_X, -HALF_Z, HALF_X, HALF_Z)
    # 1. bounds
    if not (A[0] <= ground[0] and A[1] <= ground[1] and A[2] >= ground[2] and A[3] >= ground[3]):
        bad.append(f"Stage A {A} must contain the existing ground {ground}")
    if not (T[0] <= A[0] and T[1] <= A[1] and T[2] >= A[2] and T[3] >= A[3]):
        bad.append(f"Stage A {A} must lie inside the target {T}")
    area = lambda r: (r[2] - r[0]) * (r[3] - r[1])
    info.append(f"Stage A {A[2]-A[0]:g} × {A[3]-A[1]:g} m = {area(A):g} m² ({area(A)/area(ground):.2f}× today's ground, "
                f"{area(A)/area(T):.0%} of the {T[2]-T[0]:g} × {T[3]-T[1]:g} m target)")
    for n, b in plan["band"].items():
        if not (A[0] <= b[0] and A[1] <= b[1] and b[2] <= A[2] and b[3] <= A[3]):
            bad.append(f"band {n} must lie inside Stage A")
    paths = {n: p for n, p in plan["path"].items()}
    allpaths = list(plan["path"].items()) + list(plan["threshold"].items())
    # 2. trees
    for n, t in plan["tree"].items():
        c = (t["x"], t["z"])
        reach, bottom, top = t["crown"]
        for r, what in ((t["keepclear"], "keep-clear circle"), (reach, "crown")):
            if not inside_rect(c, A, r):
                bad.append(f"{n}: its {what} (r {r:g}) must lie inside Stage A")
            for bn, b in plan["band"].items():
                gap = circle_rect_gap(c, r, b)
                if gap < 0:
                    bad.append(f"{n}: its {what} (r {r:g}) overlaps band {bn} by {-gap:.2f} m")
        for on, ox, oz, orr, kind in OBJECTS:
            if kind != "zone" and math.hypot(ox - c[0], oz - c[1]) - orr < t["keepclear"]:
                bad.append(f"{n}: existing {on} lies inside its keep-clear circle")
        for cn, (cx, cz, cr) in plan["clearing"].items():
            if math.hypot(cx - c[0], cz - c[1]) < t["keepclear"] + cr:
                bad.append(f"{n}: clearing {cn} overlaps its keep-clear circle")
        for pn, (w, pts) in allpaths:
            if poly_dist(c, pts) - w / 2 < t["katte"] + 0.3:
                bad.append(f"{n}: path {pn} runs onto its katte (r {t['katte']:g})")
        info.append(f"{n} at {c}: keep-clear r {t['keepclear']:g} m, crown r {reach:g} m; nearest band edge "
                    f"{min(circle_rect_gap(c, t['keepclear'], b) for b in plan['band'].values()):.2f} m beyond the keep-clear circle")
    # 3. paths
    first = next(iter(paths.values()))[1][0] if paths else None
    if first is None or poly_dist(first, TO_FOREST) > 0.2:
        bad.append(f"the first path must start on the planned to_forest path {TO_FOREST} (starts at {first})")
    for pn, (w, pts) in allpaths:
        threshold = pn in plan["threshold"]
        if threshold:
            gap, on = min((poly_dist((x, z), pts) - r - w / 2, nm) for nm, x, z, r in TRUNKS)
            if gap < 0.8:
                bad.append(f"threshold {pn}: its edge passes {gap:.2f} m from the trunk of {on} (needs 0.8 m)")
            info.append(f"threshold {pn} ({w:g} m): {gap:.2f} m from the nearest trunk ({on})")
        else:
            for on, ox, oz, orr, kind in OBJECTS:
                if kind != "zone" and poly_dist((ox, oz), pts) - w / 2 - orr < 0:
                    bad.append(f"path {pn}: its edge enters {on}'s layout radius")
            for p in pts[1:] if pn == next(iter(paths)) else pts:
                if not inside_rect(p, A, 1.5 + w / 2):
                    bad.append(f"path {pn}: {p} must lie 1.5 m inside Stage A")
        if rect_poly_dist(HOUSE, pts) - w / 2 < 0.8:
            bad.append(f"{'threshold' if threshold else 'path'} {pn}: passes {rect_poly_dist(HOUSE, pts) - w/2:.2f} m from the house (needs 0.8 m)")
    ends = [pts[0] for _, (_, pts) in allpaths] + [pts[-1] for _, (_, pts) in allpaths]
    for pn, (w, pts) in allpaths[1:]:
        if min(math.dist(pts[0], e) for e in ends if e is not pts[0]) > 0.01 and \
           min(poly_dist(pts[0], q) for qn, (_, q) in allpaths if qn != pn) > 0.5 and \
           min(math.hypot(pts[0][0] - c[0], pts[0][1] - c[1]) - c[2] for c in plan["clearing"].values()) > 0.5:
            bad.append(f"path {pn} must start on another path or at a clearing's edge")
    # 4. clearings and houses
    for cn, (cx, cz, cr) in plan["clearing"].items():
        for on, ox, oz, orr, kind in OBJECTS:
            if kind != "zone" and math.hypot(ox - cx, oz - cz) - orr < cr:
                bad.append(f"clearing {cn}: existing {on} reaches into it")
        if not inside_rect((cx, cz), A, cr + 1.5):
            bad.append(f"clearing {cn} must lie 1.5 m inside Stage A")
    for hn, (x, z, w, d) in plan["house"].items():
        rect = (x - w / 2, z - d / 2, x + w / 2, z + d / 2)
        for on, ox, oz, orr, kind in OBJECTS:
            if kind != "zone" and circle_rect_gap((ox, oz), orr, rect) < 1.5:
                bad.append(f"house {hn}: within 1.5 m of existing {on}")
        for cn, (cx, cz, cr) in plan["clearing"].items():
            if circle_rect_gap((cx, cz), cr, rect) < 1.0:
                bad.append(f"house {hn}: within 1.0 m of clearing {cn}")
        for bn, b in plan["band"].items():
            if not (rect[2] + 1.5 <= b[0] or rect[0] - 1.5 >= b[2] or rect[3] + 1.5 <= b[1] or rect[1] - 1.5 >= b[3]):
                bad.append(f"house {hn}: within 1.5 m of band {bn}")
        for pn, (pw, pts) in allpaths:
            if rect_poly_dist((rect[0], rect[2], rect[1], rect[3]), pts) - pw / 2 < 0.8:
                bad.append(f"house {hn}: path {pn} passes within 0.8 m")
        door = (x, z + d / 2)
        if min(poly_dist(door, pts) - pw / 2 for _, (pw, pts) in allpaths) > 3.0:
            bad.append(f"house {hn}: its south door is more than 3 m from a path")
    # 5. seats
    for sn, (x, z, yaw, subjects) in plan["seat"].items():
        for nm, tx, tz, r in TRUNKS + [(tn, t["x"], t["z"], t["trunk"]) for tn, t in plan["tree"].items()]:
            if math.hypot(tx - x, tz - z) < r + 0.5:
                bad.append(f"seat {sn}: within 0.5 m of the trunk of {nm}")
        for pn, (pw, pts) in allpaths:
            if poly_dist((x, z), pts) - pw / 2 < 0.8:
                bad.append(f"seat {sn}: within 0.8 m of path {pn} (a seat is never on a path)")
        for pt in subjects:
            s = project(pt, (x, z), 0.0, SEAT_ARM, SEAT_OFFSET)
            if s is None or abs(s[0]) > 0.95 or abs(s[1]) > 0.95:
                bad.append(f"seat {sn}: subject {pt} is out of the default seated frame ({s})")
        bottom = [ground_hit((x, z), 0.0, SEAT_ARM, SEAT_OFFSET, u, -1.0) for u in (-1.0, 1.0)]
        if not all(b and inside_rect(b, A) for b in bottom):
            bad.append(f"seat {sn}: the bottom of its seated frame {bottom} leaves Stage A")
        cam = rig((x, z), 0.0, SEAT_ARM, SEAT_OFFSET)[0]
        for tn, t in plan["tree"].items():
            reach, bot, top = t["crown"]
            for k in range(201):
                f = k / 200
                p = (cam[0] + (x - cam[0]) * f, cam[1] + (0.9 - cam[1]) * f, cam[2] + (z - cam[2]) * f)
                if math.hypot(p[0] - t["x"], p[2] - t["z"]) <= reach and bot <= p[1] <= top:
                    bad.append(f"seat {sn}: {tn}'s crown hides the seated player")
                    break
        info.append(f"seat {sn} ({x:g}, {z:g}): " + ", ".join(
            f"{pt} at {tuple(round(c, 2) for c in project(pt, (x, z), 0.0, SEAT_ARM, SEAT_OFFSET))}" for pt in subjects))
    # 6. reveal
    for tn, dist in plan["reveal"].items():
        t = plan["tree"][tn]
        reach, bot, top = t["crown"]
        def crown_in_frame(south):
            cam = rig((t["x"], t["z"] + south), 0.0, ARM)[0]
            ahead = cam[2] - (t["z"] + reach)                      # horizontal distance camera -> crown's south edge
            return cam[1] - ahead * math.tan(math.radians(-PITCH - FOV / 2)) >= bot
        if not crown_in_frame(dist):
            bad.append(f"reveal {tn}: the crown is not yet in frame {dist:g} m south of the trunk")
        if crown_in_frame(dist + 4.0):
            info.append(f"reveal {tn}: the crown is already in frame {dist + 4:g} m south (earlier than planned)")
        info.append(f"reveal {tn}: crown underside enters the frame top by {dist:g} m south of the trunk (arm {ARM:g} m)")
    # 7. later-stage areas
    for an, (x, z, r) in plan["area"].items():
        if not inside_rect((x, z), T, r):
            bad.append(f"area {an} must lie inside the target")
        if inside_rect((x, z), ground, -r):
            bad.append(f"area {an} overlaps the existing ground")
    return bad, info

def main():
    doc = _src("docs", "VILLAGE_DESIGN_LOCK_A0.md")
    blocks = re.findall(r"^```village-plan\n(.*?)^```", doc, re.M | re.S)
    assert len(blocks) == 1, "the design lock has exactly one village-plan block"
    plan = parse(blocks[0])
    bad, info = check(plan)
    for line in info:
        print(line)
    for line in bad:
        print("FAIL", line)
    assert not bad, f"{len(bad)} village plan rule(s) broken"
    # Designs shown to break: each must fail the same checks.
    broken = []
    a0_road = dict(plan, path={"village_road": (2.5, [(-21.0, 0.0), (-31.0, 2.0), (-40.0, 4.0)])}, threshold={})
    broken.append(("A0 blueprint's straight road from the door", a0_road, "from the house"))
    t = dict(plan["tree"]["great_tree"], x=-52.0)
    broken.append(("the Great Tree at A0's x = -52", dict(plan, tree={"great_tree": t}), "overlaps band"))
    s = dict(plan["seat"])
    k = next(iter(s))
    x, z, yaw, subj = s[k]
    s[k] = (x, z, yaw, [(x, 0.5, z - 14.0)])
    broken.append(("a seat facing a subject 14 m ahead", dict(plan, seat=s), "out of the default seated frame"))
    for name, design, expect in broken:
        b, _ = check(design)
        assert any(expect in m for m in b), f"broken design not caught: {name} ({b[:3]})"
        print(f"broken design caught: {name}")
    print(f"village plan: {len(plan['provisional'])} provisional entries checked as candidates: "
          f"{sorted(f'{k} {n}' for k, n in plan['provisional'])}")
    print("ALL VILLAGE PLAN SIMULATIONS PASSED")

if __name__ == "__main__":
    main()
