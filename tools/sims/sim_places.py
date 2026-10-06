#!/usr/bin/env python3
"""Model checks for place data out of code (M03.6, A5) — a Python port, not the engine.
1. Read from the project: the PlaceDefinitions in data/places/, the areas'
   landmarks, discoveries, crops, and the structure of ExplorationManager's
   place code.
2. Port of ExplorationManager's place logic driven by that data: the ordered
   "Places" list, display names and arrival text (with the fallback for an
   unknown id), the curiosity bonus, the "every secret found" bonus, the
   garden (FarmManager's "garden found").
3. Parity: random sessions give exactly the same results as the pre-M03.6
   hard-coded constants (snapshot below). The snapshot is the migration's
   proof; update it only together with a deliberate change to the data.
"""
import glob, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _body(src, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S)
    assert m, f"{name}() not found"
    return m.group(0)

# ---------------------------------------------------------------- 1. read from the project
PLACES = []
for f in sorted(glob.glob(os.path.join(REPO, "data", "places", "*.tres"))):
    v = dict(re.findall(r'^(\w+) = (.+)$', open(f, encoding="utf-8").read().split("[resource]", 1)[1], re.M))
    PLACES.append({"id": v["id"].strip('"'), "name": v["display_name"].strip('"'), "arrival": v.get("arrival_text", '""').strip('"'),
                   "order": int(v.get("order", "0")), "secret": v.get("secret") == "true", "garden": v.get("garden") == "true",
                   "curiosity": v.get("curiosity_discovery_id", '""').strip('"')})
PLACES.sort(key=lambda p: p["order"])
EX = _src("scripts", "autoload", "exploration_manager.gd")
assert "return a.order < b.order" in _body(EX, "_load_places") and "_secret_place_count += 1" in _body(EX, "_load_places")
assert "_secret_place_count > 0 and _found_secret_locations.size() >= _secret_place_count" in _body(EX, "mark_secret_location_found")
assert 'return place_id.replace("_", " ").capitalize()' in _body(EX, "get_place_display_name")
assert 'if place != null and place.arrival_text != "":' in _body(EX, "get_place_arrival_text")
def _reward(rid): return int(re.search(r"^points = (\d+)", _src("data", "rewards", rid + ".tres"), re.M).group(1))   # M05.3: reward data
ALL_SECRETS_BONUS, CURIOSITY_BONUS = _reward("all_secret_locations"), _reward("curiosity")
LANDMARKS = {}
for path in glob.glob(os.path.join(REPO, "scenes", "**", "*.tscn"), recursive=True):
    for lid, kind in re.findall(r'location_id = "(\w+)"\nkind = (\d)', open(path, encoding="utf-8").read()):
        LANDMARKS[lid] = kind == "1"
assert {p["id"]: p["secret"] for p in PLACES} == LANDMARKS, "every place has its landmark, secret flags agree"
DISCOVERIES = {re.search(r'^id = "([^"]+)"', open(f).read(), re.M).group(1) for f in glob.glob(os.path.join(REPO, "data", "discoveries", "*.tres"))}
assert all(p["curiosity"] in DISCOVERIES for p in PLACES if p["curiosity"])

