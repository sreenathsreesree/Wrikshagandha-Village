#!/usr/bin/env python3
"""Diagnostic (NOT a pass/fail check, not run by run_all.sh): reproduces the
suspected "stuck / unresponsive" runtime states without Godot, using the
project's real constants and the exact update rules of the scripts.

  python3 tools/diagnostics/diag_stuck_states.py

Each scenario prints whether the state has an exit when the player gives
no further input. It models the scripts, not the engine: the NavigationAgent3D
arrival rule (3D distance to the last waypoint < path_desired_distance) and
the loss of a touch release are assumptions stated per scenario.
"""
import math, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _body(src, name): return re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S).group(0)
PL, IM, JOY = _src("scripts", "player", "player.gd"), _src("scripts", "autoload", "input_manager.gd"), _src("scripts", "ui", "virtual_joystick.gd")
def c(name, src=PL): return float(re.search(rf"^const {name} := ([0-9.]+)", src, re.M).group(1))
MAX_SPEED, ACCEL, DECEL = c("MAX_SPEED"), c("ACCELERATION"), c("DECELERATION")
SLOW_DIST, MIN_PACE = c("ARRIVAL_SLOWDOWN_DISTANCE"), c("ARRIVAL_MIN_SPEED")
STUCK_SECONDS, STUCK_SPEED = c("NAVIGATION_STUCK_SECONDS"), c("NAVIGATION_STUCK_SPEED")
TSCN = _src("scenes", "player", "Player.tscn")
PATH_DIST = float(re.search(r"path_desired_distance = ([0-9.]+)", TSCN).group(1))
TARGET_DIST = float(re.search(r"target_desired_distance = ([0-9.]+)", TSCN).group(1))
DT = 1.0 / 60.0                                   # project.godot sets no physics_ticks_per_second: default 60
# The code facts the scenarios depend on:
PP = _body(PL, "_physics_process")
assert "var speed := horizontal_velocity.length()" in PP and "_update_navigation_progress(delta, speed)" in PP \
    and PP.find("move_and_slide()") < PP.find("var speed := horizontal_velocity.length()"), "stall uses the commanded velocity"
assert "if speed < NAVIGATION_STUCK_SPEED:" in _body(PL, "_update_navigation_progress")
ND = _body(PL, "_navigation_direction")
assert "elif nav_agent.is_navigation_finished():" in ND and "if to_next.length() < 0.01:" in ND and "to_next.y = 0.0" in ND

def move_toward(v, t, d):
    dx, dz = t[0] - v[0], t[1] - v[1]; L = math.hypot(dx, dz)
    return t if L <= d or L == 0 else (v[0] + dx / L * d, v[1] + dz / L * d)

print(f"constants: MAX_SPEED {MAX_SPEED}, ACCELERATION {ACCEL}, stall < {STUCK_SPEED} m/s for {STUCK_SECONDS} s, "
      f"arrival min pace {MIN_PACE}, path_desired {PATH_DIST}, target_desired {TARGET_DIST}, dt 1/60")
print(f"one acceleration step = ACCELERATION*dt = {ACCEL * DT!r} m/s  ->  '{ACCEL * DT!r} < {STUCK_SPEED}' is {ACCEL * DT < STUCK_SPEED}")

# ---------------------------------------------------------------- 1. blocked head-on during a tap walk
def blocked(metric, seconds=10.0):
    v, stuck = (0.0, 0.0), 0.0
    for i in range(int(seconds / DT)):
        hv = move_toward(v, (MAX_SPEED, 0.0), ACCEL * DT)      # commanded (horizontal_velocity)
        actual = (0.0, 0.0)                                      # move_and_slide: a wall straight ahead
        v = actual                                                # velocity after the slide feeds the next frame
        speed = math.hypot(*hv) if metric == "commanded" else math.hypot(*actual)
        stuck = stuck + DT if speed < STUCK_SPEED else 0.0
        if stuck >= STUCK_SECONDS: return f"walk ended after {i * DT:.2f} s"
    return f"STILL WALKING after {seconds:.0f} s (stall timer never starts)"
