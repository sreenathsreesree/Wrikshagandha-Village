#!/usr/bin/env python3
"""Multi-session model of farm persistence (Python port of FarmManager
get_save_data/apply_save_data and FarmPlot capture/restore, JSON round-trip).
Checks across app restarts:
 - seed invariant: seeds + crops in ground = starting + found (ever)
 - exploration seeds granted once ever
 - milestone bonus points awarded once ever (no re-award on relaunch)
 - READY counts rebuilt from plots; a save taken mid-harvest never double counts
 - capture -> apply -> capture is identical
Since M04.2 the save is the farm section (no seeds/basket; starter_seeds)
plus the items section (the crops' seed items, and produce items with a
count per quality); an emptied item isn't listed, and a crop whose starting
seeds were given reads as 0 when its seed item is absent.
"""
import os, json, random, re, glob, copy

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
crops = {}
for f in sorted(glob.glob(f"{ROOT}/data/crops/*.tres")):
    s = open(f).read()
    g = lambda k, d=None: (re.search(rf'^{k} = (.+)$', s, re.M) or [None, d])[1]
    cid = g("crop_id").strip('"')
    crops[cid] = dict(start=int(g("starting_seeds", "1")), src=g("found_seed_source", '"none"').strip('"'),
                      src_id=g("found_seed_source_id", '""').strip('"'))
ITEM_OF = {}
for f in sorted(glob.glob(f"{ROOT}/data/items/*.tres")):
    s_ = open(f).read(); g_ = lambda k, d=None: (re.search(rf'^{k} = "?([^"\n]*)"?$', s_, re.M) or [None, d])[1]
    ITEM_OF[(g_("crop_id"), g_("category", "seed"))] = g_("id")
BONUS = {"first_harvest": 10, "all_starter_crops": 40, "garden_complete": 30, "garden_in_bloom": 50}
PLOTS = [f"farm_plot_0{i}" for i in range(1, 8)]
UNLOCK = {"farm_plot_06": "first_harvest", "farm_plot_07": "all_starter_crops"}
STATES = ["EMPTY", "SOIL", "PLANTED", "GROWING", "READY"]

class Plot:
    def __init__(p, pid):
        p.id = pid; p.unlocked = pid not in UNLOCK; p.state = "EMPTY"; p.crop = None; p.memory = []
        p.stage = 0; p.needs_water = False; p.timer = 0.0; p.harvesting = False; p.paid = False
        p.soil = 1; p.care = 2; p.quality = 1; p.longest = 0.0; p.thirsty_for = -1.0
    def capture(p):
        state, crop = p.state, p.crop
        if p.harvesting and p.paid: state, crop = "SOIL", None
        d = {"state": state, "soil_memory": list(p.memory)}
        if crop is None: return d
        # GrowthTimer is one_shot: time_left is only non-zero while a stage timer runs
        running = p.state == "GROWING" and not p.needs_water
        d.update(crop=crop, stage=p.stage, needs_water=p.needs_water, stage_time_left=p.timer if running else 0.0, soil=p.soil,
                 care=p.care, quality=p.quality, longest_thirst=p.longest, thirsty_for=p.thirsty_for)
        return d
    def restore(p, d, crop_known):
        p.memory = [str(x) for x in d.get("soil_memory", [])][-2:]
        st = STATES.index(d.get("state", "EMPTY")) if d.get("state", "EMPTY") in STATES else -1
        if st <= 0: return None
        p.state = "SOIL"
        if st == 1 or not crop_known: return None
        p.crop = d["crop"]; p.state = STATES[st]; p.stage = min(max(int(d.get("stage", 0)), 0), 3)
        p.needs_water = bool(d.get("needs_water", False)) and p.state != "READY"
        p.soil, p.care, p.quality = int(d["soil"]), int(d["care"]), int(d["quality"])
        p.longest = float(d["longest_thirst"]); p.thirsty_for = float(d["thirsty_for"]) if p.needs_water else -1.0
        p.timer = max(float(d.get("stage_time_left", 0.0)), 0.1) if p.state == "GROWING" and not p.needs_water else 0.0
        return p.crop

