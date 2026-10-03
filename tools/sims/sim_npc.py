#!/usr/bin/env python3
"""NPC framework (M08.3) — a 2D model of the villager and the player, every constant read from
source (npc.gd, the villager's data, Npc.tscn, player.gd, Player.tscn, Meadow.tscn).
1. The approach: the player taps a wandering NPC and walks straight to where it was at the tap
   (Player's existing approach); the NPC holds still from the tap (its NpcTalk is tap-selected)
   and stays still while the player is within NOTICE_DISTANCE; the interaction happens when the
   player's InteractionZone reaches the NPC's talk sphere. Over 4,000 random wanders, starts
   (5-25 m) and tap moments the player always gets in range — never arrives at an empty spot. An
   NPC that stops only on proximity (it can drift across its wander disk first), or never stops,
   is shown to miss.
2. Facing: from any heading, the NPC faces the player within 25 degrees by 0.5 s after the talk.
3. Walking away closes the greeting exactly when the zone loses the talk sphere.
4. Wander targets (the same rule as npc.gd) stay within the data's radius of the NPC spot and
   DOOR_CLEARANCE from every AreaEntry of the Meadow (the house door's arrival point included).
5. A walk whose straight line crosses the NPC (the player's velocity is what the collision leaves
   of it; Player's 1 s stall timer applies): with the step aside — for a player heading at it, or
   touching it (head-on, the collision can cancel the player's velocity: seen at runtime) — every
   walk passes, never overlapping, the NPC within its leash; without it the walk stalls (shown).
"""
import math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def const(src, name):
    m = re.search(rf"^const {name} := ([-0-9.]+)", src, re.M); assert m, name; return float(m.group(1))
NPC = _src("scripts", "npc", "npc.gd"); PLAYER = _src("scripts", "player", "player.gd")
NOTICE, WALK, TURN = const(NPC, "NOTICE_DISTANCE"), const(NPC, "WALK_SPEED"), const(NPC, "TURN_SPEED")
IDLE_MIN, IDLE_MAX = const(NPC, "IDLE_SECONDS_MIN"), const(NPC, "IDLE_SECONDS_MAX")
YIELD_D, YIELD_V, LEASH, CLEAR = const(NPC, "YIELD_DISTANCE"), const(NPC, "YIELD_MIN_PLAYER_SPEED"), const(NPC, "YIELD_LEASH"), const(NPC, "DOOR_CLEARANCE")
CONTACT = const(NPC, "YIELD_CONTACT")
SPEED, ACCEL = const(PLAYER, "MAX_SPEED"), const(PLAYER, "ACCELERATION")
ZONE = float(re.search(r'id="SphereShape3D_interact"\]\nradius = ([0-9.]+)', _src("scenes", "player", "Player.tscn")).group(1))
P_CAPSULE = float(re.search(r'\[sub_resource type="CapsuleShape3D"[^\]]*\]\nradius = ([0-9.]+)', _src("scenes", "player", "Player.tscn")).group(1))
NS = _src("scenes", "npc", "Npc.tscn")
TALK_R = float(re.search(r'id="SphereShape3D_talk"\]\nradius = ([0-9.]+)', NS).group(1))
N_CAPSULE = float(re.search(r'id="CapsuleShape3D_body"\]\nradius = ([0-9.]+)', NS).group(1))
RADIUS = float(re.search(r"^wander_radius = ([0-9.]+)", _src("data", "npcs", "villager.tres"), re.M).group(1))
MEADOW = _src("scenes", "world", "Meadow.tscn")
spot = re.search(r'\[node name="NpcSpot" parent="VerticalSlice"[^\]]*\]\nposition = Vector3\(([^)]*)\)', MEADOW).group(1).split(",")
HOME = (float(spot[0]), float(spot[2]))
ENTRIES = [(float(p.split(",")[0]), float(p.split(",")[2])) for p in re.findall(r'position = Vector3\(([^)]*)\)\n(?:rotation_degrees = [^\n]*\n)?script = ExtResource\("entry"\)', MEADOW)]
assert len(ENTRIES) == 2, ENTRIES
REACH = ZONE + TALK_R
DT = 1 / 60

