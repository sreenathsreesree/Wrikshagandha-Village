#!/usr/bin/env python3
"""One progression path (M13.1) — the real GDScript executed (gd_port): ProgressionRewards.reach
(scripts/rewards/progression_rewards.gd), FarmManager._reach and ExplorationManager's once-ever rewards and save
functions, each beside a frozen copy of its pre-M13.1 code, on the project's place, reward and milestone data.
1. The shared path: an id not yet in the record is recorded, then the rule's points are paid and returned (rule "" =
   nothing; an unknown rule pays 0 with RewardRules' warning); an id already recorded returns -1 and changes nothing.
   Warnings are logged with everything else, so part 2 compares them too: a farm milestone without a rule stays silent,
   and with any one of the four exploration rules missing from the data the new code warns exactly as the old did.
2. Behaviour unchanged: 2,000 random players — landmarks and secret places reached (new, repeated, unknown, of the
   other kind), paired discoveries made (the curiosity bonus), farm milestones reached, relaunches through Godot's
   JSON, and (for half of them) malformed saved exploration states — get, event for event, exactly the points,
   signals (names and arguments, in order), _reach results, records and saved sections the pre-M13.1 code gave.
3. Once ever, from one place: over the relaunch-only players each farm milestone, landmark, secret place, the
   curiosity bonus and "every secret found" is announced at most once, and the points equal the amounts announced
   (for the ids the game uses: a load keeps only places of the right kind, so an unknown id, or a landmark call with
   a secret's id, can be announced again after a relaunch — exactly as before M13.1, shown by part 2);
   for each of the five kinds the id is already in its record when the payment is made (so the save GameState makes
   on the announcement holds both).
4. Session rewards stay outside: D-21's discovery-count thresholds still pay in ExplorationManager._on_discovery_made,
   not through the shared path, and only the five once-ever rewards reach it.
Broken designs, applied to the real sources, are shown to break: the guard dropped, the record written after the
payment, a double payment, -1 never returned, a repeat landmark announced, milestones without a reward no longer
announced, the curiosity bonus recorded in the wrong list, "every secret found" announced when already paid, the
saved flags swapped, a relaunch forgetting the curiosity bonus or "every secret found", the every-secret flag loaded
from the curiosity key, a landmark paying another rule, the thresholds routed through the path, the missing-rule
warning suppressed, farm milestones without a rule warning.
"""
import glob, json, os, random, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd_port
from gd_port import translate, godot_json

REPO = gd_port.REPO
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _vals(f): return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M)}

# ---------------------------------------------------------------- the engine pieces these scripts use
TYPE_BOOL, TYPE_STRING, TYPE_DICTIONARY, TYPE_ARRAY = 1, 4, 27, 28
class GArray(list):
    def has(s, v): return v in s
    def size(s): return len(s)
class GDict(dict):
    def has(s, k): return k in s
def typeof(v):
    if isinstance(v, bool): return TYPE_BOOL
    if isinstance(v, int): return gd_port.TYPE_INT
    if isinstance(v, float): return gd_port.TYPE_FLOAT
    if isinstance(v, str): return TYPE_STRING
    if isinstance(v, dict): return TYPE_DICTIONARY
    if isinstance(v, list): return TYPE_ARRAY
    return 0
gd_port.HELPERS.update(GArray=GArray, Array=lambda a=None: GArray(a or []), str=str, _typeof=typeof,
                       TYPE_BOOL=TYPE_BOOL, TYPE_STRING=TYPE_STRING, TYPE_ARRAY=TYPE_ARRAY, TYPE_DICTIONARY=TYPE_DICTIONARY)
def prep(src):
    src = re.sub(r"^(\tfor \w+): \w+ in ", r"\1 in ", src, flags=re.M)          # typed loop variables
    return re.sub(r"(?<![\w\]])\[\]", "GArray()", src)                           # empty arrays are Godot Arrays

