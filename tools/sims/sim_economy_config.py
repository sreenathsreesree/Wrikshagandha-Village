#!/usr/bin/env python3
"""Model checks for the economy configuration (M05.4, D-23) — not the engine.
1. Read from the project: the EconomyConfig script and its one .tres, the
   reward rules, discovery and crop points_value, FarmManager's quality
   scale and harvest formula, and every gameplay script.
2. The redemption reference is exactly 1000 coins = 10 INR and nothing
   outside the config reads it (scripts, scenes, other data, UI).
3. Economy snapshot: every economy value after M05.4 equals the audited
   values — reward rules, discovery and crop points, the frozen quality
   scale, and the full harvest-points table (crop x quality) computed by the
   port of get_harvest_points(). Update the snapshot only with a deliberate
   economy change.
4. The Wallet and PointsManager stay independent of the configuration.
"""
import glob, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _vals(f): return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M)}

# ---------------------------------------------------------------- 1-2. the redemption reference
cfg = _vals(os.path.join(REPO, "data", "economy", "economy_config.tres"))
assert (int(cfg["redemption_reference_coins"]), int(cfg["redemption_reference_amount"]), cfg["redemption_reference_currency"]) == (1000, 10, "INR")
readers = []
for path in glob.glob(os.path.join(REPO, "scripts", "**", "*.gd"), recursive=True) + glob.glob(os.path.join(REPO, "scenes", "**", "*.tscn"), recursive=True):
    if path.endswith(os.path.join("economy", "economy_config.gd")): continue
    text = "\n".join(l.split("#")[0] for l in open(path, encoding="utf-8").read().splitlines() if not l.lstrip().startswith("##"))
    if re.search(r"EconomyConfig|economy_config|redemption|₹|\bINR\b", text, re.I): readers.append(os.path.relpath(path, REPO))
assert readers == [], f"the redemption reference is read by nothing: {readers}"
for f in ("wallet.gd", "points_manager.gd"):
    assert not re.search(r"Economy|redemption|INR", _src("scripts", "autoload", f)), f

# ---------------------------------------------------------------- 3. economy snapshot
RULES = {v["id"]: (int(v.get("points", "0")), int(v.get("threshold", "0"))) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")))}
DISC = {v["id"]: int(v["points_value"]) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "discoveries", "*.tres")))}
CROPS = {v["crop_id"]: int(v["points_value"]) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "crops", "*.tres")))}
FM = _src("scripts", "autoload", "farm_manager.gd")
SCALE = [float(x) for x in re.search(r"^const QUALITY_POINT_SCALE := \[([^\]]*)\]", FM, re.M).group(1).split(",")]
assert "return maxi(roundi(crop.points_value * factor), 1)" in FM and "QUALITY_POINT_SCALE[clampi(quality, 0, QUALITY_POINT_SCALE.size() - 1)]" in FM
def gd_round(x): return int(x + 0.5) if x >= 0 else -int(-x + 0.5)   # roundi: half away from zero
def harvest_points(crop, q): return max(gd_round(CROPS[crop] * SCALE[min(max(q, 0), len(SCALE) - 1)]), 1)
SNAPSHOT = {
    "rules": {"landmark": (15, 0), "secret_location": (15, 0), "all_secret_locations": (50, 0), "curiosity": (20, 0),
              "discoveries_3": (20, 3), "discoveries_5": (40, 5), "daily_discovery": (25, 0), "first_harvest": (10, 0),
              "all_starter_crops": (40, 0), "garden_complete": (30, 0), "garden_in_bloom": (50, 0)},
    "discoveries": {"river_stone": 8, "meadow_flower": 10, "small_mushroom": 12, "wild_mint": 15, "healing_herb": 20, "hidden_herb": 30,
                    "blue_mushroom": 32, "golden_leaf": 60, "ancient_seed": 100},
    "crops": {"wild_carrot": 12, "meadow_herb": 15, "golden_sunflower": 20, "elderbloom": 30},
    "quality_scale": [0.75, 1.0, 1.5],
    "harvest": {"wild_carrot": [9, 12, 18], "meadow_herb": [11, 15, 23], "golden_sunflower": [15, 20, 30], "elderbloom": [23, 30, 45]},
}
now = {"rules": RULES, "discoveries": DISC, "crops": CROPS, "quality_scale": SCALE,
       "harvest": {c: [harvest_points(c, q) for q in range(3)] for c in CROPS}}
for k in SNAPSHOT: assert now[k] == SNAPSHOT[k], f"{k} changed: {now[k]} != {SNAPSHOT[k]}"
assert all(harvest_points(c, q) == harvest_points(c, 2) for c in CROPS for q in (3, 9)) and all(harvest_points(c, -1) == harvest_points(c, 0) for c in CROPS)
# crop display order = points_value order (the documented E3 coupling)
assert sorted(CROPS, key=lambda c: (CROPS[c], c)) == ["wild_carrot", "meadow_herb", "golden_sunflower", "elderbloom"]
print(f"economy config: 1000 coins = 10 INR, read by nothing; snapshot of {len(RULES)} rules, {len(DISC)} discoveries, {len(CROPS)} crops, "
      f"quality scale {SCALE}, harvest table unchanged")
print("ALL ECONOMY CONFIG SIMULATIONS PASSED")
