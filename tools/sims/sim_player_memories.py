#!/usr/bin/env python3
"""Player memories (M14.1, D-71) — derived only. The real GDScript executed (gd_port): JournalManager.get_memories /
is_remembered and its sighting functions, the ExplorationManager and FarmManager functions that write, save, load and
answer for the records memories rest on, and the shared progression path (ProgressionRewards.reach), on the project's
memory, place, species, milestone and reward data, with relaunches through Godot's JSON.
1. Each memory appears only with its fact: from a new game (no memory) each memory's own event, through the game's
   real path — a farm milestone reached (FarmManager._reach), a secret place found, a species seen — makes exactly that
   memory; every other event (the other milestones, every landmark, an unknown species) makes none.
2. Old saves: each fixture v0..v9 (tools/fixtures/saves/v*/save.json, real saves written by the commits that introduced
   their formats), loaded through the real load functions, gives exactly the memories its own records prove: v0-v4
   the first seed and first harvest; v5-v8 also the first secret place; v9 also the rabbit and the butterfly — and the
   same again after a save and a relaunch.
3. Never inferred: saves that hold everything around a fact but not the fact give no memory — harvest counts, grown
   crops and harvested plots without the first-harvest milestone; the farm's garden flag and the landmarks; the
   curiosity and every-secret flags without a secret place; places of the wrong kind or unknown ids; unknown species;
   journal entries and points.
4. Stable and side-effect free: 1,000 random players (milestones, landmarks, secrets, sightings, discoveries,
   relaunches) — after every event the memories are exactly those whose fact the game's real path has established,
   in their fixed order; the same after each relaunch; and asking (twice) changes nothing: no points, coins, items,
   relationships, requests, saves or rewards are touched (every such call is recorded), no signal is emitted, and
   every saved section and the points are byte-identical before and after.
Broken designs, applied to the real sources, are shown to fail: every memory shown, a sighting remembered without the
sighting, the secret memory from the curiosity flag, the harvest memory from the harvest count, the secret memory from
any place reached, the first secret needing two, every farm memory from the
first seed, remembering that pays, remembering that records the sighting, remembering that announces, the memories
kept after asking, a load that keeps places of the wrong kind.
"""
import copy, glob, json, os, random, re, sys
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
    def is_empty(s): return len(s) == 0
    def duplicate(s, deep=False): return GArray(copy.deepcopy(list(s)) if deep else s)
    def clear(s): del s[:]
class GDict(dict):
    def has(s, k): return k in s
    def is_empty(s): return len(s) == 0
    def duplicate(s, deep=False): return GDict(copy.deepcopy(dict(s)) if deep else s)
    def merge(s, other, overwrite=False):
        for k, v in other.items():
            if overwrite or k not in s: s[k] = v
def wrap(v):  # a JSON value as the engine holds it
    if isinstance(v, dict): return GDict({k: wrap(x) for k, x in v.items()})
    if isinstance(v, list): return GArray(wrap(x) for x in v)
    return v
def typeof(v):
    if isinstance(v, bool): return TYPE_BOOL
    if isinstance(v, int): return gd_port.TYPE_INT
    if isinstance(v, float): return gd_port.TYPE_FLOAT
    if isinstance(v, str): return TYPE_STRING
    if isinstance(v, dict): return TYPE_DICTIONARY
    if isinstance(v, list): return TYPE_ARRAY
    return 0
def gd_str(v):  # String(value)
    if isinstance(v, bool): return "true" if v else "false"
    if isinstance(v, float) and v == int(v): return str(int(v))
    return str(v)
class Ledger:
    """Everything outside the records: points (add_points(0) is a no-op, as in points_manager.gd), and every call to
    coins, items, relationships, requests, saves, rewards — recorded, so any side effect of remembering shows."""
    def __init__(l): l.points, l.calls = 0, []
    def add_points(l, n):
        l.calls.append(("add_points", n))
        if n: l.points += n
    def __getattr__(l, k):
        if k.startswith("__"): raise AttributeError(k)
        return lambda *a: l.calls.append((k, a))
