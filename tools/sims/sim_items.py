#!/usr/bin/env python3
"""Model checks for items (M04.1) and seeds/harvests as items (M04.2) — a
Python port, not the engine.
1. Read from the project: data/items/, data/crops/, the quality scale, and
   the rule lines of ItemStore, FarmManager and SaveManager's 1 -> 2 step.
2. Ports: ItemStore (counts per quality level); FarmManager's seed/basket
   rules as they were before M04.2 (OldFarm: _seeds/_produce dictionaries)
   and after (Farm: the ItemStore holds them); SaveManager's load pipeline
   with the 1 -> 2 migration; Godot's JSON (every number a float).
3. Store: add/remove per quality, insufficient (nothing taken), zero and
   negative amounts, unknown ids and qualities, no stack limit, save data
   validation (malformed entries dropped, with a warning), copies, 20,000
   random operations against a reference ledger.
4. Parity: 3,000 random farm sessions (starting seeds, planting, harvests at
   every quality, found seeds) give the same seed counts, basket rows and
   produce counts before and after M04.2, and the seed invariant holds.
5. Save: fresh game; M04.0 (v1) saves with seeds, basket, both, empty seeds,
   empty basket, all qualities, many crops, malformed data; repeated
   load/save; migration then autosave; unrelated sections kept exactly; and
   2,000 random v1 saves load to the same farm through the migration as the
   old code loaded them directly.
"""
import copy, glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _funcs(src): return {m.group(2): m.group(0) for m in re.finditer(r"^(static )?func (\w+)\(.*?(?=^func |^static func |\Z)", src, re.M | re.S)}
def _vals(path):
    txt = open(path, encoding="utf-8").read().split("[resource]", 1)[1]
    return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', txt, re.M)}

# ---------------------------------------------------------------- 1. read from the project
ITEMS = {v["id"]: {"category": v.get("category", "seed"), "crop": v["crop_id"], "levels": int(v.get("quality_levels", "1"))}
         for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "items", "*.tres"))))}
CROPS = {v["crop_id"]: {"starting": max(int(v.get("starting_seeds", "1")), 0), "found": v.get("found_seed_source", "none")}
         for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "crops", "*.tres"))))}
SEED_ITEM = {i["crop"]: iid for iid, i in ITEMS.items() if i["category"] == "seed"}
PRODUCE_ITEM = {i["crop"]: iid for iid, i in ITEMS.items() if i["category"] == "produce"}
FMS = _src("scripts", "autoload", "farm_manager.gd")
Q = len(re.search(r'^const QUALITY_NAMES := \[([^\]]*)\]', FMS, re.M).group(1).split(","))
assert set(SEED_ITEM) == set(PRODUCE_ITEM) == set(CROPS), "every crop has a seed item and a produce item"
assert all(ITEMS[i]["levels"] == 1 for i in SEED_ITEM.values()) and all(ITEMS[i]["levels"] == Q for i in PRODUCE_ITEM.values())
ST, FM, SM = _funcs(_src("scripts", "items", "item_store.gd")), _funcs(FMS), _funcs(_src("scripts", "autoload", "save_manager.gd"))
for fn, lines in {"add": ["if not _accepts(item_id, quality) or amount < 1:", "counts[quality] = int(counts[quality]) + amount"],
                  "remove": ["if get_quantity(item_id, quality) < amount:", "if counts.max() == 0:", "_quantities.erase(item_id)"],
                  "apply_save_data": ["if counts.max() > 0:", "_quantities = loaded"],
                  "_whole_counts": ["entry.size() != get_definition(item_id).quality_levels", "counts.append(maxi(int(count), 0))"],
                  "_accepts": ["quality >= 0 and quality < get_definition(item_id).quality_levels"]}.items():
    assert all(l in ST[fn] for l in lines), fn
for fn, lines in {"choose_seed": ["if crop == null or get_seed_count(crop.crop_id) <= 0:", '_items.remove(_seed_item_ids.get(crop.crop_id, ""))'],
                  "notify_crop_harvested": ['_items.add(_seed_item_ids.get(crop_definition.crop_id, ""))',
                                            '_items.add(_produce_item_ids.get(crop_definition.crop_id, ""), 1, clampi(quality, QUALITY_PLAIN, QUALITY_FINE))'],
                  "_grant_found_seeds": ["if _found_seed_crop_ids.has(crop.crop_id):", '_items.add(_seed_item_ids.get(crop.crop_id, ""))'],
                  "_give_starting_seeds": ["if _starter_seeds_given.has(crop.crop_id):", "if crop.starting_seeds > 0:"],
                  "apply_save_data": ["if data.is_empty():", "_items.apply_save_data(items)", "_give_starting_seeds()"]}.items():
    assert all(l in FM[fn] for l in lines), fn
