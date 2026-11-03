#!/usr/bin/env python3
"""Wildlife settling in the rain (W2, D-69) — the real GDScript executed (gd_port): WildlifeActor's activity, decision,
flee and per-frame code (_process and the movement helpers it calls), WildlifeController.set_raining, and the real
WorldSimulation with its WeatherController, WorldClock and event layer (gd_port's Game) for the relay.
1. Activity: for each creature scene's tuning (and an extreme where the floor binds), every darkness the controller
   relays (and out-of-range values) × Clear/Rain, in either relay order: activity = max(0.05, lerp(1, night_activity,
   darkness) × (rain_activity while raining, else 1)); at night in the rain butterfly 0.075, small bird 0.30, rabbit 0.70.
2. Clear is exactly the pre-W2 code: 150 random decision sequences (darkness relays, rests, pauses, wanders with
   interest points and the garden's pull, startles) give identical states, timers and targets against a frozen copy of
   the pre-W2 set_darkness.
3. Next decision only: rain beginning or ending mid-rest or mid-wander changes nothing in flight; the next rest lasts
   1/activity as long.
4. Flee and startle: _enter_flee() and startle() draw the same 1–2 s at any activity.
5. A driven player approach through the real _process: 72 approaches (resting, paused, wandering and startled creatures
   of each species, morning, evening and night, Clear and Rain) — the sighting frame and the flee's start, timer, path and
   end are identical in Clear and Rain; only the rest after it stretches, by exactly the activity ratio.
6. The relay: WildlifeController.set_raining reaches every actor; WorldSimulation tells the actors the current rain at
   configure (a new game, a load and a relaunch during rain, a fresh area during rain), then once per weather change over
   days 2–40, after the startle's listener.
Broken designs, applied to the real sources, are shown to fail.
"""
import math, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd_port

REPO = gd_port.REPO
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()

# ---------------------------------------------------------------- the engine pieces the actor uses
class V3:
    def __init__(s, x=0.0, y=0.0, z=0.0): s.x, s.y, s.z = float(x), float(y), float(z)
    def __add__(s, o): return V3(s.x + o.x, s.y + o.y, s.z + o.z)
    def __sub__(s, o): return V3(s.x - o.x, s.y - o.y, s.z - o.z)
    def __mul__(s, k): return V3(s.x * k, s.y * k, s.z * k)
    __rmul__ = __mul__
    def __truediv__(s, k): return V3(s.x / k, s.y / k, s.z / k)
    def __neg__(s): return V3(-s.x, -s.y, -s.z)
    def __eq__(s, o): return isinstance(o, V3) and (s.x, s.y, s.z) == (o.x, o.y, o.z)
    def __ne__(s, o): return not s == o
    def __hash__(s): return hash((s.x, s.y, s.z))
    def length(s): return math.sqrt(s.x * s.x + s.y * s.y + s.z * s.z)
    def normalized(s):
        n = s.length(); return s / n if n > 0 else V3()
    def dot(s, o): return s.x * o.x + s.y * o.y + s.z * o.z
    def distance_to(s, o): return (s - o).length()
    def move_toward(s, to, delta):
        d = to - s; n = d.length()
        return V3(to.x, to.y, to.z) if n <= delta or n < 1e-12 else s + d / n * delta
    def t(s): return (s.x, s.y, s.z)
class GArray(list):
    def size(s): return len(s)
    def is_empty(s): return len(s) == 0
    def has(s, v): return v in s
class OneOf:
    def __init__(s, *v): s.v = v
    def __eq__(s, o): return o in s.v
def lerp_angle(a, b, w):
    diff = math.fmod(b - a, math.tau)
    return a + (math.fmod(2.0 * diff, math.tau) - diff) * w
RNG = random.Random(0)
gd_port.HELPERS.update({"Vector3": V3, "GArray": GArray, "OneOf": OneOf, "INF": math.inf, "TAU": math.tau, "sin": math.sin, "cos": math.cos,
                        "atan2": math.atan2, "lerpf": lambda a, b, w: a + (b - a) * w, "lerp_angle": lerp_angle,
                        "randf": lambda: RNG.random(), "randf_range": lambda a, b: a + (b - a) * RNG.random(), "randi": lambda: RNG.getrandbits(32)})