class SIM:
    ledger = Ledger()
    fm = em = jm = pr = None
    discovered = set()
    @staticmethod
    def is_discovered(i): return i in SIM.discovered
gd_port.HELPERS.update(GArray=GArray, GDict=GDict, Array=lambda a=None: GArray(a or []), String=gd_str, str=str, _typeof=typeof,
                       TYPE_BOOL=TYPE_BOOL, TYPE_STRING=TYPE_STRING, TYPE_ARRAY=TYPE_ARRAY, TYPE_DICTIONARY=TYPE_DICTIONARY, SIM=SIM,
                       int=lambda v=0: int(float(v)) if isinstance(v, str) else int(v), bool=bool)
def prep(src):
    src = re.sub(r"\bfor (\w+): [\w\[\]]+ in ", r"for \1 in ", src)              # typed loop variables
    src = re.sub(r"(?<![\w\]])\[\](?!\w)", "GArray()", src)                      # empty arrays are Godot Arrays
    return src

# ---------------------------------------------------------------- the project's data
MD_SRC = _src("scripts", "journal", "memory_definition.gd")
MD = type("MD", (), dict(re.findall(r'^const (\w+) := "(\w+)"$', MD_SRC, re.M)))
class Definition:
    def __init__(d, **kw): d.__dict__.update(kw)
def load_memories():
    """As JournalManager._load_memories (pinned by the checker): every MemoryDefinition with an id, by order."""
    out = []
    for f in sorted(glob.glob(os.path.join(REPO, "data", "memories", "*.tres"))):
        t = open(f, encoding="utf-8").read()
        v = _vals(f)
        if 'script_class="MemoryDefinition"' in t and v.get("id"):
            out.append(Definition(id=v["id"], text=v.get("text", ""), order=int(v.get("order", "0")), record=v.get("record", ""), fact_id=v.get("fact_id", "")))
    return sorted(out, key=lambda m: m.order)
MEMORIES = load_memories()
PLACES = sorted((Definition(id=v["id"], secret=v.get("secret") == "true", garden=v.get("garden") == "true", order=int(v.get("order", "0")),
                            curiosity_discovery_id=v.get("curiosity_discovery_id", ""))
                 for v in map(_vals, glob.glob(os.path.join(REPO, "data", "places", "*.tres")))), key=lambda p: p.order)
SECRETS, LANDMARKS = [p.id for p in PLACES if p.secret], [p.id for p in PLACES if not p.secret]
PAIRED = sorted({p.curiosity_discovery_id for p in PLACES if p.curiosity_discovery_id})
SPECIES = sorted((Definition(id=v["id"], order=int(v.get("order", "0"))) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "wildlife", "*.tres")))),
                 key=lambda s: s.order)
FM_SRC = _src("scripts", "autoload", "farm_manager.gd")
GM = re.search(r"^func get_milestones\(.*?(?=^func )", FM_SRC, re.M | re.S).group(0)
MILESTONES = [re.search(rf'^const {c} := "(\w+)"', FM_SRC, re.M).group(1) for c in re.findall(r"_milestone_row\(([A-Z_]+),", GM)]
MILESTONES += ["grown:" + v["crop_id"] for v in map(_vals, sorted(glob.glob(os.path.join(REPO, "data", "crops", "*.tres")))) if int(v.get("starting_seeds", "1")) > 0]
RULES = {v["id"]: int(v.get("points", "0")) for v in map(_vals, glob.glob(os.path.join(REPO, "data", "rewards", "*.tres")))}
SECTION_TYPES = {k: v for k, v in re.findall(r'^\t"(\w+)": \[(TYPE_\w+)', _src("scripts", "autoload", "save_manager.gd"), re.M)}
assert MEMORIES and SECRETS and LANDMARKS and SPECIES and len(MILESTONES) >= 5
assert all(SECTION_TYPES.get(s) for s in ("farm", "exploration", "journal_entries", "wildlife_sightings"))
class Rewards:
    def has(r, rid): return rid in RULES
    def points(r, rid): return RULES.get(rid, 0)

