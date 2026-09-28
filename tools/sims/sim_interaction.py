#!/usr/bin/env python3
"""Model checks for the generic interaction contract (Python port, not the engine).
1. The rules the model relies on are read from the GDScript, so it can't drift:
   availability is monitorable; Player refuses unavailable/spent objects before
   interacting; one-shot objects are dropped first; InputManager ignores
   unavailable objects; each implementation's one-shot/persistent setting.
2. Player._interact_with over three implementations of the contract:
   a discovery (one-shot, unavailable while its harvest plays), a farm plot
   (persistent) and the non-game probe (persistent, switchable) — the Player
   treats all three the same way.
3. Random sequences: no one-shot object is ever interacted with twice, no
   unavailable object is ever interacted with, INTERACT is open exactly while
   an interaction runs.
4. Verbs as data (M02.2): each object offers exactly the verb its interact()
   would perform in its current state (FarmPlot's two match statements are
   read from the GDScript and cross-checked state by state); nothing while
   unavailable; an empty list is valid; a verb passed back generically is
   performed only if offered.
"""
import itertools, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _body(src, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S)
    assert m, f"{name}() not found"
    return m.group(0)

# ---------------------------------------------------------------- 1. rules
BASE = _src("scripts", "interactables", "interactable.gd")
DISC = _src("scripts", "interactables", "discovery_interactable.gd")
PLOT = _src("scripts", "farming", "farm_plot.gd")
PROBE = _src("tools", "fixtures", "generic_interactable_probe.gd")
PL = _src("scripts", "player", "player.gd")
IM = _src("scripts", "autoload", "input_manager.gd")

assert "return monitorable" in _body(BASE, "is_interaction_available"), "availability must be monitorable"
assert re.search(r"@export var remove_on_harvest: bool = true", BASE), "base default: one-shot"
IW = _body(PL, "_interact_with")
GATE = IW.find("_spent_interactables.has(target) or not target.is_interaction_available()")
assert 0 <= GATE < IW.find("if target.remove_on_harvest") < IW.find("_begin_interaction(target)") < IW.find("target.interact()"), \
    "Player: refuse spent/unavailable, then drop one-shot objects, then INTERACT, then interact()"
assert "is_interaction_available()" in _body(IM, "_find_interactable"), "InputManager ignores unavailable objects"
ONE_SHOT = {
    "discovery": "remove_on_harvest = false" not in DISC,
    "plot": "remove_on_harvest = false" not in _body(PLOT, "_ready"),
    "probe": "remove_on_harvest = false" not in _body(PROBE, "_ready"),
}
assert ONE_SHOT == {"discovery": True, "plot": False, "probe": False}, ONE_SHOT
FEEDBACK = _body(DISC, "_play_harvest_feedback")
assert FEEDBACK.find("monitorable = false") < FEEDBACK.find("await"), "a harvesting discovery is unavailable at once"
assert "monitorable = false" in _body(PLOT, "_run_harvest_sequence"), "a harvesting plot is unavailable"

# ---------------------------------------------------------------- 2. model
class Obj:
    def __init__(o, kind, fails=False):  # fails: DiscoveryManager.discover() refused it
        o.kind, o.one_shot, o.available, o.alive = kind, ONE_SHOT[kind], True, True
        o.calls, o.running, o.fails = 0, False, fails
    def interact(o):  # starts; finish() ends it (the awaited part)
        assert o.available and o.alive, "an unavailable object was interacted with"
        o.calls += 1
        if o.kind == "discovery" and not o.fails:
            o.available, o.running = False, True
        elif o.kind == "plot" and o.calls % 3 == 0:  # every third tap harvests
            o.available, o.running = False, True
    def finish(o):
        o.running = False
        if o.kind == "discovery": o.alive = False  # queue_free
        elif o.kind == "plot": o.available = True

def tap_target(o):  # InputManager._find_interactable
    return o if o.alive and o.available else None

class Player:
    def __init__(p): p.nearby, p.spent, p.serial, p.target, p.state, p.log = [], [], 0, None, "IDLE", []
    def interact_with(p, o):
        p.spent = [s for s in p.spent if s.alive]
        if o in p.spent or not o.available: return None
        if o.one_shot:
            if o in p.nearby: p.nearby.remove(o)
            p.spent.append(o)
        p.serial += 1; p.target = o; p.state = "INTERACT"; p.log.append(o)
        o.interact()
        return p.serial
    def end(p, serial):
        if serial != p.serial or p.target is None: return
        p.target = None; p.state = "IDLE"

