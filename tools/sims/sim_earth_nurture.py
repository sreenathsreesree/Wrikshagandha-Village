#!/usr/bin/env python3
"""Earth — Nurture (M11.1, D-47): the real EarthNurture GDScript translated with gd_port (its `await` becomes a
generator yield) and run against a model of the engine pieces it uses — tweens bound to the node (parallel and
sequential steps, delays, intervals, callbacks; paused while the area is parked), the scene's Growth children read from
EarthNurture.tscn, the Player's refusal of unavailable objects (read from player.gd) and a ledger of every autoload call.
1. A fresh plant is dormant (every Growth child at dormant_scale of its authored size) and offers exactly USE.
2. One use: unavailable at once; interact() returns true when the grow-in has played (0.7 s + 0.2 s stagger per later
   child), every child then at its awake size; it holds 6 s, relaxes over 1.5 s back to dormant, then is available again
   — D-47's timeline, frame by frame.
3. While the cycle runs, taps are refused (the Player's rule) and a direct interact() returns false without touching
   the cycle; afterwards it can be used again, five cycles in a row alike.
4. Only the Growth children move: the root's scale is never written; nothing else is touched.
5. No side effects: no autoload is called (points, coins, items, discoveries, Journal, save, farming, HUD, clock...),
   it is never freed, remove_on_harvest is false; a relaunch (a new instance) is dormant and available.
6. Parked mid-cycle (a door trip), the cycle pauses and finishes the same amount later.
Broken designs (mutated sources) are shown to fail; kills by a crash are reported separately.
"""
import math, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd_port

REPO = gd_port.REPO
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
D47 = {"grow": 0.7, "stagger": 0.2, "hold": 6.0, "relax": 1.5}   # D-47's approved timeline
DT = 1 / 60

class Vec:
    def __init__(v, x, y, z): v.x, v.y, v.z = float(x), float(y), float(z)
    def __mul__(v, k): return Vec(v.x * k, v.y * k, v.z * k)
    __rmul__ = __mul__
    def close(v, o, eps=1e-6): return isinstance(o, Vec) and abs(v.x - o.x) < eps and abs(v.y - o.y) < eps and abs(v.z - o.z) < eps
    def lerp(v, o, t): return Vec(v.x + (o.x - v.x) * t, v.y + (o.y - v.y) * t, v.z + (o.z - v.z) * t)
    def __repr__(v): return f"({v.x:.3f}, {v.y:.3f}, {v.z:.3f})"

class Count(int):                       # parts.size(): an int GDScript's `for i in n:` iterates
    def __iter__(c): return iter(range(int(c)))
class Parts(list):
    def size(p): return Count(len(p))
class Part:
    def __init__(p, name, scale): p.name, p.scale, p.writes = name, scale, 0
    def __setattr__(p, k, v):
        if k == "scale" and "scale" in p.__dict__: p.__dict__["writes"] = p.__dict__.get("writes", 0) + 1
        object.__setattr__(p, k, v)
class Growth:
    def __init__(g, parts): g.parts = parts
    def get_children(g): return Parts(g.parts)

class Ledger:
    def __init__(l, name, log): l.name, l.log = name, log
    def __getattr__(l, k):
        if k.startswith("__"): raise AttributeError(k)
        return lambda *a: l.log.append(f"{l.name}.{k}")

class Step:
    def __init__(s, kind, target=None, prop=None, value=None, duration=0.0, fn=None):
        s.kind, s.target, s.prop, s.value, s.duration, s.fn, s.delay, s.parallel = kind, target, prop, value, float(duration), fn, 0.0, False
    def set_delay(s, d): s.delay = float(d); return s
    def set_trans(s, t): return s
    def set_ease(s, e): return s
