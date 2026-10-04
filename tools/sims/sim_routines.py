#!/usr/bin/env python3
"""NPC routines (M09.1, D-41) — a model of the villager following the day, its rules read from npc.gd,
npc_routine_spot.gd, world_simulation.gd, time_of_day.gd, the villager's data and Meadow.tscn.
1. The routine names a spot for every time-of-day phase: morning/afternoon by the pond path, dawn/evening/night at
   home (the NPC spot). The first phase the NPC knows places it at that phase's spot — read from the clock's own
   fraction, so a stale cached phase (before the clock's first tick, or after a restored time) never sends it to
   the wrong spot; every later phase change makes it walk there (never a jump).
2. Talking always wins: while the player is near or has tapped it, it holds still (moving only to step aside) and
   walks on afterwards; a phase change mid-conversation waits. On the way, a step aside keeps clear of doors without
   the home leash, so a player walking into a travelling NPC never deadlocks.
3. While its area is parked nothing advances (clock and NPC together); nothing is saved.
20,000 random days (taps, approaches, conversations, parking); designs that read the cached phase first, jump on
every phase, walk off mid-conversation or keep the home leash while travelling are shown to break the rules.
"""
import math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
NPC, TOD, WS, SPOT = _src("scripts", "npc", "npc.gd"), _src("scripts", "world_simulation", "time_of_day.gd"), _src("scripts", "world_simulation", "world_simulation.gd"), _src("scripts", "npc", "npc_routine_spot.gd")
VIL, MEADOW = _src("data", "npcs", "villager.tres"), _src("scenes", "world", "Meadow.tscn")
PHASE_ORDER = re.findall(r'"(\w+)"', re.search(r"^const PHASE_ORDER := \[(.*)\]", TOD, re.M).group(1))
PHASE_START = {k: float(v) for k, v in re.findall(r'"(\w+)": ([0-9.]+)', re.search(r"const PHASE_START := \{(.*?)\}", TOD, re.S).group(1))}
DAY = float(re.search(r"var day_length_seconds: float = ([0-9.]+)", TOD).group(1))
ROUTINE = dict(re.findall(r'"(\w+)": "(\w+)"', re.search(r"^routine = \{(.*?)\}$", VIL, re.M | re.S).group(1)))
RADIUS = float(re.search(r"^wander_radius = ([0-9.]+)", VIL, re.M).group(1))
SPOTS = {sid: (float(x), float(z)) for x, z, sid in re.findall(r'parent="NpcRoutine"\]\nposition = Vector3\(([-\d.]+), [-\d.]+, ([-\d.]+)\)\nscript = ExtResource\("routine_spot"\)\nspot_id = "(\w+)"', MEADOW)}
NPCSPOT = tuple(float(v) for v in re.search(r'name="NpcSpot" parent="VerticalSlice"[^\n]*\]\nposition = Vector3\(([-\d.]+), [-\d.]+, ([-\d.]+)\)', MEADOW).groups())
SPEED = float(re.search(r"^const WALK_SPEED := ([0-9.]+)", NPC, re.M).group(1))
NOTICE = float(re.search(r"^const NOTICE_DISTANCE := ([0-9.]+)", NPC, re.M).group(1))
assert sorted(ROUTINE) == sorted(PHASE_ORDER) and set(ROUTINE.values()) <= set(SPOTS), (ROUTINE, SPOTS)
assert ROUTINE["morning"] == ROUTINE["afternoon"] != ROUTINE["night"] == ROUTINE["evening"] == ROUTINE["dawn"] and SPOTS[ROUTINE["night"]] == NPCSPOT, "two spots; home is the NPC spot"
assert "_apply_phase(_time_of_day.get_phase_for_fraction(_time_of_day.day_fraction), true)" in NPC, "the first phase is read from the clock's fraction"
assert "_time_of_day.time_updated.connect(_on_time_updated)" in NPC and "_apply_phase(_time_of_day.get_phase_for_fraction(day_fraction), false)" in NPC and "phase_changed" not in NPC
assert "if place:\n\t\tglobal_position = NavigationServer3D.map_get_closest_point" in NPC, "only the first phase places"
assert re.search(r"if player != null and \(talk\.is_tap_selected\(\) or _flat_distance\(player\.global_position\) <= NOTICE_DISTANCE\):\s*_wandering = false", NPC), "the hold rule is unchanged"
assert "if _is_travelling():\n\t\treturn _clear_of_doors(step)" in NPC and "return _flat_distance(_home) > radius" in NPC
assert "time_of_day.add_to_group(TIME_GROUP)" in WS and 'const GROUP := &"npc_routine_spot"' in SPOT
assert not re.search(r"Time\.get_|SaveManager|\.day_fraction\s*=[^=]", re.sub(r"(?m)^\s*##.*$", "", NPC)), "no system time, no saving, never setting the clock"
def phase_for(f):
    r = PHASE_ORDER[0]
    for p in PHASE_ORDER:
        if f >= PHASE_START[p]: r = p
    return r