# The same Player code path for all three kinds.
for kind in ("discovery", "plot", "probe"):
    p, o = Player(), Obj(kind)
    s = p.interact_with(o); assert s and p.state == "INTERACT" and o.calls == 1, kind
    if not o.running: p.end(s)
    if kind == "discovery":
        assert p.interact_with(o) is None and o.calls == 1, "a one-shot object is never interacted with twice"
failed, p = Obj("discovery", fails=True), Player()
p.end(p.interact_with(failed))
assert failed.available and p.interact_with(failed) is None and failed.calls == 1, \
    "a one-shot object that stayed available is still never interacted with twice"
probe, p = Obj("probe"), Player()
for _ in range(5): p.end(p.interact_with(probe))
assert probe.calls == 5 and p.state == "IDLE", "the probe stays interactable, again and again"
probe.available = False
assert tap_target(probe) is None and p.interact_with(probe) is None and probe.calls == 5, "unavailable probe is refused"
probe.available = True; p.end(p.interact_with(probe)); assert probe.calls == 6, "available again"

# ---------------------------------------------------------------- 3. random
rnd = random.Random(7)
for trial in range(2000):
    objs = [Obj(k, fails=rnd.random() < 0.2) for k in rnd.choices(["discovery", "plot", "probe"], k=4)]
    p, open_serials = Player(), {}
    for _ in range(60):
        o = rnd.choice(objs); ev = rnd.random()
        if ev < 0.5:
            before = o.calls
            target = tap_target(o) if rnd.random() < 0.5 else o  # a tap, or zone entry of an approach target
            s = p.interact_with(target) if target else None
            if s: open_serials[o] = s
            assert o.calls == before or (before == o.calls - 1 and s), "interact() only through an accepted request"
        elif ev < 0.8 and o.running:
            o.finish(); p.end(open_serials.pop(o, -1))
            if not o.alive and p.target is o: p.end(p.serial)  # tree_exiting
        elif o.kind == "probe":
            o.available = rnd.random() < 0.5
        assert (p.state == "INTERACT") == (p.target is not None)
    for o in objs:
        if o.one_shot: assert o.calls <= 1, "one-shot object interacted with twice"
print("interaction contract: discovery / farm plot / probe through one Player path; 2000 random sequences OK")

# ---------------------------------------------------------------- 4. verbs
VERB = {n: int(v) for n, v in re.findall(r"(\w+) = (\d+)", re.search(r"^enum Verb \{([^}]*)\}", BASE, re.M).group(1))}
assert VERB and len(set(VERB.values())) == len(VERB), VERB
GAV = _body(BASE, "get_available_interaction_verbs")
assert re.search(r"if is_interaction_available\(\):\s*verbs = _get_interaction_verbs\(\)", GAV), "no verbs while unavailable"
IWV = _body(BASE, "interact_with_verb")
assert IWV.find("get_available_interaction_verbs().has(verb)") < IWV.find("_perform_interaction_verb(verb)"), "only offered verbs run"
assert "interact()" in _body(BASE, "_perform_interaction_verb"), "a verb runs the existing interact()"

def arms(body):  # PlotState arms of the one match statement in a function body
    out = {}
    for m in re.finditer(r"^\t\t((?:PlotState\.\w+,?\s*)+):\n(.*?)(?=^\t\tPlotState|\Z)", body, re.M | re.S):
        for st in re.findall(r"PlotState\.(\w+)", m.group(1)): out[st] = m.group(2)
    return out