class Tween:
    """A Godot Tween as EarthNurture uses it: steps run in sequence unless marked parallel (set_parallel(true) or
    parallel() before a step); a property step captures its start value when it starts; time advances only while the
    owner is in the tree (a bound tween pauses while the area is parked)."""
    def __init__(t, owner):
        t.owner, t.steps, t.all_parallel, t.next_parallel, t.time, t.done, t.started = owner, [], False, False, 0.0, False, set()
        owner.engine.tweens.append(t)
    def set_parallel(t, on=True): t.all_parallel = bool(on); return t
    def parallel(t): t.next_parallel = True; return t
    def chain(t): t.next_parallel = False; return t
    def _add(t, s):
        s.parallel = bool(t.steps) and (t.all_parallel or t.next_parallel)
        t.next_parallel = False
        t.steps.append(s)
        return s
    def tween_property(t, target, prop, value, duration): return t._add(Step("prop", target, prop, value, duration))
    def tween_interval(t, d): return t._add(Step("interval", duration=d))
    def tween_callback(t, fn): return t._add(Step("call", fn=fn))
    def groups(t):
        out = []
        for s in t.steps:
            if s.parallel and out: out[-1].append(s)
            else: out.append([s])
        return out
    def advance(t, dt):
        if t.done: return
        t.time += dt
        start = 0.0
        for g in t.groups():
            length = max(s.delay + s.duration for s in g)
            for s in g:
                a, b = start + s.delay, start + s.delay + s.duration
                if t.time + 1e-9 < a: continue
                if id(s) not in t.started:
                    t.started.add(id(s))
                    s.from_value = getattr(s.target, s.prop) if s.kind == "prop" else None
                    if s.kind == "call": s.fn()
                if s.kind == "prop":
                    k = 1.0 if s.duration <= 0 or t.time >= b else (t.time - a) / s.duration
                    setattr(s.target, s.prop, s.from_value.lerp(s.value, k) if isinstance(s.from_value, Vec) else s.value)
            start += length
        if t.time + 1e-9 >= start:
            t.done = True

class Engine:
    def __init__(e): e.tweens, e.parked, e.now = [], False, 0.0
    def tick(e):
        e.now += DT
        if not e.parked:
            for t in list(e.tweens): t.advance(DT)

def build(sources):
    gd_port.NODE_METHODS[:] = ["get_tree", "get_node_or_null", "add_to_group", "create_tween", "queue_free"]
    src = sources["en"]
    src = re.sub(r"\\\n\s*", "", src)                                   # backslash line continuations
    src = re.sub(r"^(\s*)await (\w+)\.finished\s*$", r"\1yield \2", src, flags=re.M)
    src = re.sub(r"= \$Growth$", "= None", src, flags=re.M)
    src = "var monitorable = true\nvar remove_on_harvest = true\nvar scale = ROOT_SCALE\nvar freed = false\n" + src
    verbs = dict((n, int(v)) for n, v in re.findall(r"(\w+) = (\d+)", re.search(r"^enum Verb \{([^}]*)\}", sources["base"], re.M).group(1)))
    log = []
    autoloads = re.findall(r'^(\w+)="\*?res://', re.search(r"\[autoload\]\n(.*?)(?:\n\[|\Z)", sources["project"], re.S).group(1), re.M)
    ext = {"Verb": "VERB", "Tween": "TWEENC", **{a: f"LEDGER_{a}" for a in autoloads}}
    gd_port.HELPERS.update(VERB=gd_port.Mock(**verbs), TWEENC=gd_port.Mock(TRANS_BACK=0, TRANS_SINE=1, EASE_OUT=0, EASE_IN_OUT=2),
                           ROOT_SCALE=Vec(1, 1, 1), **{f"LEDGER_{a}": Ledger(a, log) for a in autoloads})
    EN, _ = gd_port.translate(src, "EarthNurture", ext)
    def _setattr(self, k, v):                       # every write to the root's own scale after construction
        if k == "scale" and "engine" in self.__dict__: self.__dict__["root_writes"].append(k)
        object.__setattr__(self, k, v)
    EN.__setattr__ = _setattr
    scene = sources["scene"]
    names = re.findall(r'^\[node name="(\w+)" type="Node3D" parent="Growth"\]\n((?:[^\[\n].*\n?)*)', scene, re.M)
    def authored(body):
        m = re.search(r"^scale = Vector3\(([^)]*)\)", body, re.M)
        return Vec(*(float(v) for v in m.group(1).split(","))) if m else Vec(1, 1, 1)
    def make(engine):
        en = EN()
        object.__setattr__(en, "root_writes", [])
        en.engine = engine
        en.create_tween = lambda: Tween(en)
        en.queue_free = lambda: setattr(en, "freed", True)
        en._growth = Growth([Part(n, authored(b)) for n, b in names])
        en.awake = [p.scale for p in en._growth.parts]
        en._ready()
        return en
    player = sources["player"]
    refuse = re.search(r"if _spent_interactables\.has\(target\) or not target\.is_interaction_available\(\):\s*return", player) is not None
    return make, log, verbs, refuse

class Use:
    """One interaction as the Player runs it: refused while unavailable (Player._interact_with), else interact() is
    awaited — the generator is resumed when the tween it waits on finishes."""
    def __init__(u, en, refuse_rule):
        u.en, u.result, u.gen, u.waiting, u.ended_at = en, None, None, None, None
        if refuse_rule and not en.monitorable:
            u.result = "refused"; return
        r = en.interact()
        if hasattr(r, "send"): u.gen = r; u.step()
        else: u.result = r
    def step(u):
        try:
            u.waiting = next(u.gen) if u.waiting is None else u.gen.send(None)
        except StopIteration as stop:
            u.result, u.gen = stop.value, None
    def poll(u, engine):
        if u.gen is not None and (u.waiting is None or u.waiting.done):
            u.step()
            if u.result is not None: u.ended_at = engine.now