class Ledger:
    """PointsManager (add_points(0) is a no-op, as in points_manager.gd), FarmManager and DiscoveryManager as these
    scripts reach them; every effect and announcement in one ordered log."""
    def __init__(l): l.points, l.log, l.discovered, l.on_pay = 0, [], set(), None
    def add_points(l, n):
        if n == 0: return
        if l.on_pay: l.on_pay(n)
        l.points += n; l.log.append(("points", n))
    def notify_place_reached(l, pid): l.log.append(("farm_place", pid))
    def is_discovered(l, did): return did in l.discovered
class Rewards:  # RewardRules over data/rewards: has / points — an unknown id pays 0 with a warning, logged
    def __init__(r, table, log=None): r.table, r.log = table, log
    def has(r, rid): return rid in r.table
    def points(r, rid):
        if rid not in r.table and r.log is not None: r.log.append(("warning: no reward", rid))
        return r.table.get(rid, 0)
class Place:
    def __init__(p, **kw): p.__dict__.update(kw)

# ---------------------------------------------------------------- the project's data
RULES = {v["id"]: int(v.get("points", "0")) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")))}
PLACES = sorted((Place(id=v["id"], secret=v.get("secret") == "true", order=int(v.get("order", "0")), curiosity_discovery_id=v.get("curiosity_discovery_id", ""))
                 for v in map(_vals, glob.glob(os.path.join(REPO, "data", "places", "*.tres")))), key=lambda p: p.order)
SECRETS, LANDMARKS = [p.id for p in PLACES if p.secret], [p.id for p in PLACES if not p.secret]
PAIRED = sorted({p.curiosity_discovery_id for p in PLACES if p.curiosity_discovery_id})
FM_SRC = _src("scripts", "autoload", "farm_manager.gd")
GM = re.search(r"^func get_milestones\(.*?(?=^func )", FM_SRC, re.M | re.S).group(0)
MILESTONES = [re.search(rf'^const {c} := "(\w+)"', FM_SRC, re.M).group(1) for c in re.findall(r"_milestone_row\(([A-Z_]+),", GM)]
MILESTONES += ["grown:" + v["crop_id"] for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "crops", "*.tres")))) if int(v.get("starting_seeds", "1")) > 0]
assert re.search(r"func add_points\(amount: int\) -> void:\s*if amount == 0:\s*return", _src("scripts", "autoload", "points_manager.gd")), "add_points(0) is a no-op"
assert SECRETS and LANDMARKS and PAIRED and len(MILESTONES) >= 5

