#!/usr/bin/env python3
"""The weather reaction (M09.4, D-44) — the real GDScript executed: EnvironmentalEvent (environmental_event.gd) and
EnvironmentalEventController, built from Meadow.tscn's own events (the five proximity events and RainBirdDisturbance)
and wildlife roster, inside gd_port's engine model with the real WorldSimulation, WorldClock, WeatherController and
save path; every wildlife actor records the startle() calls it receives.
1. Clear -> Rain during play fires RainBirdDisturbance exactly once: each of the five SmallBirds is startled once,
   no butterfly or rabbit; Rain -> Rain (midnight inside a spell), Rain -> Clear, a load or relaunch into rain, a return
   outdoors into rain and a fresh area during rain startle nothing.
2. Every rain spell that begins during play (days 2-40) reacts exactly once; the 60 s cooldown and repeatable keep
   their meaning (a second "rain" within 60 s does nothing, after it reacts again; "clear" never does).
3. A weather-triggered event never enters the distance loop: the player standing on it fires nothing, its presence is
   never tracked.
4. The proximity events behave exactly as before: frame by frame, over random walks with discoveries and ripe crops
   changing, the real controller fires the same events at the same frames as a reference written from the pre-M09.4
   code — and RainBirdDisturbance is not among them.
5. The NPC, farming and audio take no part (their sources never name the reaction).
Broken designs, applied to the real source or scene, are shown to break: no distance-loop skip, any weather change
firing, can_trigger bypassed, a reaction on load, a one-shot rain event, a bird missing or a butterfly added, the
proximity skip reversed.
"""
import json, math, os, random, re
import gd_port
from gd_port import *

REPO = gd_port.REPO
def _code(*p): return re.sub(r"(?m)#.*$", "", open(os.path.join(REPO, *p), encoding="utf-8").read())

# ---------------------------------------------------------------- the pre-M09.4 proximity rules (environmental_event.gd / its controller before D-44)
class RefEvent:
    MARGIN = 0.75
    def __init__(r, name, props, tree):
        r.name, r.tree = name, tree
        r.pos = props.get("position", Vector3())
        r.radius = props.get("trigger_radius", 3.5); r.cooldown = props.get("cooldown_seconds", 75.0)
        r.repeatable = props.get("repeatable", True); r.related = props.get("related_discovery_id", "")
        r.crops = props.get("requires_ready_crops", False); r.arrival = props.get("trigger_on_arrival", False)
        r.on_cooldown, r.once, r.inside, r.departed = False, False, False, -1
        r.type, r.actors = props.get("event_type", 0), [a.split("/")[-1] for a in props.get("actor_paths", [])]
    def can_trigger(r):
        if r.on_cooldown or (not r.repeatable and r.once): return False
        if r.related and r.related in World.discovered: return False
        if r.crops and not World.ready_crops: return False
        if r.crops and r.arrival and World.ripened_msec <= r.departed: return False
        return True
    def presence(r, d):
        if r.inside:
            if d > r.radius + r.MARGIN: r.inside, r.departed = False, World.ms
            return False
        if d <= r.radius: r.inside = True; return True
        return False
    def fire(r, log):
        r.once, r.on_cooldown = True, True
        t = r.tree.create_timer(r.cooldown); t.timeout.connect(lambda: setattr(r, "on_cooldown", False))
        log.append(r.name)
        if r.type == 0:                            # WILDLIFE_DISTURBANCE: every listed actor is startled
            for a in r.actors: REF_STARTLES[a] = REF_STARTLES.get(a, 0) + 1
REF_STARTLES = {}
def ref_frame(events, player, log):
    for e in events:
        d = e.pos.distance_to(player)
        if e.arrival:
            if e.presence(d) and e.can_trigger(): e.fire(log)
            continue
        if d <= e.radius and e.can_trigger(): e.fire(log)

def clock_at(kit, day, f):
    return Game(kit, {"save": json.dumps({"save_version": kit["version"], "world_time": {"day": day, "fraction": f}})})

def startles(g): return {n: a.startled for n, a in g.actors.items()}
BIRDS = None

