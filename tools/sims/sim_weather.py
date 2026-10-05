#!/usr/bin/env python3
"""Simple weather (M09.3, D-43) — the real GDScript executed: WeatherController (weather_controller.gd) with its
WeatherSchedule (data/weather/weather_schedule.tres), driven by the real WorldSimulation, WorldClock, TimeOfDay and
SaveManager world_time path inside gd_port's engine model, checked against an independent reference written from
D-43 (the 32-bit hash of seed, day and slot; slots_per_day equal slots; days up to always_clear_days Clear; the ramp).
The translated code is given `Time`/`OS`/`randf`/`randi` stand-ins that change on every call, so any dependence on
them shows as different weather for the same world time.
1. A new game is Clear all of day 1, silently; days from 2 follow the schedule — every slot, the slot boundaries
   (exactly k/4 and either side), the day rollover (midnight neighbours), the pinned calendar of days 1–12.
2. Determinism: the same seed, day and fraction give the same weather and rain intensity in a fresh controller, after
   any history, after save/load cycles, at any frame timing and whatever the stand-in clocks say.
3. The intensity is derived, not accumulated: it ramps over ramp_fraction at a spell's edges, stays 1 between rainy
   neighbours (across midnight too), and after every frame equals a fresh computation for the current clock.
4. weather_changed fires exactly at the slot boundaries where the weather flips, with the new weather, once — never
   for a new game, a load (into rain too), a fresh area or a return outdoors; parked = paused, no event.
5. The saved clock reconstructs the weather after a relaunch (v8, and a v7 save → day 1, Clear); weather is never
   saved; weather never moves the clock (the clock = the frames' time); the lighting gets the current intensity in
   the same frame; the emitter shows it above the player; the M09.1 NPC and wildlife still follow the clock's phase.
Broken designs, applied to the real source, are shown to break: random weather, wall-clock weather, the wrong seed,
the wrong day, the wrong slot, day 1 not Clear, an accumulated intensity, an event on load, a lighting frame behind.
"""
import json, math, random, re, os
import gd_port
from gd_port import *

# ---------------------------------------------------------------- stand-ins that differ on every call
class _Ticking:
    def __init__(s): s.t = 1_700_000_000.0
    def _tick(s): s.t += 37.123; return s.t
    def get_unix_time_from_system(s): return s._tick()
    def get_ticks_msec(s): return int(s._tick() * 1000)
    def get_datetime_dict_from_system(s): return {"day": int(s._tick()) % 28 + 1, "hour": int(s._tick()) % 24}
    def get_date_dict_from_system(s): return s.get_datetime_dict_from_system()
_rnd = random.Random()
gd_port.HELPERS.update(Time=_Ticking(), OS=_Ticking(), randf=lambda: _rnd.random(), randi=lambda: _rnd.getrandbits(32),
                       move_toward=lambda a, b, d: b if abs(b - a) <= d else a + math.copysign(d, b - a))

# ---------------------------------------------------------------- the reference, from D-43 alone
SCHED = {k: (int(v) if re.fullmatch(r"-?\d+", v) else float(v)) for k, v in re.findall(r"^(\w+) = (-?[\d.]+)$", SOURCES["wsched"], re.M)}
M32 = 0xFFFFFFFF
def ref_hash(seed, day, slot):
    x = ((seed * 73856093) ^ (day * 19349663) ^ (slot * 83492791)) & M32
    x ^= x >> 16; x = (x * 0x7feb352d) & M32; x ^= x >> 15; x = (x * 0x2c1b3c6d) & M32; x ^= x >> 16
    return x
def ref_slot(f): return min(SCHED["slots_per_day"] - 1, max(0, math.floor(f * SCHED["slots_per_day"])))
def ref_rains(day, slot):
    if slot < 0: day, slot = day - 1, SCHED["slots_per_day"] - 1
    if slot >= SCHED["slots_per_day"]: day, slot = day + 1, 0
    return day > SCHED["always_clear_days"] and ref_hash(SCHED["weather_seed"], day, slot) < int(SCHED["rain_chance"] * 4294967296.0)
