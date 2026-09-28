#!/usr/bin/env python3
"""Model checks for camera bounds per area (M03.4) — a Python port, not the engine.
1. Read from the project: the camera's follow parameters and step
   (follow_camera.gd), the Meadow's AreaCameraBounds and its ground plane,
   Main's apply-bounds-then-snap order.
2. The Meadow: inside the bounds the bounded camera moves exactly like the
   pre-M03.4 camera (smoothing, look-ahead unchanged); at each edge the
   followed point stops at the edge (the only difference is the <= 1 m
   look-ahead past it); a player beyond the edge leaves the camera on it.
3. Area swaps: the new area's bounds replace the old ones (never leak), an
   area without bounds clears them, repeated swaps, the same player target,
   and a snap after a swap never reads the jump as speed.
"""
import math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _body(src, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S)
    assert m, f"{name}() not found"
    return m.group(0)

# ---------------------------------------------------------------- 1. read from the project
CAM, MAIN, MEADOW = _src("scripts", "camera", "follow_camera.gd"), _src("scripts", "main.gd"), _src("scenes", "world", "Meadow.tscn")
def _export(name): return float(re.search(rf"^@export var {name}: float = ([0-9.]+)", CAM, re.M).group(1))
FOLLOW_SPEED, LOOK_AHEAD, SPEED_REF = _export("follow_speed"), _export("look_ahead_distance"), _export("look_ahead_speed_reference")
PP = _body(CAM, "_physics_process")
assert "var desired_position := _clamp_to_bounds(target_position + look_ahead)" in PP
assert "var smoothing := 1.0 - exp(-follow_speed * delta)" in PP and "global_position = global_position.lerp(desired_position, smoothing)" in PP
LOOK_MIN_SPEED = float(re.search(r"if horizontal_speed > ([0-9.]+):", PP).group(1))
assert re.search(r"global_position = _clamp_to_bounds\(target\.global_position\)\s*_has_last_position = false", _body(CAM, "snap_to_target"))
bnode = re.search(r'\[node name="CameraBounds" type="Node3D" parent="\."\]\nscript = ExtResource\("camera_bounds"\)\nsize = Vector2\(([^)]*)\)', MEADOW)
ground = re.search(r'\[sub_resource type="PlaneMesh" id="PlaneMesh_ground"\]\nsize = Vector2\(([^)]*)\)', MEADOW)
assert bnode and ground and bnode.group(1) == ground.group(1), "Meadow bounds = its ground plane"
BW, BH = [float(v) for v in bnode.group(1).split(",")]
MEADOW_RECT = (-BW / 2, -BH / 2, BW / 2, BH / 2)                     # min x, min z, max x, max z (node at origin)
SWAP = _body(MAIN, "_swap_area")
assert SWAP.find("add_child(area)") < SWAP.find("_apply_camera_bounds()") < SWAP.find("follow_camera.snap_to_target()")
assert re.search(r"follow_camera\.target = player\s*_apply_camera_bounds\(\)\s*follow_camera\.snap_to_target\(\)", _body(MAIN, "_ready"))

# ---------------------------------------------------------------- 2. the camera (port)
class Cam:
    def __init__(c, target, bounded=True):
        c.target, c.bounded, c.rect, c.pos, c.last = target, bounded, None, (0.0, 0.0), None
    def set_bounds(c, rect): c.rect = rect
    def clear_bounds(c): c.rect = None
    def clamp(c, p):
        if not c.bounded or c.rect is None: return p
        x0, z0, x1, z1 = c.rect
        return (min(max(p[0], x0), x1), min(max(p[1], z0), z1))
    def snap(c): c.pos = c.clamp(c.target.pos); c.last = None
    def step(c, dt=1 / 60):
        t = c.target.pos
        if c.last is None: c.last = t
        vx, vz = (t[0] - c.last[0]) / max(dt, 0.0001), (t[1] - c.last[1]) / max(dt, 0.0001); c.last = t
        hs = math.hypot(vx, vz); ratio = min(max(hs / SPEED_REF, 0.0), 1.0)
        la = (vx / hs * LOOK_AHEAD * ratio, vz / hs * LOOK_AHEAD * ratio) if hs > LOOK_MIN_SPEED else (0.0, 0.0)
        d = c.clamp((t[0] + la[0], t[1] + la[1]))
        k = 1.0 - math.exp(-FOLLOW_SPEED * dt)
        c.pos = (c.pos[0] + (d[0] - c.pos[0]) * k, c.pos[1] + (d[1] - c.pos[1]) * k)
class Target:
    def __init__(t, x, z): t.pos = (x, z)
def inside(p, r, eps=1e-9): return r[0] - eps <= p[0] <= r[2] + eps and r[1] - eps <= p[1] <= r[3] + eps
def walk(player, cams, vx, vz, frames, stop_at=None):
    for _ in range(frames):
        x, z = player.pos[0] + vx / 60, player.pos[1] + vz / 60
        if stop_at: x, z = min(max(x, stop_at[0]), stop_at[2]), min(max(z, stop_at[1]), stop_at[3])   # the ground ends
        player.pos = (x, z)
        for c in cams: c.step()

