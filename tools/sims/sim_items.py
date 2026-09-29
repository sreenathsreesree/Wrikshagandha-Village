#!/usr/bin/env python3
"""Model checks for item definitions + the item store (M04.1) — a Python port,
not the engine.
1. Read from the project: data/items/, data/crops/, the ItemStore's rules
   (the guard and write lines of add/remove, the read functions).
2. Port of ItemStore: add / remove / get_quantity / has / get_quantities.
3. Cases: adding, removing, insufficient quantity (all or nothing), zero and
   negative amounts, unknown ids, no stack limit (nothing is ever dropped),
   repeated operations, 20,000 random operations against a plain reference
   ledger, and returned copies that can't change the store.
4. Parity with the existing seed ledger: FarmManager's seed rules (starting
   seeds, planting refused at 0, one seed back per harvest, each found seed
   once) replayed through an ItemStore of the crops' seed items give the same
   counts in 3,000 random farm sessions, and the seed invariant holds. The
   basket's per-crop totals likewise match the crops' produce items.
   (FarmManager itself is unchanged until M04.2.)
"""
import glob, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _funcs(src): return {m.group(2): m.group(0) for m in re.finditer(r"^(static )?func (\w+)\(.*?(?=^func |^static func |\Z)", src, re.M | re.S)}
def _vals(path):
    txt = open(path, encoding="utf-8").read().split("[resource]", 1)[1]
    return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', txt, re.M)}

# ---------------------------------------------------------------- 1. read from the project
ITEMS = {v["id"]: {"category": v.get("category", "seed"), "crop": v["crop_id"], "name": v["display_name"]}
         for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "items", "*.tres"))))}
CROPS = {v["crop_id"]: {"starting": max(int(v.get("starting_seeds", "1")), 0), "found": v.get("found_seed_source", "none"),
                        "found_id": v.get("found_seed_source_id", "")}
         for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "crops", "*.tres"))))}
SEED_ITEM = {i["crop"]: iid for iid, i in ITEMS.items() if i["category"] == "seed"}
PRODUCE_ITEM = {i["crop"]: iid for iid, i in ITEMS.items() if i["category"] == "produce"}
assert set(SEED_ITEM) == set(PRODUCE_ITEM) == set(CROPS), "every crop has a seed item and a produce item"
ST = _funcs(_src("scripts", "items", "item_store.gd"))
assert "if not is_valid_item(item_id) or amount < 1:" in ST["add"] and "_quantities[item_id] = get_quantity(item_id) + amount" in ST["add"]
assert "if not is_valid_item(item_id) or amount < 1:" in ST["remove"] and "if get_quantity(item_id) < amount:" in ST["remove"]
assert "_quantities.erase(item_id)" in ST["remove"] and "return amount >= 1 and get_quantity(item_id) >= amount" in ST["has"]
assert "return _quantities.duplicate()" in ST["get_quantities"]
FM = _funcs(_src("scripts", "autoload", "farm_manager.gd"))
assert "if crop == null or get_seed_count(crop.crop_id) <= 0:" in FM["choose_seed"] and "_seeds[crop.crop_id] = get_seed_count(crop.crop_id) - 1" in FM["choose_seed"]
assert "_seeds[crop_definition.crop_id] = get_seed_count(crop_definition.crop_id) + 1" in FM["notify_crop_harvested"]
assert "if _found_seed_crop_ids.has(crop.crop_id):" in FM["_grant_found_seeds"] and "_seeds[crop.crop_id] = get_seed_count(crop.crop_id) + 1" in FM["_grant_found_seeds"]

# ---------------------------------------------------------------- 2. port
class ItemStore:
    def __init__(s, items): s._defs, s._q = dict(items), {}
    def is_valid_item(s, i): return i in s._defs
    def get_quantity(s, i): return s._q.get(i, 0)
    def has(s, i, n=1): return n >= 1 and s.get_quantity(i) >= n
    def add(s, i, n=1):
        if not s.is_valid_item(i) or n < 1: return False
        s._q[i] = s.get_quantity(i) + n; return True
    def remove(s, i, n=1):
        if not s.is_valid_item(i) or n < 1: return False
        if s.get_quantity(i) < n: return False
        left = s.get_quantity(i) - n
        if left == 0: del s._q[i]
        else: s._q[i] = left
        return True
    def get_quantities(s): return dict(s._q)

