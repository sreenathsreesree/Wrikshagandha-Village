#!/usr/bin/env python3
"""Model checks for repeat-reward protection (M05.2, P-02, D-21) — a Python
port of ExplorationManager's rewards and save/load, played across many
relaunches together with the other reward sources. Not the engine.
1. Read from the project: the places (data/places), discoveries, bonus
   values, the reward/guard lines of ExplorationManager, its save shape,
   SaveManager's exploration section and 4 -> 5 step.
2. Port: landmark / secret / every-secret / curiosity bonuses, the
   first-ever-discovery thresholds and beats; DiscoveryManager (points on
   every collection, first-ever by saved ids); the collectible reward (one
   per collection, M04.3); the daily bonus (once per day); relaunch =
   save -> JSON (numbers as floats) -> load into fresh systems.
3. Cases: the pre-M05.2 (session-only) model shown to re-pay on every
   relaunch; now every once-ever reward pays exactly once over 12 relaunches
   of 1,500 random players; loading pays nothing, and load -> save -> load
   is stable; repeat collection still pays points and a collectible every
   time; a fresh game starts empty; the first session is identical to the
   old behaviour; a v4 save (no exploration) starts empty and then pays each
   reward at most once more; 3,000 malformed exploration states never pay a
   place twice or a flagged bonus again.
"""
import copy, glob, json, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _funcs(src): return {m.group(1): m.group(0) for m in re.finditer(r"^func (\w+)\(.*?(?=^func |\Z)", src, re.M | re.S)}
def _vals(f): return {k: v.strip('"') for k, v in re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M)}

# ---------------------------------------------------------------- 1. read from the project
EX_SRC = _src("scripts", "autoload", "exploration_manager.gd"); EX = _funcs(EX_SRC)
RULES = {v["id"]: (int(v.get("points", "0")), int(v.get("threshold", "0"))) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")))}
LANDMARK, SECRET, ALL_SECRETS, CURIOSITY = (RULES[r][0] for r in ("landmark", "secret_location", "all_secret_locations", "curiosity"))
THRESHOLDS = {t: p for p, t in RULES.values() if t}
PLACES = {v["id"]: {"secret": v.get("secret") == "true", "curiosity": v.get("curiosity_discovery_id", "")}
          for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "places", "*.tres"))))}
SECRETS = [p for p, v in PLACES.items() if v["secret"]]; LANDMARKS = [p for p, v in PLACES.items() if not v["secret"]]
DISC = {v["id"]: int(v.get("points_value", "10")) for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "discoveries", "*.tres"))))}
ONCE_EVER = {v["id"] for v in map(_vals, glob.glob(os.path.join(REPO, "data", "discoveries", "*.tres"))) if float(v.get("respawn_seconds", "60")) <= 0}  # M05.3
COLLECT = {v["discovery_id"]: v["id"] for v in map(_vals, glob.glob(os.path.join(REPO, "data", "items", "*.tres"))) if v.get("category") == "collectible"}
DAILY = RULES["daily_discovery"][0]
assert "if _reached_landmarks.has(landmark_id):" in EX["mark_landmark_reached"] and "if _found_secret_locations.has(location_id):" in EX["mark_secret_location_found"]
assert "and not _all_secrets_bonus_awarded:" in EX["mark_secret_location_found"] and "if _curiosity_bonus_given:" in EX["_maybe_award_curiosity_bonus"]
assert '"landmarks": Array(_reached_landmarks)' in EX["get_save_data"] and '"curiosity_bonus": _curiosity_bonus_given' in EX["get_save_data"]
assert "return value if typeof(value) == TYPE_BOOL else true" in EX["_was_paid"] and "place.secret != secret" in EX["_restore_places"]
assert '_all_secrets_bonus_awarded = _was_paid(data, "all_secrets_bonus")' in EX["apply_save_data"]
SMS = _src("scripts", "autoload", "save_manager.gd")
assert '"exploration": ExplorationManager.get_save_data(),' in SMS and re.search(r"^\t\t\t4:\s*pass", SMS, re.M)
assert int(re.search(r"^const SAVE_VERSION := (\d+)", SMS, re.M).group(1)) >= 5  # v5 = M05.2 (exploration); later sections bump it (M08.5: v6)

