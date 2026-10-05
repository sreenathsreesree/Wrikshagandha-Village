#!/usr/bin/env python3
"""Saved world time (M09.2, D-42) — the real GDScript executed: WorldClock (world_clock.gd), WorldSimulation's
_ready/_process/_present_time/configure (world_simulation.gd), TimeOfDay's own _ready/_process/phases
(time_of_day.gd, pinned) and SaveManager's world_time path (save_game / load_game / the 7 -> 8 step) are translated
line by line into Python and run inside a small model of the engine: a frame loop in tree order (a parked area gets
no frames), Godot's JSON (numbers come back as floats, 14 significant digits), a process restart, a door trip and a
free-and-reload swap; the lighting, wildlife and the M09.1 NPC listen through TimeOfDay as they do in the game.
1. A new game starts at day 1 at 0.28; a v7 save (no world_time) migrates to day 1 at 0.28; a malformed one too.
2. One clock: TimeOfDay never advances on its own; it always shows WorldClock's fraction, one time_updated per frame,
   phase_changed exactly when the fraction's phase changes; the NPC and wildlife see the restored time at once.
3. Each crossing of 1.0 raises the day exactly once and wraps the fraction (landing exactly on 1.0, tiny steps,
   zero steps, a long hitch); loading, a door trip (time pauses indoors and resumes exactly), a fresh area and a
   repeated configure() never change the day or the fraction; save/load round-trips; cycles are stable.
4. 3,000 random sessions (frames, hitches, door trips, swaps, saves, relaunches, crashes) = a reference clock.
Broken designs, applied to the real source, are shown to break: TimeOfDay's own clock left on, both clocks
advancing, a reset on area load, a reset on configure, a lost day increment, a double increment, a corrupted v7
migration, a save of the fraction only and a wrongly restored day or fraction.
"""
import json, math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
SOURCES = {"wc": _src("scripts", "autoload", "world_clock.gd"), "ws": _src("scripts", "world_simulation", "world_simulation.gd"),
           "tod": _src("scripts", "world_simulation", "time_of_day.gd"), "sm": _src("scripts", "autoload", "save_manager.gd")}

# ---------------------------------------------------------------- GDScript -> Python (the subset these files use)
TYPE_INT, TYPE_FLOAT = 2, 3
def _typeof(v): return TYPE_INT if isinstance(v, int) and not isinstance(v, bool) else TYPE_FLOAT if isinstance(v, float) else 0
class GDict(dict):
    def is_empty(self): return len(self) == 0
def gdict(v): return GDict({k: gdict(x) for k, x in v.items()}) if isinstance(v, dict) else v
WARNINGS = []
HELPERS = {"math": math, "_typeof": _typeof, "TYPE_INT": TYPE_INT, "TYPE_FLOAT": TYPE_FLOAT, "_warn": lambda *a: WARNINGS.append(a),
           "GDict": GDict, "_floori": lambda x: math.floor(x), "_floorf": lambda x: float(math.floor(x))}

def _split_funcs(src):
    return {m.group(1): m.group(0) for m in re.finditer(r"^func (\w+)\((.*?)\)[^\n]*:\n(?:(?:\t[^\n]*|)\n)*", src + "\n", re.M)}

def _sub_code(line, members, ext):
    out, parts = [], re.split(r'("(?:[^"\\]|\\.)*")', line)
    for i, part in enumerate(parts):
        if i % 2:
            out.append(part); continue
        part = re.sub(r'&$', "", part)  # a StringName literal (&"...") is a plain string here
        part = part.replace("true", "True").replace("false", "False").replace("null", "None")
        part = re.sub(r"(?<![\w.])floori\(", "_floori(", part)
        part = re.sub(r"(?<![\w.])floorf\(", "_floorf(", part)
        part = re.sub(r"(?<![\w.])is_finite\(", "math.isfinite(", part)
        part = re.sub(r"(?<![\w.])fmod\(", "math.fmod(", part)
        part = re.sub(r"(?<![\w.])typeof\(", "_typeof(", part)
        part = re.sub(r"\{\}", "GDict()", part)
        for name in members:
            part = re.sub(r"(?<![\w.])%s\b" % re.escape(name), "self." + name, part)
        for name, repl in ext.items():
            part = re.sub(r"(?<![\w.])%s\b" % re.escape(name), repl, part)
        out.append(part)
    return "".join(out)

