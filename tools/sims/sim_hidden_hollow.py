#!/usr/bin/env python3
"""The Hidden Hollow (M10, D-45): a fifth secret added as data and scene content only — the real ExplorationManager,
ExplorationLandmark and ExplorationLandmarkController translated from their GDScript (gd_port) and driven by the
project's own place data, the Meadow's landmarks and the reward data:
1. Walking the clue trail from the Secluded Pond Nook — footprints, footprints, flowers, motes, then the hollow — reaches
   the Hollow's landmark only at the hollow (none of the clues stands in it; it is clear of every other landmark), and
   no other place is reached on the way.
2. The first arrival pays exactly the existing secret_location reward (15 points) once and records it; walking out and
   back in pays nothing; a save and relaunch (Godot's JSON, a fresh manager) restores it as found and pays nothing more.
3. The Journal's Places (get_places_progress) lists "Hidden Hollow" right after the Secluded Pond Nook, "???" until found.
4. The fifth secret: with no secret found, the four older ones no longer pay "every secret found"; the Hollow as the
   fifth pays it (50) once. A save with the four older secrets found and the bonus unpaid pays 15 + 50 on the Hollow;
   one whose bonus was already paid (the saved flag) pays 15 only — no migration, no retroactive payment.
5. Nothing else: no coins (Wallet), items (Inventory) or new save field; the exploration save section and SAVE_VERSION
   (8) are unchanged.
Broken designs (mutated sources and data) are shown to fail.
"""
import glob, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd_port
from gd_port import translate, godot_json, Signal, Vector3

REPO = gd_port.REPO
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()

# ---------------------------------------------------------------- the engine pieces ExplorationManager uses
TYPE_BOOL, TYPE_STRING, TYPE_DICTIONARY, TYPE_ARRAY = 1, 4, 27, 28
class GArray(list):
    def has(s, v): return v in s
    def size(s): return len(s)
    def is_empty(s): return len(s) == 0
class GDict(gd_port.GDict):
    def has(s, k): return k in s
def gd(v):
    if isinstance(v, dict): return GDict({k: gd(x) for k, x in v.items()})
    if isinstance(v, list): return GArray(gd(x) for x in v)
    return v
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

class Ledger:  # PointsManager, Wallet, Inventory, FarmManager, DiscoveryManager as ExplorationManager reaches them
    def __init__(l): l.points, l.calls, l.discovered = 0, [], set()
    def add_points(l, n): l.points += n; l.calls.append(("points", n))
    def notify_place_reached(l, pid): l.calls.append(("farm_place", pid))
    def is_discovered(l, did): return did in l.discovered
    def __getattr__(l, k):   # any other call (a coin, an item, ...) is recorded as such
        if k.startswith("__"): raise AttributeError(k)
        return lambda *a: l.calls.append(("other", k) + a)
class Rewards:
    def __init__(r, rewards): r.rewards = rewards
    def points(r, rid): return r.rewards.get(rid, 0)
CURRENT = gd_port.Mock(em=None)   # the ExplorationManager autoload the landmarks reach
class Place:
    def __init__(p, **kw): p.__dict__.update(kw)

def read_places(texts):
    out = []
    for txt in texts:
        v = dict(re.findall(r'^(\w+) = (.+)$', txt.split("[resource]", 1)[1], re.M))
        out.append(Place(id=v["id"].strip('"'), display_name=v["display_name"].strip('"'), arrival_text=v.get("arrival_text", '""').strip('"'),
                         order=int(v.get("order", "0")), secret=v.get("secret") == "true", garden=v.get("garden") == "true",
                         curiosity_discovery_id=v.get("curiosity_discovery_id", '""').strip('"')))
    return out

