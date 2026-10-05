"""Shared by the world-time simulations (sim_world_clock, sim_weather): a small GDScript -> Python translator for the
subset the clock, weather and WorldSimulation scripts use, and a model of the engine around them — frames in tree
order (a parked area gets none), Godot's JSON, a process restart, the Meadow's WorldSimulation with its TimeOfDay,
lighting, wildlife, an NPC following its routine and the weather. Not a simulation itself (run_all runs sim_*.py)."""
import json, math, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def load_sources():
    return {"wc": _src("scripts", "autoload", "world_clock.gd"), "ws": _src("scripts", "world_simulation", "world_simulation.gd"),
            "tod": _src("scripts", "world_simulation", "time_of_day.gd"), "sm": _src("scripts", "autoload", "save_manager.gd"),
            "wctl": _src("scripts", "world_simulation", "weather_controller.gd"), "wsched": _src("data", "weather", "weather_schedule.tres"),
            "evt": _src("scripts", "world_simulation", "environmental_event.gd"), "evc": _src("scripts", "world_simulation", "environmental_event_controller.gd"),
            "meadow": _src("scenes", "world", "Meadow.tscn")}
SOURCES = load_sources()

# ---------------------------------------------------------------- GDScript -> Python (the subset these files use)
TYPE_INT, TYPE_FLOAT = 2, 3
def _typeof(v): return TYPE_INT if isinstance(v, int) and not isinstance(v, bool) else TYPE_FLOAT if isinstance(v, float) else 0
class GDict(dict):
    def is_empty(self): return len(self) == 0
def gdict(v): return GDict({k: gdict(x) for k, x in v.items()}) if isinstance(v, dict) else v
WARNINGS = []
class Vector3:
    def __init__(s, x=0.0, y=0.0, z=0.0): s.x, s.y, s.z = x, y, z
    def __add__(s, o): return Vector3(s.x + o.x, s.y + o.y, s.z + o.z)
    def distance_to(s, o): return math.sqrt((s.x - o.x) ** 2 + (s.y - o.y) ** 2 + (s.z - o.z) ** 2)
    def __eq__(s, o): return isinstance(o, Vector3) and (s.x, s.y, s.z) == (o.x, o.y, o.z)
class Color:
    def __init__(s, r=0.0, g=0.0, b=0.0, a=1.0):
        if isinstance(r, Color): r, g, b, a = r.r, r.g, r.b, g   # Color(from, alpha)
        s.r, s.g, s.b, s.a = r, g, b, a
HELPERS = {"math": math, "_typeof": _typeof, "TYPE_INT": TYPE_INT, "TYPE_FLOAT": TYPE_FLOAT, "_warn": lambda *a: WARNINGS.append(a),
           "GDict": GDict, "_floori": lambda x: math.floor(x), "_floorf": lambda x: float(math.floor(x)),
           "clampi": lambda v, a, b: max(a, min(b, int(v))), "clampf": lambda v, a, b: max(a, min(b, v)), "minf": min, "maxf": max,
           "Vector3": Vector3, "Color": Color, "is_instance_valid": lambda o: o is not None, "NodePath": lambda p="": p, "CONNECT_ONE_SHOT": 4}

def _split_funcs(src):
    return {m.group(1): m.group(0) for m in re.finditer(r"^(?:static )?func (\w+)\((.*?)\)[^\n]*:\n(?:(?:\t[^\n]*|)\n)*", src + "\n", re.M)}

NODE_METHODS = ["get_tree", "get_node_or_null", "add_to_group"]   # Node's own methods, called bare in a script