assert all(l in SM["_move_holdings_to_items"] for l in ('farm["starter_seeds"] = (seeds as Dictionary).keys()', "items[seed_items[crop_id]] = [seeds[crop_id]]",
                                                        "items[produce_items[crop_id]] = basket[crop_id]", 'farm.erase("seeds")', 'farm.erase("basket")'))
SAVE_VERSION = int(re.search(r"^const SAVE_VERSION := (\d+)", _src("scripts", "autoload", "save_manager.gd"), re.M).group(1))
assert SAVE_VERSION == 2

def godot_json(text):
    def conv(x):
        if isinstance(x, bool): return x
        if isinstance(x, int): return float(x)
        if isinstance(x, list): return [conv(v) for v in x]
        if isinstance(x, dict): return {k: conv(v) for k, v in x.items()}
        return x
    return conv(json.loads(text))
def is_num(v): return isinstance(v, (int, float)) and not isinstance(v, bool)
WARNINGS = []

# ---------------------------------------------------------------- 2. ports
class ItemStore:
    def __init__(s, items=ITEMS): s._defs, s._q = dict(items), {}
    def is_valid_item(s, i): return i in s._defs
    def _accepts(s, i, q): return s.is_valid_item(i) and 0 <= q < s._defs[i]["levels"]
    def get_quantity(s, i, q=-1):
        c = s._q.get(i, [])
        return sum(c) if q < 0 else (c[q] if q < len(c) else 0)
    def has(s, i, n=1, q=-1): return n >= 1 and s.get_quantity(i, q) >= n
    def _counts_of(s, i): return list(s._q[i]) if i in s._q else [0] * s._defs[i]["levels"]
    def add(s, i, n=1, q=0):
        if not s._accepts(i, q) or n < 1: WARNINGS.append(("add", i)); return False
        c = s._counts_of(i); c[q] += n; s._q[i] = c; return True
    def remove(s, i, n=1, q=0):
        if not s._accepts(i, q) or n < 1: WARNINGS.append(("remove", i)); return False
        if s.get_quantity(i, q) < n: return False
        c = s._counts_of(i); c[q] -= n
        if max(c) == 0: del s._q[i]
        else: s._q[i] = c
        return True
    def get_save_data(s): return copy.deepcopy(s._q)
    def _whole(s, i, v):
        if not s.is_valid_item(i) or not isinstance(v, list) or len(v) != s._defs[i]["levels"]: return []
        if not all(is_num(x) for x in v): return []
        return [max(int(x), 0) for x in v]
    def apply_save_data(s, data):
        loaded = {}
        for i, v in data.items():
            c = s._whole(i, v)
            if not c: WARNINGS.append(("load", i)); continue
            if max(c) > 0: loaded[i] = c
        s._q = loaded

def gd_int(v): return int(v) if is_num(v) else 0
class OldFarm:  # FarmManager's seeds and basket before M04.2 (commit 3532b14)
    def __init__(f): f.seeds, f.found, f.basket, f.rest = {c: CROPS[c]["starting"] for c in CROPS}, [], {}, {}
    def seed_count(f, c): return f.seeds.get(c, 0)
    def produce(f, c, q=-1):
        k = f.basket.get(c, [0, 0, 0]); return sum(k) if q < 0 else k[min(max(q, 0), 2)]
    def plant(f, c):
        if f.seed_count(c) <= 0: return False
        f.seeds[c] -= 1; return True
    def harvest(f, c, q):
        f.seeds[c] = f.seed_count(c) + 1; k = f.basket.get(c, [0, 0, 0]); k[min(max(q, 0), 2)] += 1; f.basket[c] = k
    def find(f, c):
        if c in f.found: return False
        f.found.append(c); f.seeds[c] = f.seed_count(c) + 1; return True
    def save_farm(f):
        return {"version": 1, "seeds": dict(f.seeds), "found_seeds": {c: {"source": "place", "source_id": "x"} for c in f.found},
                "basket": {c: list(k) for c, k in f.basket.items()}, **copy.deepcopy(f.rest)}
    def apply(f, d):
        if not d: return
        for c in CROPS:
            sv = d.get("seeds", {}).get(c)
            f.seeds[c] = max(gd_int(sv), 0) if sv is not None else CROPS[c]["starting"]
        f.found = [c for c in d.get("found_seeds", {}) if c in CROPS]
        f.basket = {c: [max(gd_int(x), 0) for x in k] for c, k in d.get("basket", {}).items() if c in CROPS and len(k) == 3}