# ---------------------------------------------------------------- the real scripts
JM_FUNCS = ["get_memories", "is_remembered", "record_sighting", "has_sighted", "get_sighted_ids", "get_species", "get_sightings_save_data",
            "apply_sightings_save_data", "get_save_data", "apply_save_data"]
EM_FUNCS = ["mark_landmark_reached", "mark_secret_location_found", "_maybe_award_curiosity_bonus", "has_reached_landmark", "has_found_secret_location",
            "get_found_secret_count", "get_garden_place_id", "get_save_data", "apply_save_data", "_restore_places", "_was_paid", "_find_place"]
FM_FUNCS = ["is_milestone_reached", "_reach", "notify_place_reached", "is_garden_found", "get_activity_counts", "get_save_data", "apply_save_data", "_find_crop"]
OTHERS = {n: "SIM.ledger" for n in ("PointsManager", "Wallet", "Inventory", "Market", "Relationships", "Requests", "CollectionManager",
                                    "DailyDiscoveryManager", "SaveManager", "GameState")}
def sources():
    return {"jm": _src("scripts", "autoload", "journal_manager.gd"), "em": _src("scripts", "autoload", "exploration_manager.gd"), "fm": FM_SRC,
            "pr": _src("scripts", "rewards", "progression_rewards.gd")}
def build(s):
    ext = dict(OTHERS, FarmManager="SIM.fm", ExplorationManager="SIM.em", ProgressionRewards="SIM.pr", DiscoveryManager="SIM", MemoryDefinition="MD")
    gd_port.HELPERS["MD"] = MD
    PR, _ = translate(s["pr"], "ProgressionRewards", ext, ["reach"])
    JM, _ = translate(prep(s["jm"]), "JournalManager", ext, JM_FUNCS)
    EM, _ = translate(prep(s["em"]), "ExplorationManager", ext, EM_FUNCS)
    FM, _ = translate(prep(s["fm"]), "FarmManager", ext, FM_FUNCS)
    return PR, JM, EM, FM

class Game:
    """One process: the three autoloads with their data, loaded from `disk` at boot as SaveManager would (each section of
    the right type to its owner), and a save that writes them back."""
    def __init__(g, kit, disk=None):
        PR, JM, EM, FM = kit
        SIM.pr, g.ledger = PR(), Ledger()
        SIM.ledger = g.ledger
        g.jm, g.em, g.fm = JM(), EM(), FM()
        g.jm._species, g.jm._memories = GArray(SPECIES), GArray(MEMORIES)
        g.em._places, g.em._rewards, g.em._secret_place_count = GArray(PLACES), Rewards(), len(SECRETS)
        g.fm._rewards = Rewards()
        g.fm._crops = GArray(Definition(crop_id=c.split(":", 1)[1]) for c in MILESTONES if c.startswith("grown:"))
        g.fm._unlock_plots_for = lambda mid: 0
        g.fm._give_starting_seeds = g.fm._start_fresh_seeds = g.fm._update_garden_interest = lambda: None
        g.fm._grant_found_seeds = lambda source, sid: None
        g.signals = [getattr(o, n) for o in (g.jm, g.em, g.fm) for n in vars(o) if isinstance(getattr(o, n), gd_port.Signal)]
        g.activate()
        if disk:
            g.load(disk)
    def activate(g):
        SIM.jm, SIM.em, SIM.fm, SIM.ledger = g.jm, g.em, g.fm, g.ledger
    def load(g, text):
        data = wrap(json.loads(text))
        ok = lambda k, v: (SECTION_TYPES[k] == "TYPE_DICTIONARY" and isinstance(v, dict)) or (SECTION_TYPES[k] == "TYPE_ARRAY" and isinstance(v, list))
        data = GDict({k: v for k, v in data.items() if k in SECTION_TYPES and ok(k, v)})
        g.jm.apply_save_data(data.get("journal_entries", GDict()))
        g.fm.apply_save_data(data.get("farm", GDict()))
        g.em.apply_save_data(data.get("exploration", GDict()))
        g.jm.apply_sightings_save_data(data.get("wildlife_sightings", GArray()))
    def save(g):
        g.activate()
        return json.dumps(godot_json({"save_version": 9, "points": g.ledger.points, "journal_entries": g.jm.get_save_data(), "farm": g.fm.get_save_data(),
                                      "exploration": g.em.get_save_data(), "wildlife_sightings": g.jm.get_sightings_save_data()}))
    def memories(g):
        g.activate()
        return [m.id for m in g.jm.get_memories()]
    def state(g):  # every saved section, the points, every call outside the records, every signal emitted
        return (g.save(), g.ledger.points, len(g.ledger.calls), [s.emitted for s in g.signals])
    def act(g, ev):
        g.activate()
        kind, x = ev
        if kind == "milestone": g.fm._reach(x, "")
        elif kind == "landmark": g.em.mark_landmark_reached(x)
        elif kind == "secret": g.em.mark_secret_location_found(x)
        elif kind == "sighting": g.jm.record_sighting(x)
        elif kind == "discovery": SIM.discovered.add(x)