def _sub_code(line, members, ext):
    out, parts = [], re.split(r'("(?:[^"\\]|\\.)*")', line)
    for i, part in enumerate(parts):
        if i % 2:
            out.append(part); continue
        part = re.sub(r'&$', "", part)  # a StringName literal (&"...") is a plain string here
        if i + 1 < len(parts):
            part = re.sub(r'\^$', "", part)  # so is a NodePath literal (^"...")
        part = re.sub(r"\btrue\b", "True", re.sub(r"\bfalse\b", "False", re.sub(r"\bnull\b", "None", part)))
        part = re.sub(r"(?<![\w.])floori\(", "_floori(", part)
        part = re.sub(r"(?<![\w.])floorf\(", "_floorf(", part)
        part = re.sub(r"(?<![\w.])is_finite\(", "math.isfinite(", part)
        part = re.sub(r"(?<![\w.])fmod\(", "math.fmod(", part)
        part = re.sub(r"(?<![\w.])typeof\(", "_typeof(", part)
        part = re.sub(r"\{\}", "GDict()", part)
        for name in list(members) + NODE_METHODS:
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
    for name in re.findall(r"^(?:@onready |@export(?:_range\([^)]*\))? )?var (\w+)(?::\s*[\w\[\]]+)?\s*$", code, re.M):
        lines.append(f"        self.{name} = None")           # declared without a value
    for m in re.finditer(r"^(?:@export(?:_range\([^)]*\))? )?var (\w+)(?::\s*[\w\[\]]+)?\s*:?=\s*(.+)$", code, re.M):
        lines.append(f"        self.{m.group(1)} = {_sub_code(m.group(2), members, ext)}")
    for name in (funcs or fn):
        body = fn.get(name)
        if body is None:
            continue
        head = re.match(r"(?:static )?func (\w+)\((.*?)\)", body)
        args = [a.split(":")[0].strip() for a in head.group(2).split(",") if a.strip()]
        lines.append(f"    def {name}(self{''.join(', ' + a for a in args)}):")
        matches = []                                         # open `match` blocks: (depth, subject variable)
        for raw in body.split("\n")[1:]:
            if not raw.strip() or raw.strip().startswith("#"):
                continue
            depth = len(raw) - len(raw.lstrip("\t"))
            text = raw.strip()
            while matches and depth <= matches[-1][0]:
                matches.pop()
            if text.startswith("match ") and text.endswith(":"):
                var = f"_match{len(matches)}"
                lines.append("    " * (depth + 1 - len(matches)) + f"{var} = {_sub_code(text[6:-1], members, ext)}")
                matches.append((depth, var)); continue
            if matches and depth == matches[-1][0] + 1 and text.endswith(":"):
                var = matches[-1][1]
                lines.append("    " * (depth - len(matches) + 1) + f"if {var} == {_sub_code(text[:-1], members, ext)}:")
                continue
            depth -= len(matches)                                # a case's body sits one level shallower in Python
            if text.startswith("push_warning("):
                text = "_warn()"
            text = re.sub(r"^var (\w+)(?::\s*[\w\[\]]+)?\s*:?=\s*", r"\1 = ", text)
            text = re.sub(r"\s+as\s+\w+$", "", text)
            lines.append("    " * (depth + 1) + _sub_code(text, members, ext))
        lines.append("    " * 2 + "pass")
    enums = {}
    for m in re.finditer(r"^enum (\w+) \{([^}]*)\}", code, re.M):
        enums[m.group(1)] = Mock(**{n.strip(): i for i, n in enumerate(m.group(2).split(",")) if n.strip()})
    g = dict(HELPERS, Node=Node, Signal=Signal, WORLD=globals().get("WORLD"), **enums)
    g.update({k: eval(_sub_code(v, [], ext), g) for k, v in consts.items()})
    exec("\n".join(lines), g)
    return g[cls], {k: g[k] for k in consts}

class Signal:
    def __init__(s): s.handlers, s.emitted = [], 0
    def connect(s, fn, flags=0): s.handlers.append(fn)
    def emit(s, *a):
        s.emitted += 1
        for fn in list(s.handlers): fn(*a)
class Node:
    def __init__(s): s.processing, s.groups = True, set()
    def set_process(s, on): s.processing = bool(on)
    def add_to_group(s, g): s.groups.add(g); WORLD.tree.join(g, s)
    def get_tree(s): return WORLD.tree
    def get_node_or_null(s, path): return WORLD.tree.resolve(path)
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
    WCTL, wctl_consts = translate(sources["wctl"], "WeatherController", {})
    EVT, _ = translate(sources["evt"], "EnvironmentalEvent", {"DiscoveryManager": "WORLD.discovery", "FarmManager": "WORLD.farm", "Time": "WORLD.time"})
    EVC, _ = translate(sources["evc"], "EnvironmentalEventController", {})
    events, wildlife = meadow_events(sources["meadow"])
    sched = Mock(**{k: (int(v) if re.fullmatch(r"-?\d+", v) else float(v)) for k, v in re.findall(r"^(\w+) = (-?[\d.]+)$", sources["wsched"], re.M)})
    sm = sources["sm"]
    save_expr = re.search(r'^\t\t"world_time": (.+),$', sm, re.M)
    load_line = re.search(r"^\tWorldClock\.apply_save_data\((.+)\)$", sm, re.M)
    step7 = re.search(r"^\t\t\t7:\n((?:\t\t\t\t.*\n)+)", sm, re.M)
    steps = [int(x) for x in re.findall(r"^\t\t\t(\d+):", sm, re.M)]
    version = int(re.search(r"^const SAVE_VERSION := (\d+)", sm, re.M).group(1))
    return dict(EVT=EVT, EVC=EVC, events=events, wildlife=wildlife, WC=WC, TOD=TOD, WS=WS, WCTL=WCTL, schedule=sched, wctl=wctl_consts, wc=wc_consts, tod=tod_consts, version=version, steps=steps,
                save_expr=save_expr.group(1) if save_expr else None, load_arg=load_line.group(1) if load_line else None,
                step7=[l.strip() for l in step7.group(1).splitlines()] if step7 else None)