class Farm:  # after M04.2: the ItemStore holds seeds and the basket
    def __init__(f):
        f.items, f.given, f.found, f.rest = ItemStore(), [], [], {}
        f.give_starting()
    def give_starting(f):
        for c in CROPS:
            if c in f.given: continue
            f.given.append(c)
            if CROPS[c]["starting"] > 0: f.items.add(SEED_ITEM[c], CROPS[c]["starting"])
    def seed_count(f, c): return f.items.get_quantity(SEED_ITEM.get(c, ""))
    def produce(f, c, q=-1):
        i = PRODUCE_ITEM.get(c, "")
        return f.items.get_quantity(i) if q < 0 else f.items.get_quantity(i, min(max(q, 0), Q - 1))
    def plant(f, c):
        if f.seed_count(c) <= 0: return False
        assert f.items.remove(SEED_ITEM[c]); return True
    def harvest(f, c, q): f.items.add(SEED_ITEM[c]); f.items.add(PRODUCE_ITEM[c], 1, min(max(q, 0), Q - 1))
    def find(f, c):
        if c in f.found: return False
        f.found.append(c); f.items.add(SEED_ITEM[c]); return True
    def save_farm(f):
        return {"version": 1, "starter_seeds": list(f.given), "found_seeds": {c: {"source": "place", "source_id": "x"} for c in f.found},
                **copy.deepcopy(f.rest)}
    def apply(f, d, items):
        if not d: return
        f.items.apply_save_data(items)
        f.given = []
        for c in d.get("starter_seeds", []):
            if str(c) in CROPS and str(c) not in f.given: f.given.append(str(c))
        f.give_starting()
        f.found = [c for c in d.get("found_seeds", {}) if c in CROPS]
        # the farm's other fields (grown, milestones, counts, plots...) round-trip unchanged (sim_persistence.py models them)
        f.rest = {k: copy.deepcopy(v) for k, v in d.items() if k not in ("version", "starter_seeds", "found_seeds")}
def observe(f):
    return ({c: f.seed_count(c) for c in CROPS}, {c: [f.produce(c, q) for q in range(Q)] for c in CROPS},
            [(c, f.produce(c)) for c in CROPS if f.produce(c) > 0], sorted(f.found))

SECTION_TYPES = {"points": (float,), "discovered_ids": (list,), "journal_entries": (dict,), "daily_discovery": (dict,),
                 "farm": (dict,), "settings": (dict,), "items": (dict,)}
def migrate_1_to_2(data):  # SaveManager._move_holdings_to_items
    items, farm = {}, data.get("farm")
    if isinstance(farm, dict) and farm:
        seeds, basket = farm.get("seeds", {}), farm.get("basket", {})
        farm["starter_seeds"] = []
        if isinstance(seeds, dict):
            farm["starter_seeds"] = list(seeds.keys())
            for c, n in seeds.items():
                if c in SEED_ITEM: items[SEED_ITEM[c]] = [n]
                else: WARNINGS.append(("migrate", c))
        if isinstance(basket, dict):
            for c, k in basket.items():
                if c in PRODUCE_ITEM: items[PRODUCE_ITEM[c]] = k
                else: WARNINGS.append(("migrate", c))
        farm.pop("seeds", None); farm.pop("basket", None)
    data["items"] = items
def load(text):
    """SaveManager.load_game -> a fresh Farm with the save applied (None = not loaded)."""
    farm = Farm()
    parsed = godot_json(text)
    if not isinstance(parsed, dict): return farm, None
    v = parsed.get("save_version", 0.0)
    v = int(v) if is_num(v) and v >= 0 and v == int(v) else -1
    if v < 0 or v > SAVE_VERSION: return farm, None
    data = copy.deepcopy(parsed)
    while v < SAVE_VERSION:
        if v == 1: migrate_1_to_2(data)
        v += 1; data["save_version"] = float(v)
    data = {k: data[k] for k in SECTION_TYPES if k in data and type(data[k]) in SECTION_TYPES[k] and not isinstance(data[k], bool)}
    farm.apply(data.get("farm", {}), data.get("items", {}))
    return farm, data