class Farm:
    def __init__(f):
        f.seeds = {c: max(v["start"], 0) for c, v in crops.items()}
        f.found = {}; f.grown = []; f.basket = {}; f.milestones = []; f.planted = 0; f.harvested = 0
        f.harvested_plots = []; f.garden_found = False; f.saved_plots = {}; f.plots = {}; f.ready = {}
        f.points = 0
    def register(f, plot):
        f.plots[plot.id] = plot
        if not plot.unlocked and UNLOCK.get(plot.id) in f.milestones: plot.unlocked = True
        if plot.id in f.saved_plots:
            d = f.saved_plots.pop(plot.id)
            r = plot.restore(d, d.get("crop", "") in crops)
            if r and plot.state == "READY": f.ready[r] = f.ready.get(r, 0) + 1
    def reach(f, m):
        if m in f.milestones: return False
        f.milestones.append(m); f.points += BONUS.get(m, 0)
        for p in f.plots.values():
            if not p.unlocked and UNLOCK.get(p.id) == m: p.unlocked = True
        return True
    def save(f):
        plots = copy.deepcopy(f.saved_plots)
        for pid, p in f.plots.items(): plots[pid] = p.capture()
        items = {ITEM_OF[(c, "seed")]: [n] for c, n in f.seeds.items() if n > 0}
        items.update({ITEM_OF[(c, "produce")]: list(k) for c, k in f.basket.items() if max(k) > 0})
        farm = {"version": 1, "starter_seeds": list(crops), "found_seeds": copy.deepcopy(f.found), "grown": list(f.grown),
                "milestones": list(f.milestones), "counts": {"planted": f.planted, "harvested": f.harvested},
                "harvested_plots": list(f.harvested_plots), "garden_found": f.garden_found, "plots": plots}
        return {"farm": farm, "items": items}
    def apply(f, save):
        d, items = save.get("farm", {}), save.get("items", {})
        if not d: return
        given = set(d.get("starter_seeds", []))
        for c, v in crops.items():
            held = items.get(ITEM_OF[(c, "seed")], [0])[0]
            f.seeds[c] = max(int(held), 0) + (max(v["start"], 0) if c not in given else 0)
        f.found = {k: v for k, v in d.get("found_seeds", {}).items() if k in crops}
        f.grown = [x for x in d.get("grown", []) if x in crops]
        f.basket = {c: [max(int(x), 0) for x in items[ITEM_OF[(c, "produce")]]] for c in crops if ITEM_OF[(c, "produce")] in items}
        f.milestones = [str(x) for x in d.get("milestones", [])]
        f.planted = int(d.get("counts", {}).get("planted", 0)); f.harvested = int(d.get("counts", {}).get("harvested", 0))
        f.harvested_plots = [str(x) for x in d.get("harvested_plots", [])]
        f.garden_found = bool(d.get("garden_found", False)); f.saved_plots = copy.deepcopy(d.get("plots", {}))

def boot(save_json, points):
    farm = Farm(); farm.points = points
    farm.apply(json.loads(save_json) if save_json else {})
    for pid in PLOTS: farm.register(Plot(pid))
    return farm

def check(farm):
    ground = sum(1 for p in farm.plots.values() if p.crop is not None and not (p.harvesting and p.paid))
    ground_all = sum(1 for p in farm.plots.values() if p.crop is not None)
    # during a paid harvest the seed is already back but the crop object lingers until reset
    assert sum(farm.seeds.values()) + ground == 5 + len(farm.found), (farm.seeds, ground, farm.found)
    assert min(farm.seeds.values()) >= 0
    for c in crops:
        assert farm.ready.get(c, 0) == sum(1 for p in farm.plots.values() if p.state == "READY" and p.crop == c and not p.paid)
    for p in farm.plots.values():
        assert p.unlocked == (p.id not in UNLOCK or UNLOCK[p.id] in farm.milestones)

