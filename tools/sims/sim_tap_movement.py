#!/usr/bin/env python3
"""Model checks for tap-to-move / tap-to-interact (Python ports, not the engine).
1. Tap routing decision table (InputManager._track_tap/_handle_tap), exhaustive;
   mode-independent; constants read from the GDScript.
2. Player tap state machine: walk-to-interact on InteractionZone entry, the
   exact target preserved, retargeting, joystick/keyboard cancellation.
   Facing on arrival (M02.3): accept -> face the target -> interact, from the
   target's position (behind/side/underfoot), never for a cancelled or
   replaced target; walking faces the path, not a target.
3. Meadow geometry: spawn, every interactable and the NPC spot (M07.2) reachable
   (not inside an obstacle footprint grown by the nav agent radius; the forest-edge
   trees and the house placeholder count as obstacles). The pond's blocked core
   (M07.3, O-07B) is an obstacle too; a discovery inside it must be within the
   Player's INTERACTION_RADIUS (0.3 m to spare) of the walkable edge.
"""
import itertools, math, os, random, re

# ---------------------------------------------------------------- 1. routing
# Constants come from the GDScript itself, so the model can't drift from it.
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_IM = open(os.path.join(REPO, "scripts", "autoload", "input_manager.gd")).read()
def _const(name, src=_IM):
    return float(re.search(rf"^const {name} := ([0-9.]+)", src, re.M).group(1))
TAP_MAX_MOVE, TAP_MAX_MSEC = _const("TAP_MAX_MOVE"), _const("TAP_MAX_MSEC")
SNAP_H, SNAP_V = _const("WALKABLE_SNAP_HORIZONTAL"), _const("WALKABLE_SNAP_VERTICAL")
SELECT_TOL = _const("TAP_SELECT_TOLERANCE")
PLAYER_TAP_R = _const("PLAYER_TAP_RADIUS")
ZONE_R = float(re.search(r'SphereShape3D_interact"\]\s*radius = ([0-9.]+)',
                         open(os.path.join(REPO, "scenes", "player", "Player.tscn")).read()).group(1))
_PL_SRC = open(os.path.join(REPO, "scripts", "player", "player.gd")).read()
FACE_MIN = _const("FACE_TARGET_MIN_DISTANCE", _PL_SRC)
_IW = re.search(r"^func _interact_with\(.*?(?=^func )", _PL_SRC, re.M | re.S).group(0)
assert _IW.find("is_interaction_available()") < _IW.find("_face_target(target)") < _IW.find("target.interact()"), \
    "the model's order (accept, face, interact) is the script's"
assert "_facing_angle = atan2(to_target.x, -to_target.z)" in _PL_SRC and "_facing_angle = atan2(direction.x, -direction.z)" in _PL_SRC

def route(gui_consumed, move_px, msec, ray_hit, ray_hit_active, player_tap, near_active, ground_hit, has_mesh, snap_h, snap_v):
    """Port of InputManager._track_tap + _handle_tap. Mode is deliberately
    not an input: taps behave the same in Joystick and Tap to Move."""
    if gui_consumed: return None                                   # never reaches _unhandled_input
    if move_px > TAP_MAX_MOVE or msec > TAP_MAX_MSEC: return None   # drag / hold
    if ray_hit and ray_hit_active: return "interact:exact"
    if not ground_hit: return None
    if player_tap: return "stop"                                    # tap the player = deliberate stop
    if near_active: return "interact:near"                          # small-object tolerance
    if not has_mesh: return "move:direct"                           # mesh not built yet
    if snap_h > SNAP_H or snap_v > SNAP_V: return None              # top of an obstacle / off the edge
    return "move:snapped"