# ---------------------------------------------------------------- 2. the logic (port, data-driven)
class Exploration:
    def __init__(e, places):
        e.places = sorted(places, key=lambda p: p["order"]); e.secret_count = sum(p["secret"] for p in e.places)
        e.landmarks, e.secrets, e.points, e.all_bonus, e.curiosity_given, e.events = [], [], 0, False, False, []
    def find(e, pid): return next((p for p in e.places if p["id"] == pid), None)
    def display_name(e, pid):
        p = e.find(pid); return p["name"] if p else " ".join(w.capitalize() for w in pid.replace("_", " ").split(" "))
    def arrival_text(e, pid):
        p = e.find(pid); return p["arrival"] if p and p["arrival"] else e.display_name(pid)
    def garden_id(e): return next((p["id"] for p in e.places if p["garden"]), "")
    def progress(e): return [(p["id"], p["name"], p["id"] in e.landmarks or p["id"] in e.secrets) for p in e.places]
    def reach(e, pid, discovered):
        if e.find(pid) and e.find(pid)["secret"]:
            if pid in e.secrets: return
            e.secrets.append(pid); e.events.append(("secret", pid))
            p = e.find(pid)
            if not e.curiosity_given and p["curiosity"] and p["curiosity"] not in discovered:
                e.curiosity_given = True; e.points += CURIOSITY_BONUS; e.events.append(("curiosity", pid))
            if e.secret_count > 0 and len(e.secrets) >= e.secret_count and not e.all_bonus:
                e.all_bonus = True; e.points += ALL_SECRETS_BONUS; e.events.append(("all_secrets",))
        else:
            if pid in e.landmarks: return
            e.landmarks.append(pid); e.events.append(("landmark", pid))
        if pid == e.garden_id(): e.events.append(("garden_found",))

# ---------------------------------------------------------------- 3. parity with the pre-M03.6 constants
OLD_PLACES = [("overlook", "Overlook", ""), ("wildflower_clearing", "Wildflower Clearing", ""), ("ancient_grove", "Ancient Grove", ""),
              ("stone_ring", "Stone Ring", ""), ("secluded_pond_nook", "Secluded Pond Nook", ""),
              ("hidden_hollow", "Hidden Hollow", ""),      # M10 (D-45): a fifth secret, deliberately added to the snapshot
              ("mystery_grove_tree", "Mystery Grove Tree", ""), ("hidden_flower_pocket", "Hidden Flower Pocket", ""),
              ("quiet_farm", "Quiet Garden", "A quiet place to grow.")]
OLD_CURIOSITY = {"secluded_pond_nook": "river_stone", "mystery_grove_tree": "golden_leaf"}
OLD_SECRET_THRESHOLD, OLD_GARDEN = 5, "quiet_farm"   # 4 until M10 (D-45) added the Hidden Hollow
class OldExploration(Exploration):  # the old code: constants + the scene's landmark kinds
    def __init__(e):
        places = [{"id": i, "name": n, "arrival": a, "order": k, "secret": LANDMARKS[i], "garden": i == OLD_GARDEN,
                   "curiosity": OLD_CURIOSITY.get(i, "")} for k, (i, n, a) in enumerate(OLD_PLACES)]
        super().__init__(places); e.secret_count = OLD_SECRET_THRESHOLD
new = Exploration(PLACES); old = OldExploration()
assert new.progress() == old.progress(), "same Places list, same order"
assert new.garden_id() == old.garden_id() == OLD_GARDEN and new.secret_count == OLD_SECRET_THRESHOLD
for pid in [p[0] for p in OLD_PLACES] + ["unknown_spot", "a_b"]:
    assert new.display_name(pid) == old.display_name(pid) and new.arrival_text(pid) == old.arrival_text(pid), pid
assert new.display_name(new.garden_id()) == "Quiet Garden", "the bloom milestone text is unchanged"
ids = [p[0] for p in OLD_PLACES]
rnd = random.Random(6)
for _ in range(3000):
    new, old = Exploration(PLACES), OldExploration(); discovered = set()
    for _ in range(rnd.randint(1, 25)):
        if rnd.random() < 0.3: discovered.add(rnd.choice(sorted(DISCOVERIES)))
        pid = rnd.choice(ids + ["unknown_spot"])
        new.reach(pid, discovered); old.reach(pid, discovered)
        assert new.events == old.events and new.points == old.points and new.progress() == old.progress()
    assert new.all_bonus == (len(new.secrets) == OLD_SECRET_THRESHOLD)
print(f"places: {len(PLACES)} from data ({new.secret_count} secret, garden {new.garden_id()}); list/names/arrival/"
      "curiosity/all-secrets/garden identical to the pre-M03.6 constants over 3000 random sessions")
print("ALL PLACE SIMULATIONS PASSED")
