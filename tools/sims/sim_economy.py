#!/usr/bin/env python3
"""Economy simulation (M05.6) — the CURRENT economy, modelled from the
repository. Not the engine; invents no coin economics (O-01 open).
1. Source register: every Wriksha Points earning path, derived from the code
   (the pay sites, their guards, what is saved) and the data (reward rules,
   discovery respawns, crop timings, plots). Each source is classified —
   once-ever / per-session bounded / per-day / repeatable / rate-limited
   repeatable — with its amount and, where repeatable, its natural rate.
   The classification is compared with a deliberate REGRESSION SNAPSHOT
   (not configuration): a missing or new source, a changed amount or a
   changed classification fails.
2. Bounds: once-ever and per-session sources have a finite lifetime total
   (computed); unbounded sources are EXPECTED and only quantified:
   natural respawn farming, the relaunch-respawn loop, the daily clock loop,
   harvest throughput (an upper bound from growth timers, plots and seeds).
3. Save lifecycle: GameState's actual autosave triggers (read from the
   code) decide which payments are saved at once and which wait; 3,000
   random players with random crashes and relaunches: nothing is paid twice,
   a crash loses a payment together with its claim, never one without the
   other.
4. Coins: zero earn sources, zero spend sources — no Wallet.credit/debit
   caller, the Wallet touched only by SaveManager's save/load — and in every
   modelled loop the balance stays 0 with an empty ledger.
"""
import glob, itertools, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _vals(f): return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M)}
def _code(s): return "\n".join(l.split("#")[0] for l in s.splitlines() if not l.lstrip().startswith("##"))
def _funcs(s): return {m.group(1): _code(m.group(0)) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", s, re.M | re.S)}
SCRIPTS = {os.path.relpath(p, REPO): _code(open(p, encoding="utf-8").read()) for p in glob.glob(os.path.join(REPO, "scripts", "**", "*.gd"), recursive=True)}
F = {f: _funcs(open(os.path.join(REPO, f), encoding="utf-8").read()) for f in SCRIPTS}
EX, FM, DM, DD, FP, GS, SM = ("scripts/autoload/exploration_manager.gd", "scripts/autoload/farm_manager.gd", "scripts/autoload/discovery_manager.gd",
                              "scripts/autoload/daily_discovery_manager.gd", "scripts/farming/farm_plot.gd", "scripts/autoload/game_state.gd",
                              "scripts/autoload/save_manager.gd")

# ---------------------------------------------------------------- data (the source of truth)
RULES = {v["id"]: (int(v.get("points", "0")), int(v.get("threshold", "0"))) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")))}
DISC = {v["id"]: (int(v["points_value"]), float(v.get("respawn_seconds", "60"))) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "discoveries", "*.tres")))}
CROPS = {v["crop_id"]: {"points": int(v["points_value"]), "starting": int(v.get("starting_seeds", "1")), "found": v.get("found_seed_source", "none") != "none",
                        "cycle": float(v.get("seed_duration", "0")) + float(v.get("sprout_duration", "14")) + float(v.get("growing_duration", "24"))}
         for v in map(_vals, glob.glob(os.path.join(REPO, "data", "crops", "*.tres")))}
PLACES = {v["id"]: v.get("secret") == "true" for v in map(_vals, glob.glob(os.path.join(REPO, "data", "places", "*.tres")))}
MEADOW = _src("scenes", "world", "Meadow.tscn")
PLOTS = len(re.findall(r'^plot_id = "', MEADOW, re.M))
SCALE = [float(x) for x in re.search(r"^const QUALITY_POINT_SCALE := \[([^\]]*)\]", _src("scripts", "autoload", "farm_manager.gd"), re.M).group(1).split(",")]
def harvest_points(crop, q): return max(int(CROPS[crop]["points"] * SCALE[q] + 0.5), 1)
MILESTONE_RULES = {re.search(rf'^const {c} := "(\w+)"', _src("scripts", "autoload", "farm_manager.gd"), re.M).group(1)
                   for c in re.findall(r"_rewards\.points\(([A-Z_]+)\)", SCRIPTS[FM])}