rows = 0
for combo in itertools.product([False, True], [0.0, 10.0, 30.0], [100, 400, 600], [False, True], [False, True],
                               [False, True], [False, True], [False, True], [False, True], [0.0, 0.3, 0.9, 1.5], [0.0, 0.8]):
    gui, move, ms, hit, hit_active, ptap, near, ground, mesh, sh, sv = combo
    r = route(*combo); rows += 1
    tap = not gui and move <= TAP_MAX_MOVE and ms <= TAP_MAX_MSEC
    if gui: assert r is None, "UI touch leaked into the world"
    if move > TAP_MAX_MOVE: assert r is None, "drag issued a command"
    if tap and hit and hit_active: assert r == "interact:exact", "exact interactable must win"
    if tap and not (hit and hit_active) and ground and ptap: assert r == "stop", "tapping the player must stop"
    free = tap and not (hit and hit_active) and ground and not ptap
    if free and hit and not hit_active and not near and mesh and sh <= SNAP_H and sv <= SNAP_V:
        assert r == "move:snapped", "an inactive interactable must not block the ground"
    if free and not near and mesh and sh <= SNAP_H and sv <= SNAP_V:
        assert r == "move:snapped", "walkable ground tap must move"
    if free and near: assert r == "interact:near", "small-object tolerance"
    if free and not near and not mesh: assert r == "move:direct"
    if r and r.startswith("move"): assert not (hit and hit_active) and not near and not ptap
    if r == "stop": assert not (hit and hit_active), "an exact interactable hit wins over stop"
print(f"routing table: {rows} combinations OK (mode-independent; snap {SNAP_H} m, select tolerance {SELECT_TOL} m, player tap {PLAYER_TAP_R} m)")
assert SNAP_H >= 0.5, "snap tolerance must reach past the nav agent radius around obstacles"

# ------------------------------------------------------------ 2. player model
# Port of Player tap handling. Interaction range = the InteractionZone
# sphere (from Player.tscn): an object is "in range" once the zone overlaps
# its shape; interaction fires on that zone-entry event, never earlier.
class Player:
    def __init__(p):
        p.pos = (0.0, 0.0); p.nav = False; p.dest = None; p.approach = None
        p.stuck = 0.0; p.interacted = []; p.nearby = set()
        p.facing = 0.0; p.events = []  # (kind, id): "face" / "interact", in order
    def interact_with(p, t):  # _interact_with: face the target, then interact
        dx, dz = t["pos"][0] - p.pos[0], t["pos"][1] - p.pos[1]
        if math.hypot(dx, dz) >= FACE_MIN:
            p.facing = math.atan2(dx, -dz); p.events.append(("face", t["id"]))
        p.events.append(("interact", t["id"])); p.interacted.append(t["id"])
    def face_move(p, dx, dz):  # _update_facing: the intended movement direction
        if dx * dx + dz * dz > 0.01: p.facing = math.atan2(dx, -dz)
    def in_zone(p, t): return math.dist(p.pos, t["pos"]) <= ZONE_R + t["r"]
    def stop(p): p.nav = False; p.approach = None; p.stuck = 0.0
    def start(p, d): p.approach = None; p.dest = d; p.nav = True; p.stuck = 0.0
    def on_interact_target(p, t):
        if t["id"] in p.nearby: p.stop(); p.interact_with(t); return
        p.start(t["pos"]); p.approach = t
    def on_move(p, d): p.start(d)
    def on_stop(p): p.stop()
    def zone_update(p, objects):  # area_entered / area_exited
        for t in objects:
            inside = p.in_zone(t)
            if inside and t["id"] not in p.nearby:
                p.nearby.add(t["id"])
                if p.approach is not None and p.approach["id"] == t["id"]:
                    tgt = p.approach; p.stop(); p.interact_with(tgt)
            elif not inside: p.nearby.discard(t["id"])
    def physics(p, move_vector, objects, dt=1 / 60, blocked=False):
        if move_vector:
            p.stop(); p.face_move(*move_vector)
            p.pos = (p.pos[0] + move_vector[0] * 4.3 * dt, p.pos[1] + move_vector[1] * 4.3 * dt)
        elif p.nav:
            d = math.dist(p.pos, p.dest)
            if d <= 0.3: p.stop()
            else:
                speed = 0.0 if blocked else 4.3 * max(min(d / 1.2, 1.0), 0.35)
                step = min(speed * dt, d)
                p.face_move((p.dest[0] - p.pos[0]) / d, (p.dest[1] - p.pos[1]) / d)
                if step > 0: p.pos = (p.pos[0] + (p.dest[0] - p.pos[0]) / d * step, p.pos[1] + (p.dest[1] - p.pos[1]) / d * step)
                if speed < 0.25:
                    p.stuck += dt
                    if p.stuck >= 1.0: p.stop()
                else: p.stuck = 0.0
        p.zone_update(objects)

def objects_for(rnd):
    return [{"id": f"o{i}", "pos": (rnd.uniform(-30, 30), rnd.uniform(-30, 30)), "r": rnd.choice([0.18, 0.2, 0.55])}
            for i in range(12)]