def translate(src, cls, ext, funcs=None):
    """A Python class for one GDScript file: members (var/@onready/@export/signal) become attributes, consts module
    globals, each translated func a method. `ext` maps names outside the file (autoloads) to Python expressions."""
    code = re.sub(r"(?m)^\s*##.*$", "", src)
    consts = {}
    for m in re.finditer(r"^const (\w+)\s*:?=\s*", code, re.M):  # the value runs until its brackets balance
        i, depth = m.end(), 0
        while i < len(code) and not (code[i] == "\n" and depth == 0):
            depth += code[i] in "[{(" and 1 or code[i] in "]})" and -1 or 0
            i += 1
        consts[m.group(1)] = code[m.end():i].strip()
    members = re.findall(r"^(?:@onready |@export(?:_range\([^)]*\))? )?var (\w+)", code, re.M) + re.findall(r"^signal (\w+)", code, re.M)
    fn = _split_funcs(code)
    members += list(fn)
    lines = [f"class {cls}(Node):", "    def __init__(self):", "        Node.__init__(self)"]
    for name in re.findall(r"^signal (\w+)", code, re.M):
        lines.append(f"        self.{name} = Signal()")
    for m in re.finditer(r"^(?:@export(?:_range\([^)]*\))? )?var (\w+)(?::\s*\w+)?\s*:?=\s*(.+)$", code, re.M):
        lines.append(f"        self.{m.group(1)} = {_sub_code(m.group(2), members, ext)}")
    for name in (funcs or fn):
        body = fn.get(name)
        if body is None:
            continue
        head = re.match(r"func (\w+)\((.*?)\)", body)
        args = [a.split(":")[0].strip() for a in head.group(2).split(",") if a.strip()]
        lines.append(f"    def {name}(self{''.join(', ' + a for a in args)}):")
        for raw in body.split("\n")[1:]:
            if not raw.strip() or raw.strip().startswith("#"):
                continue
            depth = len(raw) - len(raw.lstrip("\t"))
            text = raw.strip()
            if text.startswith("push_warning("):
                text = "_warn()"
            text = re.sub(r"^var (\w+)(?::\s*[\w\[\]]+)?\s*:?=\s*", r"\1 = ", text)
            text = re.sub(r"\s+as\s+\w+$", "", text)
            lines.append("    " * (depth + 1) + _sub_code(text, members, ext))
        lines.append("    " * 2 + "pass")
    g = dict(HELPERS, Node=Node, Signal=Signal, WORLD=globals().get("WORLD"), **{k: eval(_sub_code(v, [], ext), dict(HELPERS)) for k, v in consts.items()})
    exec("\n".join(lines), g)
    return g[cls], {k: g[k] for k in consts}

class Signal:
    def __init__(s): s.handlers, s.emitted = [], 0
    def connect(s, fn): s.handlers.append(fn)
    def emit(s, *a):
        s.emitted += 1
        for fn in list(s.handlers): fn(*a)
class Node:
    def __init__(s): s.processing, s.groups = True, set()
    def set_process(s, on): s.processing = bool(on)
    def add_to_group(s, g): s.groups.add(g)
class Mock:
    def __init__(s, **kw): s.__dict__.update(kw)
    def __getattr__(s, k): return Mock() if not k.startswith("__") else None
    def __call__(s, *a, **k): return Mock()
    def __float__(s): return 0.0

def build(sources):
    """The game's clock pieces from (possibly mutated) sources."""
    WC, wc_consts = translate(sources["wc"], "WorldClock", {})
    TOD, tod_consts = translate(sources["tod"], "TimeOfDay", {})
    WS, ws_consts = translate(sources["ws"], "WorldSimulation", {"WorldClock": "WORLD.clock", "FarmManager": "WORLD.farm"},
                              ["_ready", "_process", "_present_time", "configure", "_on_time_updated", "_on_garden_interest_changed"])
    sm = sources["sm"]
    save_expr = re.search(r'^\t\t"world_time": (.+),$', sm, re.M)
    load_line = re.search(r"^\tWorldClock\.apply_save_data\((.+)\)$", sm, re.M)
    step7 = re.search(r"^\t\t\t7:\n((?:\t\t\t\t.*\n)+)", sm, re.M)
    steps = [int(x) for x in re.findall(r"^\t\t\t(\d+):", sm, re.M)]
    version = int(re.search(r"^const SAVE_VERSION := (\d+)", sm, re.M).group(1))
    return dict(WC=WC, TOD=TOD, WS=WS, wc=wc_consts, tod=tod_consts, version=version, steps=steps,
                save_expr=save_expr.group(1) if save_expr else None, load_arg=load_line.group(1) if load_line else None,
                step7=[l.strip() for l in step7.group(1).splitlines()] if step7 else None)