def scripted(kit):
    p = []
    birds = [n for n, k in kit["wildlife"] if k == "bird"]
    others = [n for n, k in kit["wildlife"] if k != "bird"]
    if len(birds) != 5: p.append(f"{len(birds)} birds in the Meadow")
    def only_birds_once(g, label, n=1):
        s = startles(g)
        if any(s[b] != n for b in birds) or any(s[o] for o in others): p.append(f"{label}: startles {s}, expected each bird {n}, nothing else")
    # 1. Clear -> Rain during play: once; then midnight inside the spell, then Rain -> Clear: nothing more
    g = clock_at(kit, 4, 0.749)
    for _ in range(200): g.frame(1 / 60)
    if [w for _, _, w in g.weather_events] != ["rain"]: p.append(f"expected one rain flip, got {g.weather_events}")
    only_birds_once(g, "Clear -> Rain")
    g2 = clock_at(kit, 4, 0.9985)
    for _ in range(400): g2.frame(1 / 60)
    only_birds_once(g2, "midnight inside a spell", 0)
    g3 = clock_at(kit, 5, 0.2497)
    for _ in range(300): g3.frame(1 / 60)
    if [w for _, _, w in g3.weather_events] != ["clear"]: p.append(f"expected Rain -> Clear, got {g3.weather_events}")
    only_birds_once(g3, "Rain -> Clear", 0)
    # load / relaunch / return outdoors / fresh area during rain: silent
    gl = clock_at(kit, 5, 0.1)
    for _ in range(120): gl.frame(1 / 60)
    gl.meadow_in_tree = False
    for _ in range(300): gl.frame(1 / 60)
    gl.meadow_in_tree = True
    for _ in range(120): gl.frame(1 / 60)
    only_birds_once(gl, "load into rain, a return outdoors", 0)
    gl.new_meadow()
    for _ in range(120): gl.frame(1 / 60)
    only_birds_once(gl, "a fresh area during rain", 0)
    disk = {}; gs = clock_at(kit, 7, 0.6); gs.disk = disk; gs.save(); gr = Game(kit, disk)
    for _ in range(120): gr.frame(1 / 60)
    only_birds_once(gr, "a relaunch into rain", 0)
    # 2. every spell that begins during play reacts once
    ga = clock_at(kit, 2, 0.0); flips = 0
    while ga.clock.get_day() < 40:
        ga.frame(1.0)
    flips = sum(1 for _, _, w in ga.weather_events if w == "rain")
    fired = ga.events["RainBirdDisturbance"]._triggered_once
    s = startles(ga)
    if flips < 10 or any(s[b] != flips for b in birds) or any(s[o] for o in others):
        p.append(f"{flips} rain spells began in days 2-40, startles {s}")
    # cooldown and repeatable, through on_weather_changed itself
    gc = clock_at(kit, 2, 0.1)
    gc.evc.on_weather_changed("rain"); gc.evc.on_weather_changed("rain")
    for _ in range(59): gc.frame(1.0)
    gc.evc.on_weather_changed("rain")
    only_birds_once(gc, "a second rain within the 60 s cooldown")
    for _ in range(2): gc.frame(1.0)
    gc.evc.on_weather_changed("clear")
    only_birds_once(gc, "clear after the cooldown")
    gc.evc.on_weather_changed("rain")
    only_birds_once(gc, "rain again after the cooldown", 2)
    # 3. never by distance: the player on the rain event (and walking around it), its presence never tracked
    gp = clock_at(kit, 2, 0.3)
    rain_evt = gp.events["RainBirdDisturbance"]
    tracked = []
    orig = rain_evt.update_player_presence
    rain_evt.update_player_presence = lambda d: (tracked.append(d), orig(d))[1]
    for k in range(900):
        gp.player.global_position = rain_evt.global_position + Vector3(math.cos(k / 30) * (k % 5), 0.0, math.sin(k / 30) * (k % 5))
        gp.frame(1 / 30)
    if rain_evt._triggered_once or tracked or any(startles(gp).values()): p.append(f"the rain event reacted to the player (fired {rain_evt._triggered_once}, presence tracked {len(tracked)})")
    # 5. the NPC, farming and audio never take part
    for f in (("scripts", "npc", "npc.gd"), ("scripts", "autoload", "farm_manager.gd"), ("scripts", "farming", "farm_plot.gd"), ("scripts", "autoload", "ambient_audio_manager.gd")):
        if re.search(r"weather|trigger_weather|on_weather_changed|RainBird", _code(*f)): p.append(f"{'/'.join(f)} takes part in the weather reaction")
    for root, _, files in os.walk(os.path.join(REPO, "scripts")):
        for fn in files:
            if fn.endswith(".gd") and fn != "ambient_audio_manager.gd" and "play_wildlife_sound(" in _code(root, fn): p.append(f"{fn} plays a wildlife sound")
    return p