def prep(src):
    src = re.sub(r"\bfor (\w+): [\w\[\]]+ in ", r"for \1 in ", src)
    src = re.sub(r"(?<![\w\]])\[\](?!\w)", "GArray()", src)
    src = re.sub(r'^(\t+)("[^"\n]*"(?:, "[^"\n]*")+):$', lambda m: f"{m.group(1)}OneOf({m.group(2)}):", src, flags=re.M)
    return src.replace("node is WildlifeActor", "isinstance(node, SIM_ACTOR)")

ACTOR_FUNCS = ["_ready", "_process", "_idle_look_around", "_face_player", "_move_toward", "_keep_out_detour", "_is_kept_out", "_flee_target",
               "startle", "set_attraction", "set_darkness", "set_raining", "_update_activity", "_enter_idle", "_enter_pause", "_enter_wander", "_enter_flee"]
EXT = {"Vector3.ZERO": "Vector3()", "position": "self.position", "rotation": "self.rotation"}
# The pre-W2 activity code, frozen: the one function W2 replaced (set_darkness), as it was at 5e5fd81.
OLD_SET_DARKNESS = "func set_darkness(darkness: float) -> void:\n\t_activity = lerpf(1.0, night_activity, clampf(darkness, 0.0, 1.0))\n\n"

def sources():
    return {"actor": _src("scripts", "world_simulation", "wildlife_actor.gd"), "butterfly": _src("scripts", "world_simulation", "wildlife_butterfly.gd"),
            "ctl": _src("scripts", "world_simulation", "wildlife_controller.gd"), "world": gd_port.load_sources()}
def pre_w2(actor_src):
    """The actor as it was before W2: the same file with set_darkness / set_raining / _update_activity replaced by the
    frozen pre-W2 set_darkness (the rest of the file is the unmutated original, so only W2's change differs)."""
    out = actor_src
    for fn in ("set_darkness", "set_raining", "_update_activity"):
        out = re.sub(rf"^func {fn}\(.*?(?=^func |^## |\Z)", "", out, flags=re.M | re.S)
    return out + "\n" + OLD_SET_DARKNESS
def actor_class(src, name):
    funcs = [f for f in ACTOR_FUNCS if re.search(rf"^func {f}\(", src, re.M)]
    cls, consts = gd_port.translate(prep(src), name, EXT, funcs)
    class Actor(cls):
        def __init__(a, tuning):
            cls.__init__(a)
            a.position, a.rotation = V3(), V3()
            a._home_position, a._target_position = V3(), V3()   # Vector3 members declared without a value start at zero, as in Godot
            for k, v in tuning.items(): setattr(a, k, v)
    return Actor

def scene_tuning(name):
    t = _src("scenes", "wildlife", f"{name}.tscn")
    root = re.search(r'^\[node name="\w+" type="Node3D" groups=\["wildlife_actor"\]\]\n((?:[^\[\n].*\n)+)', t, re.M).group(1)
    vals = {}
    for k, v in re.findall(r"^(\w+) = (.+)$", root, re.M):
        if k in ("script",): continue
        vals[k] = v.strip('"') if v.startswith('"') else float(v)
    return vals
SPECIES = {"rabbit": scene_tuning("Rabbit"), "small_bird": scene_tuning("SmallBird"), "butterfly": scene_tuning("WildlifeButterfly")}
CTL_SRC0 = _src("scripts", "world_simulation", "wildlife_controller.gd")
DARKNESS = dict(re.findall(r'"(\w+)": ([\d.]+)', re.search(r"^const PHASE_DARKNESS := \{(.*)\}$", CTL_SRC0, re.M).group(1)))
DARKNESS = {k: float(v) for k, v in DARKNESS.items()}
PHASES = {"morning": DARKNESS.get("morning", 0.0), "evening": DARKNESS["evening"], "night": DARKNESS["night"]}
assert set(SPECIES) == {"rabbit", "small_bird", "butterfly"} and all("rain_activity" in v for v in SPECIES.values()), SPECIES
EXPECT_NIGHT_RAIN = {"butterfly": 0.075, "small_bird": 0.30, "rabbit": 0.70}   # D-69

