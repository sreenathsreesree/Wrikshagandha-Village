#!/usr/bin/env python3
"""Model checks for reward rules as data (M05.3, D-22) — not the engine.
1. Read from the project: data/rewards/, the reward call sites, the
   discoveries' respawn data, the once-ever claim lines.
2. Parity: the reward data equals the amounts the code held before M05.3
   (the snapshot below — update it only with a deliberate change to the
   data), the discovery-count thresholds and the summary point are
   unchanged, every rule is paid somewhere and every paid id has a rule.
3. Once-ever discoveries (respawn_seconds <= 0 — the Ancient Seed): the
   first collection pays and claims it; after that it neither spawns (at
   launch, after an area reload) nor pays, across 20 relaunches of 2,000
   random players; respawning discoveries stay repeatable; a save from
   before M05.3 that already has it in discovered_ids is already claimed;
   the daily target is never a claimed discovery and every other day keeps
   its target.
"""
import glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _vals(f): return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M)}
def _funcs(src): return {m.group(1): m.group(0) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", src, re.M | re.S)}

# ---------------------------------------------------------------- 1. read
RULES = {v["id"]: (int(v.get("points", "0")), int(v.get("threshold", "0"))) for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "rewards", "*.tres"))))}
DISC = [(v["id"], float(v.get("respawn_seconds", "60")), int(v.get("points_value", "10"))) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "discoveries", "*.tres")))]
DISC.sort()                                           # DiscoveryDatabase order (sorted files == sorted ids here)
ONCE_EVER = {d for d, r, _ in DISC if r <= 0}
assert ONCE_EVER == {"ancient_seed"}, f"the once-ever discoveries are exactly the Ancient Seed today ({ONCE_EVER})"
EX, FM, DD = _src("scripts", "autoload", "exploration_manager.gd"), _src("scripts", "autoload", "farm_manager.gd"), _src("scripts", "autoload", "daily_discovery_manager.gd")
PAID = set(re.findall(r'_rewards\.points\("(\w+)"\)', EX)) | set(re.findall(r'RewardRules\.new\(\)\.points\("(\w+)"\)', DD))
def _farm_milestones(fm):  # M06.4: get_milestones()'s registered ids (constants + "grown:<starter crop>")
    gm = re.search(r"^func get_milestones\(.*?(?=^func )", fm, re.M | re.S).group(0)
    ids = {re.search(rf'^const {c} := "(\w+)"', fm, re.M).group(1) for c in re.findall(r"_milestone_row\(([A-Z_]+),", gm)}
    if "_milestone_row(CROP_GROWN_PREFIX + crop.crop_id," in gm:
        prefix = re.search(r'^const CROP_GROWN_PREFIX := "([^"]*)"', fm, re.M).group(1)
        for f in glob.glob(os.path.join(REPO, "data", "crops", "*.tres")):
            t = open(f, encoding="utf-8").read(); st = re.search(r"^starting_seeds = (\d+)", t, re.M)
            if int(st.group(1) if st else 1) > 0: ids.add(prefix + re.search(r'crop_id = "([^"]+)"', t).group(1))
    assert "var bonus_points := _rewards.points(milestone_id) if _rewards.has(milestone_id) else 0" in fm, "farm milestones pay by id in _reach()"
    return ids
PAID |= _farm_milestones(FM) & {os.path.basename(f)[:-5] for f in glob.glob(os.path.join(REPO, "data", "rewards", "*.tres"))}
DM, SP = _funcs(_src("scripts", "autoload", "discovery_manager.gd")), _funcs(_src("scripts", "interactables", "discovery_spawn_point.gd"))
assert "definition.respawn_seconds <= 0.0 and discovered_ids.has(id)" in DM["is_claimed"] and "if is_claimed(id):" in DM["discover"]
assert "if DiscoveryManager.is_claimed(instance.discovery_id):" in SP["_spawn"]
DDF = _funcs(DD)
assert "if not DiscoveryManager.is_claimed(candidate.id):" in DDF["_ensure_today_target"]