# ---------------------------------------------------------------- 2. ports
class World:
    """Points, discoveries, collectibles, daily, exploration — one launch. persist=False = the pre-M05.2 model."""
    def __init__(w, persist=True):
        w.persist, w.points, w.discovered, w.items, w.daily_done = persist, 0, [], {}, ""
        w.landmarks, w.secrets, w.all_paid, w.cur_paid = [], [], False, False
        w.session_count, w.thresholds, w.paid = 0, [], []          # paid: log of (reward, id) this launch
    # DiscoveryManager.discover + listeners
    def collect(w, d, today="d1"):
        if d in ONCE_EVER and d in w.discovered: return          # M05.3: a claimed once-ever find is gone for good
        first = d not in w.discovered
        if first: w.discovered.append(d)
        w.points += DISC[d]
        if d in COLLECT: w.items[COLLECT[d]] = w.items.get(COLLECT[d], 0) + 1       # Inventory, every collection
        if w.daily_done != today and d == sorted(DISC)[sum(map(ord, today)) % len(DISC)]:     # DailyDiscoveryManager
            w.daily_done = today; w.points += DAILY; w.paid.append(("daily", today))
        if first:                                                                     # ExplorationManager._on_discovery_made
            w.session_count += 1
            if w.session_count in THRESHOLDS and w.session_count not in w.thresholds:
                w.thresholds.append(w.session_count); w.points += THRESHOLDS[w.session_count]; w.paid.append(("threshold", w.session_count))
    def reach(w, p):
        if PLACES[p]["secret"]:
            if p in w.secrets: return
            w.secrets.append(p); w.points += SECRET; w.paid.append(("secret", p))
            if not w.cur_paid and PLACES[p]["curiosity"] and PLACES[p]["curiosity"] not in w.discovered:
                w.cur_paid = True; w.points += CURIOSITY; w.paid.append(("curiosity", p))
            if SECRETS and len(w.secrets) >= len(SECRETS) and not w.all_paid:
                w.all_paid = True; w.points += ALL_SECRETS; w.paid.append(("all_secrets", ""))
        else:
            if p in w.landmarks: return
            w.landmarks.append(p); w.points += LANDMARK; w.paid.append(("landmark", p))
    def save(w):
        d = {"save_version": 5, "points": w.points, "discovered_ids": list(w.discovered), "items": {k: [n] for k, n in w.items.items()},
             "daily_discovery": {"completed_date": w.daily_done}}
        if w.persist:
            d["exploration"] = {"landmarks": list(w.landmarks), "secrets": list(w.secrets), "all_secrets_bonus": w.all_paid, "curiosity_bonus": w.cur_paid}
        return json.dumps(d)
    @staticmethod
    def load(text, persist=True):
        d = json.loads(text); w = World(persist)
        w.points, w.discovered = int(d.get("points", 0)), [str(x) for x in d.get("discovered_ids", [])]
        w.items = {k: int(v[0]) for k, v in d.get("items", {}).items()}; w.daily_done = d.get("daily_discovery", {}).get("completed_date", "")
        if persist: w.apply_exploration(d.get("exploration", {}))
        return w
    def apply_exploration(w, data):   # ExplorationManager.apply_save_data
        w.landmarks, w.secrets = [], []
        def restore(saved, secret, into):
            if not isinstance(saved, list): return
            for p in saved:
                if not isinstance(p, str) or p not in PLACES or PLACES[p]["secret"] != secret or p in into: continue
                into.append(p)
        restore(data.get("landmarks", []), False, w.landmarks); restore(data.get("secrets", []), True, w.secrets)
        def was_paid(k): return (data[k] if isinstance(data[k], bool) else True) if k in data else False
        w.cur_paid = was_paid("curiosity_bonus")
        w.all_paid = was_paid("all_secrets_bonus")

def session(w, rnd, steps):
    for _ in range(steps):
        if rnd.random() < 0.5: w.collect(rnd.choice(sorted(DISC)), today=rnd.choice(["d1", "d2"]))
        else: w.reach(rnd.choice(sorted(PLACES)))
def once_ever(log): return [(r, i) for r, i in log if r in ("landmark", "secret", "all_secrets", "curiosity")]

