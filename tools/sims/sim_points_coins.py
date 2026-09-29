#!/usr/bin/env python3
"""Model checks for points and coins independence (M05.5, O-02 closed, D-24).
Not the engine.
1. Read from the project: every script that pays points (the 9 audited
   sites) and every script that touches the Wallet; the reward data,
   discovery/crop points and the harvest quality scale.
2. Static facts: points are paid only through PointsManager.add_points at
   the audited sites; nothing but SaveManager touches the Wallet, and only
   to save/load it; no script mixes the two.
3. Model (ports of PointsManager and Wallet, a SaveManager round trip):
   2,000 random sessions of every point reward (discoveries incl. the
   once-ever Ancient Seed, thresholds, landmarks, secrets, every-secret,
   curiosity, daily, harvests at every quality, farm milestones) produce
   exactly the audited totals, while the wallet stays at 0 with an empty
   ledger; save/reload keeps both independently; changing points never
   changes the wallet and changing the wallet never changes points.
"""
import glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _vals(f): return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M)}
def code(s): return "\n".join(l.split("#")[0] for l in s.splitlines() if not l.lstrip().startswith("##"))

# ---------------------------------------------------------------- 1-2. static facts
SCRIPTS = {os.path.relpath(p, REPO): code(open(p, encoding="utf-8").read()) for p in glob.glob(os.path.join(REPO, "scripts", "**", "*.gd"), recursive=True)}
payers = sorted(f for f, s in SCRIPTS.items() if "PointsManager.add_points(" in s)
assert payers == sorted(["scripts/autoload/discovery_manager.gd", "scripts/autoload/exploration_manager.gd", "scripts/autoload/daily_discovery_manager.gd",
                         "scripts/autoload/farm_manager.gd", "scripts/farming/farm_plot.gd"]), payers
assert sum(s.count("PointsManager.add_points(") for s in SCRIPTS.values()) == 9, "exactly the 9 audited pay sites"
wallet_users = sorted(f for f, s in SCRIPTS.items() if re.search(r"\bWallet\.", s))
assert wallet_users == ["scripts/autoload/save_manager.gd"], wallet_users
assert re.findall(r"Wallet\.(\w+)\(", SCRIPTS["scripts/autoload/save_manager.gd"]) == ["get_save_data", "apply_save_data"]
assert not any(re.search(r"\bWallet\b", SCRIPTS[f]) for f in payers), "no pay site touches the Wallet"
assert not re.search(r"Wallet|coin|balance|ledger", SCRIPTS["scripts/autoload/points_manager.gd"], re.I)
assert not re.search(r"PointsManager|add_points|points_changed", SCRIPTS["scripts/autoload/wallet.gd"])

# ---------------------------------------------------------------- 3. model
RULES = {v["id"]: int(v["points"]) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")))}
THRESH = {int(v["threshold"]): int(v["points"]) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "rewards", "*.tres"))) if v.get("threshold")}
DISC = {v["id"]: (int(v["points_value"]), float(v.get("respawn_seconds", "60")) <= 0) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "discoveries", "*.tres")))}
CROPS = {v["crop_id"]: int(v["points_value"]) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "crops", "*.tres")))}
SCALE = [float(x) for x in re.search(r"^const QUALITY_POINT_SCALE := \[([^\]]*)\]", _src("scripts", "autoload", "farm_manager.gd"), re.M).group(1).split(",")]
# the audited amounts (M05.3/M05.4 snapshot) — independent of the data read above
AUDITED = {"landmark": 15, "secret_location": 15, "all_secret_locations": 50, "curiosity": 20, "daily_discovery": 25,
           "first_harvest": 10, "all_starter_crops": 40, "garden_complete": 30, "garden_in_bloom": 50}
AUDITED_THRESH = {3: 20, 5: 40}
AUDITED_HARVEST = {"wild_carrot": [9, 12, 18], "meadow_herb": [11, 15, 23], "golden_sunflower": [15, 20, 30], "elderbloom": [23, 30, 45]}
AUDITED_DISC = {"river_stone": 8, "meadow_flower": 10, "small_mushroom": 12, "wild_mint": 15, "healing_herb": 20, "hidden_herb": 30,
                "blue_mushroom": 32, "golden_leaf": 60, "ancient_seed": 100}