class World:  # the autoload slots WorldSimulation reaches (WorldClock, FarmManager)
    clock = None
    farm = Mock(garden_interest_changed=Signal(), get_garden_interest=lambda: 0.0, WILDLIFE_ATTRACTION_KEY="garden")
WORLD = World()

def godot_json(v):  # JSON.stringify (14 significant digits) then JSON.parse_string (every number a float)
    def enc(x):
        if isinstance(x, bool): return x
        if isinstance(x, (int, float)): return float("%.14g" % x)
        if isinstance(x, dict): return {k: enc(y) for k, y in x.items()}
        if isinstance(x, list): return [enc(y) for y in x]
        return x
    return gdict(json.loads(json.dumps(enc(v))))

class Game:
    """One process: autoloads (WorldClock restored from the disk at boot), the Meadow (TimeOfDay, WorldSimulation,
    lighting, wildlife, an NPC following its routine) in or out of the tree, frames in tree order."""
    NAV_FRAMES = 3
    def __init__(g, kit, disk):
        g.kit, g.disk, g.trace = kit, disk, []
        WORLD.clock = g.clock = kit["WC"]()
        g.loaded = g.load()
        g.new_meadow()
    def new_meadow(g):
        g.tod, g.ws = g.kit["TOD"](), g.kit["WS"]()
        g.ws.time_of_day = g.tod
        g.lights, g.wild = Mock(applied=[]), Mock(phase=None)
        g.lights.apply_time = lambda f: g.lights.applied.append(f)
        g.wild.set_time_phase = lambda p: setattr(g.wild, "phase", p)
        g.ws.environment_controller, g.ws.wildlife_controller = g.lights, g.wild
        for k in ("vegetation_controller", "ambient_controller", "environmental_event_controller", "exploration_landmark_controller"):
            setattr(g.ws, k, Mock())
        g.tod._ready()                       # children are ready before their parent
        g.ws._ready()
        g.configure()
        g.npc_phase, g.npc_wait = None, g.NAV_FRAMES   # the M09.1 NPC: follows once its navigation map is ready
        g.meadow_in_tree = True
    def configure(g):
        WORLD.clock = g.clock
        g.ws.configure(Mock(), Mock(), Mock())
    def frame(g, delta):
        WORLD.clock = g.clock
        g.tod.time_updated.emitted = g.tod.phase_changed.emitted = 0
        g.phase_before = phase_for(g.kit, g.clock.get_fraction())
        if not g.meadow_in_tree:
            return
        g.ws._process(delta)                 # parent first, then its children
        if g.tod.processing:
            g.tod._process(delta)
        if g.npc_phase is None:
            g.npc_wait -= 1
            if g.npc_wait <= 0:              # npc.gd _follow_time_of_day: phase from the clock's own fraction, then time_updated
                g.npc_phase = g.tod.get_phase_for_fraction(g.tod.day_fraction)
                g.tod.time_updated.connect(lambda f: setattr(g, "npc_phase", g.tod.get_phase_for_fraction(f)))
    def save(g):
        data = {"save_version": g.kit["version"]}
        if g.kit["save_expr"]:
            data["world_time"] = eval(_sub_code(g.kit["save_expr"], [], {"WorldClock": "CLOCK"}), dict(HELPERS, CLOCK=g.clock))
        g.disk["save"] = json.dumps(data)
    def load(g):
        if "save" not in g.disk:
            return False
        data = godot_json(json.loads(g.disk["save"]))
        version = int(data.get("save_version", 0))
        if version > g.kit["version"]:
            return False
        while version < g.kit["version"]:
            if version not in g.kit["steps"]:
                return False
            if version == 7:
                for line in g.kit["step7"] or ["MISSING"]:
                    if line.startswith("pass"): continue
                    exec(_sub_code(line, [], {}), dict(HELPERS), {"data": data})
            version += 1
        data = gdict(data)
        if "world_time" in data and not isinstance(data["world_time"], dict):
            del data["world_time"]
        if g.kit["load_arg"]:
            g.clock.apply_save_data(eval(_sub_code(g.kit["load_arg"], [], {}), dict(HELPERS), {"data": data}))
        return True
    def total(g): return g.clock.get_day() + g.clock.get_fraction()

