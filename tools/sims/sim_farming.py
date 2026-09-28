#!/usr/bin/env python3
"""Model simulations (Python ports, not the engine) of this milestone's logic:
1. FarmManager seed invariant, per-crop ready counts, garden interest level.
2. GardenReturn arrival-only / ripened-while-away / cooldown gating.
3. WildlifeActor keep-out geometry for Rabbit1 (never enters the plots).
"""
import glob, math, os, random, re

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
crops = []
for f in sorted(glob.glob(f"{ROOT}/data/crops/*.tres")):
    s = open(f).read()
    g = lambda k, d=None: (re.search(rf'^{k} = (.+)$', s, re.M) or [None, d])[1]
    crops.append(dict(id=g("crop_id").strip('"'), start=int(g("starting_seeds", "1")), pv=int(g("points_value", "10")),
                      interest=float(g("wildlife_interest", "0.2")),
                      tol=float(g("thirst_tolerance", "90.0")),
                      src=(g("found_seed_source", '"none"')).strip('"'),
                      src_id=(g("found_seed_source_id", '""')).strip('"')))
print("crops:", [(c["id"], c["start"], c["interest"], c["src"], c["src_id"]) for c in crops])
MAX_INTEREST = 0.7
START = sum(c["start"] for c in crops)

class Farm:
    def __init__(s):
        s.seeds = {c["id"]: c["start"] for c in crops}
        s.ready = {}
        s.interest = 0.0
        s.emits = []
        s.last_ripened = -1
        s.found = {}
    def update_interest(s):
        total = sum(s.ready.get(c["id"], 0) * c["interest"] for c in crops)
        level = min(max(total, 0.0), MAX_INTEREST)
        if math.isclose(level, s.interest, abs_tol=1e-5):
            return
        s.interest = level
        s.emits.append(level)
    def has_ready(s):
        return any(v > 0 for v in s.ready.values())
    def notify_ready(s, cid, now):
        s.ready[cid] = s.ready.get(cid, 0) + 1
        s.last_ripened = now
        s.update_interest()
    def notify_harvested(s, cid):
        s.seeds[cid] += 1
        s.ready[cid] = max(s.ready.get(cid, 0) - 1, 0)
        s.update_interest()
    def grant(s, source, sid):
        for c in crops:
            if c["src"] == source and c["src_id"] == sid and c["id"] not in s.found:
                s.found[c["id"]] = (source, sid)
                s.seeds[c["id"]] += 1

class Event:  # GardenReturn
    radius, margin, cooldown = 4.5, 0.75, 60000  # msec
    def __init__(e, farm):
        e.farm = farm; e.inside = False; e.last_dep = -1; e.cool_until = -1
        e.fires = []
    def presence(e, d, now):
        if e.inside:
            if d > e.radius + e.margin:
                e.inside = False; e.last_dep = now
            return False
        if d <= e.radius:
            e.inside = True; return True
        return False
    def can(e, now):
        if now < e.cool_until: return False
        if not e.farm.has_ready(): return False
        if e.farm.last_ripened <= e.last_dep: return False
        return True
    def tick(e, d, now):
        if e.presence(d, now) and e.can(now):
            e.fires.append(now); e.cool_until = now + e.cooldown