# ---------------------------------------------------------------- 1. the pay sites (static)
SITES = {}
for f, funcs in F.items():
    for fn, body in funcs.items():
        n = body.count("PointsManager.add_points(")
        if n: SITES[(f, fn)] = n
REGISTER_SITES = {  # source -> the pay site(s) that pay it
    "discovery_collection": [(DM, "discover")], "discovery_thresholds": [(EX, "_on_discovery_made")],
    "landmark": [(EX, "mark_landmark_reached")], "secret_location": [(EX, "mark_secret_location_found")],
    "all_secret_locations": [(EX, "mark_secret_location_found")], "curiosity": [(EX, "_maybe_award_curiosity_bonus")],
    "daily_discovery": [(DD, "_on_discovery_made")], "harvest": [(FP, "_run_harvest_sequence")], "farm_milestones": [(FM, "_reach")]}
expected_sites = {}
for sites in REGISTER_SITES.values():
    for s in sites: expected_sites[s] = expected_sites.get(s, 0) + 1
assert SITES == expected_sites, f"an unregistered or missing points source: {SITES} vs register {expected_sites}"

# ---------------------------------------------------------------- classification, derived from the code
exs = F[EX]; dms = F[DM]; dds = F[DD]; fms = F[FM]
saved_exploration = F[EX].get("get_save_data", "")
def once_ever(guard_fn, guard, record, saved_key):
    return guard in exs.get(guard_fn, "") and record in exs.get(guard_fn, "") and saved_key in saved_exploration \
        and exs[guard_fn].find(guard) < exs[guard_fn].find("PointsManager.add_points(")
CLASS = {}
CLASS["landmark"] = "once_ever" if once_ever("mark_landmark_reached", "if _reached_landmarks.has(landmark_id):\n\t\treturn", "_reached_landmarks.append(landmark_id)", '"landmarks": Array(_reached_landmarks)') else "repeatable"
CLASS["secret_location"] = "once_ever" if once_ever("mark_secret_location_found", "if _found_secret_locations.has(location_id):\n\t\treturn", "_found_secret_locations.append(location_id)", '"secrets": Array(_found_secret_locations)') else "repeatable"
CLASS["all_secret_locations"] = "once_ever" if ("and not _all_secrets_bonus_awarded:" in exs["mark_secret_location_found"] and "_all_secrets_bonus_awarded = true" in exs["mark_secret_location_found"]
                                                and '"all_secrets_bonus": _all_secrets_bonus_awarded' in saved_exploration) else "repeatable"
CLASS["curiosity"] = "once_ever" if ("if _curiosity_bonus_given:\n\t\treturn" in exs["_maybe_award_curiosity_bonus"] and "_curiosity_bonus_given = true" in exs["_maybe_award_curiosity_bonus"]
                                     and '"curiosity_bonus": _curiosity_bonus_given' in saved_exploration) else "repeatable"
thr_ok = "if _thresholds.has(_session_discovery_count) and not _awarded_thresholds.has(_session_discovery_count):" in exs["_on_discovery_made"] \
    and "DiscoveryManager.discovery_made.connect(_on_discovery_made)" in exs["_ready"] and "discovery_repeated" not in exs["_ready"] \
    and '"discovered_ids": DiscoveryManager.get_discovered_ids()' in SCRIPTS[SM]
CLASS["discovery_thresholds"] = "per_session_bounded" if thr_ok else "repeatable"
CLASS["daily_discovery"] = "per_day" if ("if is_completed_today():\n\t\treturn" in dds["_on_discovery_made"] and "completed_date = _today_string()" in dds["_on_discovery_made"]
                                         and '"completed_date": completed_date' in dds["get_save_data"]) else "repeatable"