def run(sources):
    p = []
    make, log, verbs, refuse = build(sources)
    eng = Engine(); en = make(eng)
    n = len(en._growth.parts)
    if n < 2: return [f"the plant needs staggered Growth children (found {n})"]
    grow_total = D47["grow"] + D47["stagger"] * (n - 1)
    def scales(): return [q.scale for q in en._growth.parts]
    def is_dormant(): return all(s.close(a * en.dormant_scale) for s, a in zip(scales(), en.awake))
    def is_awake(): return all(s.close(a) for s, a in zip(scales(), en.awake))
    if not (is_dormant() and en.monitorable and en.remove_on_harvest is False and en._get_interaction_verbs() == [verbs["USE"]]):
        p.append("a fresh plant is dormant, available, persistent and offers exactly USE")
    if not math.isclose(en.dormant_scale, 0.4): p.append(f"dormant at 0.4 of its awake size (found {en.dormant_scale})")
    def cycle(tag, parked_for=0.0, taps=True):
        start = eng.now
        u = Use(en, refuse)
        if en.monitorable: p.append(f"{tag}: unavailable as soon as it is used")
        refused, direct = 0, []
        returned_at, awake_ok, avail_at, park_done = None, None, None, parked_for <= 0
        while eng.now - start < 60 + parked_for:
            if not park_done and eng.now - start >= 0.5:
                eng.parked = True
                if eng.now - start >= 0.5 + parked_for: eng.parked, park_done = False, True
            eng.tick(); u.poll(eng)
            if u.ended_at is not None and returned_at is None:
                returned_at = eng.now - start; awake_ok = is_awake()
            if taps and not en.monitorable and random.random() < 0.05:
                v = Use(en, refuse); refused += v.result == "refused"
                d = en.interact()
                if hasattr(d, "send"):                  # interact() awaits, so it runs as a generator
                    try:
                        next(d); d = "started"
                    except StopIteration as stop:
                        d = stop.value
                direct.append(d is False)
            if en.monitorable and avail_at is None:
                avail_at = eng.now - start
                break
        exp_ret = grow_total + parked_for
        if u.result is not True or returned_at is None or abs(returned_at - exp_ret) > 2.5 * DT:
            p.append(f"{tag}: interact() returns true when the grow-in has played ({exp_ret:.2f} s; got {u.result} at {returned_at})")
        if awake_ok is False: p.append(f"{tag}: every Growth child is awake when interact() returns")
        exp_av = grow_total + D47["hold"] + D47["relax"] + parked_for
        if avail_at is None or abs(avail_at - exp_av) > 2.5 * DT:
            p.append(f"{tag}: available again after hold and relax ({exp_av:.2f} s; got {avail_at})")
        if not is_dormant(): p.append(f"{tag}: back to dormant at the end")
        if taps and (not refuse or not all(direct)):
            p.append(f"{tag}: taps during the cycle are refused and a direct interact() returns false ({refused} refused, {direct.count(False)} accepted)")
        return avail_at
    random.seed(11)
    # the awake hold: sample mid-hold
    eng2 = Engine(); en2 = make(eng2); u2 = Use(en2, refuse)
    while eng2.now < grow_total + D47["hold"] / 2:
        eng2.tick(); u2.poll(eng2)
    if not all(s.close(a) for s, a in zip([q.scale for q in en2._growth.parts], en2.awake)) or en2.monitorable:
        p.append("mid-hold the plant is fully awake and still unavailable")
    times = [cycle(f"cycle {k + 1}") for k in range(5)]
    if len(set(round(t or -1, 3) for t in times)) != 1: p.append(f"five cycles in a row behave alike ({times})")
    cycle("parked mid-cycle", parked_for=30.0, taps=False)
    if en.root_writes: p.append(f"the root's scale is never written ({len(en.root_writes)} writes)")
    if log: p.append(f"no side effects: no autoload is called ({sorted(set(log))})")
    if getattr(en, "freed", False): p.append("the plant is never freed")
    fresh = make(Engine())
    if not (fresh.monitorable and all(q.scale.close(a * fresh.dormant_scale) for q, a in zip(fresh._growth.parts, fresh.awake))):
        p.append("a relaunch (a new instance) is dormant and available")
    return p