PHASE_START = None
def phase_for(kit, f):
    r = "dawn"
    for p, s in kit["tod"]["PHASE_START"].items():
        if f >= s: r = p
    return r

def check_frame(g, problems, label=""):
    f = g.clock.get_fraction()
    if not (0.0 <= f < 1.0): problems.append(f"fraction out of range {f}{label}")
    if g.meadow_in_tree:
        if abs(g.tod.day_fraction - f) > 1e-12: problems.append(f"TimeOfDay shows {g.tod.day_fraction}, the clock {f}{label}")
        if g.tod.time_updated.emitted != 1: problems.append(f"{g.tod.time_updated.emitted} time_updated in a frame{label}")
        changed = int(phase_for(g.kit, f) != getattr(g, "phase_before", phase_for(g.kit, f)))
        if g.tod.phase_changed.emitted != changed: problems.append(f"{g.tod.phase_changed.emitted} phase_changed in a frame where the phase changed {bool(changed)}{label}")
        if g.wild.phase != phase_for(g.kit, f): problems.append(f"wildlife phase {g.wild.phase} at {f:.4f}{label}")
        if g.npc_phase is not None and g.npc_phase != phase_for(g.kit, f): problems.append(f"NPC phase {g.npc_phase} at {f:.4f}{label}")
        if g.lights.applied and abs(g.lights.applied[-1] - f) > 1e-12: problems.append(f"lighting at {g.lights.applied[-1]}{label}")