def expected(facts):
    """The memories whose fact the game's own path has established (facts: kind -> set of ids), in their order."""
    def holds(m):
        if m.record == MD.FARM_MILESTONE: return m.fact_id in facts["milestone"]
        if m.record == MD.SECRET_PLACE: return bool(facts["secret"]) if m.fact_id == "" else m.fact_id in facts["secret"]
        if m.record == MD.WILDLIFE: return m.fact_id in facts["sighting"]
        return False
    return [m.id for m in MEMORIES if holds(m)]
def raw_oracle(save):
    """The memories a raw save's records prove, from the JSON alone (as run_save_fixtures.sh does in Godot)."""
    sec = lambda k: save.get(k) if isinstance(save.get(k), dict) else {}
    lst = lambda v: v if isinstance(v, list) else []
    kinds = {p.id: p.secret for p in PLACES}
    facts = {"milestone": set(x for x in lst(sec("farm").get("milestones")) if isinstance(x, str)),
             "landmark": {x for x in lst(sec("exploration").get("landmarks")) if isinstance(x, str) and kinds.get(x) is False},
             "secret": {x for x in lst(sec("exploration").get("secrets")) if isinstance(x, str) and kinds.get(x) is True},
             "sighting": {x for x in lst(save.get("wildlife_sightings")) if x in {s.id for s in SPECIES}}}
    return sorted(expected(facts))

def fact_event(m):
    if m.record == MD.FARM_MILESTONE: return ("milestone", m.fact_id)
    if m.record == MD.SECRET_PLACE: return ("secret", m.fact_id or SECRETS[0])
    return ("sighting", m.fact_id)