# scripted cases
objs = [{"id": "flower", "pos": (20.0, 0.0), "r": 0.18}]
p = Player(); p.on_interact_target(objs[0])
assert p.nav and p.approach["id"] == "flower" and p.interacted == [], "far tap: walk first, no instant interaction"
frames = 0
while p.nav and frames < 2000: p.physics(None, objs); frames += 1
assert p.interacted == ["flower"], "interacts on reaching range"
assert math.dist(p.pos, (20.0, 0.0)) > 1.5, "stops at interaction range, not on top of the object"
print(f"far flower: walked {frames} frames, interacted at {math.dist(p.pos, (20.0, 0.0)):.2f} m (zone {ZONE_R} m + shape)")
p = Player(); p.on_move((10.0, 0.0)); p.on_move((0.0, 10.0)); assert p.dest == (0.0, 10.0) and p.approach is None, "new tap replaces"
p = Player(); p.on_move((10.0, 0.0)); p.on_interact_target(objs[0]); assert p.approach["id"] == "flower", "interactable replaces move target"
p = Player(); p.on_interact_target(objs[0]); p.physics((1.0, 0.0), objs); assert not p.nav and p.approach is None, "joystick/keyboard cancels"
p = Player(); p.pos = (19.0, 0.0); p.zone_update(objs); p.on_interact_target(objs[0]); assert p.interacted == ["flower"] and not p.nav, "in range: immediate"
p = Player(); p.on_move((10.0, 0.0)); p.on_stop(); assert not p.nav and p.approach is None, "tap-player stops a walk"
p = Player(); p.on_interact_target(objs[0]); p.on_stop()
for _ in range(2000): p.physics(None, objs)
assert p.interacted == [] and not p.nav, "stop cancels a pending interaction"
p = Player(); p.on_stop(); assert not p.nav and p.interacted == [], "stop while idle is harmless"

# facing on arrival (M02.3): accept -> face target -> interact
def angle_to(p, pos): return math.atan2(pos[0] - p.pos[0], -(pos[1] - p.pos[1]))
def same_angle(a, b): return abs(math.remainder(a - b, math.tau)) < 1e-9
p = Player(); p.on_interact_target(objs[0])
while p.nav: p.physics(None, objs)
assert p.events[-2:] == [("face", "flower"), ("interact", "flower")], "arrival -> face -> interact"
assert same_angle(p.facing, angle_to(p, (20.0, 0.0)))
for label, pos in (("behind", (0.0, 1.5)), ("left", (-1.5, 0.0)), ("right", (1.5, 0.0)), ("ahead", (0.0, -1.5))):
    p = Player(); p.facing = 0.0; t = {"id": label, "pos": pos, "r": 0.2}
    p.zone_update([t]); p.on_interact_target(t)
    assert p.events == [("face", label), ("interact", label)], f"in range ({label}): face before interacting"
    assert same_angle(p.facing, {"behind": math.pi, "left": -math.pi / 2, "right": math.pi / 2, "ahead": 0.0}[label]), (label, p.facing)
p = Player(); p.facing = 1.0; t = {"id": "underfoot", "pos": (0.0, 0.0), "r": 0.2}
p.zone_update([t]); p.on_interact_target(t)
assert p.facing == 1.0 and not math.isnan(p.facing) and p.events == [("interact", "underfoot")], "no direction: facing kept"
p = Player(); p.on_interact_target(objs[0]); p.physics(None, objs); p.on_stop()
for _ in range(2000): p.physics(None, objs)
assert p.events == [], "a cancelled target is never faced"
a, b = {"id": "a", "pos": (5.0, 0.0), "r": 0.2}, {"id": "b", "pos": (20.0, 0.0), "r": 0.2}
p = Player(); p.on_interact_target(a); p.on_interact_target(b)
while p.nav: p.physics(None, [a, b])
assert p.events == [("face", "b"), ("interact", "b")], "a replaced target is never faced, even when passed on the way"
p = Player(); p.on_interact_target(objs[0]); fac = []
for _ in range(60): p.physics(None, objs); fac.append(p.facing)
assert all(same_angle(f, math.atan2(1.0, -0.0)) for f in fac) and p.events == [], "walking faces the path, not a target lock"
print("facing: arrival/in-range/behind/left/right/underfoot/cancel/replace OK")