CLASS["farm_milestones"] = "once_ever" if ("if _milestones_reached.has(milestone_id):\n\t\treturn false" in fms["_reach"] and '"milestones": Array(_milestones_reached)' in fms["get_save_data"]) else "repeatable"
plot_capture = F["scripts/farming/farm_plot.gd"].get("capture", "")
CLASS["harvest"] = "rate_limited_repeatable" if ('"stage_time_left"' in plot_capture and all(c["cycle"] > 0 for c in CROPS.values())) else "repeatable"
claimed = "definition.respawn_seconds <= 0.0 and discovered_ids.has(id)" in dms.get("is_claimed", "") and "if is_claimed(id):\n\t\treturn false" in dms["discover"] \
    and "if DiscoveryManager.is_claimed(instance.discovery_id):" in F["scripts/interactables/discovery_spawn_point.gd"]["_spawn"]
CLASS["discovery_collection"] = {d: ("once_ever" if (r <= 0 and claimed) else "repeatable") for d, (p, r) in DISC.items()}

# ---------------------------------------------------------------- REGRESSION SNAPSHOT (deliberate; not configuration)
SNAPSHOT = {
    "classes": {"landmark": "once_ever", "secret_location": "once_ever", "all_secret_locations": "once_ever", "curiosity": "once_ever",
                "discovery_thresholds": "per_session_bounded", "daily_discovery": "per_day", "farm_milestones": "once_ever",
                "harvest": "rate_limited_repeatable",
                "discovery_collection": {"ancient_seed": "once_ever", **{d: "repeatable" for d in ("blue_mushroom", "golden_leaf", "healing_herb",
                                         "hidden_herb", "meadow_flower", "river_stone", "small_mushroom", "wild_mint")}}},
    "amounts": {"landmark": 15, "secret_location": 15, "all_secret_locations": 50, "curiosity": 20, "daily_discovery": 25,
                "thresholds": {3: 20, 5: 40}, "farm_milestones": {"first_harvest": 10, "all_starter_crops": 40, "garden_complete": 30, "garden_in_bloom": 50}},
    "discoveries": {"ancient_seed": (100, 0.0), "blue_mushroom": (32, 240.0), "golden_leaf": (60, 600.0), "healing_herb": (20, 120.0), "hidden_herb": (30, 240.0),
                    "meadow_flower": (10, 60.0), "river_stone": (8, 45.0), "small_mushroom": (12, 60.0), "wild_mint": (15, 90.0)},
    "crops": {"wild_carrot": (12, 30.0, 2), "meadow_herb": (15, 38.0, 2), "golden_sunflower": (20, 46.0, 1), "elderbloom": (30, 56.0, 0)},
    "plots": 7, "places": {"landmarks": 4, "secrets": 4},
    "quality_scale": [0.75, 1.0, 1.5],
    "harvest": {"wild_carrot": [9, 12, 18], "meadow_herb": [11, 15, 23], "golden_sunflower": [15, 20, 30], "elderbloom": [23, 30, 45]},
}
assert CLASS == SNAPSHOT["classes"], f"a source changed classification: {CLASS}"
now_amounts = {"landmark": RULES["landmark"][0], "secret_location": RULES["secret_location"][0], "all_secret_locations": RULES["all_secret_locations"][0],
               "curiosity": RULES["curiosity"][0], "daily_discovery": RULES["daily_discovery"][0],
               "thresholds": {t: p for p, t in RULES.values() if t}, "farm_milestones": {m: RULES[m][0] for m in sorted(MILESTONE_RULES)}}
assert now_amounts == SNAPSHOT["amounts"], f"an audited reward amount changed: {now_amounts}"
assert set(RULES) == {"landmark", "secret_location", "all_secret_locations", "curiosity", "daily_discovery", "discoveries_3", "discoveries_5"} | MILESTONE_RULES
assert DISC == SNAPSHOT["discoveries"], f"discovery points/respawn changed: {DISC}"
assert {c: (v["points"], v["cycle"], v["starting"]) for c, v in CROPS.items()} == SNAPSHOT["crops"]
assert SCALE == SNAPSHOT["quality_scale"] and {c: [harvest_points(c, q) for q in range(len(SCALE))] for c in CROPS} == SNAPSHOT["harvest"], "harvest points changed"
assert PLOTS == SNAPSHOT["plots"] and {"landmarks": sum(not s for s in PLACES.values()), "secrets": sum(PLACES.values())} == SNAPSHOT["places"]