class Points:                                   # PointsManager
    def __init__(p): p.points = 0
    def add_points(p, n):
        if n == 0: return
        p.points += n
class Wallet:                                   # Wallet (M05.1)
    def __init__(w): w.balance, w.ledger = 0, []
    def credit(w, n, reason):
        if n < 1 or not reason: return False
        w.ledger.append({"amount": n, "reason": reason}); w.balance += n; return True
    def debit(w, n, reason):
        if n < 1 or not reason or n > w.balance: return False
        w.ledger.append({"amount": -n, "reason": reason}); w.balance -= n; return True
def harvest_points(crop, q):
    x = CROPS[crop] * SCALE[q]; return max(int(x + 0.5), 1)
EVENTS = ["discovery", "landmark", "secret_location", "all_secret_locations", "curiosity", "daily_discovery", "harvest",
          "first_harvest", "all_starter_crops", "garden_complete", "garden_in_bloom"]
def play(rnd, pm, found, steps):
    """Pays through the model PointsManager; returns the audited total paid, computed independently."""
    expected, session_first = 0, 0
    for _ in range(steps):
        e = rnd.choice(EVENTS)
        if e == "discovery":
            d = rnd.choice(sorted(DISC)); pts, once = DISC[d]
            if once and d in found: continue
            first = d not in found; found.add(d)
            pm.add_points(pts); expected += AUDITED_DISC[d]
            if first:
                session_first += 1
                if session_first in THRESH: pm.add_points(THRESH[session_first]); expected += AUDITED_THRESH[session_first]
        elif e == "harvest":
            c, q = rnd.choice(sorted(CROPS)), rnd.randrange(3)
            pm.add_points(harvest_points(c, q)); expected += AUDITED_HARVEST[c][q]
        else:
            pm.add_points(RULES[e]); expected += AUDITED[e]
    return expected
rnd = random.Random(55); total_paid = 0
for _ in range(2000):
    pm, w, found = Points(), Wallet(), set(); expected = 0
    for launch in range(rnd.randint(1, 6)):
        before_wallet = (w.balance, json.dumps(w.ledger))
        expected += play(rnd, pm, found, rnd.randint(0, 40))
        assert pm.points == expected, "point rewards pay exactly the audited amounts"
        assert (w.balance, json.dumps(w.ledger)) == before_wallet == (0, "[]"), "the wallet stays at 0 with an empty ledger"
        save = json.loads(json.dumps({"points": pm.points, "wallet": {"ledger": w.ledger}}))     # SaveManager round trip
        pm2, w2 = Points(), Wallet(); pm2.points = int(save["points"])
        for e in save["wallet"]["ledger"]: w2.credit(e["amount"], e["reason"]) if e["amount"] > 0 else w2.debit(-e["amount"], e["reason"])
        assert (pm2.points, w2.balance, w2.ledger) == (pm.points, w.balance, w.ledger), "save/reload keeps both, independently"
        pm, w = pm2, w2
    total_paid += pm.points
# independence both ways (the model has no bridge; the static facts above show the code has none either)
pm, w = Points(), Wallet()
for _ in range(5000):
    if rnd.random() < 0.5:
        before = (w.balance, list(w.ledger)); pm.add_points(rnd.randint(-50, 100)); assert (w.balance, w.ledger) == before
    else:
        before = pm.points; (w.credit if rnd.random() < 0.6 else w.debit)(rnd.randint(-5, 50), rnd.choice(["t", ""])); assert pm.points == before
print(f"points and coins: 9 pay sites, points only; the Wallet touched only by SaveManager's save/load; 2000 players paid exactly the audited "
      f"amounts ({total_paid} points) with the wallet at 0 / empty ledger; save/reload independent; 5000 cross-mutations never leak")
print("ALL POINTS/COINS SIMULATIONS PASSED")