def ref_weather(day, f): return "rain" if ref_rains(day, ref_slot(f)) else "clear"
def ref_intensity(day, f):
    s = ref_slot(f)
    if not ref_rains(day, s): return 0.0
    w, r = 1.0 / SCHED["slots_per_day"], SCHED["ramp_fraction"]
    into = f - s * w
    up = 1.0 if ref_rains(day, s - 1) else max(0.0, min(1.0, into / r))
    down = 1.0 if ref_rains(day, s + 1) else max(0.0, min(1.0, (w - into) / r))
    return min(up, down)
# the calendar the fixed seed gives (slots 0..3 of days 1..12): a seed or hash change is deliberate and updates this
CALENDAR = {1: "....", 2: "....", 3: "....", 4: "...R", 5: "R.R.", 6: "....", 7: "..R.", 8: "....", 9: ".R..", 10: "...R", 11: "R...", 12: "R..."}

def clock_at(kit, day, f):
    return Game(kit, {"save": json.dumps({"save_version": kit["version"], "world_time": {"day": day, "fraction": f}})})

def check_frame(g, p, label=""):
    """After a frame: the weather and intensity are the clock's; the lighting and the emitter show them; NPC/wildlife phase."""
    d, f = g.clock.get_day(), g.clock.get_fraction()
    if g.weather.get_weather() != ref_weather(d, f): p.append(f"weather {g.weather.get_weather()} at day {d} {f:.5f}, schedule says {ref_weather(d, f)}{label}")
    if abs(g.weather.get_rain_intensity() - ref_intensity(d, f)) > 1e-9: p.append(f"intensity {g.weather.get_rain_intensity():.4f} at day {d} {f:.5f}, expected {ref_intensity(d, f):.4f}{label}")
    if g.meadow_in_tree:
        if abs(getattr(g.lights, "rain", 0.0) - g.weather.get_rain_intensity()) > 1e-12: p.append(f"lighting got rain {getattr(g.lights, 'rain', None)} vs {g.weather.get_rain_intensity()}{label}")
        r = g.weather._rain
        if r.emitting != (g.weather.get_rain_intensity() > 0.0) or abs(r.color.a - 0.55 * g.weather.get_rain_intensity()) > 1e-9: p.append(f"emitter shows {r.emitting}/{r.color.a}{label}")
        if not (isinstance(r.global_position, Vector3) and r.global_position == Vector3(1.0, 9.0, 2.0)): p.append(f"emitter not above the player{label}")
        if g.wild.phase != phase_for(g.kit, f): p.append(f"wildlife phase {g.wild.phase}{label}")
        if g.npc_phase is not None and g.npc_phase != phase_for(g.kit, f): p.append(f"NPC phase {g.npc_phase} at {f:.4f}{label}")