# ---------------------------------------------------------------- 2. bounds and abuse loops
LANDMARKS, SECRETS = [p for p, s in PLACES.items() if not s], [p for p, s in PLACES.items() if s]
THRESH = {t: p for p, t in RULES.values() if t}
def max_threshold_total(n_first_ever):
    """Best split of every first-ever discovery into sessions (thresholds reset per session)."""
    best = [0] * (n_first_ever + 1)
    for n in range(1, n_first_ever + 1):
        best[n] = max(best[n - k] + sum(p for t, p in THRESH.items() if t <= k) for k in range(1, n + 1))
    return best[n_first_ever]
BOUNDED = {"landmark": len(LANDMARKS) * RULES["landmark"][0], "secret_location": len(SECRETS) * RULES["secret_location"][0],
           "all_secret_locations": RULES["all_secret_locations"][0], "curiosity": RULES["curiosity"][0],
           "farm_milestones": sum(RULES[m][0] for m in MILESTONE_RULES), "discovery_thresholds": max_threshold_total(len(DISC)),
           "once_ever_discoveries": sum(p for d, (p, r) in DISC.items() if CLASS["discovery_collection"][d] == "once_ever")}
REPEATABLE = {d: p for d, (p, r) in DISC.items() if CLASS["discovery_collection"][d] == "repeatable"}
natural = {d: DISC[d][0] * 3600.0 / DISC[d][1] for d in REPEATABLE}                 # points/hour, ignoring walking time
relaunch_loop = (sum(REPEATABLE.values()), len([d for d in REPEATABLE]))            # points, collectibles per relaunch (all respawn at launch)
seed_cap = {c: v["starting"] + (1 if v["found"] else 0) for c, v in CROPS.items()}   # the seed invariant's ceiling per crop
rate = {c: harvest_points(c, len(SCALE) - 1) / CROPS[c]["cycle"] for c in CROPS}     # best-quality points per second of growth
plots_left, harvest_per_hour = PLOTS, 0.0
for c in sorted(CROPS, key=lambda c: -rate[c]):
    use = min(plots_left, seed_cap[c]); plots_left -= use; harvest_per_hour += use * rate[c] * 3600
# the model's own checks of the bounds
assert all(isinstance(v, int) and v >= 0 for v in BOUNDED.values()), "bounded sources have a finite lifetime total"
assert BOUNDED["discovery_thresholds"] == max_threshold_total(len(DISC)) < sum(THRESH.values()) * len(DISC), "thresholds are bounded by first-ever discoveries"
assert plots_left >= 0 and sum(min(seed_cap[c], PLOTS) for c in CROPS) >= 1, "harvest throughput is limited by plots and the seed invariant"

# ---------------------------------------------------------------- 3. save lifecycle (from GameState's code)
gs_ready = F[GS]["_ready"]
TRIGGERS = set(re.findall(r"(\w+\.\w+)\.connect\(", gs_ready))
assert TRIGGERS == {"DiscoveryManager.discovery_made", "FarmManager.crop_planted", "FarmManager.crop_harvested", "FarmManager.seed_found",
                    "FarmManager.milestone_reached", "InputManager.movement_mode_changed"}, f"autosave triggers changed: {TRIGGERS}"
assert "NOTIFICATION_APPLICATION_PAUSED" in F[GS]["_notification"] and "NOTIFICATION_WM_CLOSE_REQUEST" in F[GS]["_notification"]
AL = re.findall(r'^(\w+)="\*?res://', _src("project.godot").split("[autoload]", 1)[1].split("\n[", 1)[0], re.M)
assert all(AL.index(x) < AL.index("GameState") for x in ("DailyDiscoveryManager", "Inventory", "ExplorationManager", "FarmManager")), \
    "everything paid on a first discovery is in before its autosave (handlers connect in autoload order)"