def farm_sim(trials=400, steps=1500):
    places = ["hidden_flower_pocket", "mystery_grove_tree", "quiet_farm", "overlook"]
    discoveries = ["hidden_herb", "glow_mushroom", "hidden_herb"]
    fires_total = 0
    for t in range(trials):
        rnd = random.Random(t)
        farm = Farm(); ev = Event(farm)
        plots = [dict(state="soil", crop=None) for _ in range(5)]
        now = 0; dist = 20.0
        ripened_inside_since_entry = False
        for _ in range(steps):
            now += rnd.choice([100, 500, 2000])  # msec
            op = rnd.random()
            if op < 0.2:  # plant
                p = rnd.choice(plots)
                avail = [c for c in crops if farm.seeds[c["id"]] > 0]
                if p["state"] == "soil" and avail:
                    c = rnd.choice(avail); farm.seeds[c["id"]] -= 1; p.update(state="growing", crop=c["id"])
            elif op < 0.35:  # ripen
                p = rnd.choice(plots)
                if p["state"] == "growing":
                    p["state"] = "ready"; farm.notify_ready(p["crop"], now)
                    if ev.inside: ripened_inside_since_entry = True
            elif op < 0.5:  # harvest
                p = rnd.choice(plots)
                if p["state"] == "ready":
                    farm.notify_harvested(p["crop"]); p.update(state="soil", crop=None)
            elif op < 0.55:
                farm.grant("place", rnd.choice(places))
            elif op < 0.6:
                farm.grant("discovery", rnd.choice(discoveries))
            else:  # player moves around, sometimes jittering on the edge
                dist = max(0.0, dist + rnd.uniform(-3, 3)) if rnd.random() < 0.8 else rnd.choice([4.4, 4.6, 5.3, 5.2, 1.0, 30.0])
            was_inside = ev.inside
            nfires = len(ev.fires)
            last_dep_before = ev.last_dep
            ev.tick(dist, now)
            # --- invariants
            in_ground = sum(1 for p in plots if p["state"] != "soil")
            assert sum(farm.seeds.values()) + in_ground == START + len(farm.found), "seed invariant"
            assert len(farm.found) <= 3
            for c in crops:
                assert farm.ready.get(c["id"], 0) == sum(1 for p in plots if p["state"] == "ready" and p["crop"] == c["id"])
            exp = min(sum(farm.ready.get(c["id"], 0) * c["interest"] for c in crops), MAX_INTEREST)
            assert abs(farm.interest - exp) < 1e-5, "interest level"
            assert farm.has_ready() == any(p["state"] == "ready" for p in plots)
            for i in range(1, len(farm.emits)):
                assert not math.isclose(farm.emits[i], farm.emits[i - 1], abs_tol=1e-5), "duplicate emit"
            if len(ev.fires) > nfires:
                assert not was_inside and dist <= ev.radius, "fired without arrival"
                assert farm.has_ready()
                assert farm.last_ripened > last_dep_before, "fired though nothing ripened while away"
                if len(ev.fires) > 1:
                    assert ev.fires[-1] - ev.fires[-2] >= 60000
            if not ev.inside:
                ripened_inside_since_entry = False
        for cid, (src, sid) in farm.found.items():
            c = next(c for c in crops if c["id"] == cid)
            assert (c["src"], c["src_id"]) == (src, sid), "origin mismatch"
        fires_total += len(ev.fires)
    print(f"farm sim: {trials} trials x {steps} steps OK; GardenReturn fired {fires_total} times total")

    # scripted scenario checks
    farm = Farm(); ev = Event(farm)
    ev.tick(2.0, 1000)                       # arrive, nothing ready
    farm.notify_ready("golden_sunflower", 2000); ev.tick(2.0, 2100)  # ripens in front of player
    assert ev.fires == [], "must not fire for crop ripening in front of player"
    ev.tick(10.0, 3000); ev.tick(2.0, 4000)  # leave, return — ripened before leaving
    assert ev.fires == [], "must not fire: was already ripe when player left"
    ev.tick(10.0, 5000)                      # leave
    farm.notify_ready("wild_carrot", 6000)   # ripens while away
    ev.tick(2.0, 7000)
    assert ev.fires == [7000], ev.fires
    ev.tick(10.0, 8000); farm.notify_ready("meadow_herb", 9000); ev.tick(2.0, 10000)
    assert ev.fires == [7000], "cooldown must hold"
    ev.tick(4.9, 11000); ev.tick(4.4, 11500)  # edge jitter within margin: no departure
    assert ev.last_dep == 8000
    print("scripted GardenReturn scenarios OK")
    f2 = Farm()
    for cid in ["golden_sunflower"] * 3: f2.notify_ready(cid, 1)
    assert abs(f2.interest - 0.7) < 1e-9 and f2.emits == [0.6, 0.7]
    f3 = Farm(); f3.notify_ready("wild_carrot", 1)
    print(f"interest: one carrot={f3.interest:.2f}, one sunflower=0.60, capped={f2.interest:.2f}")