def expected_activity(tuning, darkness, raining):
    night = tuning.get("night_activity", 1.0); rain = tuning.get("rain_activity", 1.0)
    d = min(1.0, max(0.0, darkness))
    return max(0.05, (1.0 + (night - 1.0) * d) * (rain if raining else 1.0))

def snapshot(a):
    return (a.state, round(a._state_timer, 12), a._target_position.t(), a._current_interest_index)

def run(S, quick=False):
    fails = []
    def check(ok, what):
        if not ok: fails.append(what)
    NEW = actor_class(S["actor"], "WildlifeActorW2")
    OLD = actor_class(pre_w2(S0["actor"]), "WildlifeActorPreW2")
    # 0. the butterfly's own code never reads the activity or the rain
    check(not re.search(r"\b(_activity|_raining|rain_activity|set_raining)\b", S["butterfly"]), "the butterfly's own code reads the activity or the rain")
    # 1. activity table
    extreme = {"night_activity": 0.05, "rain_activity": 0.05}
    for name, tuning in list(SPECIES.items()) + [("extreme", extreme)]:
        for d in sorted(set(DARKNESS.values()) | {0.0, -1.0, 2.0}):
            for raining in (False, True):
                for order in (0, 1):
                    a = NEW(tuning)
                    if order: a.set_raining(raining); a.set_darkness(d)
                    else: a.set_darkness(d); a.set_raining(raining)
                    want = expected_activity(tuning, d, raining)
                    check(abs(a._activity - want) < 1e-12, f"{name} darkness {d} {'rain' if raining else 'clear'} order {order}: activity {a._activity}, expected {want}")
                if not raining:
                    o = OLD(tuning); o.set_darkness(d); a = NEW(tuning); a.set_darkness(d)
                    check(a._activity == o._activity, f"{name} darkness {d} clear: {a._activity} vs pre-W2 {o._activity}")
    for name, want in EXPECT_NIGHT_RAIN.items():
        a = NEW(SPECIES[name]); a.set_darkness(DARKNESS["night"]); a.set_raining(True)
        check(abs(a._activity - want) < 1e-9, f"{name} at night in the rain: {a._activity}, D-69 says {want}")
    # 2. Clear identical to the pre-W2 code over random decision sequences
    rng = random.Random(6901)
    for seq in range(60 if quick else 150):
        name = rng.choice(list(SPECIES)); tuning = dict(SPECIES[name])
        tuning.update(interest_points=GArray([V3(1.0, 0.0, 0.5), V3(-0.8, 0.0, 1.2)]), attraction_key="garden", attraction_interest_index=0)
        o, n = OLD(tuning), NEW(tuning)
        seed = rng.getrandbits(32); ops = [rng.choice(["dark", "clear", "idle", "pause", "wander", "startle", "pull"]) for _ in range(rng.randint(5, 40))]
        darks = [rng.choice(list(DARKNESS.values()) + [0.0]) for _ in ops]; pulls = [rng.random() for _ in ops]
        logs = []
        for actor, is_new in ((o, False), (n, True)):
            RNG.seed(seed); log = []
            for op, dk, pull in zip(ops, darks, pulls):
                if op == "dark": actor.set_darkness(dk)
                elif op == "clear":
                    if is_new: actor.set_raining(False)
                elif op == "idle": actor._enter_idle()
                elif op == "pause": actor.state = "wander"; actor._current_interest_index = 0; actor._enter_pause()
                elif op == "wander": actor._enter_wander()
                elif op == "startle": actor.state = "idle"; actor.startle()
                elif op == "pull": actor.set_attraction("garden", pull)
                log.append(snapshot(actor))
            logs.append(log)
        if logs[0] != logs[1]:
            fails.append(f"Clear differs from the pre-W2 code in sequence {seq} ({name}, ops {ops[:8]}...)"); break
    # 3. next decision only
    for name, tuning in SPECIES.items():
        a = NEW(tuning); RNG.seed(11); a._enter_idle(); before = snapshot(a)
        a.set_raining(True); check(snapshot(a) == before, f"{name}: rain beginning changed a rest in flight")
        a.set_raining(False); check(snapshot(a) == before, f"{name}: rain ending changed a rest in flight")
        a._enter_wander(); before = snapshot(a); a.set_raining(True); check(snapshot(a) == before, f"{name}: rain beginning changed a wander in flight")
        RNG.seed(12); a.set_raining(False); a._enter_idle(); clear_t = a._state_timer
        RNG.seed(12); a.set_raining(True); a._enter_idle(); rain_t = a._state_timer
        want = clear_t * expected_activity(tuning, 0.0, False) / expected_activity(tuning, 0.0, True)
        check(abs(rain_t - want) < 1e-9, f"{name}: the next rest in the rain lasts {rain_t}, expected {want}")
    # 4. flee and startle at any activity
    for name, tuning in SPECIES.items():
        draws = set()
        for d in DARKNESS.values():
            for raining in (False, True):
                a = NEW(tuning); a.set_darkness(d); a.set_raining(raining)
                RNG.seed(77); a._enter_flee(); draws.add(("flee", a._state_timer))
                b = NEW(tuning); b.set_darkness(d); b.set_raining(raining); b.state = "idle"
                RNG.seed(77); b.startle(); draws.add(("startle", b._state_timer, b.state))
        check(len(draws) == 2 and all(1.0 <= x[1] < 2.0 for x in draws), f"{name}: the flee or the startle depends on the activity {draws}")
    # 5. driven approaches through the real _process
    approaches = 0
    for name, tuning in SPECIES.items():
        for start in ("rest", "pause", "wander", "startled"):
            for phase, dk in PHASES.items():
                runs = {}
                for raining in (False, True):
                    a = NEW(tuning); a.set_darkness(dk); a.set_raining(raining)
                    RNG.seed(hash((name, start, phase)) & 0xFFFFFFFF)
                    a._ready()
                    if start == "pause": a.state = "wander"; a._enter_pause()
                    elif start == "wander": a._enter_wander()
                    elif start == "startled": a.startle()
                    player = gd_port.Mock(global_position=V3(a.alert_distance + 1.5, 0.0, 0.3))
                    a.player = player
                    seen = []
                    a.sighted.connect(lambda sid, seen=seen: seen.append(frame))
                    rec = {"sighted": None, "flee_start": None, "flee_timer": None, "flee_path": [], "flee_end": None, "rest_after": None}
                    if start == "startled":               # already fleeing before the first frame: the startle is the flee's start
                        rec["flee_start"], rec["flee_timer"] = -1, round(a._state_timer, 12)
                    prev = a.state
                    for frame in range(int(9.0 * 60)):
                        if player.global_position.x > 0.6:
                            player.global_position = player.global_position + V3(-5.0 / 60.0, 0.0, 0.0)
                        a._process(1.0 / 60.0)
                        if seen and rec["sighted"] is None: rec["sighted"] = seen[0]
                        if a.state == "flee" and prev != "flee" and rec["flee_start"] is None:
                            rec["flee_start"], rec["flee_timer"] = frame, round(a._state_timer, 12)
                        if a.state == "flee" and rec["flee_end"] is None and rec["flee_start"] is not None:
                            rec["flee_path"].append(tuple(round(c, 9) for c in a.position.t()))
                        if prev == "flee" and a.state == "idle" and rec["flee_end"] is None:
                            rec["flee_end"], rec["rest_after"] = frame, a._state_timer
                            break
                        prev = a.state
                    runs[raining] = rec
                    approaches += 1
                c, r = runs[False], runs[True]
                tag = f"{name}/{start}/{phase}"
                check(c["flee_start"] is not None and c["flee_end"] is not None, f"{tag}: the approach never made it flee and settle ({c})")
                for k in ("sighted", "flee_start", "flee_timer", "flee_path", "flee_end"):
                    check(c[k] == r[k], f"{tag}: {k} differs in the rain ({str(c[k])[:60]} vs {str(r[k])[:60]})")
                if c["rest_after"] is not None and r["rest_after"] is not None:
                    ratio = expected_activity(tuning, dk, False) / expected_activity(tuning, dk, True)
                    check(abs(r["rest_after"] - c["rest_after"] * ratio) < 1e-9, f"{tag}: the rest after the flee is {r['rest_after']}, expected {c['rest_after'] * ratio}")
    check(approaches == 72, f"{approaches} approaches, expected 72")
    # 6a. the controller relays to every actor
    gd_port.HELPERS["SIM_ACTOR"] = NEW            # `node is WildlifeActor` in the controller (bound when translated)
    CTL, _ = gd_port.translate(prep(S["ctl"]), "WildlifeControllerW2", {}, ["set_raining", "set_time_phase"])
    tree = gd_port.Tree(); gd_port.WORLD.tree = tree
    actors = [NEW(t) for t in SPECIES.values()]
    for a in actors: tree.join("wildlife_actor", a)
    ctl = CTL()
    CTL.__init__(ctl)
    import types
    ctl.get_tree = types.MethodType(lambda self: tree, ctl)
    ctl.set_raining(True)
    check(all(a._raining for a in actors) and all(abs(a._activity - expected_activity(t, 0.0, True)) < 1e-12 for a, t in zip(actors, SPECIES.values())),
          "WildlifeController.set_raining(true) does not reach every actor")
    ctl.set_raining(False)
    check(not any(a._raining for a in actors), "WildlifeController.set_raining(false) does not reach every actor")
    # 6b. WorldSimulation's relay (gd_port's Game: the real WorldSimulation, WeatherController, WorldClock and event layer)
    kit = gd_port.build(S["world"])
    disk = {}
    g = gd_port.Game(kit, disk)
    check(g.wild.rain_calls == 1 and g.wild.raining is False, f"a new game: told {g.wild.rain_calls} time(s), raining {g.wild.raining} (day 1 is Clear)")
    handlers = g.weather.weather_changed.handlers
    i_startle = next((i for i, h in enumerate(handlers) if getattr(h, "__func__", None) is getattr(g.evc.on_weather_changed, "__func__", 0)), -1)
    i_relay = next((i for i, h in enumerate(handlers) if getattr(h, "__func__", None) is getattr(g.ws._on_weather_changed, "__func__", 0)), -1)
    check(0 <= i_startle < i_relay, f"the startle's listener ({i_startle}) comes before the rain relay ({i_relay})")
    g.clock.apply_save_data(gd_port.GDict({"day": 2, "fraction": 0.0}))
    calls, changes, mismatch, rain_moment = g.wild.rain_calls, 0, 0, None
    last = len(g.weather_events)
    step = 2.0 if quick else 1.0
    while g.clock.get_day() <= (12 if quick else 40):
        g.frame(step)
        if len(g.weather_events) != last:
            changes += len(g.weather_events) - last; last = len(g.weather_events)
        if g.wild.raining != g.weather.is_raining(): mismatch += 1
        if rain_moment is None and g.weather.is_raining() and g.clock.get_fraction() > 0.02:
            rain_moment = (g.clock.get_day(), g.clock.get_fraction())
    check(changes > 0 and g.wild.rain_calls - calls == changes, f"days 2–40: {changes} weather changes, {g.wild.rain_calls - calls} relays")
    check(mismatch == 0, f"the actors' rain differed from the weather in {mismatch} frames")
    check(rain_moment is not None, "no rain in the calendar to test a load during")
    if rain_moment:
        g2 = gd_port.Game(kit, {})
        g2.clock.apply_save_data(gd_port.GDict({"day": rain_moment[0], "fraction": rain_moment[1]}))
        g2.save()
        g3 = gd_port.Game(kit, g2.disk)          # a load / relaunch during rain: told before the first frame
        check(g3.wild.rain_calls == 1 and g3.wild.raining is True, f"a load during rain: told {g3.wild.rain_calls} time(s), raining {g3.wild.raining}")
        g3.new_meadow()                          # a fresh area during rain
        check(g3.wild.rain_calls >= 1 and g3.wild.raining is True and g3.weather.is_raining(), "a fresh area during rain is not raining at once")
    return fails

