#!/usr/bin/env python3
"""Model checks for clamped pinch zoom + mouse wheel (M03.5) — a Python port, not the engine.
1. Read from the project: the zoom limits and the scene's arm length
   (follow_camera.gd, FollowCamera.tscn), the wheel step and tap limits
   (input_manager.gd), and the structure of the touch/pinch/wheel code.
2. The camera: one clamped zoom path; minimum, maximum and values between;
   repeated pinch in/out and wheel up/down; crossing both limits; exact
   limits held when hammered (deterministic).
3. Gestures: two world fingers pinch (apart = closer); a pinch never taps,
   not even its still pivot finger; one finger never zooms; a third finger
   pauses the pinch and adding/removing one never makes the zoom jump;
   quick single taps still tap; the wheel never taps.
4. Area reload keeps the zoom; zoom never moves the camera's focus or its
   M03.4 bounds. 2,000 random input sequences.
"""
import math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _body(src, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S)
    assert m, f"{name}() not found"
    return m.group(0)
def _const(src, name): return float(re.search(rf"^const {name} := ([0-9.]+)", src, re.M).group(1))

# ---------------------------------------------------------------- 1. read from the project
CAM, IM, MAIN = _src("scripts", "camera", "follow_camera.gd"), _src("scripts", "autoload", "input_manager.gd"), _src("scripts", "main.gd")
ZMIN, ZMAX = _const(CAM, "ZOOM_MIN_DISTANCE"), _const(CAM, "ZOOM_MAX_DISTANCE")
START = float(re.search(r"spring_length = ([0-9.]+)", _src("scenes", "camera", "FollowCamera.tscn")).group(1))
STEP, TAP_MOVE, TAP_MSEC = _const(IM, "WHEEL_ZOOM_STEP"), _const(IM, "TAP_MAX_MOVE"), _const(IM, "TAP_MAX_MSEC")
assert 0 < ZMIN < START < ZMAX and STEP > 1.0
assert "_spring_arm.spring_length = clampf(distance, ZOOM_MIN_DISTANCE, ZOOM_MAX_DISTANCE)" in _body(CAM, "set_zoom_distance")
assert "set_zoom_distance(_spring_arm.spring_length * factor)" in _body(CAM, "zoom_by")
UI = _body(IM, "_unhandled_input")
assert UI.find("_track_touch(") < UI.find("if _world_touches.size() >= 2:") < UI.find("_tap_starts.clear()") < UI.find("_track_tap(touch.index")
assert "zoom_requested.emit(1.0 / WHEEL_ZOOM_STEP if wheel.button_index == MOUSE_BUTTON_WHEEL_UP else WHEEL_ZOOM_STEP)" in UI
assert "zoom_requested.emit(_pinch_distance / distance)" in _body(IM, "_track_pinch")
assert "if _world_touches.size() != 2:" in _body(IM, "_two_finger_distance")
assert "InputManager.zoom_requested.connect(follow_camera.zoom_by)" in _body(MAIN, "_ready")
assert "follow_camera.snap_to_target()" in _body(MAIN, "_swap_area") and "zoom" not in _body(CAM, "snap_to_target")

# ---------------------------------------------------------------- 2-3. ports
class Camera:  # FollowCamera zoom (and the M03.4 focus it must not touch)
    def __init__(c): c.distance, c.focus, c.bounds = START, (0.0, 5.0), (-32.0, -32.0, 32.0, 32.0)
    def zoom_by(c, f):
        if not (f > 0 and math.isfinite(f)): return
        c.set_zoom_distance(c.distance * f)
    def set_zoom_distance(c, d): c.distance = min(max(d, ZMIN), ZMAX)