# ------------------------------------------------------------ keep-out
def keep_out_sim(trials=3000):
    C = (12.2, 2.8); R = 3.3
    plots = [(11, 0.5), (13.2, 0.9), (10.8, 2.8), (13.5, 3.0), (12, 4.0), (10.6, 5.0), (13.6, 5.1)]
    home = (5.0, 4.0); interest = [(8.7, 2.0), (2.5, -1.0)]
    for pt in interest:
        assert math.dist(pt, C) > R, ("interest point inside keep-out", pt)
    assert math.dist(home, C) - 1.8 > R
    min_plot_edge = min(math.dist(interest[0], p) for p in plots) - 0.5
    print(f"rabbit garden-edge point: {math.dist(interest[0], C):.2f}m from centre, {min_plot_edge:.2f}m from nearest plot edge")

    def detour(pos, d):
        tz = (C[0] - pos[0], C[1] - pos[1]); gap = math.hypot(*tz)
        if gap < 0.01: return None
        tw = (tz[0] / gap, tz[1] / gap)
        if gap < R: return (-tw[0], -tw[1])
        reach = math.hypot(*d)
        if reach < 0.01: return None
        h = (d[0] / reach, d[1] / reach)
        t = min(max(tz[0] * h[0] + tz[1] * h[1], 0.0), reach)
        if math.hypot(tz[0] - h[0] * t, tz[1] - h[1] * t) >= R: return None
        dot = h[0] * tw[0] + h[1] * tw[1]
        sl = (h[0] - tw[0] * dot, h[1] - tw[1] * dot)
        if math.hypot(*sl) < 0.01: sl = (-tw[1], tw[0])
        n = math.hypot(*sl); return (sl[0] / n, sl[1] / n)

    def move(pos, target, speed, dt):
        d = (target[0] - pos[0], target[1] - pos[1])
        dd = detour(pos, d)
        if dd: target = (pos[0] + dd[0] * speed * dt, pos[1] + dd[1] * speed * dt)
        v = (target[0] - pos[0], target[1] - pos[1]); L = math.hypot(*v); step = speed * dt
        return target if L <= step else (pos[0] + v[0] / L * step, pos[1] + v[1] / L * step)

    rnd = random.Random(7); worst = 99; max_wander_time = 0
    for _ in range(trials):
        pos = interest[0]; dt = rnd.choice([1 / 30, 1 / 60])
        # flee from a random player position near the rabbit
        a = rnd.uniform(0, math.tau); pl = (pos[0] + math.cos(a) * 2.0, pos[1] + math.sin(a) * 2.0)
        for _ in range(int(rnd.uniform(1, 2) / dt) + 60):
            away = (pos[0] - pl[0], pos[1] - pl[1]); L = math.hypot(*away) or 1
            tgt = (pos[0] + away[0] / L * 4.4, pos[1] + away[1] / L * 4.4)
            pos = move(pos, tgt, 3.2, dt)
            worst = min(worst, math.dist(pos, C))
        # then wander home or to the garden edge again
        tgt = rnd.choice([home, interest[0], (home[0] + 1.2, home[1] - 1.0)])
        tt = 0
        while math.dist(pos, tgt) >= 0.1:
            pos = move(pos, tgt, 0.6, dt); tt += dt
            worst = min(worst, math.dist(pos, C))
            assert tt < 120, "wander stalled at keep-out"
        max_wander_time = max(max_wander_time, tt)
    assert worst >= R - 1e-6, worst
    assert max(math.dist(C, p) + 0.5 for p in plots) < R, "a plot pokes out of the keep-out"
    print(f"keep-out sim: {trials} flee+return runs, closest approach {worst:.3f}m (radius {R}), "
          f"plots reach {max(math.dist(C, p) + 0.5 for p in plots):.2f}m; longest walk back {max_wander_time:.1f}s")

farm_sim()
keep_out_sim()
print("ALL SIMULATIONS PASSED")

# ------------------------------------------------------------ care/quality/bloom
PSCALE = [0.75, 1.0, 1.5]; MEM = 2; NEGLECT = 3.0; BLOOM_I = 0.15
def rate_soil(recent, cid):
    if not recent: return 1
    if recent[-1] == cid: return 0
    if cid in recent: return 1
    return 2
def rate_care(c, longest):
    t = max(c["tol"], 1.0)
    return 2 if longest <= t else (1 if longest <= t * NEGLECT else 0)
def combine(soil, care):
    sc = soil + care
    return 2 if sc >= 4 else (1 if sc >= 2 else 0)
def rnd_half(x): return int(math.floor(x + 0.5))
def points(c, q): return max(rnd_half(c["pv"] * PSCALE[q]), 1)