def proximity_session(kit, seed):
    """Random walks with discoveries and ripe crops changing: the real controller vs the pre-M09.4 reference."""
    rnd, p = random.Random(seed), []
    World.discovered, World.ready_crops, World.ripened_msec = set(), False, -1
    g = clock_at(kit, 1, 0.3)                      # day 1: Clear all day, so only proximity can fire
    new_log, ref_log = [], []
    REF_STARTLES.clear()
    for name, e in g.events.items():
        orig = e.fire
        e.fire = (lambda n, o: (lambda: (new_log.append(n), o())))(name, orig)
    ref_tree = Tree()
    refs = [RefEvent(n, pr, ref_tree) for n, par, pr in kit["events"] if pr.get("trigger_weather", "") == ""]
    pos = Vector3(rnd.uniform(-20, 20), 0.0, rnd.uniform(-15, 15))
    targets = [e.global_position for e in g.events.values()] + [Vector3(rnd.uniform(-25, 25), 0, rnd.uniform(-25, 25)) for _ in range(4)]
    goal = rnd.choice(targets)
    for frame in range(rnd.randint(600, 1500)):
        if rnd.random() < 0.01: World.discovered ^= {rnd.choice(["hidden_herb", "river_stone", "wild_mint"])}
        if rnd.random() < 0.01: World.ready_crops = not World.ready_crops
        if rnd.random() < 0.005: World.ripened_msec = World.ms
        if pos.distance_to(goal) < 0.5 or rnd.random() < 0.004: goal = rnd.choice(targets)
        step = min(4.3 / 30, pos.distance_to(goal))
        d = max(pos.distance_to(goal), 1e-9)
        pos = Vector3(pos.x + (goal.x - pos.x) / d * step, 0.0, pos.z + (goal.z - pos.z) / d * step)
        g.player.global_position = pos
        n0, r0 = len(new_log), len(ref_log)
        g.frame(1 / 30)                           # timers advance first in the model, as in the reference below
        ref_tree.advance(1 / 30)
        ref_frame(refs, pos, ref_log)
        if new_log[n0:] != ref_log[r0:]:
            p.append(f"frame {frame} at ({pos.x:.1f}, {pos.z:.1f}): fired {new_log[n0:]}, before M09.4 {ref_log[r0:]}"); break
        got = {n: c for n, c in startles(g).items() if c}
        if got != REF_STARTLES:
            p.append(f"frame {frame}: startled {got}, before M09.4 {REF_STARTLES}"); break
    if "RainBirdDisturbance" in new_log: p.append("the rain event fired by proximity")
    return p

def mutate(name):
    s = dict(SOURCES)
    def rep(key, old, new):
        assert old in s[key], (name, old); s[key] = s[key].replace(old, new, 1)
    if name == "no_distance_skip": rep("evc", 'if event == null or event.trigger_weather != "":', "if event == null:")
    elif name == "any_weather_fires": rep("evc", 'or event.trigger_weather != weather:', ":")
    elif name == "can_trigger_bypassed": rep("evc", "\t\tif event.can_trigger():\n\t\t\tevent.fire()\n", "\t\tevent.fire()\n")
    elif name == "reaction_on_load": rep("ws", "\tweather_controller.weather_changed.connect(environmental_event_controller.on_weather_changed)\n",
                                         "\tweather_controller.weather_changed.connect(environmental_event_controller.on_weather_changed)\n\tenvironmental_event_controller.on_weather_changed(weather_controller.get_weather())\n")
    elif name == "rain_event_one_shot": rep("meadow", 'repeatable = true\ntrigger_weather = "rain"', 'repeatable = false\ntrigger_weather = "rain"')
    elif name == "bird_missing": rep("meadow", 'NodePath("../../Wildlife/SmallBird3"), ', "")
    if name == "butterfly_added":
        old = 'trigger_weather = "rain"\nactor_paths = ['; new = 'trigger_weather = "rain"\nactor_paths = [NodePath("../../Wildlife/WildlifeButterfly1"), '
        assert old in s["meadow"]; s["meadow"] = s["meadow"].replace(old, new, 1)
    elif name == "proximity_skip_reversed": rep("evc", 'if event == null or event.trigger_weather != "":', 'if event == null or event.trigger_weather == "":')
    return s

REAL = build(SOURCES)
bad = scripted(REAL)
assert not bad, bad
N = 120
fails = [d for d in range(N) if proximity_session(REAL, d)]
assert not fails, f"{len(fails)} walks differ from the pre-M09.4 proximity rules, e.g. {proximity_session(REAL, fails[0])}"
BROKEN = ["no_distance_skip", "any_weather_fires", "can_trigger_bypassed", "reaction_on_load", "rain_event_one_shot", "bird_missing", "butterfly_added", "proximity_skip_reversed"]
caught = {}
for name in BROKEN:
    kit = build(mutate(name))
    try:
        probs = scripted(kit) or next((r for d in range(40) for r in [proximity_session(kit, d)] if r), [])
    except Exception as e:
        probs = [f"{type(e).__name__}: {e}"]
    assert probs, f"the {name} design is shown to break the reaction"
    caught[name] = probs[0]
birds = [n for n, k in REAL["wildlife"] if k == "bird"]
print(f"weather reaction: RainBirdDisturbance startles {birds} once per rain spell begun during play (none on Rain -> Rain, Rain -> Clear, load, relaunch, "
      f"return outdoors, fresh area); every spell of days 2-40 reacts; 60 s cooldown and repeatable kept; never by distance; the five proximity events "
      f"fire frame for frame as before over {N} random walks; NPC, farming and audio take no part")
print("broken designs caught: " + "; ".join(f"{k}: {v[:100]}" for k, v in caught.items()))
print("ALL WEATHER REACTION SIMULATIONS PASSED")