def same(a, b): return godot_json(a) == godot_json(b)
def save(farm, data):
    out = {k: copy.deepcopy(v) for k, v in data.items() if k not in ("farm", "items")}
    out.update({"save_version": SAVE_VERSION, "farm": farm.save_farm(), "items": farm.items.get_save_data()})
    return json.dumps(out)

# ---------------------------------------------------------------- 3. the store
ids = sorted(ITEMS); seed, prod = SEED_ITEM[sorted(CROPS)[0]], PRODUCE_ITEM[sorted(CROPS)[0]]
s = ItemStore()
assert s.get_quantity(seed) == 0 and not s.has(seed) and s.get_save_data() == {}
assert s.add(seed) and s.add(seed, 4) and s.get_quantity(seed) == 5 and s.has(seed, 5) and not s.has(seed, 6)
assert s.remove(seed, 2) and s.get_quantity(seed) == 3 and not s.remove(seed, 4) and s.get_quantity(seed) == 3, "all or nothing"
assert s.remove(seed, 3) and seed not in s.get_save_data() and not s.remove(seed), "emptied: unlisted; never below zero"
assert not s.add(seed, 1, 1) and not s.add(seed, 1, -1), "a seed has no quality levels"
for q in range(Q): assert s.add(prod, q + 1, q)
assert [s.get_quantity(prod, q) for q in range(Q)] == list(range(1, Q + 1)) and s.get_quantity(prod) == sum(range(1, Q + 1))
assert not s.add(prod, 1, Q) and not s.remove(prod, 1, Q) and s.get_quantity(prod, Q) == 0, "no such quality level"
assert not s.remove(prod, 2, 0) and s.remove(prod, 1, 0) and s.get_quantity(prod, 0) == 0 and prod in s.get_save_data(), "other levels still held"
for n in (0, -1, -9):
    assert not s.add(prod, n, 1) and not s.remove(prod, n, 1) and not s.has(prod, n)
for bad in ("", "nope", seed.upper(), seed + " "):
    assert not s.add(bad) and not s.remove(bad) and s.get_quantity(bad) == 0 and bad not in s.get_save_data()
big = ItemStore(); assert big.add(prod, 10**6, Q - 1) and big.add(prod, 10**6, Q - 1) and big.get_quantity(prod) == 2 * 10**6
snap = s.get_save_data(); snap[prod][1] = 99; assert s.get_quantity(prod, 1) == 2, "save data is a copy"
WARNINGS.clear(); t = ItemStore()
t.apply_save_data({seed: [3.0], prod: [1.0, 0.0, 2.0], "nope": [1.0], PRODUCE_ITEM[sorted(CROPS)[1]]: [1.0, 1.0],
                   SEED_ITEM[sorted(CROPS)[1]]: ["2"], SEED_ITEM[sorted(CROPS)[2]]: [-4.0], SEED_ITEM[sorted(CROPS)[3]]: [2.9]})
assert t.get_save_data() == {seed: [3], prod: [1, 0, 2], SEED_ITEM[sorted(CROPS)[3]]: [2]}
assert [w[1] for w in WARNINGS] == ["nope", PRODUCE_ITEM[sorted(CROPS)[1]], SEED_ITEM[sorted(CROPS)[1]]], "every dropped entry warned about"
rnd = random.Random(42); pool = ids + ["", "stone"]; ref = {}; s = ItemStore()
for _ in range(20000):
    op, i, n, q = rnd.choice(["add", "remove", "has"]), rnd.choice(pool), rnd.choice([-1, 0, 1, 1, 2, 5]), rnd.choice([-1, 0, 0, 1, 2, 3])
    ok = i in ITEMS and 0 <= q < ITEMS[i]["levels"] and n >= 1
    held = ref.get(i, {}).get(q, 0)
    if op == "add":
        assert s.add(i, n, q) == ok
        if ok: ref.setdefault(i, {})[q] = held + n
    elif op == "remove":
        assert s.remove(i, n, q) == (ok and held >= n)
        if ok and held >= n: ref[i][q] = held - n
    else:
        want = sum(ref.get(i, {}).values()) if q < 0 else held
        assert s.has(i, n, q) == (n >= 1 and want >= n)
    ref = {k: v for k, v in ref.items() if any(v.values())}
    assert set(s.get_save_data()) == set(ref) and all(min(c) >= 0 for c in s.get_save_data().values())
    assert all(s.get_quantity(k, qq) == ref[k].get(qq, 0) for k in ref for qq in range(ITEMS[k]["levels"]))