DIST = math.dist(*SPOTS.values())                       # straight-line stand-in for the walk between the two spots

class Npc:
    """npc.gd's routine and hold logic along the line between the spots (0 = home, DIST = pond)."""
    def __init__(n, design="real"): n.design, n.pos, n.spot, n.home, n.jumps, n.started = design, 0.0, None, 0.0, 0, False
    def at(n, sid): return 0.0 if sid == ROUTINE["night"] else DIST
    def start(n, clock):
        phase = clock.cached if n.design == "cached_phase_first" else phase_for(clock.f)
        n.apply(phase, True); n.started = True
    def apply(n, phase, place):
        sid = ROUTINE[phase]
        if sid == n.spot: return
        n.spot, n.home = sid, n.at(sid)
        if place or n.design == "jump_every_phase":
            if n.started: n.jumps += 1
            n.pos = n.home
    def step(n, dt, held, blocked):
        if held and n.design != "walk_off_mid_talk": return "held"
        if abs(n.pos - n.home) > RADIUS:                                    # travelling home first
            if blocked and n.design == "leash_while_travelling": return "stuck"
            d = min(SPEED * dt, abs(n.home - n.pos)); n.pos += d if n.home > n.pos else -d
            return "moved" if d > 0 else "idle"
        return "idle"

START = float(re.search(r"var start_fraction: float = ([0-9.]+)", TOD).group(1))
class Clock:
    """time_of_day.gd: _ready caches the START fraction's phase; the fraction may then be set (a restored time)."""
    def __init__(c, f): c.f, c.cached = f, phase_for(START)
    def tick(c, dt):
        c.f = math.fmod(c.f + dt / DAY, 1.0); p = phase_for(c.f)
        changed = p != c.cached; c.cached = p
        return (p if changed else None), c.f                                # (phase_changed, time_updated)

def day(seed, design="real"):
    rnd = random.Random(seed); problems = []
    clock = Clock(rnd.random()); npc = Npc(design); npc.start(clock)
    if npc.pos != npc.at(ROUTINE[phase_for(clock.f)]): problems.append("the first phase placed it at the wrong spot")
    held = False; parked = False; talk_left = 0.0; waited = 0.0
    for _ in range(rnd.randint(200, 900)):
        dt = 1.0
        a = rnd.random()
        if a < 0.02: held, talk_left = True, rnd.uniform(3, 40)               # a tap or an approach starts a conversation
        if a > 0.99: parked = not parked
        if parked: continue                                                   # the whole area is out of the tree: nothing advances
        changed, f = clock.tick(dt)
        before = npc.pos
        if npc.design == "trust_phase_changed":
            if changed: npc.apply(changed, False)
        else: npc.apply(phase_for(f), False)                                  # time_updated: the phase from the fraction
        r = npc.step(dt, held, blocked=(rnd.random() < 0.05))
        if held and npc.pos != before and design != "jump_every_phase": problems.append("moved during a conversation")
        if r == "stuck": waited += dt
        if held:
            talk_left -= dt
            if talk_left <= 0: held = False
    if npc.jumps: problems.append(f"jumped {npc.jumps} time(s) after the first phase")
    if waited > 30: problems.append("deadlocked against the player while travelling")
    # with time to walk and no conversation, it ends at the current phase's spot
    for _ in range(int(DIST / SPEED) + 5):
        npc.step(1.0, False, False)
    if abs(npc.pos - npc.at(ROUTINE[phase_for(clock.f)])) > RADIUS: problems.append("never reached the phase's spot")
    return problems

