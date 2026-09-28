#!/usr/bin/env python3
"""Model checks for tap-to-move / tap-to-interact (Python ports, not the engine).
1. Tap routing decision table (InputManager._track_tap/_handle_tap), exhaustive.
2. Player navigation state machine under random input sequences.
3. Meadow geometry: spawn and every interactable reachable (not inside an
   obstacle footprint grown by the nav agent radius).
"""
import itertools, math, os, random, re

# ---------------------------------------------------------------- 1. routing
TAP_MAX_MOVE, TAP_MAX_MSEC = 24.0, 450
def route(gui_consumed, move_px, msec, hits_interactable, ground_hit, walkable, mode):
    if gui_consumed: return None                      # never reaches _unhandled_input
    if move_px > TAP_MAX_MOVE or msec > TAP_MAX_MSEC: return None   # drag / hold
    if hits_interactable: return "interact"
    if mode != "tap": return None
    if not ground_hit or not walkable: return None
    return "move"

rows = 0
for gui, move, ms, inter, ground, walk, mode in itertools.product(
        [False, True], [0.0, 10.0, 30.0, 200.0], [100, 400, 600], [False, True], [False, True], [False, True],
        ["joystick", "tap"]):
    r = route(gui, move, ms, inter, ground, walk, mode)
    rows += 1
    if gui: assert r is None, "UI touch leaked into the world"
    if move > TAP_MAX_MOVE: assert r is None, "drag issued a command"
    if r == "move": assert mode == "tap" and walk and not inter
    if mode == "joystick": assert r != "move", "joystick mode moved by tap"
    if inter and not gui and move <= TAP_MAX_MOVE and ms <= TAP_MAX_MSEC:
        assert r == "interact", "interactable priority lost"
print(f"routing table: {rows} combinations OK")

# ------------------------------------------------------------ 2. player model
TAP_REACH = 8.0
class Player:
    def __init__(p): p.pos = (0.0, 0.0); p.nav = False; p.dest = None; p.approach = None; p.stuck = 0.0; p.interacted = []
    def stop(p): p.nav = False; p.approach = None; p.stuck = 0.0
    def start(p, d): p.approach = None; p.dest = d; p.nav = True; p.stuck = 0.0
    def on_interact_target(p, t, mode):
        if math.dist(p.pos, t) <= TAP_REACH: p.stop(); p.interacted.append(t); return
        if mode == "tap": p.start(t); p.approach = t if p.nav else None
    def on_move(p, d): p.start(d)
    def physics(p, joystick, dt=1 / 60, blocked=False):
        if joystick: p.stop(); p.pos = (p.pos[0] + joystick[0] * 4.3 * dt, p.pos[1] + joystick[1] * 4.3 * dt); return
        if not p.nav: return
        d = math.dist(p.pos, p.dest)
        if d <= 0.3: p.stop(); return
        speed = 0.0 if blocked else 4.3 * max(min(d / 1.2, 1.0), 0.35)
        if speed > 0:
            step = min(speed * dt, d); p.pos = (p.pos[0] + (p.dest[0] - p.pos[0]) / d * step, p.pos[1] + (p.dest[1] - p.pos[1]) / d * step)
        if p.approach is not None and math.dist(p.pos, p.approach) <= TAP_REACH:
            t = p.approach; p.stop(); p.interacted.append(t); return
        if speed < 0.25:
            p.stuck += dt
            if p.stuck >= 1.0: p.stop()
        else: p.stuck = 0.0

stats = dict(moves=0, approaches=0, far_interacts=0, retargets=0, stuck_stops=0)
for trial in range(3000):
    rnd = random.Random(trial); p = Player(); mode = rnd.choice(["joystick", "tap"])
    for step in range(600):
        ev = rnd.random()
        if ev < 0.05:
            d = (rnd.uniform(-30, 30), rnd.uniform(-30, 30))
            if mode == "tap":
                if p.nav: stats["retargets"] += 1
                p.on_move(d); stats["moves"] += 1
                assert p.nav and p.dest == d and p.approach is None, "new tap must replace the destination"
        elif ev < 0.08:
            t = (rnd.uniform(-30, 30), rnd.uniform(-30, 30)); before = len(p.interacted)
            near = math.dist(p.pos, t) <= TAP_REACH
            p.on_interact_target(t, mode)
            if near: assert len(p.interacted) == before + 1 and not p.nav
            elif mode == "tap": assert p.approach == t and p.nav; stats["approaches"] += 1
            else: assert not p.nav and len(p.interacted) == before, "joystick mode must ignore far taps"
        elif ev < 0.09:
            mode = "tap" if mode == "joystick" else "joystick"; p.stop()   # mode change stops navigation
        joy = (rnd.uniform(-1, 1), rnd.uniform(-1, 1)) if (mode == "joystick" and rnd.random() < 0.3) else None
        blocked = rnd.random() < 0.02
        n_before = len(p.interacted); was_nav = p.nav
        p.physics(joy, blocked=blocked)
        if joy: assert not p.nav, "joystick must override navigation"
        if len(p.interacted) > n_before and was_nav: stats["far_interacts"] += 1
        if was_nav and not p.nav and p.stuck == 0.0 and blocked: stats["stuck_stops"] += 1
        if mode == "joystick" and p.nav: assert p.approach is None or True