S0 = sources()
if __name__ == "__main__":
    bad = run(S0)
    for b in bad[:12]: print("FAIL:", b)
    assert not bad, "wildlife in the rain failed"
    def mut(part, old, new, key="actor"):
        s = {k: (dict(v) if isinstance(v, dict) else v) for k, v in S0.items()}
        if key == "world":
            assert s["world"][part].count(old) == 1, (part, old[:60]); s["world"][part] = s["world"][part].replace(old, new)
        else:
            assert s[key].count(old) == 1, (key, old[:60]); s[key] = s[key].replace(old, new)
        return s
    MUTANTS = {
        "the rain factor applied in Clear too": mut(None, "var rain_factor := rain_activity if _raining else 1.0", "var rain_factor := rain_activity"),
        "the floor dropped": mut(None, "_activity = maxf(MIN_ACTIVITY, lerpf(1.0, night_activity, _darkness) * rain_factor)", "_activity = lerpf(1.0, night_activity, _darkness) * rain_factor"),
        "the rain scales the darkness instead": mut(None, "_activity = maxf(MIN_ACTIVITY, lerpf(1.0, night_activity, _darkness) * rain_factor)",
                                                     "_activity = maxf(MIN_ACTIVITY, lerpf(1.0, night_activity * rain_factor, _darkness))"),
        "the darkness no longer clamped": mut(None, "_darkness = clampf(darkness, 0.0, 1.0)", "_darkness = darkness"),
        "the activity not recomputed on darkness": mut(None, "\t_darkness = clampf(darkness, 0.0, 1.0)\n\t_update_activity()\n", "\t_darkness = clampf(darkness, 0.0, 1.0)\n"),
        "rain interrupts the rest in flight": mut(None, "\t_raining = raining\n\t_update_activity()\n", "\t_raining = raining\n\t_update_activity()\n\t_state_timer /= _activity\n"),
        "the activity reaches the flee's timer": mut(None, "\t_state_timer = randf_range(1.0, 2.0)\n", "\t_state_timer = randf_range(1.0, 2.0) / _activity\n"),
        "the activity reaches the flee's trigger distance": mut(None, "if state != \"flee\" and player_distance < flee_distance:", "if state != \"flee\" and player_distance < flee_distance / _activity:"),
        "the activity reaches the flee's speed": mut(None, "_move_toward(_flee_target(), flee_speed, delta)", "_move_toward(_flee_target(), flee_speed * _activity, delta)"),
        "the activity reaches the flee's end": mut(None, "position.distance_to(player.global_position) > flee_distance * 1.5)", "position.distance_to(player.global_position) > flee_distance * 1.5 / _activity)"),
        "the controller relays to no actor": mut(None, "\t\t\tactor.set_raining(raining)\n", "\t\t\tpass\n", key="ctl"),
        "the relay inverted": mut("ws", "wildlife_controller.set_raining(weather_controller.is_raining())", "wildlife_controller.set_raining(not weather_controller.is_raining())", key="world"),
        "not told at configure": mut("ws", "\t_on_weather_changed(weather_controller.get_weather())\n", "", key="world"),
        "the relay connected before the startle": mut("ws", "\tweather_controller.weather_changed.connect(environmental_event_controller.on_weather_changed)\n",
                                                       "", key="world"),
    }
    MUTANTS["the relay connected before the startle"]["world"]["ws"] = MUTANTS["the relay connected before the startle"]["world"]["ws"].replace(
        "\tweather_controller.weather_changed.connect(_on_weather_changed)\n",
        "\tweather_controller.weather_changed.connect(_on_weather_changed)\n\tweather_controller.weather_changed.connect(environmental_event_controller.on_weather_changed)\n")
    caught, crashed, survivors = 0, [], []
    for name, s in MUTANTS.items():
        try:
            f = run(s, quick=True)
        except Exception as e:
            f = [f"crash {type(e).__name__}: {e}"]; crashed.append(name)
        if f: caught += 1
        else: survivors.append(name)
    tuning_txt = ", ".join(f"{k} {v['rain_activity']}" for k, v in SPECIES.items())
    print(f"wildlife in the rain (W2): rain_activity {tuning_txt}; activity table, Clear = pre-W2 over 150 sequences, next decision only, "
          f"flee/startle fixed, 72 driven approaches, relay at configure/load/fresh area and once per change (days 2-40)")
    print(f"broken designs: {caught} caught — {caught - len(crashed)} by behaviour, {len(crashed)} by a crash {crashed}")
    if survivors:
        print("SURVIVED:", survivors); sys.exit(1)
    print("ALL WILDLIFE WEATHER SIMULATIONS PASSED")
