#!/usr/bin/env python3
"""Selling produce (M06.2, O-01 closed -> D-25) — a model, not the engine.
1. Read from the project: every item's category / quality levels /
   sell_value (data/items), the quality percents (data/market/
   sell_rules.tres), SAVE_VERSION, GameState's sale autosave, the harvest
   rule — and the Market's own GDScript: _unit_coins(), get_unit_price()
   and sell() are TRANSLATED line by line from market.gd and executed, so
   the model runs the order the real code has (a reordered, missing or
   changed step changes what the model does).
2. Prices: every item x quality against an independent exact rational
   round-half-up (fractions), and a sweep of bases x percents; only produce
   with a sell_value sells, seeds and collectibles never at any quality or
   quantity; quantity multiplies the rounded unit price (never rounds a
   total).
3. Sales: remove -> one credit "sell:<item_id>:<quality>" -> announce; every
   refusal (unknown item, not produce, no price, bad quality, quantity < 1,
   more than held) changes nothing and announces nothing; a forced credit
   refusal restores exactly the items removed; a harvest pays points and
   produce but never coins; a sale never moves points; no unit is paid twice.
4. Saves: GameState saves on produce_sold, so items and wallet are written
   together; save -> Godot JSON (floats) -> load keeps both; a v5 save from
   before M06.2 (produce, empty wallet) and a v4 save (no wallet) load with 0
   coins — no retroactive grant — and their produce sells normally.
5. 5,000 random sequences (harvests, valid and invalid sales, forced credit
   refusals, points changes, save/reload, crashes): ledger sum = balance =
   the independently priced sales; produce = harvested - sold; points =
   harvest points only; deterministic.
"""
import copy, glob, json, os, random, re
from fractions import Fraction

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _vals(f): return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M)}
def _code(s): return "\n".join(l.split("#")[0].rstrip() for l in s.splitlines() if not l.lstrip().startswith("##"))
def _funcs(s): return {m.group(1): m.group(0) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", s, re.M | re.S)}

# ---------------------------------------------------------------- 1. read from the project
ITEMS = {}
for f in glob.glob(os.path.join(REPO, "data", "items", "*.tres")):
    v = _vals(f)
    ITEMS[v["id"]] = {"category": v.get("category", "seed"), "levels": int(v.get("quality_levels", "1")),
                      "sell_value": int(v.get("sell_value", "0")), "crop_id": v.get("crop_id", "")}
PRODUCE = sorted(i for i, v in ITEMS.items() if v["category"] == "produce")
UNSELLABLE = sorted(i for i, v in ITEMS.items() if v["category"] != "produce")
assert PRODUCE and UNSELLABLE and {v["category"] for v in ITEMS.values()} == {"seed", "produce", "collectible"}
# Model-only fixtures (never game data — the checker forbids them there): cases the real data can't reach,
# so every guard of sell() is observable on its own (defence in depth is not an equivalent mutant here).
FIXTURES = {"fixture_unpriced_produce": {"category": "produce", "levels": 3, "sell_value": 0, "crop_id": ""},
            "fixture_priced_seed": {"category": "seed", "levels": 1, "sell_value": 3, "crop_id": ""},
            "fixture_priced_collectible": {"category": "collectible", "levels": 1, "sell_value": 5, "crop_id": ""}}
ITEMS.update(FIXTURES)
SR = _src("data", "market", "sell_rules.tres")
PERCENTS = [int(x) for x in re.search(r"^quality_percents = Array\[int\]\(\[([^\]]*)\]\)", SR, re.M).group(1).split(",")]
LEVELS = {v["levels"] for i, v in ITEMS.items() if i in PRODUCE}
assert LEVELS == {len(PERCENTS)}, "one percent per produce quality level"
SMS = _src("scripts", "autoload", "save_manager.gd")
SAVE_VERSION = int(re.search(r"^const SAVE_VERSION := (\d+)", SMS, re.M).group(1))
GS = _funcs(_src("scripts", "autoload", "game_state.gd"))
SAVES_ON_SALE = "Market.produce_sold.connect(_save.unbind(4))" in _code(GS["_ready"])
FM = _funcs(_src("scripts", "autoload", "farm_manager.gd"))
HARVEST = _code(FM["notify_crop_harvested"])
assert "Inventory.add(_produce_item_ids.get(crop_definition.crop_id, \"\"), 1, clampi(quality, QUALITY_PLAIN, QUALITY_FINE))" in HARVEST
HARVEST_PAYS_COINS = bool(re.search(r"\bWallet\b|\bMarket\b", HARVEST + _code(_funcs(_src("scripts", "farming", "farm_plot.gd"))["_run_harvest_sequence"])))

# ---------------------------------------------------------------- the Market, translated from market.gd
MK = _funcs(_src("scripts", "autoload", "market.gd"))
def translate(fn):
    """A GDScript function of market.gd as Python source (the subset the Market uses; anything else fails)."""
    lines = _code(MK[fn]).splitlines()
    head = re.match(r"func (\w+)\((.*)\) -> \w+:$", lines[0])
    args = ", ".join(a.split(":")[0].strip() for a in head.group(2).split(",") if a.strip())
    out = [f"def {fn}({args}):"]
    for raw in lines[1:]:
        if not raw.strip() or raw.strip().startswith("@warning_ignore"):
            continue
        indent = len(raw) - len(raw.lstrip("\t"))
        t = raw.strip()
        t = re.sub(r"^var (\w+) := ", r"\1 = ", t)
        t = re.sub(r"\b(\w+)\.size\(\)", r"len(\1)", t)
        t = t.replace("null", "None").replace("true", "True").replace("false", "False")
        t = re.sub(r'% \[(.*)\]', r"% (\1)", t)
        t = re.sub(r"(\+ \d+\)) / (\d+)", r"\1 // \2", t)               # whole-number division (non-negative operands)
        if re.search(r"[^\w\s\.\(\),:=<>!+\-*/%\"\[\]]", t) or re.search(r"\b(PointsManager|SaveManager|FarmManager|load)\b|points|POINT|[Ee]conomy|redemption", t):
            raise AssertionError(f"market.gd {fn}: untranslatable or out-of-scope line: {raw.strip()}")
        out.append("    " * indent + t)
    return "\n".join(out)
MARKET_PY = "\n".join(translate(fn) for fn in ("_unit_coins", "get_unit_price", "sell"))
READY = _code(MK["_ready"])
assert re.findall(r"load\((\w+)\)", READY) == ["SELL_RULES_PATH"] and 'const SELL_RULES_PATH := "res://data/market/sell_rules.tres"' in _src("scripts", "autoload", "market.gd") \
    and not re.search(r"[Ee]conomy|redemption|points|POINT|res://", READY), "the Market takes its percents from the one sell rules file only"
assert "_quality_percents = rules.quality_percents.duplicate()" in READY and set(MK) == {"_ready", "_unit_coins", "get_unit_price", "sell"}

class Item:
    def __init__(i, item_id): d = ITEMS[item_id]; i.id, i.category, i.quality_levels, i.sell_value = item_id, d["category"], d["levels"], d["sell_value"]
class Inventory:                                  # the ItemStore rules the Market relies on
    def __init__(inv): inv.q, inv.changes, inv.trace = {}, 0, []
    def get_definition(inv, item_id): inv.trace.append("get_definition"); return Item(item_id) if item_id in ITEMS else None
    def _ok(inv, item_id, quality, amount): return item_id in ITEMS and 0 <= quality < ITEMS[item_id]["levels"] and amount >= 1
    def get_quantity(inv, item_id, quality): return inv.q.get((item_id, quality), 0)
    def has(inv, item_id, amount=1, quality=-1):
        inv.trace.append("has")
        total = sum(n for (i, _), n in inv.q.items() if i == item_id) if quality < 0 else inv.get_quantity(item_id, quality)
        return amount >= 1 and total >= amount
    def add(inv, item_id, amount=1, quality=0):
        inv.trace.append("add")
        if not inv._ok(item_id, quality, amount): return False
        inv.q[(item_id, quality)] = inv.get_quantity(item_id, quality) + amount; inv.changes += 1; return True
    def remove(inv, item_id, amount=1, quality=0):
        inv.trace.append("remove")
        if not inv._ok(item_id, quality, amount) or inv.get_quantity(item_id, quality) < amount: return False
        inv.q[(item_id, quality)] -= amount
        if not inv.q[(item_id, quality)]: del inv.q[(item_id, quality)]
        inv.changes += 1; return True
    def save(inv):
        out = {}
        for (i, qu), n in inv.q.items(): out.setdefault(i, [0] * ITEMS[i]["levels"])[qu] = n
        return out
    def load(inv, data):
        inv.q = {(i, qu): int(n) for i, counts in data.items() if i in ITEMS for qu, n in enumerate(counts) if int(n) > 0}
class Wallet:                                     # wallet.gd's credit/debit/load (sim_wallet.py checks it in full)
    def __init__(w): w.balance, w.ledger, w.refuse, w.trace = 0, [], False, []
    def credit(w, n, reason):
        w.trace.append("credit")
        if w.refuse or n < 1 or reason == "": return False           # refuse: a forced failure, for the rollback test
        w.ledger.append({"amount": n, "reason": reason}); w.balance += n; return True
    def debit(w, n, reason): raise AssertionError("M06.2 has no coin sink: nothing debits")
    def save(w): return {"ledger": copy.deepcopy(w.ledger)}
    def load(w, data):
        w.balance, w.ledger = 0, []
        for e in data.get("ledger", []):
            a, r = e.get("amount"), e.get("reason")
            if not isinstance(a, (int, float)) or a != int(a) or int(a) == 0 or not r or w.balance + int(a) < 0: break
            w.ledger.append({"amount": int(a), "reason": r}); w.balance += int(a)
class Game:
    def __init__(g, percents=None):
        g.inventory, g.wallet, g.points, g.emitted, g.disk = Inventory(), Wallet(), 0, [], None
        g.trace = g.inventory.trace = g.wallet.trace = []                # one call trace: what the Market asked, in order
        ns = {"Inventory": g.inventory, "Wallet": g.wallet, "_quality_percents": list(PERCENTS if percents is None else percents),
              "produce_sold": type("Signal", (), {"emit": staticmethod(g._on_sold)})(), "len": len}
        exec(MARKET_PY, ns)
        g.sell, g.get_unit_price = ns["sell"], ns["get_unit_price"]
    def _on_sold(g, item_id, quality, quantity, coins):
        g.emitted.append((item_id, quality, quantity, coins))
        if SAVES_ON_SALE: g.save()                                   # GameState: Market.produce_sold -> save
    def harvest(g, item_id, quality, points):                        # FarmPlot pays points; FarmManager adds the produce
        g.points += points; g.inventory.add(item_id, 1, quality); g.save()
    def save(g):
        g.disk = json.dumps({"save_version": SAVE_VERSION, "points": g.points, "items": g.inventory.save(), "wallet": g.wallet.save()})
    @staticmethod
    def load(text):
        d = json.loads(text, parse_int=float)                         # Godot's JSON: every number a float
        g = Game(); g.points = int(d.get("points", 0))
        g.inventory.load(d.get("items", {})); g.wallet.load(d.get("wallet", {})); g.disk = text
        assert int(d.get("save_version", 0)) == SAVE_VERSION or "wallet" not in d or d.get("save_version", 0) < SAVE_VERSION
        return g

# ---------------------------------------------------------------- 2. prices
def exact_unit(item_id, q):                                           # independent: exact rational, halves up
    d = ITEMS[item_id]
    if d["category"] != "produce" or d["sell_value"] < 1 or not 0 <= q < d["levels"]: return 0
    x = Fraction(d["sell_value"] * PERCENTS[q], 100)
    return int(x) + (1 if x - int(x) >= Fraction(1, 2) else 0)
g = Game()
for i in ITEMS:
    for q in range(-1, 4):
        assert g.get_unit_price(i, q) == exact_unit(i, q), f"price of {i} at quality {q}"
assert all(exact_unit(i, q) >= 1 for i in PRODUCE for q in range(len(PERCENTS))), "every produce quality sells for at least 1 coin"
assert all(exact_unit(i, q) == 0 for i in UNSELLABLE for q in range(-1, 4)), "seeds and collectibles never sell"
for i in PRODUCE:
    prices = [exact_unit(i, q) for q in range(len(PERCENTS))]
    assert prices == sorted(prices) and prices[1] == ITEMS[i]["sell_value"], f"{i}: prices rise with quality, Good = its sell_value"
assert PERCENTS == sorted(PERCENTS) and PERCENTS[1] == 100
unit_src = _code(MK["_unit_coins"])
for base in range(1, 301):                                           # the formula itself, over a sweep of prices and percents
    for pct in (1, 25, 49, 50, 51, 75, 80, 99, 100, 101, 125, 140, 150, 199, 250):
        ns = {"_quality_percents": [pct], "len": len}; exec(translate("_unit_coins"), ns)
        x = Fraction(base * pct, 100)
        assert ns["_unit_coins"](type("I", (), {"sell_value": base})(), 0) == int(x) + (x - int(x) >= Fraction(1, 2)), (base, pct)
TABLE = {i: [exact_unit(i, q) for q in range(len(PERCENTS))] for i in PRODUCE}

# ---------------------------------------------------------------- 3. sales
def fresh(held):
    g = Game()
    for (i, q), n in held.items(): g.inventory.add(i, n, q)
    return g
def unchanged(g, before): return (dict(g.inventory.q), g.wallet.balance, list(g.wallet.ledger), g.points, list(g.emitted)) == before
def state(g): return (dict(g.inventory.q), g.wallet.balance, list(g.wallet.ledger), g.points, list(g.emitted))
for i in PRODUCE:
    for q in range(len(PERCENTS)):
        for n in (1, 2, 3, 7):
            g = fresh({(i, q): 7}); disk_before = g.disk
            assert g.sell(i, q, n) == TABLE[i][q] * n, "a sale pays the rounded unit price x quantity"
            assert g.inventory.get_quantity(i, q) == 7 - n and g.wallet.ledger == [{"amount": TABLE[i][q] * n, "reason": f"sell:{i}:{q}"}]
            assert g.emitted == [(i, q, n, TABLE[i][q] * n)] and g.points == 0, "announced once; points untouched"
            assert g.disk != disk_before and json.loads(g.disk)["wallet"]["ledger"] == g.wallet.ledger and json.loads(g.disk)["items"] == g.inventory.save(), \
                "the sale is saved: items and wallet in one save"
            assert re.fullmatch(r"sell:[a-z][a-z0-9_]*:\d", g.wallet.ledger[0]["reason"])
g = fresh({(PRODUCE[0], 2): 3}); assert g.sell(PRODUCE[0], 2, 3) == TABLE[PRODUCE[0]][2] * 3, "a whole stack in one sale"
# refusals: nothing changes, nothing announced, nothing saved
refusals = [("no_such_item", 0, 1)] + [(i, 0, 1) for i in UNSELLABLE] + [(i, q, n) for i in PRODUCE for q, n in ((-1, 1), (3, 1), (0, 0), (0, -2), (0, 4))]
for i, q, n in refusals:
    held = {(p, qq): 3 for p in PRODUCE for qq in range(len(PERCENTS))}
    held.update({(u, 0): 5 for u in UNSELLABLE})
    g = fresh(held); before, disk = state(g), g.disk
    assert g.sell(i, q, n) == 0 and unchanged(g, before) and g.disk == disk, f"refused sale changed something: {(i, q, n)}"
# the order of the checks (call traces): every refusal stops at its own check, before touching what it needn't
VALIDATE, HELD, SOLD, RESTORED = ["get_definition"], ["get_definition", "has"], ["get_definition", "has", "remove", "credit"], \
    ["get_definition", "has", "remove", "credit", "add"]
def trace_of(g, i, q, n): del g.trace[:]; g.sell(i, q, n); return list(g.trace)
held_all = {(p, qq): 3 for p in list(PRODUCE) + ["fixture_unpriced_produce"] for qq in range(len(PERCENTS))}
held_all.update({(u, 0): 5 for u in UNSELLABLE + ["fixture_priced_seed", "fixture_priced_collectible"]})
cases = [("no_such_item", 0, 1, VALIDATE), ("fixture_priced_seed", 0, 1, VALIDATE), ("fixture_priced_collectible", 0, 1, VALIDATE),
         ("fixture_unpriced_produce", 1, 1, VALIDATE)] + [(u, 0, 1, VALIDATE) for u in UNSELLABLE] + \
        [(i, q, n, VALIDATE) for i in PRODUCE for q, n in ((-1, 1), (3, 1), (0, 0), (0, -2))] + \
        [(i, 0, 4, HELD) for i in PRODUCE] + [(i, 0, 2, SOLD) for i in PRODUCE]
for i, q, n, want in cases:
    g = fresh(held_all); before = state(g)
    got = trace_of(g, i, q, n)
    assert got == want, f"sell{(i, q, n)} asked {got}, expected {want}"
    assert (want == SOLD) != unchanged(g, before), f"sell{(i, q, n)}"
for i in ("fixture_priced_seed", "fixture_priced_collectible", "fixture_unpriced_produce"):
    assert all(Game().get_unit_price(i, q) == 0 for q in range(-1, 4)), f"{i}: no price for anything but priced produce"
g = Game(percents=[1] * len(PERCENTS)); g.inventory.add(PRODUCE[0], 3, 0); before = state(g)   # a price that rounds to 0 coins
assert trace_of(g, PRODUCE[0], 0, 3) == HELD and unchanged(g, before), "a sale worth 0 coins stops before touching the items"
# forced credit refusal: the exact items come back, no coins, no announcement
for i in PRODUCE:
    for q in range(len(PERCENTS)):
        g = fresh({(i, q): 4, (i, (q + 1) % len(PERCENTS)): 2}); g.wallet.refuse = True; before = state(g)
        assert g.sell(i, q, 3) == 0 and unchanged(g, before), "a refused credit restores exactly the items removed"
        assert g.inventory.changes == 2 + 2, "removed then restored — nothing else"
        assert trace_of(fresh({(i, q): 4}), i, q, 3) == SOLD
        g2 = fresh({(i, q): 4}); g2.wallet.refuse = True; assert trace_of(g2, i, q, 3) == RESTORED
# harvest: points and produce, never coins; no unit paid twice
assert not HARVEST_PAYS_COINS, "a harvest never touches coins"
g = Game(); g.harvest(PRODUCE[0], 2, 18)
assert (g.points, g.wallet.balance, g.wallet.ledger) == (18, 0, []), "harvest: points + produce, no coins"
assert g.sell(PRODUCE[0], 2, 1) == TABLE[PRODUCE[0]][2] and g.sell(PRODUCE[0], 2, 1) == 0, "one harvested unit sells once"
assert g.wallet.balance == TABLE[PRODUCE[0]][2] and g.points == 18

# ---------------------------------------------------------------- 4. saves
assert SAVE_VERSION == 5 and SAVES_ON_SALE, "SAVE_VERSION stays 5; GameState saves on produce_sold"
g = fresh({(i, q): 5 for i in PRODUCE for q in range(len(PERCENTS))}); g.points = 123
for i in PRODUCE: g.sell(i, 2, 2)
g2 = Game.load(g.disk)
assert (g2.inventory.q, g2.wallet.balance, g2.wallet.ledger, g2.points) == (g.inventory.q, g.wallet.balance, g.wallet.ledger, g.points), "reload keeps both"
g2.save(); assert Game.load(g2.disk).wallet.ledger == g.wallet.ledger, "save -> load -> save stable"
old_v5 = json.dumps({"save_version": 5, "points": 900, "items": {PRODUCE[0]: [2, 1, 3]}, "wallet": {"ledger": []}})
old_v4 = json.dumps({"save_version": 4, "points": 900, "items": {PRODUCE[0]: [2, 1, 3]}})
for old in (old_v5, old_v4):
    g = Game.load(old)
    assert (g.wallet.balance, g.wallet.ledger, g.points) == (0, [], 900), "no retroactive coins for old progress or old produce"
    assert g.sell(PRODUCE[0], 2, 3) == TABLE[PRODUCE[0]][2] * 3 and g.points == 900, "existing produce sells normally"

# ---------------------------------------------------------------- 5. random sequences
def run(seed):
    rnd = random.Random(seed); g = Game(); harvested, sold, points_paid, last_saved = {}, [], 0, None
    for _ in range(rnd.randint(1, 60)):
        r = rnd.random()
        if r < 0.35:
            i, q, p = rnd.choice(PRODUCE), rnd.randrange(len(PERCENTS)), rnd.randint(1, 45)
            g.harvest(i, q, p); harvested[(i, q)] = harvested.get((i, q), 0) + 1; points_paid += p
        elif r < 0.75:
            if g.inventory.q and rnd.random() < 0.7:                  # mostly what is held, sometimes anything
                (i, q), n = rnd.choice(sorted(g.inventory.q)), rnd.randint(1, 4)
            else:
                i = rnd.choice(sorted(ITEMS) + ["nope"]); q, n = rnd.randint(-1, 3), rnd.randint(-1, 5)
            g.wallet.refuse = rnd.random() < 0.1; before = state(g)
            paid = g.sell(i, q, n); g.wallet.refuse = False
            if paid:
                assert paid == exact_unit(i, q) * n and n >= 1 and i in PRODUCE; sold.append((i, q, n, paid))
            else:
                assert unchanged(g, before)
        elif r < 0.85:
            before = (g.wallet.balance, list(g.wallet.ledger)); d = rnd.randint(-20, 60); g.points += d; points_paid += d
            assert (g.wallet.balance, g.wallet.ledger) == before, "points never move coins"
            g.save()                                                   # (points saved too, so a relaunch keeps them)
        elif r < 0.95:
            g = Game.load(g.disk) if g.disk else Game()               # relaunch (everything above saved at once)
        else:
            g.save()
        assert g.wallet.balance == sum(e["amount"] for e in g.wallet.ledger) == sum(s[3] for s in sold) >= 0, "ledger = balance = the sales"
        assert [e["reason"] for e in g.wallet.ledger] == [f"sell:{i}:{q}" for i, q, _, _ in sold], "one entry per sale, in order"
        for k in set(harvested) | set(g.inventory.q):
            assert g.inventory.q.get(k, 0) == harvested.get(k, 0) - sum(s[2] for s in sold if (s[0], s[1]) == k), "produce = harvested - sold"
        assert g.points == points_paid, "points are exactly what was paid — a sale adds none"
    return g.disk, len(sold)
total_sales = 0
for seed in range(5000):
    disk, n = run(seed); total_sales += n
    assert run(seed)[0] == disk if seed % 250 == 0 else True, "deterministic"
assert total_sales > 0

print(f"selling: {len(PRODUCE)} produce sellable, {len(UNSELLABLE)} seeds/collectibles never; percents {PERCENTS}; unit prices {TABLE}; "
      f"round half up per unit (exact rationals + 4500 sweeps); {len(refusals)} refusals change nothing; {len(cases)} call traces in order; forced credit refusals restore items; "
      f"harvest pays no coins; saves at v{SAVE_VERSION} keep items + wallet together; old saves get no coins; 5000 random sequences ({total_sales} sales)")
print("ALL SELLING SIMULATIONS PASSED")
