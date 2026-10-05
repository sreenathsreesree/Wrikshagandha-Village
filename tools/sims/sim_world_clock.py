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
import gd_port

from gd_port import *  # the GDScript translator and the engine model, shared with sim_weather

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