print("\n[1] tap-walk pressed head-on into something the path didn't avoid (or a walk before the navmesh exists):")
print("    as coded (commanded speed):", blocked("commanded"))
print("    if measured by real velocity:", blocked("actual"))

# ---------------------------------------------------------------- 2. arrival: agent never reports finished
def arrive(dy, approach_deg, seconds=20.0, stop_on_horizontal=False, metric="commanded"):
    """The final waypoint W is at the origin, dy metres above/below the player's feet (navmesh surface
    offset on a slope/terrace edge). Player starts 3 m away. Godot's agent finishes when the 3D distance
    to W < path_desired_distance; the script steers horizontally (pace floored at ARRIVAL_MIN_SPEED)."""
    a = math.radians(approach_deg); p = (3 * math.cos(a), 3 * math.sin(a)); v = (0.0, 0.0)
    stuck, flips, last_dir, t = 0.0, 0, None, 0.0
    while t < seconds:
        d3 = math.sqrt(p[0] ** 2 + p[1] ** 2 + dy ** 2)
        horiz = math.hypot(*p)
        if d3 < PATH_DIST: return f"finished ({t:.2f} s)"
        if stop_on_horizontal and horiz <= TARGET_DIST: return f"finished by horizontal check ({t:.2f} s)"
        if horiz < 0.01: direction = (0.0, 0.0)
        else:
            pace = min(max(horiz / SLOW_DIST, MIN_PACE), 1.0); direction = (-p[0] / horiz * pace, -p[1] / horiz * pace)
        rate = ACCEL if direction != (0.0, 0.0) else DECEL
        hv = move_toward(v, (direction[0] * MAX_SPEED, direction[1] * MAX_SPEED), rate * DT)
        v = hv; p = (p[0] + v[0] * DT, p[1] + v[1] * DT)
        speed = math.hypot(*hv)
        stuck = stuck + DT if speed < STUCK_SPEED else 0.0
        if stuck >= STUCK_SECONDS: return f"stall timeout ({t:.2f} s)"
        if direction != (0.0, 0.0):
            ang = math.atan2(direction[0], -direction[1])
            if last_dir is not None and abs(math.remainder(ang - last_dir, math.tau)) > math.pi / 2: flips += 1
            last_dir = ang
        t += DT
    return f"NEVER ENDS: {seconds:.0f} s later still navigating, facing reversed {flips} times (jitter/spin in place)"
print("\n[2] arriving at the final point (no further input):")
for dy in (0.0, 0.25, 0.39, 0.45, 0.6):
    print(f"    navmesh {dy:.2f} m off the player's feet: {arrive(dy, 30)}")
print(f"    fix preview — also end on horizontal distance <= target_desired_distance (dy 0.6): {arrive(0.6, 30, stop_on_horizontal=True)}")
def arrive_blocked(dy, gap, seconds=20.0, metric="commanded"):
    """As [2], but the capsule is physically stopped `gap` metres short of the final point (a terrace
    step, a rock edge the navmesh reaches but the body can't): move_and_slide removes the radial motion."""
    p, v, stuck, t = (3.0, 0.0), (0.0, 0.0), 0.0, 0.0
    while t < seconds:
        if math.sqrt(p[0] ** 2 + dy ** 2) < PATH_DIST: return f"finished ({t:.2f} s)"
        horiz = abs(p[0]); pace = min(max(horiz / SLOW_DIST, MIN_PACE), 1.0)
        hv = move_toward(v, (-pace * MAX_SPEED, 0.0), ACCEL * DT)
        nx = p[0] + hv[0] * DT
        if nx <= gap: v, p = (0.0, 0.0), (gap, 0.0)           # blocked: slide leaves no velocity
        else: v, p = hv, (nx, 0.0)
        speed = math.hypot(*hv) if metric == "commanded" else math.hypot(*v)
        stuck = stuck + DT if speed < STUCK_SPEED else 0.0
        if stuck >= STUCK_SECONDS: return f"stall timeout ({t:.2f} s)"
        t += DT
    return f"NEVER ENDS: {seconds:.0f} s later still pressing {gap:.2f} m short of the point"