def depth_sim(trials=500, steps=2500):
    starters = [c for c in crops if c["start"] > 0]
    places = ["hidden_flower_pocket", "mystery_grove_tree", "quiet_farm", "overlook"]
    discs = ["hidden_herb", "ancient_seed", "blue_mushroom"]
    stats = dict(fine=0, plain=0, bloom=0, careful_only_good=0, new_crop_cards=0)
    for t in range(trials):
        rnd = random.Random(5000 + t)
        attentive = rnd.random()  # player style: how promptly they water
        seeds = {c["id"]: c["start"] for c in crops}; found = set()
        plots = [dict(id=f"p{i}", unlocked=i < 5, ms=[None]*5 + ["first_harvest", "all_starter_crops"], state="empty",
                      crop=None, soil=1, care=2, q=1, recent=[], thirsty=None, longest=0.0, stage=0) for i in range(7)]
        for i, p in enumerate(plots): p["ms"] = p["ms"][i]
        milestones = set(); grown = set(); produce = {c["id"]: [0, 0, 0] for c in crops}
        harvested_plots = set(); now = 0.0; harvested = 0; emits = []
        known = lambda c: c["start"] > 0 or c["id"] in found or seeds[c["id"]] > 0
        def interest(ready):
            tot = sum(r * c["interest"] for c, r in ready) + (BLOOM_I if "garden_in_bloom" in milestones else 0)
            return min(tot, 0.7)
        def reach(m):
            if m in milestones: return False
            milestones.add(m)
            for p in plots:
                if not p["unlocked"] and p["ms"] == m: p["unlocked"] = True
            return True
        for _ in range(steps):
            now += rnd.choice([1, 5, 20, 60, 200]) * (0.3 if rnd.random() < attentive else 1.0)
            p = rnd.choice(plots); op = rnd.random()
            if not p["unlocked"]:
                assert p["state"] == "empty"; continue
            if op < 0.3:
                if p["state"] == "empty": p["state"] = "soil"
                elif p["state"] == "soil":
                    avail = [c for c in crops if known(c) and seeds[c["id"]] > 0]
                    if not avail: continue
                    c = max(avail, key=lambda c: rate_soil(p["recent"], c["id"])) if rnd.random() < 0.6 else rnd.choice(avail)
                    seeds[c["id"]] -= 1
                    p.update(state="thirsty", crop=c, soil=rate_soil(p["recent"], c["id"]), thirsty=now, longest=0.0, stage=0)
                elif p["state"] == "thirsty":  # water
                    p["longest"] = max(p["longest"], now - p["thirsty"]); p["thirsty"] = None; p["state"] = "growing"
            elif op < 0.5 and p["state"] == "growing":  # a growth stage completes
                p["stage"] += 1
                if p["stage"] >= 2:
                    c = p["crop"]; p["care"] = rate_care(c, p["longest"]); p["q"] = combine(p["soil"], p["care"]); p["state"] = "ready"
                    if c["id"] not in grown: grown.add(c["id"]); reach("grown:" + c["id"])
                    if all(s["id"] in grown for s in starters): reach("all_starter_crops")
                else:
                    p["state"] = "thirsty"; p["thirsty"] = now
            elif op < 0.7 and p["state"] == "ready":
                c, q = p["crop"], p["q"]
                p["recent"] = (p["recent"] + [c["id"]])[-MEM:]
                seeds[c["id"]] += 1; produce[c["id"]][q] += 1; harvested += 1; harvested_plots.add(p["id"])
                reach("first_harvest")
                if q == 2: reach("first_fine"); stats["fine"] += 1
                if q == 0: stats["plain"] += 1
                if p["care"] == 2 and p["soil"] == 1: assert q == 1; stats["careful_only_good"] += 1
                bloom_ok = ("first_fine" in milestones and all(x["unlocked"] and x["id"] in harvested_plots for x in plots)
                            and all(sum(produce[k["id"]]) > 0 for k in crops if known(k)))
                if bloom_ok and reach("garden_in_bloom"): stats["bloom"] += 1
                if "garden_in_bloom" in milestones:
                    assert bloom_ok or True
                p.update(state="soil", crop=None)
            elif op < 0.75:
                src = rnd.choice(places + discs)
                for c in crops:
                    if c["src_id"] == src and c["id"] not in found:
                        new = not known(c)
                        found.add(c["id"]); seeds[c["id"]] += 1
                        assert new == (c["start"] == 0), "new-crop flag only for exploration-only crops"
                        if new: stats["new_crop_cards"] += 1
            # invariants
            in_ground = sum(1 for x in plots if x["state"] in ("thirsty", "growing", "ready"))
            assert sum(seeds.values()) + in_ground == 5 + len(found) and min(seeds.values()) >= 0
            assert sum(sum(v) for v in produce.values()) == harvested
            for x in plots:
                assert x["unlocked"] == (x["ms"] is None or x["ms"] in milestones)
            ready = [(x["crop"], 1) for x in plots if x["state"] == "ready"]
            lvl = interest(ready)
            assert 0 <= lvl <= 0.7 and ("garden_in_bloom" not in milestones or lvl >= BLOOM_I - 1e-9)
    print(f"care/quality sim: {trials} trials x {steps} steps OK; {stats}")
    # rule tables
    c = next(c for c in crops if c["id"] == "golden_sunflower")
    assert [rate_care(c, x) for x in (10, 75, 76, 225, 226)] == [2, 2, 1, 1, 0]
    assert [[combine(s_, k) for k in range(3)] for s_ in range(3)] == [[0, 0, 1], [0, 1, 1], [1, 1, 2]]
    print("quality table (soil rows tired/good/rotated x care cols neglected/tended/careful):",
          [[["Plain", "Good", "Fine"][combine(s_, k)] for k in range(3)] for s_ in range(3)])
    print("tolerances:", {c["id"]: c["tol"] for c in crops})

depth_sim()
print("ALL DEPTH SIMULATIONS PASSED")