# Inside the Meadow: identical to the pre-M03.4 camera.
rnd = random.Random(4)
p = Target(0.0, 5.0); new, old = Cam(p), Cam(p, bounded=False); new.set_bounds(MEADOW_RECT); new.snap(); old.snap()
inner = (MEADOW_RECT[0] + LOOK_AHEAD + 1, MEADOW_RECT[1] + LOOK_AHEAD + 1, MEADOW_RECT[2] - LOOK_AHEAD - 1, MEADOW_RECT[3] - LOOK_AHEAD - 1)
for _ in range(400):
    a = rnd.uniform(0, math.tau); s = rnd.choice([0.0, 1.5, 4.3])
    walk(p, [new, old], s * math.cos(a), s * math.sin(a), rnd.randint(5, 40), stop_at=inner)
    assert new.pos == old.pos, "inside the bounds the camera is unchanged (smoothing, look-ahead)"
# Near each edge: walk into it at full speed; the followed point stops at the edge.
for name, vx, vz in (("east", 4.3, 0), ("west", -4.3, 0), ("south", 0, 4.3), ("north", 0, -4.3)):
    p = Target(0.0, 0.0); new, old = Cam(p), Cam(p, bounded=False); new.set_bounds(MEADOW_RECT); new.snap(); old.snap()
    walk(p, [new, old], vx, vz, 900, stop_at=MEADOW_RECT)          # reaches the edge and keeps pushing
    assert inside(new.pos, MEADOW_RECT), f"{name}: camera focus inside the Meadow"
    edge = MEADOW_RECT[2] if vx > 0 else MEADOW_RECT[0] if vx < 0 else MEADOW_RECT[3] if vz > 0 else MEADOW_RECT[1]
    axis = 0 if vx else 1
    assert abs(new.pos[axis] - edge) < 1e-3, f"{name}: settles on the edge ({new.pos})"
    diff = math.dist(new.pos, old.pos)
    assert diff <= LOOK_AHEAD + 1e-6, f"{name}: the only change is the look-ahead past the edge ({diff:.3f} m)"
# Beyond the edge (e.g. walked off the ground): the camera stays on it.
p = Target(40.0, -45.0); c = Cam(p); c.set_bounds(MEADOW_RECT); c.snap()
assert c.pos == (MEADOW_RECT[2], MEADOW_RECT[1])
for _ in range(120): c.step()
assert c.pos == (MEADOW_RECT[2], MEADOW_RECT[1]), "a player beyond the bounds leaves the camera at the edge"

# ---------------------------------------------------------------- 3. area swaps
def swap(cam, rect):  # Main._swap_area: new area installed, then bounds applied (or cleared), then snap
    cam.set_bounds(rect) if rect else cam.clear_bounds()
    cam.snap()
p = Target(0.0, 5.0); cam = Cam(p); swap(cam, MEADOW_RECT); player_ref = cam.target
house = (100.0, 100.0, 106.0, 104.0)                                  # a small interior elsewhere
p.pos = (103.0, 102.0); swap(cam, house)
assert inside(cam.pos, house) and cam.pos == (103.0, 102.0)
p.pos = (0.0, 0.0); cam.snap()
assert inside(cam.pos, house) and not inside(cam.pos, MEADOW_RECT), "the Meadow's bounds no longer apply"
p.pos = (20.0, 20.0); swap(cam, MEADOW_RECT); assert cam.pos == (20.0, 20.0)
p.pos = (300.0, 300.0); swap(cam, None); assert cam.pos == (300.0, 300.0), "an area without bounds clears them"
for _ in range(60): cam.step()
assert cam.pos == (300.0, 300.0)
# a snap after a teleport starts the look-ahead fresh (no speed spike)
q = Target(0.0, 0.0); c = Cam(q); c.set_bounds((-500, -500, 500, 500)); c.snap(); c.step()
q.pos = (200.0, 0.0); c.snap(); c.step(); assert c.pos == (200.0, 0.0), "no look-ahead jump after a snap"
rnd = random.Random(11)
for _ in range(2000):
    p = Target(0.0, 5.0); cam = Cam(p); swap(cam, MEADOW_RECT)
    for _ in range(rnd.randint(1, 6)):
        rect = None if rnd.random() < 0.2 else (lambda x, z, w, h: (x, z, x + w, z + h))(rnd.uniform(-200, 200), rnd.uniform(-200, 200), rnd.uniform(4, 80), rnd.uniform(4, 80))
        p.pos = (rnd.uniform(-250, 250), rnd.uniform(-250, 250)); swap(cam, rect)
        walk(p, [cam], rnd.uniform(-4.3, 4.3), rnd.uniform(-4.3, 4.3), rnd.randint(1, 90))
        assert cam.target is p and cam.rect == rect, "one camera, the same player, the current area's bounds only"
        if rect: assert inside(cam.pos, rect), "never outside the current area's bounds"
print(f"camera bounds: Meadow {MEADOW_RECT} (ground plane); unchanged inside; edges stop the focus (<= {LOOK_AHEAD} m look-ahead); "
      "swaps replace/clear bounds; 2000 random swap runs OK")
print("ALL CAMERA SIMULATIONS PASSED")