def scripted(kit):
    """The required cases; returns the problems found (none for the real sources)."""
    p, wc = [], kit["wc"]
    D, S0, DAY = wc["START_DAY"], wc["START_FRACTION"], wc["DAY_LENGTH_SECONDS"]
    g = Game(kit, {})
    if (g.clock.get_day(), g.clock.get_fraction(), g.tod.day_fraction) != (1, 0.28, 0.28): p.append(f"fresh: {g.clock.get_day()} / {g.clock.get_fraction()}")
    if g.tod.processing: p.append("TimeOfDay's own frame advance is still on")
    g.frame(1.0); check_frame(g, p, " (first frame)")
    if abs(g.clock.get_fraction() - (0.28 + 1.0 / DAY)) > 1e-12: p.append(f"one second advanced to {g.clock.get_fraction()}")
    # v7 save: no world_time -> day 1 at 0.28, saved again as v8 with both
    disk = {"save": json.dumps({"save_version": 7, "points": 5})}
    g7 = Game(kit, disk)
    if not g7.loaded or (g7.clock.get_day(), g7.clock.get_fraction()) != (1, 0.28): p.append(f"v7 migrated to {g7.clock.get_day()} / {g7.clock.get_fraction()}")
    g7.frame(2.0); g7.save(); saved = json.loads(disk["save"])
    if saved.get("save_version") != kit["version"] or set(saved.get("world_time", {})) != {"day", "fraction"}: p.append(f"re-saved as {saved}")
    # malformed sections fall back to day 1 at 0.28, never half-restored
    for bad in ({"day": "x", "fraction": 0.5}, {"day": 3, "fraction": 1.0}, {"day": 0, "fraction": 0.5}, {"day": 2.5, "fraction": 0.1},
                {"fraction": 0.5}, {"day": 4}, {"day": 3, "fraction": -0.1}):
        gb = Game(kit, {"save": json.dumps({"save_version": kit["version"], "world_time": bad})})
        if (gb.clock.get_day(), gb.clock.get_fraction()) != (1, 0.28): p.append(f"malformed {bad} restored {gb.clock.get_day()} / {gb.clock.get_fraction()}")
    # save -> relaunch: the same day and fraction, before anything reads it; NPC and wildlife at once
    disk = {}; g = Game(kit, disk)
    for _ in range(int(0.4 * DAY)): g.frame(1.0)
    for _ in range(int(1.37 * DAY * 60)): g.frame(1 / 60)
    before = (g.clock.get_day(), g.clock.get_fraction()); g.save()
    g2 = Game(kit, disk)
    if (g2.clock.get_day(), abs(g2.clock.get_fraction() - before[1]) < 1e-12) != (before[0], True): p.append(f"relaunch {before} -> {g2.clock.get_day()} / {g2.clock.get_fraction()}")
    if g2.tod.day_fraction != g2.clock.get_fraction() or g2.wild.phase != phase_for(kit, before[1]): p.append("restored time not presented before the first frame")
    for _ in range(Game.NAV_FRAMES): g2.frame(1 / 60); check_frame(g2, p, " (after relaunch)")
    if g2.npc_phase != phase_for(kit, g2.clock.get_fraction()): p.append(f"NPC placed for {g2.npc_phase}")
    # 20 save/load cycles without frames: nothing drifts, the day never rises
    disk = {"save": json.dumps({"save_version": kit["version"], "world_time": {"day": 7, "fraction": 0.123456789}})}
    for _ in range(20):
        gc = Game(kit, disk); gc.save()
    if (gc.clock.get_day(), abs(gc.clock.get_fraction() - 0.123456789) < 1e-12) != (7, True): p.append(f"cycles drifted to {gc.clock.get_day()} / {gc.clock.get_fraction()}")
    # the boundary: once per crossing — exactly 1.0, tiny steps, zero steps, a long hitch
    def at(day, frac):
        return Game(kit, {"save": json.dumps({"save_version": kit["version"], "world_time": {"day": day, "fraction": frac}})})
    gb = at(3, 0.9995); days = []
    for _ in range(120): gb.frame(1 / 60); days.append(gb.clock.get_day()); check_frame(gb, p, " (boundary)")
    if days.count(3) + days.count(4) != len(days) or sorted(days) != days or days[-1] != 4: p.append(f"boundary days {sorted(set(days))}")
    gx = at(5, 1.0 - 0.6 / DAY); gx.frame(0.6)
    if (gx.clock.get_day(), gx.clock.get_fraction()) != (6, 0.0) and not (gx.clock.get_day() == 6 and gx.clock.get_fraction() < 1e-12): p.append(f"exactly 1.0 -> {gx.clock.get_day()} / {gx.clock.get_fraction()}")
    for _ in range(50): gx.frame(0.0)
    if gx.clock.get_day() != 6: p.append("zero-length frames raised the day")
    gh = at(2, 0.99); gh.frame(DAY + 0.02 * DAY)
    if gh.clock.get_day() != 4 or abs(gh.clock.get_fraction() - 0.01) > 1e-9: p.append(f"a {DAY * 1.02:.0f} s hitch -> {gh.clock.get_day()} / {gh.clock.get_fraction()}")
    # door trip: parked = paused, back = resumed exactly; configure again and a fresh area never change it
    gd = at(2, 0.5)
    for _ in range(30): gd.frame(1 / 60)
    held = (gd.clock.get_day(), gd.clock.get_fraction()); gd.meadow_in_tree = False
    for _ in range(600): gd.frame(1 / 60)
    if (gd.clock.get_day(), gd.clock.get_fraction()) != held: p.append("time moved while the Meadow was parked")
    gd.meadow_in_tree = True; gd.frame(0.5)
    if abs(gd.total() - (held[0] + held[1] + 0.5 / DAY)) > 1e-12: p.append("time did not resume where it paused")
    check_frame(gd, p, " (back outside)")
    held = gd.total(); gd.configure(); gd.configure()
    if gd.total() != held: p.append("configure() changed the time")
    gd.new_meadow()
    if gd.total() != held or gd.tod.day_fraction != gd.clock.get_fraction(): p.append("a fresh area changed the time")
    gd.frame(1 / 60); check_frame(gd, p, " (fresh area)")
    return p