stats = dict(taps=0, approaches=0, zone_interactions=0, cancels=0, retargets=0)
for trial in range(2000):
    rnd = random.Random(trial); p = Player(); objs = objects_for(rnd); p.zone_update(objs)
    for step in range(600):
        ev = rnd.random()
        if ev < 0.05:
            d = (rnd.uniform(-30, 30), rnd.uniform(-30, 30))
            if p.nav: stats["retargets"] += 1
            p.on_move(d); stats["taps"] += 1
            assert p.nav and p.dest == d and p.approach is None
        elif ev < 0.1 and ev >= 0.09:
            p.on_stop(); assert not p.nav and p.approach is None
        elif ev < 0.09:
            t = rnd.choice(objs); before = list(p.interacted); was_near = t["id"] in p.nearby
            p.on_interact_target(t)
            if was_near: assert p.interacted == before + [t["id"]] and not p.nav
            else: assert p.approach is t and p.nav and p.interacted == before; stats["approaches"] += 1
        mv = (rnd.uniform(-1, 1), rnd.uniform(-1, 1)) if rnd.random() < 0.15 else None
        approach_before = p.approach; n_before = len(p.interacted); was_nav = p.nav
        p.physics(mv, objs, blocked=rnd.random() < 0.02)
        if mv: assert not p.nav and p.approach is None; stats["cancels"] += was_nav
        if len(p.interacted) > n_before and not mv and approach_before is not None and was_nav:
            assert p.interacted[-1] == approach_before["id"], "the exact tapped object is the one interacted with"
            t = approach_before; assert p.in_zone(t), "interaction only once in range"
            stats["zone_interactions"] += 1
        if p.approach is not None: assert p.nav, "an approach target implies an active walk"
        for i, (kind, oid) in enumerate(p.events):
            if kind == "face": assert p.events[i + 1] == ("interact", oid), "every face is immediately followed by its interaction"
        if len(p.interacted) > n_before and not mv:
            t = next(o for o in objs if o["id"] == p.interacted[-1])
            if math.dist(p.pos, t["pos"]) >= FACE_MIN:
                assert p.events[-2:] == [("face", t["id"]), ("interact", t["id"])] and same_angle(p.facing, angle_to(p, t["pos"]))
print(f"player model: 2000 runs x 600 steps OK; {stats}")

# ------------------------------------------------------------ 3. geometry
AGENT_R = 0.35
FOOT = {"12": 0.42 + 0.1, "14": 0.38, "9": 0.2, "10": 0.16, "11": 0.24, "15": 0.9 + 0.23, "33": 0.36,  # rock (offset), bush, trees, log half-length, monolith half-diag
        "41": math.hypot(3.0, 2.5),                                     # M07.2: the 6 x 5 m house placeholder, as its half-diagonal (conservative)
        "17": float(re.search(r'id="CylinderShape3D_core"\]\nradius = ([0-9.]+)', open(os.path.join(REPO, "scenes", "world", "props", "PondWater.tscn")).read()).group(1))}
REACH_ONLY = {"17"}   # M07.3 (O-07B): discoveries inside the pond's blocked core are reached by the interaction range, not by standing on them
INTERACTION_R = _const("INTERACTION_RADIUS", _PL_SRC)
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
        obstacles.append((name, x, z, FOOT[inst.group(1)] * k, inst.group(1) in REACH_ONLY))
    if inst and inst.group(1) in ("3", "4", "5", "6", "7", "19", "20", "21", "22", "23", "38", "42"):   # 42: the NPC spot (M07.2) must be reachable
        points.append((name, x, z))
# The player now lives in the persistent Main scene (M03.1), with the Meadow
# instanced at the origin — so its position there is its Meadow position.
_main = open(os.path.join(REPO, "scenes", "Main.tscn")).read()
assert not re.search(r'\[node name="Meadow"[^\n]*\]\n(position|transform)', _main), "Meadow instanced at the origin"
_pp = re.search(r'\[node name="Player" parent="\." [^\n]*\]\nposition = Vector3\(([^)]*)\)', _main)
assert _pp, "Main.tscn places the Player"
_px, _, _pz = [float(v) for v in _pp.group(1).split(",")]
points.append(("PlayerSpawn", _px, _pz))
bad, by_reach = [], []
for pn, px, pz in points:
    for on, ox, oz, r, reach_only in obstacles:
        d = math.hypot(px - ox, pz - oz)
        if d < r + AGENT_R * 0.5:
            if reach_only and pn != "PlayerSpawn" and (r + AGENT_R) - d <= INTERACTION_R - 0.3:
                by_reach.append(f"{pn} ({(r + AGENT_R) - d:.2f} m from the {on} edge)")
                continue
            bad.append(f"{pn} inside {on} ({d:.2f} < {r + AGENT_R*0.5:.2f})")