# ---------------------------------------------------------------- 4. parity with the pre-M04.2 farm
FINDABLE = [c for c in CROPS if CROPS[c]["found"] != "none"]
def play(rnd, farms, steps):
    ground = {c: 0 for c in CROPS}
    for _ in range(steps):
        c, r = rnd.choice(sorted(CROPS)), rnd.random()
        if r < 0.4:
            got = {f.plant(c) for f in farms}; assert len(got) == 1
            if got.pop(): ground[c] += 1
        elif r < 0.8 and ground[c]:
            ground[c] -= 1; q = rnd.choice([0, 1, 2, 2, 3, -1])   # FarmPlot sends 0..2; out-of-range clamps as before
            for f in farms: f.harvest(c, q)
        elif FINDABLE:
            c = rnd.choice(FINDABLE); got = {f.find(c) for f in farms}; assert len(got) == 1
        views = {json.dumps(observe(f)) for f in farms}; assert len(views) == 1, "old and new farm agree"
        for f in farms:
            for k in CROPS:
                assert f.seed_count(k) >= 0 and f.seed_count(k) + ground[k] == CROPS[k]["starting"] + (k in f.found), "seed invariant"
    return ground
for _ in range(3000):
    play(random.Random(rnd.random()), [OldFarm(), Farm()], rnd.randint(1, 60))

# ---------------------------------------------------------------- 5. save, load, migration
OTHER = {"points": 57, "discovered_ids": ["river_stone"], "journal_entries": {"river_stone": {"name": "Smooth River Stone"}},
         "daily_discovery": {"target_id": "wild_mint", "target_date": "2026-09-29", "completed_date": ""}, "settings": {"movement_mode": "joystick"}}
FARM_REST = {"grown": ["wild_carrot"], "milestones": ["first_seed"], "counts": {"planted": 3, "harvested": 1}, "harvested_plots": ["farm_plot_01"],
             "garden_found": True, "plots": {"farm_plot_01": {"state": "GROWING", "soil_memory": ["meadow_herb"], "crop": "wild_carrot", "stage": 2,
                                                              "needs_water": False, "stage_time_left": 3.5, "soil": 2, "care": 1, "quality": 1,
                                                              "longest_thirst": 4.0, "thirsty_for": -1.0}}}
def v1_save(seeds=None, basket=None, farm=True, **extra):
    d = {"save_version": 1, **copy.deepcopy(OTHER)}
    if farm:
        d["farm"] = {"version": 1, "found_seeds": {}, **copy.deepcopy(FARM_REST)}
        if seeds is not None: d["farm"]["seeds"] = seeds
        if basket is not None: d["farm"]["basket"] = basket
    d.update(extra); return json.dumps(d)
def old_load(text):
    f = OldFarm(); d = godot_json(text); f.apply(d.get("farm", {}) if isinstance(d.get("farm"), dict) else {}); return f