def dist(a, b): return math.hypot(a[0] - b[0], a[1] - b[1])
def clear(p): return all(dist(p, e) >= CLEAR for e in ENTRIES)

# ---------------------------------------------------------------- 4. wander targets
def wander_target(rng, home=HOME, radius=RADIUS):
    for _ in range(6):
        a = rng.uniform(0, math.tau); r = rng.uniform(0.4, radius)
        p = (home[0] + math.cos(a) * r, home[1] + math.sin(a) * r)
        if dist(p, home) <= radius and clear(p): return p
    return None
rng = random.Random(83)
targets = [t for t in (wander_target(rng) for _ in range(20000)) if t]
assert targets and all(dist(t, HOME) <= RADIUS + 1e-9 and clear(t) for t in targets), "wander targets stay home-bound and clear of entries"
assert clear(HOME), "the NPC spot itself is clear of every entry"

# ---------------------------------------------------------------- 1. the approach
class Villager:
    def __init__(v, rng, notice=NOTICE, stops=True, holds_when_tapped=True):
        v.rng, v.pos, v.target, v.idle, v.notice, v.stops = rng, HOME, None, rng.uniform(IDLE_MIN, IDLE_MAX), notice, stops
        v.holds, v.selected = holds_when_tapped, False
    def step(v, player):
        if v.stops and ((v.holds and v.selected) or dist(player, v.pos) <= v.notice):
            v.target = None; return
        if v.target:
            d = dist(v.target, v.pos)
            if d <= 0.3: v.target = None; v.idle = v.rng.uniform(IDLE_MIN, IDLE_MAX); return
            s = min(WALK * DT, d)
            v.pos = (v.pos[0] + (v.target[0] - v.pos[0]) / d * s, v.pos[1] + (v.target[1] - v.pos[1]) / d * s)
        else:
            v.idle -= DT
            if v.idle <= 0:
                v.target = wander_target(v.rng)
                if v.target is None: v.idle = v.rng.uniform(IDLE_MIN, IDLE_MAX)
def approach(seed, **kw):
    r = random.Random(seed); v = Villager(r, **kw)
    for _ in range(int(r.uniform(0, 20) / DT)): v.step((1e9, 1e9))           # wanders a while, player far away
    a = r.uniform(0, math.tau); d0 = r.uniform(5, 25)
    p = (v.pos[0] + math.cos(a) * d0, v.pos[1] + math.sin(a) * d0)
    goal = v.pos                                                             # Player walks to the tap-time position
    v.selected = True                                                        # the tap selects it (set_tap_selected)
    for _ in range(int(30 / DT)):
        if dist(p, v.pos) <= REACH: return True                              # InteractionZone overlaps the talk sphere
        g = dist(goal, p)
        if g <= 0.3: return False                                            # arrived where it was: nobody there
        s = min(SPEED * DT, g); p = (p[0] + (goal[0] - p[0]) / g * s, p[1] + (goal[1] - p[1]) / g * s)
        v.step(p)
    return False
N_TRIALS = 4000
misses = sum(not approach(i) for i in range(N_TRIALS))
assert misses == 0, f"{misses} approaches arrived at an empty spot"
no_hold = sum(not approach(i, holds_when_tapped=False) for i in range(N_TRIALS))
assert no_hold > 0, "an NPC that only stops on proximity (not on the tap) is shown to miss"
assert sum(not approach(i, stops=False) for i in range(N_TRIALS)) > 0, "an NPC that never stops is shown to miss"
assert "talk.is_tap_selected() or _flat_distance(player.global_position) <= NOTICE_DISTANCE" in NPC, "npc.gd holds still once tap-selected"

# ---------------------------------------------------------------- 2. facing
def facing_after(t, start_err):
    err = math.radians(start_err)
    for _ in range(int(t / DT)): err *= math.exp(-TURN * DT)              # lerp_angle with 1 - exp(-TURN * dt)
    return math.degrees(err)
assert facing_after(0.5, 180.0) <= 25.0, "faces the player within 25 degrees half a second into the talk"

# ---------------------------------------------------------------- 3. walking away
close_at = REACH
assert ZONE < close_at <= ZONE + 1.0, "the greeting closes when the zone loses the talk sphere, about 3 m away"