print(f"geometry: {len(obstacles)} solid obstacles, {len(points)} interactables/spawn checked; problems: {len(bad)}; reached from the pond edge: {by_reach}")
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
# ------------------------------------------------ 5. animation state hook
# Port of Player's IDLE/WALK/INTERACT state (constants read from player.gd).
_PL = open(os.path.join(REPO, "scripts", "player", "player.gd")).read()
WALK_START, WALK_STOP = _const("WALK_START_SPEED", _PL), _const("WALK_STOP_SPEED", _PL)
assert WALK_START > WALK_STOP, "hysteresis needs start > stop"
class Anim:
    def __init__(a): a.state = "IDLE"; a.changes = []; a.serial = 0; a.target = None; a.speed = 0.0
    def set(a, st):
        if st == a.state: return
        a.changes.append((a.state, st)); a.state = st
    def physics(a, speed):
        a.speed = speed
        if a.state == "INTERACT": return
        if a.state == "WALK":
            if speed < WALK_STOP: a.set("IDLE")
        elif speed > WALK_START: a.set("WALK")
    def begin(a, target):
        a.serial += 1; a.target = target; a.set("INTERACT"); return a.serial
    def end(a, serial):
        if serial != a.serial or a.target is None: return
        a.target = None; a.set("WALK" if a.speed >= WALK_STOP else "IDLE")
    def exiting(a): a.end(a.serial)

a = Anim(); a.physics(0.0); assert a.state == "IDLE" and a.changes == []
a.physics(2.0); assert a.state == "WALK", "IDLE -> WALK on real movement"
a.physics(0.5); assert a.state == "WALK"
a.physics(0.05); assert a.state == "IDLE", "WALK -> IDLE when stopped / arrived / cancelled"
s1 = a.begin("flower"); assert a.state == "INTERACT", "IDLE -> INTERACT"
a.physics(3.0); assert a.state == "INTERACT", "stays INTERACT while the interaction runs, even if moving"
a.end(s1); assert a.state == "WALK", "INTERACT -> WALK if moving when it ends"
a.physics(0.0); assert a.state == "IDLE"
a.physics(2.0); s2 = a.begin("plot"); assert (("WALK", "INTERACT") in a.changes), "WALK -> INTERACT"
a.physics(0.0); a.end(s2); assert a.state == "IDLE", "INTERACT -> IDLE"
s3 = a.begin("gone"); a.physics(0.0); a.exiting(); assert a.state == "IDLE", "object vanished -> IDLE"
s4 = a.begin("fails"); a.end(s4); assert a.state == "IDLE", "failed/instant interaction -> IDLE"
s5 = a.begin("first"); s6 = a.begin("second"); a.end(s5); assert a.state == "INTERACT", "stale end ignored"
a.end(s6); assert a.state == "IDLE"
a = Anim(); a.physics(2.0)
for v in [0.3, 0.2, 0.3, 0.2, 0.3]: a.physics(v)                # hovering between the thresholds
assert a.changes == [("IDLE", "WALK")], "no IDLE/WALK flicker between thresholds"
rnd = random.Random(11); a = Anim(); open_serials = []
for _ in range(50000):
    ev = rnd.random()
    if ev < 0.6: a.physics(rnd.choice([0.0, 0.1, 0.2, 0.4, 1.0, 4.3]))
    elif ev < 0.75: open_serials.append(a.begin(rnd.random()))
    elif ev < 0.9 and open_serials: a.end(open_serials.pop(rnd.randrange(len(open_serials))))
    else: a.exiting()
    assert a.state in ("IDLE", "WALK", "INTERACT")
    assert (a.state == "INTERACT") == (a.target is not None), "INTERACT exactly while an interaction is open"
    for prev, new in a.changes[-1:]: assert prev != new
print(f"animation state: scripted transitions + 50000 random events OK (walk {WALK_START}/{WALK_STOP} m/s)")
print("ALL TAP SIMULATIONS PASSED")