# which payment is saved at once, which waits for the next save
AUTOSAVED = {"first_discovery": "DiscoveryManager.discovery_made" in TRIGGERS, "threshold": "DiscoveryManager.discovery_made" in TRIGGERS,
             "harvest": "FarmManager.crop_harvested" in TRIGGERS, "milestone": "FarmManager.milestone_reached" in TRIGGERS,
             "repeat_discovery": False, "landmark": False, "secret": False, "daily_on_repeat": False}
assert AUTOSAVED == {"first_discovery": True, "threshold": True, "harvest": True, "milestone": True,
                     "repeat_discovery": False, "landmark": False, "secret": False, "daily_on_repeat": False}

class Game:
    """Points + the claims that make rewards once-ever/per-day + the wallet; a save is one JSON of all of it."""
    def __init__(g, save=None):
        d = json.loads(save) if save else {}
        g.points, g.found = d.get("points", 0), list(d.get("found", []))
        g.places, g.milestones, g.daily = list(d.get("places", [])), list(d.get("milestones", [])), d.get("daily", "")
        g.all_secrets, g.curiosity = d.get("all_secrets", False), d.get("curiosity", False)
        g.wallet = d.get("wallet", {"ledger": []}); g.session_first, g.thresholds = 0, []
        g.log = list(d.get("log", []))                     # what was paid, for auditing duplicates
    def save(g): return json.dumps({"points": g.points, "found": g.found, "places": g.places, "milestones": g.milestones, "daily": g.daily,
                                    "all_secrets": g.all_secrets, "curiosity": g.curiosity, "wallet": g.wallet, "log": g.log})
    def pay(g, source, key, n): g.points += n; g.log.append([source, key, n])
    def collect(g, d, day):
        p, r = DISC[d]
        if r <= 0 and d in g.found: return False                                   # once-ever: claimed
        first = d not in g.found
        if first: g.found.append(d)
        g.pay("discovery", d, p)
        if g.daily != day and d == sorted(DISC)[day % len(DISC)]: g.daily = day; g.pay("daily", day, RULES["daily_discovery"][0])
        if first:
            g.session_first += 1
            if g.session_first in THRESH and g.session_first not in g.thresholds:
                g.thresholds.append(g.session_first); g.pay("threshold", g.session_first, THRESH[g.session_first])
        return first                                                                # autosave iff first-ever
    def reach(g, p):
        if p in g.places: return False
        g.places.append(p)
        if PLACES[p]:
            g.pay("secret", p, RULES["secret_location"][0])
            if not g.curiosity and rnd.random() < 0.3: g.curiosity = True; g.pay("curiosity", p, RULES["curiosity"][0])
            if not g.all_secrets and all(s in g.places for s in SECRETS): g.all_secrets = True; g.pay("all_secrets", "", RULES["all_secret_locations"][0])
        else: g.pay("landmark", p, RULES["landmark"][0])
        return False                                                                # not autosaved
    def harvest(g, c, q):
        g.pay("harvest", c, harvest_points(c, q))
        for m in sorted(MILESTONE_RULES):
            if m not in g.milestones and rnd.random() < 0.1: g.milestones.append(m); g.pay("milestone", m, RULES[m][0])
        return True                                                                 # crop_harvested autosaves
def check(g):
    once = [(s, k) for s, k, n in g.log if s in ("landmark", "secret", "all_secrets", "curiosity", "milestone")] + \
           [("discovery", k) for s, k, n in g.log if s == "discovery" and DISC[k][1] <= 0]
    assert len(once) == len(set(once)), f"a once-ever reward paid twice: {once}"
    days = [k for s, k, n in g.log if s == "daily"]; assert len(days) == len(set(days)), "a day's bonus paid twice"
    assert g.points == sum(n for _, _, n in g.log), "points = exactly what was paid"
    claims = {("landmark", p) for p in g.places if not PLACES[p]} | {("secret", p) for p in g.places if PLACES[p]} | {("milestone", m) for m in g.milestones}
    assert claims == {(s, k) for s, k, n in g.log if s in ("landmark", "secret", "milestone")}, "every paid claim is recorded and every claim was paid"
    assert g.wallet == {"ledger": []}, "the wallet stays empty"