class Input:  # InputManager: world touches, taps, pinch, wheel
    def __init__(i, cam): i.cam, i.touches, i.tap_starts, i.pinch, i.taps, i.zooms, i.t = cam, {}, {}, 0.0, [], [], 0
    def _emit_zoom(i, f): i.zooms.append(f); i.cam.zoom_by(f)
    def _two(i):
        if len(i.touches) != 2: return 0.0
        a, b = list(i.touches.values()); return math.dist(a, b)
    def touch(i, idx, pressed, pos, gui=False):
        if gui: return                                  # the GUI (joystick, buttons) consumed it
        if pressed: i.touches[idx] = pos
        else: i.touches.pop(idx, None)
        i.pinch = i._two()
        if len(i.touches) >= 2: i.tap_starts.clear(); return
        if pressed: i.tap_starts[idx] = (pos, i.t); return
        if idx not in i.tap_starts: return
        start, t0 = i.tap_starts.pop(idx)
        if math.dist(pos, start) <= TAP_MOVE and i.t - t0 <= TAP_MSEC: i.taps.append(pos)
    def drag(i, idx, pos):
        if idx not in i.touches: return
        i.touches[idx] = pos; d = i._two()
        if i.pinch > 0 and d > 0: i._emit_zoom(i.pinch / d)
        i.pinch = d
    def wheel(i, up, pressed=True):
        if pressed: i._emit_zoom(1.0 / STEP if up else STEP)
    def wait(i, ms): i.t += ms

def pinch(inp, start, end, steps=10, a=(500.0, 800.0)):
    """Two fingers: one still at a, the other moving from start to end distance."""
    inp.touch(0, True, a); inp.touch(1, True, (a[0] + start, a[1]))
    for k in range(1, steps + 1): inp.drag(1, (a[0] + start + (end - start) * k / steps, a[1]))
    inp.wait(120); inp.touch(1, False, (a[0] + end, a[1])); inp.touch(0, False, a)

cam = Camera(); inp = Input(cam)
assert cam.distance == START
pinch(inp, 200, 300); assert abs(cam.distance - START * 200 / 300) < 1e-9, "fingers apart: closer, by the distance ratio"
assert inp.taps == [], "a pinch never taps — not even its still finger"
pinch(inp, 300, 200); assert abs(cam.distance - START) < 1e-9, "fingers together: back out"
for _ in range(30): pinch(inp, 200, 320)
assert cam.distance == ZMIN, "repeated pinch-in stops exactly at the minimum"
for _ in range(30): pinch(inp, 320, 200)
assert cam.distance == ZMAX, "repeated pinch-out stops exactly at the maximum"
pinch(inp, 100, 2000); assert cam.distance == ZMIN, "one huge pinch crosses the minimum: clamped"
pinch(inp, 2000, 50); assert cam.distance == ZMAX, "one huge pinch crosses the maximum: clamped"
cam.set_zoom_distance(START)
inp.wheel(True); assert abs(cam.distance - START / STEP) < 1e-9, "wheel up: closer"
inp.wheel(False); inp.wheel(False); assert abs(cam.distance - START * STEP) < 1e-9, "wheel down: farther"
inp.wheel(True, pressed=False); assert abs(cam.distance - START * STEP) < 1e-9, "wheel release does nothing"
for _ in range(100): inp.wheel(True)
assert cam.distance == ZMIN
for _ in range(3): inp.wheel(True)
assert cam.distance == ZMIN, "hammering the limit stays exactly on it"
for _ in range(100): inp.wheel(False)
assert cam.distance == ZMAX and inp.taps == [], "wheel never taps"
between = []
cam.set_zoom_distance(START)
for up in (True, False, True, True, False): inp.wheel(up); between.append(cam.distance)
assert all(ZMIN < d < ZMAX for d in between), "values between the limits"
for bad in (0.0, -1.0, float("inf"), float("nan")): d = cam.distance; cam.zoom_by(bad); assert cam.distance == d, "invalid factors ignored"

# pinch -> single touch: lifting one finger ends the pinch; the other finger never taps or zooms
cam.set_zoom_distance(START); inp = Input(cam)
inp.touch(0, True, (500, 800)); inp.touch(1, True, (700, 800)); inp.drag(1, (760, 800)); z = cam.distance
inp.touch(1, False, (760, 800)); inp.drag(0, (520, 820)); inp.drag(0, (400, 700))
assert cam.distance == z, "one finger left: no zoom"
inp.touch(0, False, (400, 700)); assert inp.taps == [], "the finger left over from a pinch is not a tap"
# third finger: pauses the pinch; adding or removing it never jumps the zoom
cam.set_zoom_distance(START); inp = Input(cam)
inp.touch(0, True, (500, 800)); inp.touch(1, True, (700, 800)); inp.drag(1, (720, 800)); z = cam.distance
inp.touch(2, True, (100, 100)); inp.drag(1, (900, 800)); inp.drag(2, (50, 50))
assert cam.distance == z, "three fingers: no zoom"
inp.touch(2, False, (50, 50)); z = cam.distance
inp.drag(1, (900, 800)); assert cam.distance == z, "back to two fingers: resumes from where they are, no jump"
inp.drag(1, (1000, 800)); assert abs(cam.distance - z * 400 / 500) < 1e-9
inp.touch(1, False, (1000, 800)); inp.touch(0, False, (500, 800)); assert inp.taps == []
# tap-to-move and tap-to-interact untouched: a quick single touch taps and never zooms
cam.set_zoom_distance(START); inp = Input(cam)
inp.touch(0, True, (300, 300)); inp.drag(0, (305, 302)); inp.wait(100); inp.touch(0, False, (305, 302))
assert inp.taps == [(305, 302)] and cam.distance == START and inp.zooms == []
# joystick (GUI) finger + one world finger: no pinch, the world tap still works
inp = Input(cam)
inp.touch(5, True, (80, 900), gui=True); inp.touch(0, True, (600, 400)); inp.wait(100); inp.touch(0, False, (600, 401))
assert inp.taps == [(600, 401)] and cam.distance == START