def sources():
    return {"en": _src("scripts", "elements", "earth_nurture.gd"), "scene": _src("scenes", "elements", "EarthNurture.tscn"),
            "base": _src("scripts", "interactables", "interactable.gd"), "player": _src("scripts", "player", "player.gd"),
            "project": _src("project.godot")}

S = sources()
bad = run(S)
assert not bad, f"Earth Nurture: {bad}"

def mutate(key, old, new):
    s = dict(S); assert old in s[key], (key, old); s[key] = s[key].replace(old, new, 1); return s
MUTANTS = {
    "grow-in 1.4 s": mutate("en", "var grow_seconds: float = 0.7", "var grow_seconds: float = 1.4"),
    "no stagger": mutate("en", ".set_delay(i * stagger_seconds)", ".set_delay(0.0)"),
    "hold 60 s": mutate("en", "var hold_seconds: float = 6.0", "var hold_seconds: float = 60.0"),
    "no relaxation (stays awake)": mutate("en", "_awake_scales[i] * dormant_scale, relax_seconds", "_awake_scales[i], relax_seconds"),
    "never available again": mutate("en", "func _on_dormant() -> void:\n\tmonitorable = true", "func _on_dormant() -> void:\n\tpass"),
    "no guard, never unavailable": mutate("en", "\tif not monitorable:\n\t\treturn false\n\tmonitorable = false\n", ""),
    "never made unavailable (guard kept)": mutate("en", "\tmonitorable = false\n\tvar parts", "\tvar parts"),
    "returns before the grow-in": mutate("en", "\tawait grow.finished\n\t_hold_then_relax()", "\t_hold_then_relax()"),
    "the root's scale animated": mutate("en", "\tawait grow.finished", "\tscale = scale * 1.2\n\tawait grow.finished"),
    "a reward": mutate("en", "\t_hold_then_relax()\n\treturn true", "\t_hold_then_relax()\n\tPointsManager.add_points(5)\n\treturn true"),
    "a save": mutate("en", "\t_hold_then_relax()\n\treturn true", "\t_hold_then_relax()\n\tSaveManager.save_game()\n\treturn true"),
    "a farming call": mutate("en", "\tmonitorable = false\n\tvar parts", "\tmonitorable = false\n\tFarmManager.notify_place_reached(\"x\")\n\tvar parts"),
    "a Journal entry": mutate("en", "\t_hold_then_relax()\n\treturn true", "\t_hold_then_relax()\n\tJournalManager.add_entry(null)\n\treturn true"),
    "freed after use": mutate("en", "func _on_dormant() -> void:\n\tmonitorable = true", "func _on_dormant() -> void:\n\tmonitorable = true\n\tqueue_free()"),
    "one-shot (remove_on_harvest stays true)": mutate("en", "\tremove_on_harvest = false\n", ""),
    "offers COLLECT": mutate("en", "verbs.append(Verb.USE)", "verbs.append(Verb.COLLECT)"),
    "a single growth child": {**S, "scene": S["scene"].replace('[node name="Leaves" type="Node3D" parent="Growth"]', '[node name="Leaves" type="Node3D" parent="Growth/Stem"]')
                                               .replace('[node name="Bud" type="Node3D" parent="Growth"]', '[node name="Bud" type="Node3D" parent="Growth/Stem"]')},
}
killed = {}
for name, s in MUTANTS.items():
    try:
        r = run(s)
        killed[name] = ("behaviour", r[0]) if r else None
    except Exception as e:  # noqa: BLE001 — a mutant that breaks the run is reported separately
        killed[name] = ("crash", f"{type(e).__name__}: {e}")
survivors = [n for n, k in killed.items() if k is None]
assert not survivors, f"broken designs not caught: {survivors}"
crashes = [n for n, k in killed.items() if k[0] == "crash"]
n_parts = len(re.findall(r'parent="Growth"\]', S["scene"]))
print(f"earth nurture: {n_parts} growth parts dormant at 0.4; use -> unavailable at once, interact() true after "
      f"{D47['grow'] + D47['stagger'] * (n_parts - 1):.1f} s (awake), hold {D47['hold']:.0f} s, relax {D47['relax']} s, available again; "
      f"taps and direct calls refused while active; 5 cycles alike; parked 30 s mid-cycle -> 30 s later; root scale never "
      f"written; no autoload called; never freed; a new instance is dormant")
print(f"broken designs: {len(MUTANTS)} caught — {len(MUTANTS) - len(crashes)} by behaviour, {len(crashes)} by a crash {crashes}")
print("ALL EARTH NURTURE SIMULATIONS PASSED")