# ---------------------------------------------------------------- scripted checks
c = Clock(PHASE_START["evening"]); n = Npc(); n.start(c); assert n.pos == 0.0, "evening: placed at home"
c = Clock(PHASE_START["morning"] + 0.01); n = Npc(); n.start(c); assert n.pos == DIST, "morning: placed by the pond"
c = Clock(0.649); n = Npc(); n.start(c); assert n.pos == DIST
for _ in range(int(0.02 * DAY)): n.apply(phase_for(c.tick(1.0)[1]), False)
assert n.home == 0.0 and n.pos == DIST and n.jumps == 0, "evening begins: home moves, the NPC hasn't jumped"
for _ in range(5): n.step(1.0, True, False)
assert n.pos == DIST, "talking: it holds still"
for _ in range(int(DIST / SPEED) + 5): n.step(1.0, False, False)
assert n.pos <= RADIUS, "afterwards it walks home"
# a player pressed against the NPC halfway along its walk: npc.gd's _step_allowed lets it step aside (clear of doors,
# no home leash while travelling); keeping the home leash forbids every step there, so neither can pass
LEASH = float(re.search(r"^const YIELD_LEASH := ([0-9.]+)", NPC, re.M).group(1))
def step_aside_allowed(pos_on_way, home, design):
    travelling = abs(pos_on_way - home) > RADIUS
    if travelling and design != "leash_while_travelling": return True                 # return _clear_of_doors(step)
    return abs(pos_on_way - home) <= RADIUS + LEASH                                     # within the home leash
assert step_aside_allowed(DIST / 2, 0.0, "real"), "travelling: it can step aside, so a walk past it never deadlocks"
assert not step_aside_allowed(DIST / 2, 0.0, "leash_while_travelling"), "keeping the home leash while travelling deadlocks the player (the bug avoided)"
assert step_aside_allowed(0.5, 0.0, "real") and step_aside_allowed(RADIUS, 0.0, "real") == (RADIUS <= RADIUS + LEASH), "at home (within its radius) the M08.3 leash still applies"
stale = Clock(0.7); s = Npc("cached_phase_first"); s.start(stale); assert s.pos != 0.0, "reading the cached phase first misplaces it (the bug avoided)"

N = 20000
bad = [d for d in range(N) if day(d)]
assert not bad, f"{len(bad)} days broke a rule, e.g. {day(bad[0])}"
for design in ("cached_phase_first", "trust_phase_changed", "jump_every_phase", "walk_off_mid_talk"):
    assert any(day(d, design) for d in range(3000)), f"the {design} design is shown to break a rule"
print(f"routines: villager {ROUTINE}; spots {SPOTS} (home = NpcSpot {NPCSPOT}), {DIST:.1f} m apart, {DIST / SPEED:.0f} s walk at {SPEED} m/s; "
      f"first phase placed from the clock's fraction, later phases walked; talking holds; travel never deadlocks; parked = paused; "
      f"{N} random days OK; cached-phase-first, trust-phase-changed (misses a boundary after a set fraction), jump-every-phase, walk-off-mid-talk and leash-while-travelling shown to break")
print("ALL ROUTINE SIMULATIONS PASSED")