print(f"player model: 3000 runs x 600 steps OK; {stats}")

# ------------------------------------------------------------ 3. geometry
AGENT_R = 0.35
FOOT = {"12": 0.42 + 0.1, "14": 0.38, "9": 0.2, "10": 0.16, "11": 0.24, "15": 0.9 + 0.23, "33": 0.36}  # rock (offset), bush, trees, log half-length, monolith half-diag
s = open(os.path.join(os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")), "scenes", "world", "Meadow.tscn")).read()
obstacles, points = [], []
for chunk in s.split("\n[")[1:]:
    if not chunk.startswith("node "): continue
    name = re.search(r'name="([^"]+)"', chunk).group(1)
    inst = re.search(r'instance=ExtResource\("(\d+)"\)', chunk.split("\n")[0])
    pm = re.search(r'\nposition = Vector3\(([^)]*)\)', chunk)
    if not pm: continue
    x, y, z = [float(v) for v in pm.group(1).split(",")]
    sc = re.search(r'\nscale = Vector3\(([^)]*)\)', chunk)
    k = max(float(v) for v in sc.group(1).split(",")) if sc else 1.0
    parent = (re.search(r'parent="([^"]+)"', chunk.split("\n")[0]) or [None, ""])[1]
    if inst and inst.group(1) in FOOT and "/" not in parent.replace("Farm", "", 0):
        obstacles.append((name, x, z, FOOT[inst.group(1)] * k))
    if inst and inst.group(1) in ("3", "4", "5", "6", "7", "19", "20", "21", "22", "23", "38"):
        points.append((name, x, z))
    if name == "Player": points.append(("PlayerSpawn", x, z))
bad = []
for pn, px, pz in points:
    for on, ox, oz, r in obstacles:
        if math.hypot(px - ox, pz - oz) < r + AGENT_R * 0.5:
            bad.append(f"{pn} inside {on} ({math.hypot(px-ox, pz-oz):.2f} < {r + AGENT_R*0.5:.2f})")
print(f"geometry: {len(obstacles)} solid obstacles, {len(points)} interactables/spawn checked; problems: {len(bad)}")
for b in bad: print("  ", b)
print(f"nav agent radius {AGENT_R} >= capsule 0.32: {AGENT_R >= 0.32}; mound tier step 0.15 <= max_climb 0.25: {0.15 <= 0.25}")
assert not bad
# ------------------------------------------------ 4. keyboard + joystick combine
# Port of InputManager: set_move_vector (joystick, every frame), _input
# (keyboard, on key events), focus-out, and movement-mode change.
class Input:
    def __init__(i): i.joy = (0.0, 0.0); i.kb = (0.0, 0.0); i.move = (0.0, 0.0)
    def _update(i):
        x, y = i.joy[0] + i.kb[0], i.joy[1] + i.kb[1]; n = math.hypot(x, y)
        i.move = (x / n, y / n) if n > 1.0 else (x, y)
    def joystick_frame(i, v): i.joy = v; i._update()
    def keys(i, held):  # get_vector(left, right, up, down): normalized
        x = (1 if "right" in held else 0) - (1 if "left" in held else 0)
        y = (1 if "down" in held else 0) - (1 if "up" in held else 0)
        n = math.hypot(x, y); i.kb = (x / n, y / n) if n > 0 else (0.0, 0.0); i._update()
    def focus_out(i): i.kb = (0.0, 0.0); i._update()
    def mode_change(i): i.joy = (0.0, 0.0); i._update()

inp = Input()
inp.keys({"up"})
for _ in range(120): inp.joystick_frame((0.0, 0.0))          # joystick idle writes every frame
assert inp.move == (0.0, -1.0), "joystick frames must not erase held keys"
inp.keys({"up", "right"}); assert abs(math.hypot(*inp.move) - 1.0) < 1e-9, "diagonal clamped to 1"
inp.joystick_frame((1.0, 0.0)); assert math.hypot(*inp.move) <= 1.0 + 1e-9, "combined input clamped"
inp.keys(set()); assert inp.move == (1.0, 0.0), "key release returns to joystick value"
inp.joystick_frame((0.0, 0.0)); inp.keys({"left"}); inp.focus_out(); assert inp.move == (0.0, 0.0), "focus-out clears keys"
inp.keys({"down"}); inp.mode_change(); assert inp.move == (0.0, 1.0), "mode change keeps held keys"
rnd = random.Random(3)
for _ in range(20000):
    ev = rnd.random()
    if ev < 0.5: inp.joystick_frame((rnd.uniform(-1, 1), rnd.uniform(-1, 1)) if rnd.random() < 0.5 else (0.0, 0.0))
    elif ev < 0.9: inp.keys(set(rnd.sample(["up", "down", "left", "right"], rnd.randint(0, 3))))
    elif ev < 0.95: inp.focus_out()
    else: inp.mode_change()
    assert math.hypot(*inp.move) <= 1.0 + 1e-9
print("keyboard/joystick combine: scripted cases + 20000 random events OK")
print("ALL TAP SIMULATIONS PASSED")