# ---------------------------------------------------------------- the pre-M13.1 code, frozen (from 766ca6f / de0b1b1)
OLD_EX = """extends Node
signal landmark_reached(landmark_id: String, bonus_points: int)
signal secret_location_found(location_id: String, bonus_points: int)
signal all_secret_locations_found(bonus_points: int)
signal curiosity_bonus_awarded(location_id: String, bonus_points: int)
var _places: Array[PlaceDefinition] = []
var _rewards: RewardRules
var _secret_place_count: int = 0
var _reached_landmarks: Array[String] = []
var _found_secret_locations: Array[String] = []
var _all_secrets_bonus_awarded: bool = false
var _curiosity_bonus_given: bool = false

func mark_landmark_reached(landmark_id: String) -> void:
	if _reached_landmarks.has(landmark_id):
		return
	_reached_landmarks.append(landmark_id)
	var bonus := _rewards.points("landmark")
	PointsManager.add_points(bonus)
	landmark_reached.emit(landmark_id, bonus)
	FarmManager.notify_place_reached(landmark_id)

func mark_secret_location_found(location_id: String) -> void:
	if _found_secret_locations.has(location_id):
		return
	_found_secret_locations.append(location_id)
	var bonus := _rewards.points("secret_location")
	PointsManager.add_points(bonus)
	secret_location_found.emit(location_id, bonus)
	FarmManager.notify_place_reached(location_id)

	_maybe_award_curiosity_bonus(location_id)

	if _secret_place_count > 0 and _found_secret_locations.size() >= _secret_place_count and not _all_secrets_bonus_awarded:
		_all_secrets_bonus_awarded = true
		var all_bonus := _rewards.points("all_secret_locations")
		PointsManager.add_points(all_bonus)
		all_secret_locations_found.emit(all_bonus)

func _maybe_award_curiosity_bonus(location_id: String) -> void:
	if _curiosity_bonus_given:
		return
	var place := _find_place(location_id)
	var paired_discovery_id := place.curiosity_discovery_id if place else ""
	if paired_discovery_id == "" or DiscoveryManager.is_discovered(paired_discovery_id):
		return
	_curiosity_bonus_given = true
	var bonus := _rewards.points("curiosity")
	PointsManager.add_points(bonus)
	curiosity_bonus_awarded.emit(location_id, bonus)

func get_save_data() -> Dictionary:
	return {
		"landmarks": Array(_reached_landmarks),
		"secrets": Array(_found_secret_locations),
		"all_secrets_bonus": _all_secrets_bonus_awarded,
		"curiosity_bonus": _curiosity_bonus_given,
	}

func apply_save_data(data: Dictionary) -> void:
	_reached_landmarks.clear()
	_found_secret_locations.clear()
	_restore_places(data.get("landmarks", []), false, _reached_landmarks)
	_restore_places(data.get("secrets", []), true, _found_secret_locations)
	_curiosity_bonus_given = _was_paid(data, "curiosity_bonus")
	_all_secrets_bonus_awarded = _was_paid(data, "all_secrets_bonus")

func _restore_places(saved: Variant, secret: bool, into: Array[String]) -> void:
	if typeof(saved) != TYPE_ARRAY:
		push_warning("ExplorationManager: saved places are not a list; ignored")
		return
	for place_id: Variant in saved:
		var place: PlaceDefinition = null
		if typeof(place_id) == TYPE_STRING:
			place = _find_place(place_id)
		if place == null or place.secret != secret or into.has(place.id):
			push_warning("ExplorationManager: ignoring saved place %s" % str(place_id))
			continue
		into.append(place.id)

func _was_paid(data: Dictionary, key: String) -> bool:
	if not data.has(key):
		return false
	var value: Variant = data[key]
	return value if typeof(value) == TYPE_BOOL else true

func _find_place(place_id: String) -> PlaceDefinition:
	for place in _places:
		if place.id == place_id:
			return place
	return null
"""
OLD_REACH = """
func _reach(milestone_id: String, message: String) -> bool:
	if _milestones_reached.has(milestone_id):
		return false
	_milestones_reached.append(milestone_id)
	var bonus_points := _rewards.points(milestone_id) if _rewards.has(milestone_id) else 0
	if bonus_points > 0:
		PointsManager.add_points(bonus_points)
	if _unlock_plots_for(milestone_id) > 0:
		message += " There's room to grow a little more."
	milestone_reached.emit(milestone_id, message, bonus_points)
	return true
"""
FARM_HEAD = """extends Node
signal milestone_reached(milestone_id: String, message: String, bonus_points: int)
var _milestones_reached: Array[String] = []
var _rewards: RewardRules

func _unlock_plots_for(milestone_id: String) -> int:
	return 0
"""
EX_FUNCS = ["mark_landmark_reached", "mark_secret_location_found", "_maybe_award_curiosity_bonus", "get_save_data", "apply_save_data",
            "_restore_places", "_was_paid", "_find_place"]

def sources():
    return {"pr": _src("scripts", "rewards", "progression_rewards.gd"), "ex": _src("scripts", "autoload", "exploration_manager.gd"), "fm": FM_SRC}

class Sys:  # what one system's scripts reach: its ledger and its shared path
    def __init__(s): s.ledger, s.pr = Ledger(), None
SYS = {"old": Sys(), "new": Sys()}
gd_port.HELPERS["SYS_OLD"], gd_port.HELPERS["SYS_NEW"] = SYS["old"], SYS["new"]