rnd = random.Random(56); crashes = 0; lost_together = 0
for _ in range(3000):
    disk, g, day = None, Game(), rnd.randint(0, 99)
    for _ in range(rnd.randint(1, 8)):                                              # launches
        for _ in range(rnd.randint(0, 40)):
            r = rnd.random()
            if r < 0.45:
                d = rnd.choice(sorted(DISC)); was_new = d not in g.found and not (DISC[d][1] <= 0 and d in g.found)
                saved_now = g.collect(d, day)
                assert saved_now == (AUTOSAVED["first_discovery"] if was_new else AUTOSAVED["repeat_discovery"]), "model vs GameState triggers"
            elif r < 0.65:
                p = rnd.choice(sorted(PLACES)); saved_now = g.reach(p)
                assert saved_now == AUTOSAVED["secret" if PLACES[p] else "landmark"], "model vs GameState triggers"
            elif r < 0.9:
                saved_now = g.harvest(rnd.choice(sorted(CROPS)), rnd.randrange(len(SCALE)))
                assert saved_now == AUTOSAVED["harvest"], "model vs GameState triggers"
            else: day += 1; saved_now = False
            if saved_now: disk = g.save()
            check(g)
        if rnd.random() < 0.3:                                                      # crash: no pause save
            crashes += 1; before = g.points
            g = Game(disk); check(g); lost_together += g.points < before
        else:
            disk = g.save(); g = Game(disk); check(g)                                # pause/close save, relaunch
        if disk: assert Game(disk).save() == Game(Game(disk).save()).save(), "reload is stable"

# ---------------------------------------------------------------- 4. coins: zero sources, zero sinks
callers = sorted((f, m.group(1)) for f, s in SCRIPTS.items() for m in re.finditer(r"\bWallet\.(credit|debit)\(", s))
assert callers == [], f"a coin source or sink appeared: {callers}"
wallet_users = sorted({f for f, s in SCRIPTS.items() if re.search(r"\bWallet\.", s)})
assert wallet_users == [SM] and sorted(set(re.findall(r"Wallet\.(\w+)\(", SCRIPTS[SM]))) == ["apply_save_data", "get_save_data"]
wl = F["scripts/autoload/wallet.gd"]
assert set(wl) == {"get_balance", "can_afford", "get_ledger", "credit", "debit", "get_save_data", "apply_save_data", "_record", "_parse_entry"}
assert "_ready" not in wl and "_process" not in wl, "the Wallet does nothing on its own"
assert re.search(r"var _balance: int = 0", SCRIPTS["scripts/autoload/wallet.gd"]) and re.search(r"var _ledger: Array\[Dictionary\] = \[\]", SCRIPTS["scripts/autoload/wallet.gd"])

print("economy register:")
for s in sorted(REGISTER_SITES):
    c = CLASS[s] if s != "discovery_collection" else "repeatable x8 + once-ever x1 (ancient_seed)"
    print(f"  {s:22} {c}")
print(f"bounded lifetime totals: {BOUNDED} (sum {sum(BOUNDED.values())})")
print(f"abuse loops (quantified, expected — caps are O-01): relaunch loop {relaunch_loop[0]} points + {relaunch_loop[1]} collectibles per relaunch; "
      f"natural respawn farming {sum(natural.values()):.0f} points/hour (walking ignored); daily clock loop {RULES['daily_discovery'][0]} per clock change; "
      f"harvest upper bound {harvest_per_hour:.0f} points/hour ({PLOTS} plots, seed caps {seed_cap})")
print(f"save lifecycle: autosaved {sorted(k for k, v in AUTOSAVED.items() if v)}, waits {sorted(k for k, v in AUTOSAVED.items() if not v)}; "
      f"3000 players, {crashes} crashes ({lost_together} lost unsaved earnings together with their claims), no duplicate payment")
print("coins: 0 earn sources, 0 spend sources, balance 0, empty ledger")
print("ALL ECONOMY SIMULATIONS PASSED")