def landmarks_of(meadow):
    """Every ExplorationLandmark in the Meadow — (name, id, kind, radius, position); their parents carry no transform."""
    out = []
    for m in re.finditer(r'^\[node name="(\w+)" type="Node3D" parent="(\w+)"\]\nscript = ExtResource\("37"\)\nposition = Vector3\(([^)]*)\)\n'
                         r'location_id = "(\w+)"\nkind = (\d)\nradius = ([\d.]+)', meadow, re.M):
        parent = re.search(r'^\[node name="%s" type="Node3D" parent="\."\]\n((?:[^\[\n].*\n?)*)' % m.group(2), meadow, re.M)
        assert parent and "position" not in parent.group(1) and "transform" not in parent.group(1), f"{m.group(2)} carries no transform"
        x, y, z = (float(c) for c in m.group(3).split(","))
        out.append((m.group(1), m.group(4), int(m.group(5)), float(m.group(6)), Vector3(x, y, z)))
    return out

def sources():
    return {"ex": _src("scripts", "autoload", "exploration_manager.gd"), "lm": _src("scripts", "world_simulation", "exploration_landmark.gd"),
            "lc": _src("scripts", "world_simulation", "exploration_landmark_controller.gd"), "sm": _src("scripts", "autoload", "save_manager.gd"),
            "meadow": _src("scenes", "world", "Meadow.tscn"),
            "places": {os.path.basename(f): open(f, encoding="utf-8").read() for f in sorted(glob.glob(os.path.join(REPO, "data", "places", "*.tres")))},
            "rewards": {re.search(r'^id = "(\w+)"', t, re.M).group(1): int(re.search(r"^points = (\d+)", t, re.M).group(1))
                        for t in (open(f, encoding="utf-8").read() for f in glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")))}}

EX_FUNCS = ["has_reached_landmark", "mark_landmark_reached", "has_found_secret_location", "mark_secret_location_found",
            "_maybe_award_curiosity_bonus", "get_places_progress", "get_visited_place_count", "_is_place_visited",
            "get_save_data", "apply_save_data", "_restore_places", "_was_paid", "_find_place"]

def build(s):
    ex = re.sub(r"^(\tfor \w+): \w+ in ", r"\1 in ", s["ex"], flags=re.M)        # typed loop variables
    ex = re.sub(r"(?<![\w\]])\[\]", "GArray()", ex)                               # empty arrays are Godot Arrays
    ledger = Ledger()
    ext = {"PointsManager": "LEDGER", "FarmManager": "LEDGER", "DiscoveryManager": "LEDGER", "Wallet": "LEDGER", "Inventory": "LEDGER",
           "ItemManager": "LEDGER", "ExplorationManager": "CURRENT.em"}
    gd_port.HELPERS["LEDGER"], gd_port.HELPERS["CURRENT"] = ledger, CURRENT
    EM, _ = translate(ex, "ExplorationManager", ext, EX_FUNCS)
    lm = s["lm"].replace("Kind.SECRET_LOCATION", "1")
    LM, _ = translate(lm, "ExplorationLandmark", ext, ["is_reached", "mark_reached"])
    LC, _ = translate(s["lc"], "ExplorationLandmarkController", ext, ["_process"])
    places = sorted(read_places(s["places"].values()), key=lambda p: p.order)
    # _load_places() itself (ResourceDirectory, load(), sort_custom) is checked structurally: the data sorted by order,
    # the secret places counted
    lp = re.search(r"^func _load_places\(\).*?(?=^func |\Z)", s["ex"], re.M | re.S).group(0)
    assert "return a.order < b.order" in lp and re.search(r"for place in _places:\s*if place\.secret:\s*_secret_place_count \+= 1", lp)
    def manager():
        em = EM()
        em._places, em._rewards, em._secret_place_count = GArray(places), Rewards(s["rewards"]), sum(p.secret for p in places)
        return em
    return EM, LM, LC, ledger, manager, places

def scene(s, LM, LC, em):
    """The Meadow's landmarks in the group, a controller and a player — the frame loop as WorldSimulation runs it."""
    tree = gd_port.Tree(); gd_port.World.tree = tree
    for name, lid, kind, radius, pos in landmarks_of(s["meadow"]):
        node = LM(); node.name, node.location_id, node.kind, node.radius, node.global_position = name, lid, kind, radius, pos
        node.add_to_group("exploration_landmark")
    CURRENT.em = em
    ctl = LC(); ctl.player = gd_port.Mock(global_position=Vector3())
    return ctl

def walk(ctl, ledger, em, points, step=0.1):
    """Walks the player along the points a frame per step; returns [(where, what changed)] as it happened."""
    log, p = [], points[0]
    for target in points[1:]:
        d = p.distance_to(target)
        n = max(1, int(d / step))
        for i in range(1, n + 1):
            pos = Vector3(p.x + (target.x - p.x) * i / n, 0.0, p.z + (target.z - p.z) * i / n)
            ctl.player.global_position = pos
            before = (ledger.points, list(em._found_secret_locations), list(em._reached_landmarks))
            ctl._process(1 / 60)
            if (ledger.points, list(em._found_secret_locations), list(em._reached_landmarks)) != before:
                log.append(((round(pos.x, 2), round(pos.z, 2)), ledger.points - before[0],
                            [x for x in em._found_secret_locations + em._reached_landmarks if x not in before[1] + before[2]]))
        p = target
    return log

def relaunch(s, em, manager):
    """SaveManager's round trip: the exploration section through Godot's JSON into a fresh manager."""
    sm = s["sm"]
    assert re.search(r'^\t\t"exploration": ExplorationManager\.get_save_data\(\),$', sm, re.M)
    assert re.search(r'^\tExplorationManager\.apply_save_data\(data\.get\("exploration", \{\}\)\)$', sm, re.M)
    data = gd(dict(godot_json(em.get_save_data())))
    fresh = manager(); fresh.apply_save_data(data)
    return fresh, data

HOLLOW_TRAIL = ["HollowTrailFootprints1", "HollowTrailFootprints2", "HollowTrailFlowers", "HollowTrailMotes"]
OLD_SECRETS = ["stone_ring", "secluded_pond_nook", "mystery_grove_tree", "hidden_flower_pocket"]

def run(s):
    p = []
    EM, LM, LC, ledger, manager, places = build(s)
    meadow = s["meadow"]
    # ---- place data and the scene agree
    hollow = next((pl for pl in places if pl.id == "hidden_hollow"), None)
    if not hollow or not hollow.secret or hollow.display_name != "Hidden Hollow" or hollow.arrival_text or hollow.garden or hollow.curiosity_discovery_id:
        return ["the Hidden Hollow is a secret place named \"Hidden Hollow\" with no arrival text, garden role or curiosity pairing"]
    lms = {lid: (name, kind, r, pos) for name, lid, kind, r, pos in landmarks_of(meadow)}
    if {pl.id: pl.secret for pl in places} != {lid: k == 1 for lid, (_, k, _, _) in lms.items()}:
        p.append("every place has its landmark and the secret flags agree")
    if "hidden_hollow" not in lms or lms["hidden_hollow"][0] != "HiddenHollowLandmark" or lms["hidden_hollow"][2] != 3.0:
        return p + ["the Hollow's landmark is HiddenHollowLandmark, a secret with radius 3"]
    hpos, hr = lms["hidden_hollow"][3], lms["hidden_hollow"][2]
    nook = lms["secluded_pond_nook"][3]
    def at(name):
        m = re.search(r'^\[node name="%s" parent="HiddenPlaces"[^\]]*\]\nposition = Vector3\(([^)]*)\)' % name, meadow, re.M)
        return Vector3(*(float(c) for c in m.group(1).split(","))) if m else None
    clues = [at(n) for n in HOLLOW_TRAIL]
    if None in clues:
        return p + [f"the clue trail {HOLLOW_TRAIL} sits under HiddenPlaces"]
    flat = lambda v: Vector3(v.x, 0.0, v.z)
    dists = [flat(c).distance_to(nook) for c in clues] + [hpos.distance_to(nook)]
    if dists != sorted(dists):
        p.append(f"each clue leads further from the Nook ({[round(d, 1) for d in dists]})")
    for lid, (name, kind, r, pos) in lms.items():
        if lid != "hidden_hollow" and pos.distance_to(hpos) < r + hr:
            p.append(f"the Hollow's zone overlaps {name}'s")
    # ---- 1/2. a fresh save: the trail from the Nook, by frames
    em = manager(); ctl = scene(s, LM, LC, em)
    start = Vector3(nook.x, 0.0, nook.z)
    log = walk(ctl, ledger, em, [start] + [flat(c) for c in clues] + [hpos])
    nook_hits = [e for e in log if e[2] == ["secluded_pond_nook"]]
    hollow_hits = [e for e in log if "hidden_hollow" in e[2]]
    # the Nook pays its own 15 and, on a fresh save, the existing curiosity bonus (20, river_stone not yet found); the Hollow 15
    if [e[2] for e in log] != [["secluded_pond_nook"], ["hidden_hollow"]] or [e[1] for e in log] != [15 + s["rewards"]["curiosity"], 15]:
        p.append(f"the trail reaches the Nook (where it starts) and then only the Hollow, which pays 15 ({log})")
    for name, c in zip(HOLLOW_TRAIL[:-1], clues[:-1]):
        if flat(c).distance_to(hpos) <= hr:
            p.append(f"{name} stands inside the Hollow's zone — the hollow would be reached before the trail's end")
    if hollow_hits:
        (hx, hz), _, _ = hollow_hits[0]
        if abs(Vector3(hx, 0, hz).distance_to(hpos) - hr) > 0.11 or Vector3(hx, 0, hz).distance_to(flat(clues[-1])) > hr + 0.11:
            p.append(f"the Hollow is reached on its edge, at the motes ({hx}, {hz})")
    if [c for c in ledger.calls if c[0] != "points" and c[0] != "farm_place"]:
        p.append(f"reaching the Hollow pays only points — no coins or items ({[c for c in ledger.calls if c[0] not in ('points', 'farm_place')]})")
    paid = ledger.points
    # out to the Nook and back in
    log2 = walk(ctl, ledger, em, [hpos, start, hpos])
    if log2 or ledger.points != paid or em._found_secret_locations.count("hidden_hollow") != 1:
        p.append(f"re-entering pays nothing ({log2})")
    rows = em.get_places_progress()
    ids = [r["id"] for r in rows]
    if "hidden_hollow" not in ids or ids.index("hidden_hollow") != ids.index("secluded_pond_nook") + 1 \
       or not next(r for r in rows if r["id"] == "hidden_hollow")["visited"] or next(r for r in rows if r["id"] == "hidden_hollow")["display_name"] != "Hidden Hollow":
        p.append(f"the Journal's Places lists Hidden Hollow, visited, right after the Secluded Pond Nook ({rows})")
    # ---- save and relaunch
    fresh, data = relaunch(s, em, manager)
    if list(data) != ["landmarks", "secrets", "all_secrets_bonus", "curiosity_bonus"]:
        p.append(f"the exploration section keeps its four fields — no new one ({list(data)})")
    if not fresh.has_found_secret_location("hidden_hollow") or not next(r for r in fresh.get_places_progress() if r["id"] == "hidden_hollow")["visited"]:
        p.append("the Hollow is restored as found after a relaunch")
    before = ledger.points
    ctl = scene(s, LM, LC, fresh)
    if walk(ctl, ledger, fresh, [start, hpos]) or ledger.points != before:
        p.append("after a relaunch the Hollow pays nothing")
    # ---- 3. the Journal before finding it
    em0 = manager()
    if next(r for r in em0.get_places_progress() if r["id"] == "hidden_hollow")["visited"]:
        p.append("the Hollow is unvisited on a fresh save")
    # ---- 4. the fifth secret
    def pay(em, pid):
        b = ledger.points; em.mark_secret_location_found(pid); return ledger.points - b
    em = manager()
    if pay(em, "hidden_hollow") != 15 or em._curiosity_bonus_given:
        p.append("the Hollow has no curiosity pairing — found first, it pays 15 and leaves the curiosity bonus unpaid")
    def manager(manager=manager):   # below, the curiosity bonus is taken as paid so only the secret rewards show
        em = manager(); em._curiosity_bonus_given = True; return em
    em = manager()
    first4 = [pay(em, pid) for pid in OLD_SECRETS]
    if first4 != [15, 15, 15, 15] or em._all_secrets_bonus_awarded:
        p.append(f"the four older secrets no longer pay 'every secret found' — it needs five ({first4})")
    if pay(em, "hidden_hollow") != 65 or not em._all_secrets_bonus_awarded or pay(em, "hidden_hollow") != 0:
        p.append("the Hollow as the fifth secret pays 15 + the 50-point bonus, once")
    for order in ([("hidden_hollow")] + OLD_SECRETS, OLD_SECRETS[:2] + ["hidden_hollow"] + OLD_SECRETS[2:]):
        em = manager(); got = [pay(em, pid) for pid in order]
        if got != [15, 15, 15, 15, 65]:
            p.append(f"the bonus pays on whichever secret is fifth ({order}: {got})")
    old_unpaid = gd({"landmarks": [], "secrets": list(OLD_SECRETS), "all_secrets_bonus": False, "curiosity_bonus": True})
    old_paid = gd({"landmarks": [], "secrets": list(OLD_SECRETS), "all_secrets_bonus": True, "curiosity_bonus": True})
    for save, want, what in ((old_unpaid, 65, "four older secrets, bonus unpaid"), (old_paid, 15, "four older secrets, bonus already paid")):
        em = manager(); b = ledger.points
        em.apply_save_data(save)
        if ledger.points != b:
            p.append(f"loading a save pays nothing ({what})")
        got = pay(em, "hidden_hollow")
        again, _ = relaunch(s, em, manager)
        if got != want or pay(again, "hidden_hollow") != 0 or not again._all_secrets_bonus_awarded:
            p.append(f"{what}: the Hollow pays {want} once and the bonus stays paid after a relaunch (got {got})")
    # ---- 5. the save format
    sm = s["sm"]
    if int(re.search(r"^const SAVE_VERSION := (\d+)", sm, re.M).group(1)) != 8:
        p.append("SAVE_VERSION stays 8 — the Hollow is saved in the existing exploration section")
    if [c for c in ledger.calls if c[0] == "other"]:
        p.append(f"no coins, items or other effects ({[c for c in ledger.calls if c[0] == 'other']})")
    return p

S = sources()
bad = run(S)
assert not bad, f"the Hidden Hollow: {bad}"

def mutate(key, old, new, place=None):
    s = dict(S, places=dict(S["places"]))
    if place:
        assert old in s["places"][place], (place, old); s["places"][place] = s["places"][place].replace(old, new)
    else:
        assert old in s[key], (key, old); s[key] = s[key].replace(old, new, 1)
    return s
MUTANTS = {
    "the bonus counts four secrets (hard-coded)": mutate("ex", "_found_secret_locations.size() >= _secret_place_count", "_found_secret_locations.size() >= 4"),
    "the bonus ignores the saved flag": mutate("ex", " and not _all_secrets_bonus_awarded:", ":"),
    "a relaunch forgets the paid bonus": mutate("ex", '_all_secrets_bonus_awarded = _was_paid(data, "all_secrets_bonus")', "_all_secrets_bonus_awarded = false"),
    "a secret pays again on re-entry": mutate("ex", "\tif _found_secret_locations.has(location_id):\n\t\treturn\n\t_found_secret_locations.append(location_id)",
                                              "\tif not _found_secret_locations.has(location_id):\n\t\t_found_secret_locations.append(location_id)"),
    "found secrets are not saved": mutate("ex", '"secrets": Array(_found_secret_locations),', '"secrets": GArray(),'),
    "a new save field": mutate("ex", '"curiosity_bonus": _curiosity_bonus_given,', '"curiosity_bonus": _curiosity_bonus_given,\n\t\t"hollow": true,'),
    "the Hollow also gives coins": mutate("ex", "\tsecret_location_found.emit(location_id, bonus)", "\tsecret_location_found.emit(location_id, bonus)\n\tWallet.add_coins(5)"),
    "the Hollow also gives an item": mutate("ex", "\tsecret_location_found.emit(location_id, bonus)", "\tsecret_location_found.emit(location_id, bonus)\n\tInventory.add_item(location_id, 1)"),
    "the secret reward doubled": mutate("ex", 'var bonus := _rewards.points("secret_location")', 'var bonus := 2 * _rewards.points("secret_location")'),
    "the Hollow is not a secret (data)": mutate(None, "secret = true\n", "", place="hidden_hollow.tres"),
    "the Hollow listed first (data)": mutate(None, "order = 55", "order = 5", place="hidden_hollow.tres"),
    "the Hollow's landmark is a plain landmark": mutate("meadow", 'location_id = "hidden_hollow"\nkind = 1', 'location_id = "hidden_hollow"\nkind = 0'),
    "the Hollow's radius 6 instead of 3": mutate("meadow", 'location_id = "hidden_hollow"\nkind = 1\nradius = 3.0', 'location_id = "hidden_hollow"\nkind = 1\nradius = 6.0'),
    "the Hollow moved onto the Nook": mutate("meadow", "position = Vector3(19, 0, -24)\nlocation_id = \"hidden_hollow\"", "position = Vector3(15, 0, -14)\nlocation_id = \"hidden_hollow\""),
    "the clues out of order": mutate("meadow", "HollowTrailFootprints1\" parent=\"HiddenPlaces\" instance=ExtResource(\"26\")]\nposition = Vector3(15.8, 0, -16.3)",
                                     "HollowTrailFootprints1\" parent=\"HiddenPlaces\" instance=ExtResource(\"26\")]\nposition = Vector3(17.9, 0, -21.0)"),
    "the Hollow saved in a new version": mutate("sm", "const SAVE_VERSION := 8", "const SAVE_VERSION := 9"),
}
killed = {}
for name, s in MUTANTS.items():
    try:
        r = run(s)
        killed[name] = ("behaviour", r[0]) if r else None
    except Exception as e:  # noqa: BLE001 — a mutant that breaks the run is reported separately
        killed[name] = ("crash", f"{type(e).__name__}: {e}")
survivors = [n for n, k in killed.items() if k is None]
assert not survivors, f"broken designs not caught: {survivors}"
crashes = [n for n, k in killed.items() if k[0] == "crash"]
print("hidden hollow: trail Nook -> footprints x2 -> flowers -> motes -> hollow reaches only the Nook (15, + the existing curiosity 20 on a fresh save) then the Hollow (+15, no curiosity); "
      "re-entry 0, relaunch 0 (restored as found); Journal row after the Nook; fifth secret: four older pay no bonus, the fifth pays 15 + 50 once, "
      "an unpaid four-secret save 15 + 50, a paid one 15; exploration section unchanged, SAVE_VERSION 8; no coins or items")
print(f"broken designs: {len(MUTANTS)} caught — {len(MUTANTS) - len(crashes)} by behaviour, {len(crashes)} by a crash {crashes}")
print("ALL HIDDEN HOLLOW SIMULATIONS PASSED")