C = sorted(CROPS)
# 1. fresh game: starting seeds, an empty basket; the first save is v2 and reloads identically
f = Farm(); assert observe(f) == observe(OldFarm())
first = save(f, copy.deepcopy(OTHER)); d1 = json.loads(first)
assert d1["save_version"] == 2 and "seeds" not in d1["farm"] and "basket" not in d1["farm"] and d1["farm"]["starter_seeds"] == list(CROPS)
assert d1["items"] == {SEED_ITEM[c]: [CROPS[c]["starting"]] for c in CROPS if CROPS[c]["starting"]}
g, data = load(first); assert observe(g) == observe(f) and same(save(g, data), first)
CASES = {
    "2 seeds only": (dict({c: i + 1 for i, c in enumerate(C)}), None),
    "3 basket only": (None, {C[0]: [1, 2, 3]}),
    "4 seeds and basket": ({C[0]: 0, C[1]: 4, C[2]: 1, C[3]: 2}, {C[0]: [0, 1, 0], C[2]: [2, 0, 5]}),
    "5 empty seeds": ({}, {C[1]: [1, 0, 0]}),
    "6 empty basket": ({C[0]: 2, C[1]: 0, C[2]: 0, C[3]: 1}, {}),
    "7 all three qualities": ({C[0]: 1, C[1]: 1, C[2]: 1, C[3]: 1}, {C[0]: [3, 4, 5]}),
    "8 multiple crops": ({c: 2 for c in C}, {c: [i, i + 1, i + 2] for i, c in enumerate(C)}),
    "9 malformed": ({C[0]: 3, "removed_crop": 5, C[1]: -2, C[2]: 1.5}, {C[0]: [1, 1], C[1]: [0, 0, 1], "removed_crop": [1, 1, 1], C[3]: [2, -1, 0]}),
}
for name, (seeds, basket) in CASES.items():
    text = v1_save(seeds, basket)
    WARNINGS.clear(); new, data = load(text); old = old_load(text)
    assert observe(new) == observe(old), f"{name}: the migrated save loads to the same farm as the old code loaded it"
    if "malformed" in name:
        assert ("migrate", "removed_crop") in WARNINGS and ("load", PRODUCE_ITEM[C[0]]) in WARNINGS, "dropped data is warned about"
    else:
        assert not WARNINGS
        if basket:  # 7: every quality survives the move
            for c, k in basket.items(): assert [new.produce(c, q) for q in range(Q)] == k, name
    # 11. migration then autosave: a v2 file, no farm.seeds/basket, the same farm on the next launch
    out = save(new, data); o = json.loads(out)
    assert o["save_version"] == 2 and "seeds" not in o["farm"] and "basket" not in o["farm"] and "items" in o
    again, data2 = load(out); assert observe(again) == observe(new), name
    # 10. repeated load/save is a fixpoint
    assert same(save(again, data2), out), f"{name}: load -> save stable"
    # 12. unrelated sections (and the farm's other fields, incl. M03.3 plot states) exactly as they were
    for k, v in OTHER.items(): assert godot_json(json.dumps(o[k])) == godot_json(json.dumps(v)), (name, k)
    assert same(json.dumps({k: o["farm"][k] for k in FARM_REST}), json.dumps(FARM_REST)) and o["farm"]["version"] == 1
# a v1 save without a farm (older than the farm) and a v0 (pre-M04.0) save: fresh farm / same as old
g, _ = load(v1_save(farm=False)); assert observe(g) == observe(OldFarm())
v0 = json.loads(v1_save({C[0]: 5}, {C[1]: [0, 0, 2]})); del v0["save_version"]
g, _ = load(json.dumps(v0)); assert observe(g) == observe(old_load(json.dumps(v0)))
# a crop the save never saw (added to the game later) gets its starting seeds, as before
g, _ = load(v1_save({c: 0 for c in C[1:]}, {})); assert g.seed_count(C[0]) == CROPS[C[0]]["starting"] == old_load(v1_save({c: 0 for c in C[1:]}, {})).seed_count(C[0])
# malformed v2 items section: bad entries dropped with a warning, the rest loads
v2 = json.loads(first); v2["items"] = {SEED_ITEM[C[0]]: [2], PRODUCE_ITEM[C[0]]: [1, 2], "x": [1], SEED_ITEM[C[1]]: "3"}
WARNINGS.clear(); g, _ = load(json.dumps(v2))
assert g.seed_count(C[0]) == 2 and g.produce(C[0]) == 0 and g.seed_count(C[1]) == 0 and len(WARNINGS) == 3
# random v1 saves: migrated + loaded == loaded by the old code; then stable
rnd = random.Random(77)
for _ in range(2000):
    old = OldFarm(); play(random.Random(rnd.random()), [old], rnd.randint(0, 50))
    old.rest = copy.deepcopy(FARM_REST)
    d = {"save_version": 1, **copy.deepcopy(OTHER), "farm": old.save_farm()}
    if rnd.random() < 0.2: d["farm"]["seeds"].pop(rnd.choice(C))
    if rnd.random() < 0.1: del d["farm"]["basket"]
    text = json.dumps(d); new, data = load(text)
    assert observe(new) == observe(old_load(text))
    out = save(new, data); again, data2 = load(out)
    assert observe(again) == observe(new) and same(save(again, data2), out)
print(f"items: {len(ITEMS)} ({len(SEED_ITEM)} seed, {len(PRODUCE_ITEM)} produce x{Q} qualities); store rules + 20000 random ops; "
      f"old/new farm parity over 3000 sessions; save cases 1-12; 2000 random v1 saves migrate to the same farm and stay stable")
print("ALL ITEM SIMULATIONS PASSED")