def build(s):
    kit = {}
    for tag in ("old", "new"):
        ext = {n: f"SYS_{tag.upper()}.ledger" for n in ("PointsManager", "FarmManager", "DiscoveryManager")}
        ext["ProgressionRewards"] = f"SYS_{tag.upper()}.pr"
        if tag == "new":
            PR, _ = translate(s["pr"], "ProgressionRewards", ext, ["reach"])
            SYS[tag].pr = PR()
            EM, consts = translate(prep(s["ex"]), "ExplorationManager", ext, EX_FUNCS)
            reach = re.search(r"^func _reach\(.*?(?=^func |\Z)", s["fm"], re.M | re.S).group(0)
            kit["consts"] = consts
        else:
            EM, _ = translate(prep(OLD_EX), "ExplorationManagerPreM131", ext, EX_FUNCS)
            reach = OLD_REACH
        FM, _ = translate(prep(FARM_HEAD + "\n" + reach), "FarmManagerReach", ext, ["_reach", "_unlock_plots_for"])
        kit[tag] = (EM, FM)
    kit["src"] = s
    return kit

class Player:
    """One system (old or new) for one player: an ExplorationManager and FarmManager._reach, with every announcement logged."""
    def __init__(p, kit, tag, ledger=None, table=None):
        p.kit, p.tag = kit, tag
        p.ledger = ledger or Ledger()
        SYS[tag].ledger = p.ledger
        EM, FM = kit[tag]
        p.em, p.fm = EM(), FM()
        p.table = RULES if table is None else table
        p.em._places, p.em._rewards, p.em._secret_place_count = GArray(PLACES), Rewards(p.table, p.ledger.log), len(SECRETS)
        p.fm._rewards = Rewards(p.table, p.ledger.log)
        p.unlocks = {"first_harvest", "all_starter_crops"}       # a plot waits on these (the stub's own record)
        def unlock(mid):
            if mid in p.unlocks: p.unlocks.discard(mid); return 1
            return 0
        p.fm._unlock_plots_for = unlock
        log = p.ledger.log
        p.em.landmark_reached.connect(lambda i, b: log.append(("landmark_reached", i, b)))
        p.em.secret_location_found.connect(lambda i, b: log.append(("secret_location_found", i, b)))
        p.em.curiosity_bonus_awarded.connect(lambda i, b: log.append(("curiosity_bonus_awarded", i, b)))
        p.em.all_secret_locations_found.connect(lambda b: log.append(("all_secret_locations_found", b)))
        p.fm.milestone_reached.connect(lambda m, msg, b: log.append(("milestone_reached", m, msg, b)))
    def act(p, ev):
        SYS[p.tag].ledger = p.ledger
        kind = ev[0]
        if kind == "landmark": p.em.mark_landmark_reached(ev[1])
        elif kind == "secret": p.em.mark_secret_location_found(ev[1])
        elif kind == "discover": p.ledger.discovered.add(ev[1])
        elif kind == "milestone": p.ledger.log.append(("_reach", ev[1], p.fm._reach(ev[1], "m:" + ev[1])))
    def save(p):
        SYS[p.tag].ledger = p.ledger
        return {"exploration": godot_json(p.em.get_save_data()), "milestones": list(p.fm._milestones_reached)}
    def relaunch(p, saved):
        """A new process: fresh managers; the saved sections applied as SaveManager does (through Godot's JSON)."""
        SYS[p.tag].ledger = p.ledger
        before = len(gd_port.WARNINGS)
        EM, FM = p.kit[p.tag]
        p.em, p.fm = EM(), FM()
        p.em._places, p.em._rewards, p.em._secret_place_count = GArray(PLACES), Rewards(p.table, p.ledger.log), len(SECRETS)
        p.fm._rewards = Rewards(p.table, p.ledger.log)
        p.fm._unlock_plots_for = lambda mid: 0
        log = p.ledger.log
        p.em.landmark_reached.connect(lambda i, b: log.append(("landmark_reached", i, b)))
        p.em.secret_location_found.connect(lambda i, b: log.append(("secret_location_found", i, b)))
        p.em.curiosity_bonus_awarded.connect(lambda i, b: log.append(("curiosity_bonus_awarded", i, b)))
        p.em.all_secret_locations_found.connect(lambda b: log.append(("all_secret_locations_found", b)))
        p.fm.milestone_reached.connect(lambda m, msg, b: log.append(("milestone_reached", m, msg, b)))
        p.em.apply_save_data(to_g(saved["exploration"]))
        p.fm._milestones_reached = GArray(str(x) for x in saved["milestones"])   # FarmManager.apply_save_data: String() of each
        log.append(("load_warnings", len(gd_port.WARNINGS) - before))
    def records(p):
        return (list(p.em._reached_landmarks), list(p.em._found_secret_locations), list(p.fm._milestones_reached))