class Timer:
    def __init__(t, seconds): t.left, t.timeout = seconds, Signal()
class Tree:
    """The SceneTree as the event layer uses it: groups, one-shot timers (they run whatever is parked, as
    SceneTreeTimers do) and NodePath lookup by the path's last name."""
    def __init__(t): t.groups, t.timers, t.nodes = {}, [], {}
    def join(t, group, node):
        if node not in t.groups.setdefault(group, []): t.groups[group].append(node)
    def get_nodes_in_group(t, group): return list(t.groups.get(group, []))
    def create_timer(t, seconds):
        timer = Timer(seconds); t.timers.append(timer); return timer
    def advance(t, delta):
        for timer in list(t.timers):
            timer.left -= delta
            if timer.left <= 0.0:
                t.timers.remove(timer); timer.timeout.emit()
    def resolve(t, path): return t.nodes.get(str(path).split("/")[-1]) if path else None
class Actor:
    """A wildlife actor (or a clue prop) as the event layer sees it: it records what it is asked to do."""
    def __init__(a, name, kind): a.name, a.kind, a.startled, a.state, a.calls, a.lead_finished, a.global_position = name, kind, 0, "idle", [], Signal(), Vector3()
    def startle(a): a.startled += 1
    def is_leading(a): return False
    def lead_to(a, position): a.calls.append("lead_to")
    def has_method(a, m): return True
    def call(a, m, *args): a.calls.append(m)

class World:  # the autoload slots the translated scripts reach (WorldClock, FarmManager, DiscoveryManager, Time) and the tree
    clock = None
    tree = Tree()
    ms = 0
    discovered = set()
    farm = Mock(garden_interest_changed=Signal(), get_garden_interest=lambda: 0.0, WILDLIFE_ATTRACTION_KEY="garden",
                has_ready_crops=lambda: World.ready_crops, get_last_ripened_msec=lambda: World.ripened_msec)
    ready_crops, ripened_msec = False, -1
    discovery = Mock(is_discovered=lambda i: i in World.discovered)
    time = Mock(get_ticks_msec=lambda: World.ms)
WORLD = World()

def _tscn_value(v):
    v = v.strip()
    if v in ("true", "false"): return v == "true"
    if v.startswith('"'): return v[1:-1]
    if v.startswith("NodePath("): return re.search(r'NodePath\("([^"]*)"\)', v).group(1)
    if v.startswith("Vector3("): return Vector3(*(float(x) for x in v[8:-1].split(",")))
    if v.startswith("["): return [_tscn_value(x) for x in re.findall(r'NodePath\("[^"]*"\)', v)]
    return float(v) if "." in v else int(v)