def run(s, quick=False):
    """Every property; returns the failures (an empty list = all held)."""
    kit = build(s)
    fails = []
    def check(ok, what):
        if not ok: fails.append(what)
    fact_ids = {fact_event(m) for m in MEMORIES}
    # 1. each memory only with its own fact
    g = Game(kit)
    check(g.memories() == [], "a new game remembers something")
    for m in MEMORIES:
        SIM.discovered = set()
        g = Game(kit)
        g.act(fact_event(m))
        check(g.memories() == [m.id], f"{m.id}'s event alone gives {g.memories()}")
    for ev in [("milestone", x) for x in MILESTONES] + [("landmark", x) for x in LANDMARKS] + [("sighting", "dragon"), ("sighting", "")]:
        if ev in fact_ids: continue
        g = Game(kit)
        g.act(ev)
        check(g.memories() == [], f"{ev} (no memory's fact) gives {g.memories()}")
    # 2. the old-save fixtures
    want_by_version = {}
    for v in range(10):
        path = os.path.join(REPO, "tools", "fixtures", "saves", f"v{v}", "save.json")
        text = open(path, encoding="utf-8").read()
        g = Game(kit, text)
        got = g.memories()
        want_by_version[v] = got
        check(sorted(got) == raw_oracle(json.loads(text)) and got, f"v{v}: {got}, its records prove {raw_oracle(json.loads(text))}")
        again = Game(kit, g.save())
        check(again.memories() == got, f"v{v}: after a save and a relaunch {again.memories()}, before {got}")
        check(g.memories() == got, f"v{v}: asking again gives {g.memories()}")
    by_record = lambda *recs: [m.id for m in MEMORIES if m.record in recs]
    farm_mems = [m.id for m in MEMORIES if m.record == MD.FARM_MILESTONE and m.fact_id in ("first_seed", "first_harvest")]
    for v in range(10):
        want = farm_mems + ([] if v < 5 else [m for m in by_record(MD.SECRET_PLACE)]) + ([] if v < 9 else [m.id for m in MEMORIES if m.record == MD.WILDLIFE and m.fact_id in ("rabbit", "butterfly")])
        check(sorted(want_by_version[v]) == sorted(want), f"v{v} fixture: {want_by_version[v]}, expected {sorted(want)}")
    # 3. never inferred from what surrounds a fact
    crafted = {
        "a harvest without the milestone": {"farm": {"milestones": [], "counts": {"planted": 4, "harvested": 3}, "grown": ["wild_carrot"], "harvested_plots": ["plot_1"]}},
        "the farm's garden flag and a landmark": {"farm": {"milestones": [], "garden_found": True}, "exploration": {"landmarks": LANDMARKS[:2], "secrets": []}},
        "the bonus flags without a secret": {"exploration": {"landmarks": [], "secrets": [], "curiosity_bonus": True, "all_secrets_bonus": True}},
        "malformed bonus flags": {"exploration": {"secrets": [], "curiosity_bonus": "yes", "all_secrets_bonus": 1}},
        "places of the wrong kind / unknown": {"exploration": {"landmarks": SECRETS[:2] + ["nowhere", 5], "secrets": LANDMARKS + ["nowhere", 7, None]}},
        "unknown species": {"wildlife_sightings": ["dragon", 3, None, {"id": "rabbit"}]},
        "sections of the wrong type": {"farm": ["first_harvest"], "exploration": "quiet_farm", "wildlife_sightings": {"rabbit": True}},
        "journal entries and points": {"points": 9999, "journal_entries": {"blue_mushroom": {"id": "blue_mushroom", "points_earned": 5}}},
    }
    for name, save in crafted.items():
        g = Game(kit, json.dumps(save))
        check(g.memories() == [], f"never inferred — {name}: {g.memories()}")
    g = Game(kit, json.dumps({"wildlife_sightings": ["dragon", "rabbit", "rabbit", 4]}))
    check(g.memories() == [m.id for m in MEMORIES if m.record == MD.WILDLIFE and m.fact_id == "rabbit"], f"junk around a real sighting: {g.memories()}")
    # 4. random players: exactly the established facts, stable across relaunches, and asking changes nothing
    rng = random.Random(1401)
    events = ([("milestone", x) for x in MILESTONES] + [("landmark", x) for x in LANDMARKS] + [("secret", x) for x in SECRETS]
              + [("sighting", sp.id) for sp in SPECIES] + [("sighting", "dragon"), ("discovery", PAIRED[0]), ("discovery", PAIRED[-1])])
    for player in range(150 if quick else 1000):
        SIM.discovered = set()
        g = Game(kit)
        facts = {"milestone": set(), "landmark": set(), "secret": set(), "sighting": set()}
        for step in range(rng.randint(1, 30)):
            if rng.random() < 0.15:
                disk = g.save()
                g = Game(kit, disk)
            else:
                ev = rng.choice(events)
                g.act(ev)
                if ev[0] in facts and (ev[0] != "sighting" or ev[1] in {sp.id for sp in SPECIES}): facts[ev[0]].add(ev[1])
            before = g.state()
            got = g.memories()
            got2 = g.memories()
            after = g.state()
            if got != expected(facts) or got2 != got:
                fails.append(f"player {player} step {step}: {got} / {got2}, established {expected(facts)}"); break
            if before != after:
                fails.append(f"player {player} step {step}: asking changed the game (calls {before[2]}->{after[2]}, signals, saves or points)"); break
            if any(c[0] != "add_points" for c in g.ledger.calls):
                fails.append(f"player {player}: a call outside the records {[c for c in g.ledger.calls if c[0] != 'add_points'][:2]}"); break
        if len(fails) > 5: break
    return fails