print("\n[2b] the final point is on the navmesh but the body is stopped short of it (no further input):")
for dy, gap in ((0.0, 0.5), (0.3, 0.45), (0.5, 0.2)):
    print(f"    {gap:.2f} m short, navmesh {dy:.2f} m off the feet: as coded -> {arrive_blocked(dy, gap)};"
          f" real-velocity metric -> {arrive_blocked(dy, gap, metric='actual')}")

# ---------------------------------------------------------------- 3. InputManager ghost finger (M03.5)
UI = _body(IM, "_unhandled_input")
assert "if _world_touches.size() >= 2:" in UI and "_tap_starts.clear()" in UI
assert "_world_touches" not in _body(IM, "_notification"), "nothing clears world touches on focus loss"
class IMPort:
    def __init__(s): s.touches, s.tap_starts, s.pinch, s.taps, s.zooms = {}, {}, 0.0, 0, 0
    def _two(s):
        if len(s.touches) != 2: return 0.0
        a, b = list(s.touches.values()); return math.dist(a, b)
    def touch(s, i, pressed, pos):
        (s.touches.__setitem__(i, pos) if pressed else s.touches.pop(i, None)); s.pinch = s._two()
        if len(s.touches) >= 2: s.tap_starts.clear(); return
        if pressed: s.tap_starts[i] = pos
        elif i in s.tap_starts: s.tap_starts.pop(i); s.taps += 1
    def drag(s, i, pos):
        if i not in s.touches: return
        s.touches[i] = pos; d = s._two()
        if s.pinch > 0 and d > 0: s.zooms += 1
        s.pinch = d
im = IMPort()
im.touch(1, True, (900, 500))            # a finger on the world ... its release never arrives (focus lost, shade, call)
for k in range(20):                      # the player then taps normally, and drags one finger
    im.touch(0, True, (300 + k, 300)); im.touch(0, False, (300 + k, 300))
im.touch(0, True, (300, 300)); im.drag(0, (360, 300)); im.drag(0, (420, 300)); im.touch(0, False, (420, 300))
print("\n[3] a world touch whose release is lost (M03.5 finger tracking):")
print(f"    20 normal taps afterwards -> taps recognised: {im.taps} (tap-to-move, tap-to-interact, tap-player-to-stop all dead)")
print(f"    one-finger drag afterwards -> zoom steps: {im.zooms} (single-finger drag zooms the camera: the signature)")
print("    exit without restart: none (only a press+release of the lost index clears it)")

# ---------------------------------------------------------------- 4. joystick ghost index (pre-existing)
GI = _body(JOY, "_gui_input")
assert "if touch.pressed and _touch_index == -1:" in GI and "_release()" in _body(JOY, "_on_visibility_changed")
class Joy:
    def __init__(j): j.index, j.raw = -1, (0.0, 0.0)
    def touch(j, i, pressed, vec=(0, 0)):
        if pressed and j.index == -1: j.index, j.raw = i, vec
        elif not pressed and i == j.index: j.index, j.raw = -1, (0.0, 0.0)
    def drag(j, i, vec):
        if i == j.index: j.raw = vec
    def hide(j): j.index, j.raw = -1, (0.0, 0.0)
jy = Joy(); jy.touch(1, True, (0.0, -1.0))   # thumb pushing up with finger index 1 ... release lost
jy.touch(0, True, (1.0, 0.0)); jy.drag(0, (1.0, 0.0)); jy.touch(0, False)
print("\n[4] a joystick touch whose release is lost (virtual_joystick.gd):")
print(f"    new joystick touches with another index are ignored; move_vector stays {jy.raw} -> the player walks by itself forever")
jy.hide(); print(f"    switching to Tap to Move hides the joystick and releases it: {jy.raw}")