def scripted(kit):
    p, DAY = [], kit["wc"]["DAY_LENGTH_SECONDS"]
    W = kit["WCTL"]
    def fresh(): w = W(); w.schedule, w._rain = kit["schedule"], Mock(emitting=False, color=None, global_position=None); return w
    # 1. new game: day 1 Clear, resolved before the first frame, silently
    g = Game(kit, {})
    if g.weather.get_weather() != "clear" or g.weather_events: p.append(f"new game weather {g.weather.get_weather()!r}, events {g.weather_events}")
    for k in range(400):
        if fresh().weather_at(1, k / 400) != "clear": p.append(f"day 1 not Clear at {k / 400}"); break
    for _ in range(int(0.6 * DAY)): g.frame(1.0); check_frame(g, p, " (day 1)")
    if g.weather_events: p.append(f"events on day 1: {g.weather_events}")
    # 2. the calendar, every slot of days 1..12, and the boundaries
    w = fresh()
    for d, row in CALENDAR.items():
        got = "".join("R" if w.weather_at(d, (k + 0.5) / 4) == "rain" else "." for k in range(4))
        if got != row: p.append(f"day {d} slots {got}, calendar {row}")
    for d in range(1, 400):
        for k in range(4):
            for f in (k / 4, k / 4 + 1e-9, (k + 1) / 4 - 1e-9, (k + 0.5) / 4):
                if f >= 1.0: continue
                if w.weather_at(d, f) != ref_weather(d, f) or abs(w.rain_intensity_at(d, f) - ref_intensity(d, f)) > 1e-12:
                    p.append(f"day {d} at {f}: {w.weather_at(d, f)} / {w.rain_intensity_at(d, f)} vs {ref_weather(d, f)} / {ref_intensity(d, f)}"); break
    share = sum(ref_rains(d, k) for d in range(2, 10002) for k in range(4)) / 40000.0
    if abs(share - SCHED["rain_chance"]) > 0.01: p.append(f"rain share {share}")
    # 3. determinism: fresh vs after history, repeated, whatever the stand-in clocks do
    rnd = random.Random(7)
    hist = fresh()
    for _ in range(3000):
        d, f = rnd.randint(1, 5000), rnd.random()
        a = fresh(); a.apply_time(d, f)
        hist.apply_time(rnd.randint(1, 5000), rnd.random()); hist.apply_time(d, f)
        b = fresh(); b.apply_time(d, f); b.apply_time(d, f)
        if len({(x.get_weather(), x.get_rain_intensity()) for x in (a, hist, b)}) != 1 or a.get_weather() != ref_weather(d, f) or abs(a.get_rain_intensity() - ref_intensity(d, f)) > 1e-12:
            p.append(f"day {d} at {f:.5f}: fresh {a.get_weather()}/{a.get_rain_intensity()}, after history {hist.get_weather()}/{hist.get_rain_intensity()}, reference {ref_weather(d, f)}/{ref_intensity(d, f)}"); break
    # 4. the ramps and the midnight neighbours (day 4's last slot runs into day 5's first)
    r = SCHED["ramp_fraction"]
    if abs(w.rain_intensity_at(4, 0.75 + r / 2) - 0.5) > 1e-9 or w.rain_intensity_at(4, 0.999999) != 1.0 or w.rain_intensity_at(5, 0.0) != 1.0 \
       or abs(w.rain_intensity_at(5, 0.25 - r / 2) - 0.5) > 1e-9 or w.rain_intensity_at(5, 0.25 - 1e-12) > 1e-6:
        p.append("the ramps or the midnight neighbours are wrong")
    # 5. frames: events exactly at the flips, intensity derived every frame, the clock untouched by weather
    for dt in (1 / 60, 1 / 30, 0.25):
        g = clock_at(kit, 3, 0.95); secs = 0.0
        start = g.total()
        while g.clock.get_day() < 6:
            g.frame(dt); secs += dt; check_frame(g, p, f" (dt {dt:.3f})")
            if len(p) > 3: return p
        if abs(g.total() - (start + secs / DAY)) > 1e-7: p.append(f"the clock is not the frames' time with weather running (dt {dt})")
        flips = [(d, k, ref_weather(d, k / 4)) for d in range(4, 6) for k in range(4) if ref_weather(d, k / 4) != ref_weather(d if k else d - 1, (k - 1) % 4 / 4 + 1e-9 if k else 0.99)]
        got = [(d, ref_slot(f), wtr) for d, f, wtr in g.weather_events]
        if got != flips: p.append(f"events {got}, flips {flips} (dt {dt})")
    # 6. no event on load into rain, a fresh area, a return outdoors; parked = paused
    gr = clock_at(kit, 5, 0.1)
    if gr.weather.get_weather() != "rain" or abs(gr.weather.get_rain_intensity() - 1.0) > 1e-12 or gr.weather_events: p.append(f"load into rain: {gr.weather.get_weather()} {gr.weather.get_rain_intensity()} {gr.weather_events}")
    gr.frame(1 / 60); check_frame(gr, p, " (loaded into rain)")
    held = (gr.weather.get_weather(), gr.weather.get_rain_intensity(), gr.total()); gr.meadow_in_tree = False
    for _ in range(900): gr.frame(1 / 60)
    if (gr.weather.get_weather(), gr.weather.get_rain_intensity(), gr.total()) != held: p.append("weather or time moved while parked")
    gr.meadow_in_tree = True; gr.frame(1 / 60); check_frame(gr, p, " (back outside)")
    gr.new_meadow(); gr.frame(1 / 60); check_frame(gr, p, " (fresh area)")
    if gr.weather_events: p.append(f"events on load / return / fresh area: {gr.weather_events}")
    for d, f in ((7, 0.6), (5, 0.1), (9, 0.3), (11, 0.05), (4, 0.9), (2, 0.4), (12, 0.2)):   # loaded: resolved before the first frame
        gl = clock_at(kit, d, f)
        if gl.weather.get_weather() != ref_weather(d, f) or abs(gl.weather.get_rain_intensity() - ref_intensity(d, f)) > 1e-12 \
           or abs(getattr(gl.lights, "rain", -1.0) - ref_intensity(d, f)) > 1e-12 or gl.weather_events:
            p.append(f"loaded at day {d} {f}: {gl.weather.get_weather()!r} {gl.weather.get_rain_intensity()} (lighting {getattr(gl.lights, 'rain', None)}), "
                     f"expected {ref_weather(d, f)} {ref_intensity(d, f)} before the first frame, events {gl.weather_events}")
    gm = clock_at(kit, 4, 0.75 + r / 3)    # a relaunch mid-ramp
    if abs(gm.weather.get_rain_intensity() - 1 / 3) > 1e-9: p.append(f"relaunch mid-ramp: intensity {gm.weather.get_rain_intensity()}")
    # 7. save -> relaunch reconstructs; nothing of the weather is saved; v7 -> day 1 Clear
    disk = {}; gs = clock_at(kit, 7, 0.55); gs.disk = disk
    for _ in range(120): gs.frame(1 / 60)
    gs.save(); before = (gs.weather.get_weather(), gs.weather.get_rain_intensity())
    if set(json.loads(disk["save"])) != {"save_version", "world_time"}: p.append(f"the save holds {sorted(json.loads(disk['save']))}")
    g2 = Game(kit, disk)
    if (g2.weather.get_weather(), g2.weather.get_rain_intensity()) != before or g2.weather_events: p.append(f"relaunch {before} -> {(g2.weather.get_weather(), g2.weather.get_rain_intensity())}")
    g7 = Game(kit, {"save": json.dumps({"save_version": 7})})
    if g7.weather.get_weather() != "clear" or g7.clock.get_day() != 1: p.append("v7 save not day 1 Clear")
    # 8. calling the weather never moves the clock
    gc = clock_at(kit, 9, 0.3); t0 = gc.total()
    for _ in range(500): gc.weather.apply_time(rnd.randint(1, 99), rnd.random()); gc.weather.weather_at(5, 0.1); gc.weather.rain_intensity_at(5, 0.1)
    if gc.total() != t0: p.append("the weather moved the clock")
    return p