if __name__ == "__main__":
    S = sources()
    bad = run(S)
    for b in bad[:10]: print("FAIL:", b)
    assert not bad, "player memories failed"
    def mut(key, old, new):
        s = dict(S); assert s[key].count(old) == 1, (key, old[:60]); s[key] = s[key].replace(old, new); return s
    IR = "func is_remembered(memory: MemoryDefinition) -> bool:\n"
    MUTANTS = {
        "every memory shown": mut("jm", "\t\tif is_remembered(memory):\n\t\t\tremembered.append(memory)", "\t\tremembered.append(memory)"),
        "a sighting remembered without the sighting": mut("jm", "return has_sighted(memory.fact_id) and get_species(memory.fact_id) != null", "return get_species(memory.fact_id) != null"),
        "the secret memory from the curiosity flag": mut("jm", "return ExplorationManager.get_found_secret_count() > 0", 'return ExplorationManager.get_save_data()["curiosity_bonus"]'),
        "the harvest memory from the harvest count": mut("jm", "return FarmManager.is_milestone_reached(memory.fact_id)",
                                                         'return FarmManager.is_milestone_reached(memory.fact_id) or (memory.fact_id == "first_harvest" and int(FarmManager.get_activity_counts()["harvested"]) > 0)'),
        "the secret memory from any place reached": mut("jm", "return ExplorationManager.get_found_secret_count() > 0", 'return ExplorationManager.get_found_secret_count() > 0 or not ExplorationManager.get_save_data()["landmarks"].is_empty()'),
        "the first secret needing two": mut("jm", "return ExplorationManager.get_found_secret_count() > 0", "return ExplorationManager.get_found_secret_count() > 1"),
        "every farm memory from the first seed": mut("jm", "return FarmManager.is_milestone_reached(memory.fact_id)", 'return FarmManager.is_milestone_reached("first_seed")'),
        "remembering pays": mut("jm", IR, IR + "\tPointsManager.add_points(1)\n"),
        "remembering records the sighting": mut("jm", "return has_sighted(memory.fact_id) and get_species(memory.fact_id) != null",
                                                "record_sighting(memory.fact_id)\n\t\t\treturn has_sighted(memory.fact_id) and get_species(memory.fact_id) != null"),
        "remembering announces": mut("jm", IR, IR + "\twildlife_sighted.emit(memory.record)\n"),
        "remembering gives an item": mut("jm", IR, IR + '\tInventory.add(memory.id)\n'),
        "the memories kept after asking": mut("jm", "\t\t\tremembered.append(memory)\n\treturn remembered", "\t\t\tremembered.append(memory)\n\t_memories = remembered\n\treturn remembered"),
        "a load that keeps places of the wrong kind": mut("em", "if place == null or place.secret != secret or into.has(place.id):", "if place == null or into.has(place.id):"),
    }
    caught, crashed, survivors = 0, [], []
    for name, s in MUTANTS.items():
        try:
            f = run(s, quick=True)
        except Exception as e:
            f = [f"crash {type(e).__name__}: {e}"]; crashed.append(name)
        if f: caught += 1
        else: survivors.append(name)
    print(f"player memories (M14.1): {len(MEMORIES)} memories over {len({m.record for m in MEMORIES})} saved records; each only with its fact; "
          f"fixtures v0-v9 as their records prove, stable through a relaunch; never inferred ({8} saves around a fact); 1000 random players exact, "
          f"asking changes nothing")
    print(f"broken designs: {caught} caught — {caught - len(crashed)} by behaviour, {len(crashed)} by a crash {crashed}")
    if survivors:
        print("SURVIVED:", survivors); sys.exit(1)
    print("ALL PLAYER MEMORY SIMULATIONS PASSED")