# ---------------------------------------------------------------- 3. cases
ids = sorted(ITEMS); a, b = ids[0], ids[1]
st = ItemStore(ITEMS)
assert st.get_quantity(a) == 0 and not st.has(a) and st.get_quantities() == {}
assert st.add(a) and st.get_quantity(a) == 1 and st.add(a, 4) and st.get_quantity(a) == 5 and st.has(a, 5) and not st.has(a, 6)
assert st.remove(a, 2) and st.get_quantity(a) == 3
assert not st.remove(a, 4) and st.get_quantity(a) == 3, "insufficient: nothing taken"
assert st.remove(a, 3) and st.get_quantity(a) == 0 and a not in st.get_quantities(), "an emptied item is no longer listed"
assert not st.remove(a) and st.get_quantity(a) == 0, "never below zero"
for n in (0, -1, -50):
    assert not st.add(b, n) and not st.remove(b, n) and not st.has(b, n) and st.get_quantity(b) == 0, f"amount {n} refused"
for bad in ("", "unknown_item", "WILD_CARROT_SEED", a + " ", "wild_carrot_seeds"):
    assert not st.is_valid_item(bad) and not st.add(bad, 1) and not st.remove(bad, 1) and st.get_quantity(bad) == 0, bad
assert bad not in st.get_quantities()
big = ItemStore(ITEMS); assert big.add(a, 10**6) and big.add(a, 10**6) and big.get_quantity(a) == 2 * 10**6, "no stack limit: nothing dropped"
copy = st.get_quantities(); st.add(b, 2); copy[b] = 99; copy[a] = 7
assert st.get_quantity(b) == 2 and st.get_quantity(a) == 0, "the returned dictionary is a copy"
for _ in range(1000): assert st.add(b) and st.remove(b)
assert st.get_quantity(b) == 2, "repeated add/remove pairs leave the count unchanged"

rnd = random.Random(41); pool = ids + ["", "nope", "stone"]
st, ref = ItemStore(ITEMS), {}
for _ in range(20000):
    op, i, n = rnd.choice(["add", "remove", "has"]), rnd.choice(pool), rnd.choice([-2, -1, 0, 1, 1, 1, 2, 3, 7])
    valid = i in ITEMS and n >= 1
    if op == "add":
        assert st.add(i, n) == valid
        if valid: ref[i] = ref.get(i, 0) + n
    elif op == "remove":
        ok = valid and ref.get(i, 0) >= n
        assert st.remove(i, n) == ok
        if ok: ref[i] -= n; ref = {k: v for k, v in ref.items() if v}
    else:
        assert st.has(i, n) == (n >= 1 and ref.get(i, 0) >= n)
    q = st.get_quantities()
    assert q == ref and all(v >= 1 for v in q.values()) and set(q) <= set(ITEMS)

# ---------------------------------------------------------------- 4. parity with the existing seed ledger
class FarmSeeds:  # FarmManager's rules (choose_seed / notify_crop_harvested / _grant_found_seeds)
    def __init__(f): f.seeds, f.found = {c: CROPS[c]["starting"] for c in CROPS}, set()
    def plant(f, c):
        if f.seeds.get(c, 0) <= 0: return False
        f.seeds[c] -= 1; return True
    def harvest(f, c): f.seeds[c] = f.seeds.get(c, 0) + 1
    def found_seed(f, c):
        if c in f.found: return False
        f.found.add(c); f.seeds[c] = f.seeds.get(c, 0) + 1; return True
sessions = 0
for _ in range(3000):
    farm, store, ground, basket, sb = FarmSeeds(), ItemStore(ITEMS), {c: 0 for c in CROPS}, {c: 0 for c in CROPS}, ItemStore(ITEMS)
    for c in CROPS:
        if CROPS[c]["starting"]: store.add(SEED_ITEM[c], CROPS[c]["starting"])
    for _ in range(rnd.randint(1, 60)):
        c, r = rnd.choice(sorted(CROPS)), rnd.random()
        if r < 0.45:
            p = farm.plant(c); assert store.remove(SEED_ITEM[c]) == p
            if p: ground[c] += 1
        elif r < 0.85 and ground[c]:
            ground[c] -= 1; farm.harvest(c); store.add(SEED_ITEM[c]); basket[c] += 1; sb.add(PRODUCE_ITEM[c])
        elif CROPS[c]["found"] != "none":
            if farm.found_seed(c):           # granted once ever; a repeat changes nothing
                store.add(SEED_ITEM[c])
        for k in CROPS:
            assert store.get_quantity(SEED_ITEM[k]) == farm.seeds[k] >= 0, "same seed counts, never negative"
            assert store.get_quantity(SEED_ITEM[k]) + ground[k] == CROPS[k]["starting"] + (k in farm.found), "seed invariant"
            assert sb.get_quantity(PRODUCE_ITEM[k]) == basket[k]
    sessions += 1
print(f"items: {len(ITEMS)} ({len(SEED_ITEM)} seed, {len(PRODUCE_ITEM)} produce); add/remove/insufficient/zero/negative/unknown/"
      f"no-limit/copies OK; 20000 random ops match the reference; seed-ledger + basket parity over {sessions} farm sessions")
print("ALL ITEM SIMULATIONS PASSED")