def random_session(kit, seed):
    rnd, p = random.Random(seed), []
    disk = {}; g = clock_at(kit, rnd.randint(2, 60), rnd.random()); g.disk = disk
    for _ in range(rnd.randint(40, 160)):
        a = rnd.random()
        if a < 0.75:
            g.frame(rnd.choice([1 / 60, 1 / 30, rnd.uniform(0, 0.3), rnd.uniform(5, 90)])); check_frame(g, p)
        elif a < 0.85: g.meadow_in_tree = not g.meadow_in_tree
        elif a < 0.9: g.new_meadow(); g.frame(1 / 60); check_frame(g, p, " (fresh area)")
        else:
            g.save(); held = (g.weather.get_weather(), g.weather.get_rain_intensity()); g = Game(kit, disk)
            # the save keeps the fraction to Godot's 14 significant digits (M09.2), so a mid-ramp intensity may move by ~1e-13;
            # the weather is then exactly the restored clock's (check_frame), and the same as before within that precision
            if g.weather.get_weather() != held[0] or abs(g.weather.get_rain_intensity() - held[1]) > 1e-9: p.append(f"relaunch changed the weather {held} -> {g.weather.get_weather()} {g.weather.get_rain_intensity()}")
            g.frame(1 / 60); check_frame(g, p, " (after relaunch)")
        if p: break
    return p