# ---------------------------------------------------------------- 2. parity with the pre-M05.3 constants
BEFORE = {"landmark": 15, "secret_location": 15, "all_secret_locations": 50, "curiosity": 20, "daily_discovery": 25,
          "first_harvest": 10, "all_starter_crops": 40, "garden_complete": 30, "garden_in_bloom": 50}
BEFORE_THRESHOLDS = {3: 20, 5: 40}
assert {r: p for r, (p, t) in RULES.items() if not t} == BEFORE, "flat rewards pay exactly what the code paid"
assert {t: p for p, t in RULES.values() if t} == BEFORE_THRESHOLDS, "discovery-count thresholds unchanged"
assert max(BEFORE_THRESHOLDS) == 5, "the session summary still shows at the 5th first-ever discovery"
assert PAID == set(BEFORE), f"every flat rule is paid and nothing unknown is ({PAID ^ set(BEFORE)})"

# ---------------------------------------------------------------- 3. once-ever discoveries
class Game:
    def __init__(g, discovered=()): g.discovered, g.points, g.collected = list(discovered), 0, {}
    def claimed(g, d): return d in ONCE_EVER and d in g.discovered                  # DiscoveryManager.is_claimed
    def spawned(g): return [d for d, _, _ in DISC if not g.claimed(d)]             # DiscoverySpawnPoint._spawn (launch / area reload)
    def discover(g, d):                                                             # DiscoveryManager.discover
        if g.claimed(d): return False
        if d not in g.discovered: g.discovered.append(d)
        g.points += dict((i, p) for i, _, p in DISC)[d]; g.collected[d] = g.collected.get(d, 0) + 1
        return True
    def relaunch(g): return Game(json.loads(json.dumps(g.discovered)))              # discovered_ids is saved
def daily_target(g, day):                                                           # DailyDiscoveryManager._ensure_today_target
    ids = [d for d, _, _ in DISC]; index = abs(day) % len(ids)
    for step in range(len(ids)):
        c = ids[(index + step) % len(ids)]
        if not g.claimed(c): return c
g = Game(); assert "ancient_seed" in g.spawned() and g.discover("ancient_seed") and g.points == 100
assert not g.discover("ancient_seed") and g.points == 100 and "ancient_seed" not in g.spawned(), "claimed: gone and never paid again"
g2 = g.relaunch(); assert "ancient_seed" not in g2.spawned() and not g2.discover("ancient_seed"), "still claimed after a relaunch"
assert g2.discover("river_stone") and g2.discover("river_stone"), "respawning discoveries stay repeatable"
old = Game(["ancient_seed", "river_stone"]); assert old.claimed("ancient_seed"), "a pre-M05.3 save that found it: already claimed"
rnd = random.Random(53); relaunches = 0
for _ in range(2000):
    g = Game()
    for _ in range(20):
        for _ in range(rnd.randint(0, 15)):
            d = rnd.choice(g.spawned()); assert g.discover(d)
        if rnd.random() < 0.2: assert not g.discover("ancient_seed") or g.collected["ancient_seed"] == 1
        g = Game(g.discovered) if rnd.random() < 0.5 else g.relaunch(); relaunches += 1
    assert g.collected.get("ancient_seed", 0) <= 1
tot = Game(); [tot.discover(d) for d, _, _ in DISC]; [tot.discover("ancient_seed") for _ in range(5)]
assert tot.collected["ancient_seed"] == 1
fresh, done = Game(), Game(["ancient_seed"])
changed = 0
for day in range(-5000, 5000):
    a, b = daily_target(fresh, day), daily_target(done, day)
    assert b != "ancient_seed" and (a == b or a == "ancient_seed"), "only the claimed discovery's days move, to the next one"
    changed += a != b
assert changed and all(daily_target(fresh, d) is not None for d in range(100))
print(f"rewards: {len(RULES)} rules = the pre-M05.3 amounts (thresholds {BEFORE_THRESHOLDS}); once-ever {sorted(ONCE_EVER)}: paid once, "
      f"never respawns or pays again over {relaunches} relaunches/reloads; repeatables unchanged; daily skips it ({changed} of 10000 days moved)")
print("ALL REWARD SIMULATIONS PASSED")