def run(trials=300, sessions=8, steps=400):
    stats = dict(saves=0, midharvest_saves=0, ready_restored=0)
    for t in range(trials):
        rnd = random.Random(900 + t)
        save_json, points, bonus_ever, saved_basket = None, 0, {}, {}
        found_ever = set()
        for sess in range(sessions):
            farm = boot(save_json, points)
            assert {c: k for c, k in farm.basket.items() if max(k) > 0} == saved_basket, "the basket (every quality) survives a relaunch"
            stats["ready_restored"] += sum(farm.ready.values())
            check(farm)
            # capture -> apply -> capture identity
            if save_json:
                assert json.dumps(farm.save(), sort_keys=True) == json.dumps(json.loads(save_json), sort_keys=True), "round trip"
            for _ in range(steps):
                p = rnd.choice(list(farm.plots.values())); op = rnd.random()
                if p.harvesting:  # finish a harvest in flight
                    if not p.paid:
                        c = p.crop; p.memory = (p.memory + [c])[-2:]; p.paid = True
                        farm.seeds[c] += 1; farm.ready[c] -= 1; farm.basket.setdefault(c, [0, 0, 0])[p.quality] += 1
                        farm.harvested += 1
                        if p.id not in farm.harvested_plots: farm.harvested_plots.append(p.id)
                        farm.reach("first_harvest")
                    else:
                        p.state, p.crop, p.harvesting, p.paid = "SOIL", None, False, False
                elif not p.unlocked:
                    pass
                elif op < 0.3:
                    if p.state == "EMPTY": p.state = "SOIL"
                    elif p.state == "SOIL":
                        avail = [c for c in crops if farm.seeds[c] > 0]
                        if avail:
                            c = rnd.choice(avail); farm.seeds[c] -= 1; farm.planted += 1
                            p.crop, p.state, p.stage, p.needs_water, p.thirsty_for = c, "PLANTED", 0, True, 0.0
                    elif p.needs_water:
                        p.needs_water, p.state, p.timer, p.thirsty_for = False, "GROWING", 10.0, -1.0
                elif op < 0.5 and p.state == "GROWING" and not p.needs_water:
                    p.stage += 1
                    if p.stage >= 3:
                        p.state = "READY"; farm.ready[p.crop] = farm.ready.get(p.crop, 0) + 1
                        if p.crop not in farm.grown: farm.grown.append(p.crop)
                        if all(c in farm.grown for c, v in crops.items() if v["start"] > 0): farm.reach("all_starter_crops")
                    else: p.needs_water, p.thirsty_for = True, 0.0
                elif op < 0.65 and p.state == "READY":
                    p.harvesting, p.paid = True, False
                elif op < 0.72:
                    src = rnd.choice(["hidden_flower_pocket", "mystery_grove_tree", "hidden_herb", "ancient_seed", "overlook"])
                    for c, v in crops.items():
                        if v["src_id"] == src and c not in farm.found:
                            assert c not in found_ever, "seed granted twice across sessions"
                            found_ever.add(c); farm.found[c] = {"source": v["src"], "source_id": src}; farm.seeds[c] += 1
                if rnd.random() < 0.05:  # autosave moment
                    stats["saves"] += 1
                    stats["midharvest_saves"] += any(x.harvesting and x.paid for x in farm.plots.values())
                    save_json = json.dumps(farm.save()); points = farm.points
                    saved_basket = {c: list(k) for c, k in farm.basket.items() if max(k) > 0}
                check(farm)
            # app backgrounded: save; bonus accounting
            save_json = json.dumps(farm.save()); points = farm.points
            saved_basket = {c: list(k) for c, k in farm.basket.items() if max(k) > 0}
            for m in farm.milestones: bonus_ever[m] = bonus_ever.get(m, 0)
        # every milestone paid at most once across all sessions
        final = boot(save_json, points)
        expect = sum(BONUS.get(m, 0) for m in final.milestones)
        assert points == expect, (points, expect)  # only bonuses add points in this model
    print(f"persistence sim: {trials} players x {sessions} launches x {steps} steps OK; {stats}")

run()
print("ALL PERSISTENCE SIMULATIONS PASSED")