def to_g(v):
    if isinstance(v, dict): return GDict({k: to_g(x) for k, x in v.items()})
    if isinstance(v, list): return GArray(to_g(x) for x in v)
    return v

def malformed(saved, rng):
    """A damaged exploration section (types and contents a hand edit or a bad write could leave)."""
    ex = dict(saved["exploration"])
    for key in rng.sample(["landmarks", "secrets", "all_secrets_bonus", "curiosity_bonus"], rng.randint(1, 3)):
        ex[key] = rng.choice(["yes", 1, None, 0.5, [], {"a": 1}, [5, None, "nowhere"] + SECRETS[:1] + LANDMARKS[:1], LANDMARKS + SECRETS, True, False])
    return {"exploration": ex, "milestones": saved["milestones"]}

TRACE = []
def install_trace(kit, fails):
    """Wrap the new system's shared path: at every payment the id must already be in the record it was given."""
    real = SYS["new"].pr.reach
    def traced(record, id, rewards, rule):
        TRACE.append((record, id))
        try: return real(record, id, rewards, rule)
        finally: TRACE.pop()
    SYS["new"].pr.reach = traced
    def on_pay(n):
        if TRACE and TRACE[-1][1] not in TRACE[-1][0]:
            fails.append(f"paid {n} for {TRACE[-1][1]} before it was recorded")
    return on_pay