# ---------------------------------------------------------------- 4. area reload / bounds
cam.set_zoom_distance(9.0); focus, bounds = cam.focus, cam.bounds
cam.bounds = (100.0, 100.0, 106.0, 104.0); cam.focus = (103.0, 102.0)          # load_area -> new bounds, snap
assert cam.distance == 9.0, "zoom survives an area reload"
for f in (0.5, 2.0, 1.3): cam.zoom_by(f); assert cam.focus == (103.0, 102.0) and cam.bounds == (100.0, 100.0, 106.0, 104.0)
for edge in ((32.0, 0.0), (-32.0, 0.0), (0.0, 32.0), (0.0, -32.0)):
    cam.bounds, cam.focus = (-32.0, -32.0, 32.0, 32.0), edge
    for f in (0.8, 1.25, 0.1, 9.0): cam.zoom_by(f)
    assert cam.focus == edge and ZMIN <= cam.distance <= ZMAX, "zooming at a bound moves neither focus nor bounds"

# random sequences
rnd = random.Random(21); stats = dict(taps=0, zooms=0, pinch_taps_blocked=0)
for _ in range(2000):
    cam = Camera(); inp = Input(cam); multi_seen = {}                      # finger -> saw >= 2 world fingers
    for _ in range(rnd.randint(5, 60)):
        ev = rnd.random(); before_taps, before_d = len(inp.taps), cam.distance; did = None
        if ev < 0.3:
            idx = rnd.randint(0, 3)
            if idx in inp.touches:
                was_multi = multi_seen.pop(idx, False)
                inp.touch(idx, False, inp.touches[idx])
                if was_multi:
                    stats["pinch_taps_blocked"] += 1
                    assert len(inp.taps) == before_taps, "a finger that was ever part of a pinch never taps"
            else:
                inp.touch(idx, True, (rnd.uniform(0, 1920), rnd.uniform(0, 1080)), gui=rnd.random() < 0.15)
        elif ev < 0.65 and inp.touches:
            idx = rnd.choice(list(inp.touches)); x, y = inp.touches[idx]; did = "drag"
            inp.drag(idx, (x + rnd.uniform(-60, 60), y + rnd.uniform(-60, 60)))
        elif ev < 0.8: inp.wheel(rnd.random() < 0.5, pressed=rnd.random() < 0.8)
        elif ev < 0.9: inp.wait(rnd.randint(10, 600))
        else: cam.set_zoom_distance(cam.distance)                           # an area reload leaves zoom alone
        for f in inp.touches: multi_seen[f] = multi_seen.get(f, False) or len(inp.touches) >= 2
        for f in list(multi_seen):
            if f not in inp.touches: multi_seen.pop(f)
        assert ZMIN <= cam.distance <= ZMAX, "never outside the limits"
        if len(inp.taps) > before_taps:
            stats["taps"] += 1
            assert len(inp.touches) == 0, "a tap only when the last world finger lifts"
        if cam.distance != before_d and did == "drag":
            assert len(inp.touches) == 2, "only exactly two fingers zoom"
    stats["zooms"] += len(inp.zooms)
print(f"zoom: [{ZMIN}, {ZMAX}] m from {START} m, wheel step {STEP}; pinch/wheel/limits/third finger/tap/reload/bounds OK; "
      f"2000 random sequences {stats}")
print("ALL ZOOM SIMULATIONS PASSED")