def meadow_events(meadow):
    """Every EnvironmentalEvent in Meadow.tscn (EnvironmentalEvents and WeatherEvents) and every Wildlife actor."""
    ext = dict((i, p) for p, i in re.findall(r'^\[ext_resource type="[^"]+" path="res://([^"]+)" id="(\w+)"\]$', meadow, re.M))
    evt_id = next(i for i, p in ext.items() if p == "scripts/world_simulation/environmental_event.gd")
    events = []
    for m in re.finditer(r'^\[node name="(\w+)" type="Node3D" parent="(EnvironmentalEvents|WeatherEvents)"\]\n((?:[^\[\n].*\n?)+)', meadow, re.M):
        if f'script = ExtResource("{evt_id}")' not in m.group(3):
            continue
        props = {k: _tscn_value(v) for k, v in re.findall(r"^(\w+) = (.+)$", m.group(3), re.M) if k != "script"}
        events.append((m.group(1), m.group(2), props))
    kinds = {"scenes/wildlife/SmallBird.tscn": "bird", "scenes/wildlife/WildlifeButterfly.tscn": "butterfly", "scenes/wildlife/Rabbit.tscn": "rabbit"}
    wildlife = [(n, kinds.get(ext.get(e), "other")) for n, e in re.findall(r'^\[node name="(\w+)" parent="Wildlife" instance=ExtResource\("(\w+)"\)\]', meadow, re.M)]
    return events, wildlife

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
        g.tree, g.ms, g.player = Tree(), 0, Mock(global_position=Vector3(1.0, 0.0, 2.0))
        WORLD.tree, WORLD.ms = g.tree, g.ms
        WORLD.clock = g.clock = kit["WC"]()
        g.loaded = g.load()
        g.new_meadow()
    def new_meadow(g):
        g.tod, g.ws = g.kit["TOD"](), g.kit["WS"]()
        g.ws.time_of_day = g.tod
        g.lights, g.wild = Mock(applied=[]), Mock(phase=None)
        g.wild.set_time_phase = lambda p: setattr(g.wild, "phase", p)
        g.lights.apply_time = lambda f, rain=0.0: (g.lights.applied.append(f), setattr(g.lights, "rain", rain))
        g.ws.environment_controller, g.ws.wildlife_controller = g.lights, g.wild
        g.weather = g.kit["WCTL"]()                      # the real WeatherController, its schedule and a stand-in emitter
        g.weather.schedule, g.weather._rain = g.kit["schedule"], Mock(emitting=False, color=None, global_position=None)
        g.weather_events = []
        g.weather.weather_changed.connect(lambda w: g.weather_events.append((g.clock.get_day(), g.clock.get_fraction(), w)))
        g.ws.weather_controller = g.weather
        for k in ("vegetation_controller", "ambient_controller", "exploration_landmark_controller"):
            setattr(g.ws, k, Mock())
        # the real event layer: the controller, and every event of this (fresh) Meadow with its actors
        WORLD.tree = g.tree
        g.tree.groups["environmental_event"] = []
        g.actors = {n: Actor(n, k) for n, k in g.kit["wildlife"]}
        g.tree.nodes = dict(g.actors)
        g.evc = g.kit["EVC"]()
        g.ws.environmental_event_controller = g.evc
        g.events = {}
        for name, parent, props in g.kit["events"]:
            e = g.kit["EVT"]()
            for k, v in props.items():
                if k == "position": e.global_position = v
                else: setattr(e, k, v)
            if not isinstance(getattr(e, "global_position", None), Vector3): e.global_position = Vector3()
            e.name, e.parent = name, parent
            e._ready()
            g.events[name] = e
        for path in {p for _, _, pr in g.kit["events"] for k, p in pr.items() if k.endswith("_path") and isinstance(p, str) and p}:
            g.tree.nodes.setdefault(path.split("/")[-1], Actor(path.split("/")[-1], "prop"))
        g.tod._ready()                       # children are ready before their parent
        g.ws._ready()
        g.configure()
        g.npc_phase, g.npc_wait = None, g.NAV_FRAMES   # the M09.1 NPC: follows once its navigation map is ready
        g.meadow_in_tree = True
    def configure(g):
        WORLD.clock = g.clock
        WORLD.tree = g.tree
        g.ws.configure(g.player, Mock(), Mock())
    def frame(g, delta):
        WORLD.clock, WORLD.tree = g.clock, g.tree
        g.ms += int(delta * 1000); WORLD.ms = g.ms
        g.tree.advance(delta)                # SceneTreeTimers run whether or not the Meadow is parked
        g.tod.time_updated.emitted = g.tod.phase_changed.emitted = 0
        g.phase_before = phase_for(g.kit, g.clock.get_fraction())
        if not g.meadow_in_tree:
            return
        g.ws._process(delta)                 # parent first, then its children (TimeOfDay, ..., EnvironmentalEvents)
        if g.tod.processing:
            g.tod._process(delta)
        g.evc._process(delta)
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

def phase_for(kit, f):  # TimeOfDay's phase for a fraction, from its own PHASE_START
    r = "dawn"
    for p, s in kit["tod"]["PHASE_START"].items():
        if f >= s: r = p
    return r