# ---------------------------------------------------------------- 3. cases
# the problem: the session-only model pays every landmark again after a relaunch
old = World(persist=False); [old.reach(p) for p in LANDMARKS]
old2 = World.load(old.save(), persist=False); [old2.reach(p) for p in LANDMARKS]
assert len(once_ever(old2.paid)) == len(LANDMARKS) and old2.points == old.points + LANDMARK * len(LANDMARKS), "pre-M05.2: a relaunch re-pays"
new = World(); [new.reach(p) for p in LANDMARKS]
new2 = World.load(new.save()); [new2.reach(p) for p in LANDMARKS]
assert once_ever(new2.paid) == [] and new2.points == new.points, "M05.2: a relaunch pays nothing again"
# fresh game starts empty
f = World(); assert (f.points, f.landmarks, f.secrets, f.all_paid, f.cur_paid, f.items) == (0, [], [], False, False, {})
# loading pays nothing; load -> save -> load stable
w = World(); session(w, random.Random(1), 200); text = w.save()
a = World.load(text); assert a.paid == [] and a.points == w.points and World.load(a.save()).save() == a.save()
# many players, many relaunches: every once-ever reward exactly once; first session identical to the old model
rnd = random.Random(52); totals = {"landmark": 0, "secret": 0, "all_secrets": 0, "curiosity": 0}
for _ in range(1500):
    seed = rnd.random(); w, o = World(), World(persist=False)
    session(w, random.Random(seed), 60); session(o, random.Random(seed), 60)
    assert w.paid == o.paid and w.points == o.points, "within one session nothing changes"
    ever = list(once_ever(w.paid)); text = w.save()
    for _ in range(12):
        if rnd.random() < 0.3:
            for _ in range(rnd.randint(1, 3)): text = World.load(text).save()     # load/save cycles without play
        w = World.load(text)
        assert w.paid == [], "loading pays nothing"
        session(w, random.Random(rnd.random()), rnd.randint(0, 80))
        ever += once_ever(w.paid); text = w.save()
    assert len(ever) == len(set(ever)), f"a once-ever reward paid twice: {ever}"
    assert ever.count(("all_secrets", "")) <= 1 and sum(1 for r, _ in ever if r == "curiosity") <= 1
    final = World.load(text)
    assert sorted(final.landmarks + final.secrets) == sorted({i for r, i in ever if r in ("landmark", "secret")}), "progress survives every relaunch"
    for r, _ in ever: totals[r] += 1
# repeat collection unchanged (M04.3): points and a collectible every time, across relaunches
w = World(); d = sorted(set(COLLECT) - ONCE_EVER)[0]
for i in range(1, 6):
    w.collect(d); w = World.load(w.save())
    assert w.items[COLLECT[d]] == i and w.points >= DISC[d] * i, "repeatable collection still pays each time"
# a v4 save (no exploration section): nothing reached yet; each reward then pays at most once more, never again
v4 = World(persist=False); [v4.reach(p) for p in LANDMARKS + SECRETS]; d4 = json.loads(v4.save()); d4["save_version"] = 4
m = World.load(json.dumps(d4)); assert (m.landmarks, m.secrets, m.all_paid, m.cur_paid) == ([], [], False, False)
[m.reach(p) for p in LANDMARKS + SECRETS]; again = World.load(m.save()); [again.reach(p) for p in LANDMARKS + SECRETS]
assert once_ever(again.paid) == [], "after the first post-update visit, never again"
# malformed exploration states never re-pay: a place restored is never paid again; a malformed flag counts as paid
junk = [None, True, False, 0, 1.5, "yes", "", [], {}, ["overlook"], "overlook"] + sorted(PLACES) + ["nowhere", "OVERLOOK"]
rnd = random.Random(53)
for _ in range(3000):
    data = {}
    for k in ("landmarks", "secrets"):
        if rnd.random() < 0.8: data[k] = rnd.choice([[rnd.choice(junk) for _ in range(rnd.randint(0, 6))], rnd.choice(junk)])
    for k in ("all_secrets_bonus", "curiosity_bonus"):
        if rnd.random() < 0.8: data[k] = rnd.choice(junk)
    w = World(); w.apply_exploration(data)
    assert set(w.landmarks) <= set(LANDMARKS) and set(w.secrets) <= set(SECRETS) and len(set(w.landmarks)) == len(w.landmarks) and len(set(w.secrets)) == len(w.secrets)
    for k, attr in (("all_secrets_bonus", "all_paid"), ("curiosity_bonus", "cur_paid")):
        if k in data and data[k] is not False: assert getattr(w, attr), f"malformed/true {k} counts as paid"
    restored = set(w.landmarks + w.secrets)
    [w.reach(p) for p in sorted(PLACES)]
    paid_places = {i for r, i in once_ever(w.paid) if r in ("landmark", "secret")}
    assert not (paid_places & restored), "a restored place never pays again"
    assert sum(1 for r, _ in w.paid if r == "all_secrets") <= (0 if ("all_secrets_bonus" in data and data["all_secrets_bonus"] is not False) else 1)
    assert sum(1 for r, _ in w.paid if r == "curiosity") <= (0 if ("curiosity_bonus" in data and data["curiosity_bonus"] is not False) else 1)
print(f"repeat rewards: {len(LANDMARKS)} landmarks, {len(SECRETS)} secrets; pre-M05.2 relaunch re-pays, now never; 1500 players x 12 relaunches — "
      f"once-ever rewards paid {totals}, never twice; loading pays nothing; repeat collection unchanged; v4 save safe; 3000 malformed states safe")
print("ALL REPEAT-REWARD SIMULATIONS PASSED")