def mutate(name):
    s = dict(SOURCES)
    def rep(key, old, new):
        assert old in s[key], (name, old); s[key] = s[key].replace(old, new, 1)
    if name == "random_weather": rep("wctl", "return _hash(schedule.weather_seed, day, slot) < int(schedule.rain_chance * 4294967296.0)", "return randf() < schedule.rain_chance")
    elif name == "wall_clock_weather": rep("wctl", "return RAIN if _slot_rains(day, _slot(fraction)) else CLEAR", "return RAIN if _slot_rains(int(Time.get_unix_time_from_system() / 600.0), _slot(fraction)) else CLEAR")
    elif name == "wrong_seed": rep("wctl", "_hash(schedule.weather_seed, day, slot)", "_hash(schedule.weather_seed + 1, day, slot)")
    elif name == "wrong_day": rep("wctl", "return RAIN if _slot_rains(day, _slot(fraction)) else CLEAR", "return RAIN if _slot_rains(day + 1, _slot(fraction)) else CLEAR")
    elif name == "wrong_slot": rep("wctl", "return clampi(floori(fraction * schedule.slots_per_day), 0, schedule.slots_per_day - 1)", "return clampi(floori(fraction * 3), 0, schedule.slots_per_day - 1)")
    elif name == "day1_not_clear": rep("wctl", "\tif day <= schedule.always_clear_days:\n\t\treturn false\n", "")
    elif name == "accumulated_intensity": rep("wctl", "\t_rain_intensity = rain_intensity_at(day, fraction)\n", "\t_rain_intensity = move_toward(_rain_intensity, rain_intensity_at(day, fraction), 0.05)\n")
    elif name == "event_on_load": rep("wctl", "\tif not first:\n\t\tweather_changed.emit(weather)", "\tweather_changed.emit(weather)")
    elif name == "lighting_frame_behind": rep("ws", "\tweather_controller.apply_time(WorldClock.get_day(), fraction)\n\ttime_of_day.time_updated.emit(fraction)\n", "\ttime_of_day.time_updated.emit(fraction)\n\tweather_controller.apply_time(WorldClock.get_day(), fraction)\n")
    return s

REAL = build(SOURCES)
bad = scripted(REAL)
assert not bad, bad
N = 600
fails = [d for d in range(N) if random_session(REAL, d)]
assert not fails, f"{len(fails)} sessions broke the weather, e.g. {random_session(REAL, fails[0])}"
BROKEN = ["random_weather", "wall_clock_weather", "wrong_seed", "wrong_day", "wrong_slot", "day1_not_clear", "accumulated_intensity", "event_on_load", "lighting_frame_behind"]
caught = {}
for name in BROKEN:
    kit = build(mutate(name))
    try:
        probs = scripted(kit) or next((r for d in range(100) for r in [random_session(kit, d)] if r), [])
    except Exception as e:  # a design that cannot even run is broken too
        probs = [f"{type(e).__name__}: {e}"]
    assert probs, f"the {name} design is shown to break the weather"
    caught[name] = probs[0]
print(f"weather: seed {SCHED['weather_seed']}, {SCHED['slots_per_day']} slots/day, rain chance {SCHED['rain_chance']}, ramp {SCHED['ramp_fraction']} day, "
      f"Clear through day {SCHED['always_clear_days']}; calendar days 1-12 {''.join(CALENDAR.values())}; = the D-43 reference at every slot and boundary of days 1-399; "
      f"deterministic (fresh, after history, repeated, any frame timing, stand-in clocks ticking); intensity derived every frame; events only at real flips "
      f"(none on load, return or fresh area); parked = paused; relaunch reconstructs; nothing saved; the clock untouched; {N} random sessions OK")
print("broken designs caught: " + "; ".join(f"{k}: {v[:90]}" for k, v in caught.items()))
print("ALL WEATHER SIMULATIONS PASSED")