def run(s, quick=False):
    fails = []
    def check(ok, what):
        if not ok: fails.append(what)
    kit = build(s)
    # 1. the shared path itself
    pr, led = SYS["new"].pr, Ledger()
    SYS["new"].ledger = led
    rec = GArray()
    rw = Rewards(RULES, led.log)
    check(pr.reach(rec, "x", rw, "landmark") == RULES["landmark"] and list(rec) == ["x"] and led.points == RULES["landmark"], "a new id is recorded and its rule paid")
    check(pr.reach(rec, "x", rw, "landmark") == -1 and list(rec) == ["x"] and led.points == RULES["landmark"], "a recorded id returns -1 and changes nothing")
    n0 = len(led.log)
    check(pr.reach(rec, "y", rw, "") == 0 and "y" in rec and len(led.log) == n0, "rule \"\" records and pays nothing, silently")
    check(pr.reach(rec, "z", rw, "no_such_rule") == 0 and "z" in rec and ("warning: no reward", "no_such_rule") in led.log, "an unknown rule pays 0 with RewardRules' warning")
    for missing in ("landmark", "secret_location", "curiosity", "all_secret_locations"):
        table = {k: v for k, v in RULES.items() if k != missing}
        logs = {}
        for tag in ("old", "new"):
            p = Player(kit, tag, table=table)
            for ev in [("landmark", LANDMARKS[0])] + [("secret", sid) for sid in SECRETS] + [("milestone", "first_seed"), ("milestone", "first_harvest")]:
                p.act(ev)
            logs[tag] = p.ledger.log
        warns = [e for e in logs["new"] if e[0] == "warning: no reward"]
        check(logs["old"] == logs["new"] and warns and all(w[1] == missing for w in warns), f"with '{missing}' missing the warnings differ from before ({warns[:3]})")
    # 2. behaviour unchanged: random players, event for event
    on_pay = install_trace(kit, fails)
    rng = random.Random(1301)
    ids_l = LANDMARKS + SECRETS[:2] + ["nowhere"]
    ids_s = SECRETS + LANDMARKS[:2] + ["nowhere"]
    players = 300 if quick else 2000
    once_players, stats = [], {"events": 0, "relaunches": 0, "announcements": 0, "points": 0}
    for i in range(players):
        damaged = i % 2 == 1
        old, new = Player(kit, "old"), Player(kit, "new")
        new.ledger.on_pay = on_pay
        events = []
        for _ in range(rng.randint(5, 40)):
            r = rng.random()
            if r < 0.25: events.append(("landmark", rng.choice(ids_l)))
            elif r < 0.5: events.append(("secret", rng.choice(ids_s)))
            elif r < 0.6: events.append(("discover", rng.choice(PAIRED)))
            elif r < 0.85: events.append(("milestone", rng.choice(MILESTONES + ["no_such_milestone"])))
            else: events.append(("relaunch", rng.random()))
        for ev in events:
            stats["events"] += 1
            if ev[0] == "relaunch":
                saved = old.save()
                check(saved == new.save(), f"player {i}: the saved sections differ ({saved} vs {new.save()})")
                if damaged: saved = malformed(saved, random.Random(int(ev[1] * 1e9)))
                old.relaunch(saved); new.relaunch(saved)
                stats["relaunches"] += 1
            else:
                old.act(ev); new.act(ev)
            if old.ledger.log != new.ledger.log or old.ledger.points != new.ledger.points or old.records() != new.records():
                fails.append(f"player {i} (damaged saves: {damaged}) differs after {ev}: {old.ledger.log[-3:]} vs {new.ledger.log[-3:]}"); break
        stats["announcements"] += sum(1 for e in new.ledger.log if e[0].endswith(("_reached", "_found", "_awarded")))
        stats["points"] += new.ledger.points
        if len(fails) > 5: break
        if not damaged: once_players.append(new)
    # 3. once ever, from one place: over the relaunch-only players, each id the game uses is announced at most once, and
    #    the points equal the amounts announced (an unknown id, or a landmark call with a secret's id, is dropped by a load
    #    and may be announced again after a relaunch — exactly as before M13.1, which part 2 shows)
    for p in once_players:
        seen, announced = {}, 0
        for e in p.ledger.log:
            kind = e[0]
            if kind == "landmark_reached" and e[1] in LANDMARKS: key = (kind, e[1])
            elif kind == "secret_location_found" and e[1] in SECRETS: key = (kind, e[1])
            elif kind == "milestone_reached" and e[1] in MILESTONES: key = (kind, e[1])
            elif kind in ("curiosity_bonus_awarded", "all_secret_locations_found"): key = (kind,)
            else:
                if kind in ("landmark_reached", "secret_location_found", "milestone_reached"): announced += e[-1]
                continue
            seen[key] = seen.get(key, 0) + 1
            announced += e[-1]
        twice = sorted(k for k, n in seen.items() if n > 1)
        if twice:
            fails.append(f"announced more than once in one player's history: {twice}"); break
        if announced != p.ledger.points:
            fails.append(f"points {p.ledger.points} differ from the amounts announced {announced}"); break
    if not quick:
        print(f"  {players} players: {stats['events']} events, {stats['relaunches']} relaunches, {stats['announcements']} announcements, "
              f"{stats['points']} points paid; {len(once_players)} relaunch-only players checked for once ever")
    # 4. session rewards stay outside the path
    ex_src = s["ex"]
    od = re.search(r"^func _on_discovery_made\(.*?(?=^func |\Z)", ex_src, re.M | re.S).group(0)
    check("PointsManager.add_points(bonus)" in od and "ProgressionRewards" not in od, "D-21's discovery-count thresholds pay outside the shared path, in _on_discovery_made")
    check(ex_src.count("ProgressionRewards.reach(") == 4 and s["fm"].count("ProgressionRewards.reach(") == 1, "only the five once-ever rewards reach the shared path")
    return fails