# ---------------------------------------------------------------- 5. stepping aside
def walk_through(offset, yields, contact=True, commit=True):
    """Player walks from (-3, offset) to (3, offset) through an NPC at the origin. The player's
    velocity after a step is what the collision leaves of it (Godot's slide), rebuilt by Player's
    acceleration: pressed head-on against the NPC it stays near 0, so only the contact rule still
    sees the player."""
    p, n, goal = (-3.0, offset), (0.0, 0.0), (3.0, offset)
    home = n; minimum = 9.0; seen_vel = (SPEED, 0.0); stuck = 0.0; committed = None
    for _ in range(int(10 / DT)):
        g = dist(goal, p)
        if g <= 0.3: return True, minimum, dist(n, home)
        want = ((goal[0] - p[0]) / g * SPEED, (goal[1] - p[1]) / g * SPEED)
        dv = (want[0] - seen_vel[0], want[1] - seen_vel[1]); dl = math.hypot(*dv); a = ACCEL * DT   # Player's move_toward
        vel = want if dl <= a else (seen_vel[0] + dv[0] / dl * a, seen_vel[1] + dv[1] / dl * a)
        to_me = (n[0] - p[0], n[1] - p[1]); tl = math.hypot(*to_me)
        moving = math.hypot(*seen_vel) >= YIELD_V
        heading = moving and tl <= YIELD_D and seen_vel[0] * to_me[0] + seen_vel[1] * to_me[1] > 0
        touching = contact and tl <= CONTACT
        if yields and (heading or touching):
            if committed is None or not commit:
                line = seen_vel if moving else to_me
                side = (-line[1], line[0]); sl = math.hypot(*side); side = (side[0] / sl, side[1] / sl)
                if side[0] * to_me[0] + side[1] * to_me[1] < 0: side = (-side[0], -side[1])
                committed = side
            step = (n[0] + committed[0] * WALK * DT, n[1] + committed[1] * WALK * DT)
            if dist(step, home) <= RADIUS + LEASH: n = step
        elif yields:
            committed = None
        q = (p[0] + vel[0] * DT, p[1] + vel[1] * DT)                       # move, then slide along the NPC's capsule
        d = dist(q, n); r = P_CAPSULE + N_CAPSULE
        if d < r:
            nx, nz = (q[0] - n[0]) / d, (q[1] - n[1]) / d
            q = (n[0] + nx * r, n[1] + nz * r)
        seen_vel = ((q[0] - p[0]) / DT, (q[1] - p[1]) / DT)
        stuck = stuck + DT if math.hypot(*seen_vel) < 0.25 else 0.0         # Player's stall timer (1 s below 0.25 m/s)
        if stuck >= 1.0: return False, minimum, dist(n, home)
        p = q; minimum = min(minimum, dist(p, n))
    return False, minimum, dist(n, home)
passes = [walk_through(o, True) for o in (0.0, 0.05, -0.05, 0.12, -0.12)]
assert all(ok for ok, _, _ in passes), f"walks across the NPC pass with the step aside {passes}"
assert all(m >= P_CAPSULE + N_CAPSULE - 1e-6 for _, m, _ in passes), "never overlapping"
assert all(h <= RADIUS + LEASH + 1e-6 for _, _, h in passes), "the NPC stays within its leash"
assert not walk_through(0.0, False)[0], "without the step aside a head-on walk locks (shown)"
assert "if _yield_side == Vector3.ZERO:" in NPC and "_yield_side = Vector3.ZERO" in NPC, "npc.gd commits to one side while yielding"

print(f"npc: villager radius {RADIUS} m at NpcSpot {HOME}, entries {ENTRIES} cleared by {CLEAR} m ({len(targets)} wander targets checked); "
      f"notice {NOTICE} m > reach {REACH:.2f} m (zone {ZONE} + talk {TALK_R}); {N_TRIALS} random approaches never miss "
      f"(proximity-only stopping shown to miss {no_hold}, never stopping shown to miss); faces within 25 deg by 0.5 s; closes at {close_at:.2f} m; "
      f"head-on walks pass with the step aside (min gap {min(m for _, m, _ in passes):.2f} m), lock without it")
print("ALL NPC SIMULATIONS PASSED")