def random_session(kit, seed):
    """Frames, hitches, door trips, swaps, saves, relaunches and crashes against a reference clock in seconds."""
    rnd, p, wc = random.Random(seed), [], kit["wc"]
    DAY = wc["DAY_LENGTH_SECONDS"]
    disk, ref, saved_ref = {}, wc["START_FRACTION"] * DAY, None
    g = Game(kit, disk)
    for _ in range(rnd.randint(50, 250)):
        a = rnd.random()
        if a < 0.70:
            dt = rnd.choice([1 / 60, 1 / 30, rnd.uniform(0, 0.25), 0.0, rnd.uniform(5, 120)])
            g.frame(dt)
            if g.meadow_in_tree and dt > 0: ref += dt
            check_frame(g, p)
        elif a < 0.80: g.meadow_in_tree = not g.meadow_in_tree
        elif a < 0.84: g.new_meadow()
        elif a < 0.87: g.configure()
        elif a < 0.93: g.save(); saved_ref = ref
        elif a < 0.97: g.save(); saved_ref = ref; g = Game(kit, disk)       # background/close saves, then a relaunch
        else:                                                                 # a crash: back to the last save
            g = Game(kit, disk); ref = saved_ref if saved_ref is not None else wc["START_FRACTION"] * DAY
        expect = wc["START_DAY"] + ref / DAY
        if abs(g.total() - expect) > 1e-7: p.append(f"clock {g.total():.9f} vs reference {expect:.9f}"); break
    return p

def mutate(name):
    s = dict(SOURCES)
    def rep(key, old, new):
        assert old in s[key], (name, old); s[key] = s[key].replace(old, new, 1)
    if name == "tod_clock_left_on": rep("ws", "\ttime_of_day.set_process(false)\n", "")
    elif name == "both_clocks_advance": rep("ws", "time_of_day.set_process(false)", "time_of_day.set_process(true)")
    elif name == "reset_on_area_load": rep("ws", "\ttime_of_day.set_process(false)\n", "\ttime_of_day.set_process(false)\n\tWorldClock.apply_save_data({})\n")
    elif name == "reset_on_configure": rep("ws", "\twildlife_controller.wire_actors()\n", "\twildlife_controller.wire_actors()\n\tWorldClock.apply_save_data({})\n")
    elif name == "lost_day_increment": rep("wc", "\t_day += whole\n", "")
    elif name == "double_increment": rep("wc", "\t_day += whole\n", "\t_day += whole * 2\n")
    elif name == "v7_migration_corrupted": rep("sm", "\t\t\t7:\n\t\t\t\tpass", '\t\t\t7:\n\t\t\t\tdata["world_time"] = {"day": 2, "fraction": 0.5}')
    elif name == "save_fraction_only": rep("wc", 'return {"day": _day, "fraction": _fraction}', 'return {"fraction": _fraction}')
    elif name == "restore_wrong": rep("wc", "\t_fraction = float(fraction)\n", "\t_fraction = START_FRACTION\n")
    return s

REAL = build(SOURCES)
bad = scripted(REAL)
assert not bad, bad
N = 3000
fails = [d for d in range(N) if random_session(REAL, d)]
assert not fails, f"{len(fails)} sessions broke the clock, e.g. {random_session(REAL, fails[0])}"
BROKEN = ["tod_clock_left_on", "both_clocks_advance", "reset_on_area_load", "reset_on_configure", "lost_day_increment",
          "double_increment", "v7_migration_corrupted", "save_fraction_only", "restore_wrong"]
caught = {}
for name in BROKEN:
    kit = build(mutate(name))
    probs = scripted(kit) or next((r for d in range(300) for r in [random_session(kit, d)] if r), [])
    assert probs, f"the {name} design is shown to break the clock"
    caught[name] = probs[0]
wc = REAL["wc"]
print(f"world clock: WorldClock from day {wc['START_DAY']} at {wc['START_FRACTION']}, {wc['DAY_LENGTH_SECONDS']:.0f} s day; TimeOfDay only presents it "
      f"(own advance off, one time_updated per frame, phase_changed on the fraction's phase); v7 -> day 1 at 0.28; save/load round-trips; "
      f"boundary once per crossing; parked = paused, resumed exactly; configure/fresh area/load never change it; {N} random sessions = reference")
print("broken designs caught: " + "; ".join(f"{k}: {v}" for k, v in caught.items()))
print("ALL WORLD CLOCK SIMULATIONS PASSED")
