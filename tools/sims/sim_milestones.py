#!/usr/bin/env python3
"""Farm milestones through progression hooks (M06.4, D-27) — a model, not the engine.
1. Read from the project: the registered milestones (FarmManager.get_milestones():
   its constants + "grown:<starter crop>"), the reward rules (data/rewards/), the
   scene hooks (plots' unlock_on_milestone, MilestoneReveals' milestone_id), and
   _reach()'s own body (its order: once-ever guard, record, the id's reward, pay,
   unlocks, announce).
2. One reward path: every milestone's reward is the rule named by its id (none =
   0); the resulting table equals the amounts the call sites paid before M06.4
   (a deliberate REGRESSION SNAPSHOT — update only with a deliberate reward
   change); a rule added for an unrewarded milestone (model-only) would pay it
   with no code change.
3. Hooks: every scene hook and every farm reward rule names a registered
   milestone; every registered milestone is reachable from a game event.
4. 3,000 random players reaching milestones across save/reload (farm.milestones):
   each milestone recorded, paid and announced at most once ever; points = the
   table's sum over what was reached; a plot is unlocked exactly when its
   milestone is; the announcement (GameState's autosave) comes after the payment
   and the unlocks, so a save on it always holds both. Deterministic.
"""
import glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _code(s): return "\n".join(l.split("#")[0].rstrip() for l in s.splitlines() if not l.lstrip().startswith("##"))
def _funcs(s): return {m.group(1): _code(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", s, re.M | re.S)}

# ---------------------------------------------------------------- 1. read from the project
FM = _src("scripts", "autoload", "farm_manager.gd")
F = _funcs(FM)
def const(name): return re.search(rf'^const {name} := "([^"]*)"', FM, re.M).group(1)
CONSTS = re.findall(r"_milestone_row\(([A-Z_]+),", F["get_milestones"])
STARTERS, CROPS = [], []
for f in sorted(glob.glob(os.path.join(REPO, "data", "crops", "*.tres"))):
    t = open(f, encoding="utf-8").read(); cid = re.search(r'crop_id = "([^"]+)"', t).group(1); CROPS.append(cid)
    st = re.search(r"^starting_seeds = (\d+)", t, re.M)
    if int(st.group(1) if st else 1) > 0: STARTERS.append(cid)
assert "_milestone_row(CROP_GROWN_PREFIX + crop.crop_id," in F["get_milestones"]
REGISTERED = [const(c) for c in CONSTS] + [const("CROP_GROWN_PREFIX") + c for c in sorted(STARTERS)]
assert len(REGISTERED) == len(set(REGISTERED)), "each milestone registered once"
RULES = {}
for f in glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")):
    v = dict(re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M))
    RULES[v["id"].strip('"')] = int(v.get("points", "0"))
HOOKS = []
for scene in glob.glob(os.path.join(REPO, "scenes", "**", "*.tscn"), recursive=True):
    txt = open(scene, encoding="utf-8").read()
    for m in re.finditer(r'^\[node name="(\w+)"[^\]]*\]\n(.*?)(?=^\[|\Z)', txt, re.M | re.S):
        for kind, hook in re.findall(r'^(unlock_on_milestone|milestone_id) = "([^"]*)"$', m.group(2), re.M):
            pid = re.search(r'^plot_id = "([^"]*)"', m.group(2), re.M)
            HOOKS.append((kind, hook, pid.group(1) if pid else m.group(1)))
REACH = [l.strip() for l in F["_reach"].splitlines()[1:] if l.strip()]
def at(line): return REACH.index(line)
assert F["_reach"].startswith("func _reach(milestone_id: String, message: String) -> bool:")
order = [at("if _milestones_reached.has(milestone_id):"), at("_milestones_reached.append(milestone_id)"),
         at("var bonus_points := _rewards.points(milestone_id) if _rewards.has(milestone_id) else 0"),
         at("PointsManager.add_points(bonus_points)"), at("if _unlock_plots_for(milestone_id) > 0:"),
         at("milestone_reached.emit(milestone_id, message, bonus_points)")]
assert order == sorted(order), "guard → record → the id's reward → pay → unlock → announce"
CALLS = [c.split(",")[0].strip() for fn, b in F.items() if fn != "_reach" for c in re.findall(r"\b_reach\((.*)\)", b)]

# ---------------------------------------------------------------- 2. one reward path
def reward(mid, rules): return rules.get(mid, 0)                 # _reach: the id's rule, else nothing
TABLE = {m: reward(m, RULES) for m in REGISTERED}
SNAPSHOT_BEFORE_M064 = {"first_seed": 0, "first_harvest": 10, "first_fine": 0, "all_starter_crops": 40, "garden_complete": 30,
                        "garden_in_bloom": 50, **{f"grown:{c}": 0 for c in ("golden_sunflower", "meadow_herb", "wild_carrot")}}
assert TABLE == SNAPSHOT_BEFORE_M064, f"a milestone's reward changed: {TABLE}"
assert {r for r in RULES if r in TABLE} == {m for m, p in TABLE.items() if p}, "a farm milestone pays exactly when a rule names it"
extra = dict(RULES, first_fine=15)                                # model-only: data alone makes a milestone pay
assert reward("first_fine", extra) == 15 and reward("first_seed", extra) == 0

# ---------------------------------------------------------------- 3. hooks
assert HOOKS, "the world has milestone hooks"
assert all(h in REGISTERED for _, h, _ in HOOKS), f"a hook names an unregistered milestone: {HOOKS}"
assert {c for c in CALLS if c != "CROP_GROWN_PREFIX + crop_definition.crop_id"} == set(CONSTS), "every registered milestone is reachable"
assert "CROP_GROWN_PREFIX + crop_definition.crop_id" in CALLS
assert sorted(fn for fn, b in F.items() if fn != "_reach" and "_reach(" in b) == ["choose_seed", "notify_crop_harvested", "notify_crop_ready"], \
    "milestones come only from game events"
UNLOCKS = {pid: h for kind, h, pid in HOOKS if kind == "unlock_on_milestone"}

# ---------------------------------------------------------------- 4. once ever, across saves
class Farm:
    def __init__(f, saved=None):
        f.reached = list(json.loads(saved)["milestones"]) if saved else []
        f.unlocked = {p: (m in f.reached) for p, m in UNLOCKS.items()}   # derived on load, never saved
        f.points, f.announced, f.events, f.disk = 0, [], [], saved
    def reach(f, mid):                                            # port of _reach, in its checked order
        if mid in f.reached: return False
        f.reached.append(mid)
        bonus = reward(mid, RULES)
        if bonus > 0: f.points += bonus; f.events.append(("pay", mid))
        for p, m in UNLOCKS.items():
            if m == mid and not f.unlocked[p]: f.unlocked[p] = True; f.events.append(("unlock", p))
        f.events.append(("announce", mid)); f.announced.append(mid)
        f.disk = json.dumps({"milestones": f.reached, "points_so_far": f.points})   # GameState saves on the announcement
        return True
rnd = random.Random(64); total_reached = 0
for _ in range(3000):
    f, paid, ever = Farm(), 0, []
    for _launch in range(rnd.randint(1, 6)):
        for _step in range(rnd.randint(0, 12)):
            mid = rnd.choice(REGISTERED)
            before = f.points
            if f.reach(mid):
                paid += f.points - before; ever.append(mid)
                ev = [e for e in f.events if e[1] == mid or (e[0] == "unlock" and UNLOCKS.get(e[1]) == mid)]
                assert ev[-1] == ("announce", mid), "the announcement comes last"
                assert json.loads(f.disk)["points_so_far"] == f.points, "the save on the announcement holds the payment"
            else:
                assert f.points == before, "a milestone already reached pays nothing"
        saved = f.disk
        f = Farm(saved) if saved else Farm()                        # relaunch
        assert all(f.unlocked[p] == (m in f.reached) for p, m in UNLOCKS.items()), "a plot is open exactly when its milestone is"
    assert len(ever) == len(set(ever)), "each milestone reached once ever"
    assert paid == sum(TABLE[m] for m in ever), "points = the table over what was reached"
    total_reached += len(ever)

print(f"milestones: {len(REGISTERED)} registered ({', '.join(REGISTERED)}); rewards by id from data {({m: p for m, p in TABLE.items() if p})} = pre-M06.4 amounts; "
      f"{len(HOOKS)} scene hooks all registered; reached only from planting/ripening/harvest; 3000 players ({total_reached} milestones) "
      f"each paid/announced once ever across relaunches, announcement after payment and unlocks")
print("ALL MILESTONE SIMULATIONS PASSED")