ACTIONS = {"_prepare_soil": None, "request_seed_choice": "PLANT", "_water_crop": "WATER", "_harvest_crop": "HARVEST"}
GUARD = {"PLANT": ["can_plant()"], "WATER": ["_needs_water"], "HARVEST": ["_is_harvesting", "crop_definition"]}
DO, OFFER = arms(_body(PLOT, "interact")), arms(_body(PLOT, "_get_interaction_verbs"))
STATES = re.search(r"^enum PlotState \{([^}]*)\}", PLOT, re.M).group(1).replace(" ", "").split(",")
assert set(DO) == set(STATES), f"interact() handles every plot state {DO.keys()}"
for st in STATES:
    action = next((a for a in ACTIONS if a + "(" in DO[st]), None)
    assert action, f"{st}: unknown farm action"
    offered = re.findall(r"Verb\.(\w+)", OFFER.get(st, ""))
    want = ACTIONS[action]
    assert offered == ([want] if want else []), f"{st}: offers {offered}, but interact() does {action}"
    for g in GUARD.get(want, []):
        assert g in OFFER[st], f"{st}: Verb.{want} must be offered under the same condition as {action} ({g})"
assert re.findall(r"Verb\.(\w+)", _body(DISC, "_get_interaction_verbs")) == ["COLLECT"]
assert "DiscoveryDatabase.has_definition(discovery_id)" in _body(DISC, "_get_interaction_verbs"), \
    "COLLECT exactly when DiscoveryManager.discover() would succeed"
assert "_get_interaction_verbs" not in PROBE, "the probe keeps the base default: no verbs"

# Ports (Python) of the three objects' current-state verbs and actions.
def plot_offer(st, unlocked, harvesting, thirsty, has_crop):
    if not (unlocked and not harvesting): return []                   # monitorable = unlocked and not harvesting
    if st == "SOIL": return ["PLANT"]                                  # can_plant(): unlocked, SOIL, not harvesting
    if st in ("PLANTED", "GROWING"): return ["WATER"] if thirsty else []
    if st == "READY": return ["HARVEST"] if has_crop and not harvesting else []
    return []                                                          # EMPTY: preparing has no verb (O-10)
def plot_action(st, unlocked, harvesting, thirsty, has_crop):
    if st == "EMPTY": return "prepare"
    if st == "SOIL": return "PLANT" if unlocked and not harvesting else None
    if st in ("PLANTED", "GROWING"): return "WATER" if thirsty else None
    if st == "READY": return "HARVEST" if has_crop and not harvesting else None
for st, unlocked, harvesting, thirsty, has_crop in itertools.product(STATES, *[(False, True)] * 4):
    offer = plot_offer(st, unlocked, harvesting, thirsty, has_crop)
    action = plot_action(st, unlocked, harvesting, thirsty, has_crop)
    assert len(offer) <= 1
    if unlocked and not harvesting:
        assert offer == ([action] if action in VERB else []), (st, offer, action)
    else:
        assert offer == [], "an unavailable plot offers nothing"

class VObj:  # the generic Player-side view: verbs + interact_with_verb, no type knowledge
    def __init__(o, offer): o.offer, o.available, o.done = offer, True, []
    def verbs(o): return list(o.offer) if o.available else []
    def interact_with_verb(o, v):
        if v not in o.verbs(): return False
        o.done.append(v); return True
def player_request(obj):  # future UI path: ask, choose, pass back — nothing type-specific
    offered = obj.verbs()
    return obj.interact_with_verb(offered[0]) if offered else False
disc = VObj(["COLLECT"]); assert player_request(disc) and disc.done == ["COLLECT"]
disc.available = False; assert disc.verbs() == [] and not player_request(disc), "harvesting discovery offers nothing"
assert not disc.interact_with_verb("COLLECT") and disc.done == ["COLLECT"], "an unoffered verb is refused"
unknown = VObj([]); assert unknown.verbs() == [] and not player_request(unknown), "empty verb list is valid"
probe = VObj([]); assert not player_request(probe)
plot = VObj([])
for st, exp in (("EMPTY", []), ("SOIL", ["PLANT"]), ("GROWING", ["WATER"]), ("GROWING", []), ("READY", ["HARVEST"])):
    plot.offer = plot_offer(st, True, False, exp == ["WATER"], True)
    assert plot.verbs() == exp, (st, plot.verbs())
    assert not plot.interact_with_verb("COLLECT"), "a verb the plot doesn't offer is refused"
    if exp: assert player_request(plot) and plot.done[-1] == exp[0]
assert plot.done == ["PLANT", "WATER", "HARVEST"], "verbs follow the plot's changing state"
print(f"verbs: {sorted(VERB, key=VERB.get)}; plot states cross-checked against interact(): {STATES}")
print("ALL INTERACTION SIMULATIONS PASSED")