if __name__ == "__main__":
    S = sources()
    bad = run(S)
    for b in bad[:10]: print("FAIL:", b)
    assert not bad, "one progression path failed"
    def mut(key, old, new):
        s = dict(S); assert s[key].count(old) == 1, (key, old[:70]); s[key] = s[key].replace(old, new); return s
    MUTANTS = {
        "the guard dropped": mut("pr", "\tif record.has(id):\n\t\treturn -1\n", ""),
        "the record written after the payment": mut("pr", "\trecord.append(id)\n\tvar points := rewards.points(rule_id) if rule_id != \"\" else 0\n\tif points > 0:\n\t\tPointsManager.add_points(points)\n",
                                                    "\tvar points := rewards.points(rule_id) if rule_id != \"\" else 0\n\tif points > 0:\n\t\tPointsManager.add_points(points)\n\trecord.append(id)\n"),
        "a double payment": mut("pr", "\t\tPointsManager.add_points(points)\n", "\t\tPointsManager.add_points(points)\n\t\tPointsManager.add_points(points)\n"),
        "-1 never returned": mut("pr", "\t\treturn -1\n", "\t\treturn 0\n"),
        "a repeat landmark announced": mut("ex", "\tif bonus < 0:\n\t\treturn\n\tlandmark_reached.emit(landmark_id, bonus)", "\tlandmark_reached.emit(landmark_id, bonus)"),
        "milestones without a reward no longer announced": mut("fm", "\tif bonus_points < 0:\n", "\tif bonus_points <= 0:\n"),
        "the curiosity bonus recorded in the wrong list": mut("ex", "ProgressionRewards.reach(_bonuses_paid, CURIOSITY_RULE,", "ProgressionRewards.reach(_found_secret_locations, CURIOSITY_RULE,"),
        "every secret found announced when already paid": mut("ex", "\t\tif all_bonus >= 0:\n", "\t\tif true:\n"),
        "the saved flags swapped": mut("ex", '"all_secrets_bonus": _bonuses_paid.has(ALL_SECRETS_RULE),\n\t\t"curiosity_bonus": _bonuses_paid.has(CURIOSITY_RULE),',
                                       '"all_secrets_bonus": _bonuses_paid.has(CURIOSITY_RULE),\n\t\t"curiosity_bonus": _bonuses_paid.has(ALL_SECRETS_RULE),'),
        "a relaunch forgetting the curiosity bonus": mut("ex", 'if _was_paid(data, "curiosity_bonus"):\n\t\t_bonuses_paid.append(CURIOSITY_RULE)', 'if false:\n\t\t_bonuses_paid.append(CURIOSITY_RULE)'),
        "a relaunch forgetting every secret found": mut("ex", 'if _was_paid(data, "all_secrets_bonus"):\n\t\t_bonuses_paid.append(ALL_SECRETS_RULE)', 'if false:\n\t\t_bonuses_paid.append(ALL_SECRETS_RULE)'),
        "the every-secret flag loaded from the curiosity key": mut("ex", 'if _was_paid(data, "all_secrets_bonus"):', 'if _was_paid(data, "curiosity_bonus"):'),
        "a landmark paying another rule": mut("ex", '_rewards, "landmark")', '_rewards, "secret_location")'),
        "the thresholds routed through the path": mut("ex", "\t\tPointsManager.add_points(bonus)\n\t\texploration_bonus_awarded",
                                                      "\t\tProgressionRewards.reach(_reached_landmarks, str(bonus), _rewards, \"landmark\")\n\t\texploration_bonus_awarded"),
        "the missing-rule warning suppressed": mut("pr", 'rewards.points(rule_id) if rule_id != "" else 0', 'rewards.points(rule_id) if rewards.has(rule_id) else 0'),
        "farm milestones without a rule warning": mut("fm", 'milestone_id if _rewards.has(milestone_id) else "")', "milestone_id)"),
    }
    caught, crashed, survivors = 0, [], []
    for name, s in MUTANTS.items():
        try:
            f = run(s, quick=True)
        except Exception as e:
            f = [f"crash {type(e).__name__}: {e}"]; crashed.append(name)
        if f: caught += 1
        else: survivors.append(name)
    print(f"one progression path (M13.1): the shared path, warnings as before; 2000 random players event-for-event identical to the pre-M13.1 code "
          f"(half with damaged saves); once ever, recorded before paid; session rewards outside")
    by_source = [n for n in ("the thresholds routed through the path",) if n in MUTANTS and n not in survivors and n not in crashed]
    print(f"broken designs: {caught} caught — {caught - len(crashed) - len(by_source)} by behaviour, {len(by_source)} by a source check {by_source}, "
          f"{len(crashed)} by a crash {crashed}")
    if survivors:
        print("SURVIVED:", survivors); sys.exit(1)
    print("ALL PROGRESSION SIMULATIONS PASSED")
