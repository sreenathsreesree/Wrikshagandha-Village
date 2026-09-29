#!/usr/bin/env python3
"""Model checks for save versioning (M04.0, P-01) — a Python port of
SaveManager.save_game/load_game, not the engine.
1. Read from the project: SAVE_VERSION, VERSION_KEY, the section type
   table, the migration steps, the load order.
2. Godot's JSON is mimicked (every number comes back as a float); each
   system's apply is typed and fails on a wrong type, like the GDScript
   typed parameters it stands for.
3. Cases: a current save round-trips exactly (including M03.3 farm plots and
   unloaded plot states); a pre-M04.0 save (no version) loads and is stamped
   on the next save; a newer save is neither loaded nor overwritten; a
   malformed version or file is ignored like a corrupted file; wrongly typed
   sections fall back to defaults without breaking the rest; migration
   dispatch walks every step in order and rejects a missing one; 3,000
   random saves never reach a system with the wrong type, and loading is
   deterministic.
"""
import copy, json, math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SM = open(os.path.join(REPO, "scripts", "autoload", "save_manager.gd"), encoding="utf-8").read()
def _body(name):
    m = re.search(rf"^(?:static )?func {name}\(.*?(?=^func |^static func |\Z)", SM, re.M | re.S)
    assert m, name
    return m.group(0)

# ---------------------------------------------------------------- 1. read from the project
SAVE_VERSION = int(re.search(r"^const SAVE_VERSION := (\d+)", SM, re.M).group(1))
KEY = re.search(r'^const VERSION_KEY := "(\w+)"', SM, re.M).group(1)
TYPE = {"TYPE_INT": int, "TYPE_FLOAT": float, "TYPE_ARRAY": list, "TYPE_DICTIONARY": dict}
SECTIONS = {k: [TYPE[t.strip()] for t in v.split(",")] for k, v in re.findall(r'^\t"(\w+)": \[([^\]]*)\],', SM, re.M)}
STEPS = [int(x) for x in re.findall(r"^\t\t\t(\d+):", _body("_migrate"), re.M)]
assert SECTIONS and STEPS == list(range(SAVE_VERSION)), (SECTIONS, STEPS)
LG = _body("load_game")
assert LG.find("read_version(parsed)") < LG.find("if version > SAVE_VERSION:") < LG.find("_migrate(parsed, version)") \
    < LG.find("_valid_sections(data)") < LG.find("PointsManager.set_points(")
assert "_saving_blocked = true" in re.search(r"if version > SAVE_VERSION:(.*?)return false", LG, re.S).group(1)
assert re.search(r"if _saving_blocked:\s*push_warning\([^)]*\)\s*return", _body("save_game"))

# ---------------------------------------------------------------- 2. port
def godot_json(text):
    """JSON.parse_string: numbers become floats; bools stay bools."""
    def conv(x):
        if isinstance(x, bool): return x
        if isinstance(x, int): return float(x)
        if isinstance(x, list): return [conv(v) for v in x]
        if isinstance(x, dict): return {k: conv(v) for k, v in x.items()}
        return x
    try: return conv(json.loads(text))
    except ValueError: return None
def gd_type(v):
    if isinstance(v, bool): return bool
    return type(v)
class Systems:  # the six sections' owners, with typed apply functions
    def __init__(s): s.state = {"points": 0, "discovered_ids": [], "journal_entries": {}, "daily_discovery": {}, "farm": {}, "settings": {}}
    def apply(s, key, value):
        want = {"points": (int, float), "discovered_ids": (list,)}.get(key, (dict,))
        if gd_type(value) not in want: raise TypeError(f"{key}: wrong type reached the system")
        s.state[key] = int(value) if key == "points" else copy.deepcopy(value)
class SaveManager:
    def __init__(sm, disk): sm.disk, sm.blocked = disk, False
    def save(sm, systems):
        if sm.blocked: return False
        data = {KEY: SAVE_VERSION}
        for k in SECTIONS: data[k] = systems.state[k]
        sm.disk["save.json"] = json.dumps(data); return True
    @staticmethod
    def read_version(save):
        if KEY not in save: return 0
        v = save[KEY]
        if gd_type(v) not in (int, float): return -1
        n = float(v)
        if n < 0 or n != math.floor(n): return -1
        return int(n)
    @staticmethod
    def migrate(save, v, steps=None):
        steps = STEPS if steps is None else steps
        data = copy.deepcopy(save)
        while v < SAVE_VERSION_MODEL[0]:
            if v not in steps: return {}
            v += 1; data[KEY] = float(v)
        return data
    def load(sm, systems):
        if "save.json" not in sm.disk: return False
        parsed = godot_json(sm.disk["save.json"])
        if not isinstance(parsed, dict): return False
        v = sm.read_version(parsed)
        if v < 0: return False
        if v > SAVE_VERSION: sm.blocked = True; return False
        data = sm.migrate(parsed, v)
        if not data: return False
        valid = {k: data[k] for k in SECTIONS if k in data and gd_type(data[k]) in SECTIONS[k]}
        for k in SECTIONS:
            systems.apply(k, valid.get(k, {"points": 0, "discovered_ids": []}.get(k, {})))
        return True
SAVE_VERSION_MODEL = [SAVE_VERSION]

# ---------------------------------------------------------------- 3. cases
FARM = {"version": 1, "seeds": {"wild_carrot": 2}, "basket": {"wild_carrot": [1, 0, 1]}, "milestones": ["first_harvest"],
        "counts": {"planted": 3, "harvested": 1}, "harvested_plots": ["farm_plot_01"], "garden_found": True,
        "plots": {"farm_plot_01": {"state": "GROWING", "soil_memory": ["meadow_herb"], "crop": "wild_carrot", "stage": 2,
                                   "needs_water": True, "stage_time_left": 12.5, "soil": 2, "care": 1, "quality": 1,
                                   "longest_thirst": 30.0, "thirsty_for": 4.0},
                  "farm_plot_02": {"state": "SOIL", "soil_memory": []}}}
def full_state():
    s = Systems(); s.state.update(points=120, discovered_ids=["river_stone", "wild_mint"],
                                  journal_entries={"river_stone": {"name": "Smooth River Stone", "points_earned": 8.0}},
                                  daily_discovery={"target_id": "wild_mint", "target_date": "2026-09-29", "completed_date": ""},
                                  farm=copy.deepcopy(FARM), settings={"movement_mode": "tap_to_move"})
    return s
def roundtrip_equal(a, b): return godot_json(json.dumps(a)) == godot_json(json.dumps(b))

# current version: save -> load -> save is identical (farm, incl. M03.3 plot states)
disk = {}; a = full_state(); sm = SaveManager(disk); assert sm.save(a)
b = Systems(); assert SaveManager(disk).load(b)
assert all(roundtrip_equal(a.state[k], b.state[k]) for k in SECTIONS), "current save round-trips"
first = disk["save.json"]; SaveManager(disk).save(b); assert godot_json(disk["save.json"]) == godot_json(first), "save -> load -> save identical"
assert godot_json(first)[KEY] == SAVE_VERSION and roundtrip_equal(b.state["farm"], FARM), "farm (and its plot states) untouched"
# pre-M04.0 save (no version): loads the same, stamped on the next save
legacy = json.loads(first); del legacy[KEY]; disk = {"save.json": json.dumps(legacy)}
c = Systems(); assert SaveManager(disk).load(c) and all(roundtrip_equal(a.state[k], c.state[k]) for k in SECTIONS)
SaveManager(disk).save(c); assert godot_json(disk["save.json"])[KEY] == SAVE_VERSION, "legacy save stamped with save_version"
# newer save: neither loaded nor overwritten
for v in (SAVE_VERSION + 1, 99):
    newer = json.loads(first); newer[KEY] = v; newer["inventory"] = {"items": ["x"]}; text = json.dumps(newer)
    disk = {"save.json": text}; d = Systems(); sm = SaveManager(disk)
    assert not sm.load(d) and d.state == Systems().state and sm.blocked, "newer save not loaded"
    assert not sm.save(full_state()) and disk["save.json"] == text, "newer save never overwritten this session"
# malformed version / malformed file: ignored like a corrupted file (saving stays allowed)
for bad in ("1", True, None, -1, 1.5, [], {}, "abc"):
    m = json.loads(first); m[KEY] = bad; disk = {"save.json": json.dumps(m)}; e = Systems(); sm = SaveManager(disk)
    assert not sm.load(e) and e.state == Systems().state and not sm.blocked, f"malformed version {bad!r} rejected"
for garbage in ("[1,2]", '"text"', "{not json", "", "42"):
    disk = {"save.json": garbage}; assert not SaveManager(disk).load(Systems())
# wrongly typed sections: that section falls back to its default, the rest loads
for key, bad in (("farm", [1, 2]), ("points", "lots"), ("discovered_ids", {"a": 1}), ("journal_entries", 5), ("settings", "x"),
                 ("daily_discovery", True), ("points", True)):
    m = json.loads(first); m[key] = bad; disk = {"save.json": json.dumps(m)}; f = Systems()
    assert SaveManager(disk).load(f), key
    assert f.state[key] == Systems().state[key], f"{key}: default used"
    assert all(roundtrip_equal(f.state[k], a.state[k]) for k in SECTIONS if k != key), "other sections unaffected"
# unknown extra keys are ignored (same version)
m = json.loads(first); m["unknown_future_thing"] = {"a": 1}; disk = {"save.json": json.dumps(m)}
assert SaveManager(disk).load(Systems())
# migration dispatch: every step in order; a missing step rejects the save
SAVE_VERSION_MODEL[0] = 4
walked = SaveManager.migrate({"points": 1.0}, 0, steps=[0, 1, 2, 3])
assert walked[KEY] == 4.0 and walked["points"] == 1.0
assert SaveManager.migrate({"points": 1.0}, 1, steps=[0, 2, 3]) == {}, "a missing step rejects"
assert SaveManager.migrate({"points": 1.0, KEY: 4.0}, 4, steps=[]) == {"points": 1.0, KEY: 4.0}, "already current: returned unchanged"
SAVE_VERSION_MODEL[0] = SAVE_VERSION
assert SaveManager.migrate({"a": 1.0}, 0) == {"a": 1.0, KEY: float(SAVE_VERSION)}, "the real 0 -> 1 step changes nothing but the version"
# fuzz: nothing of the wrong type ever reaches a system; loading is deterministic
rnd = random.Random(8)
def junk(depth=0):
    r = rnd.random()
    if depth > 2 or r < 0.25: return rnd.choice([None, True, False, rnd.randint(-5, 5), rnd.uniform(-3, 3), "s", ""])
    if r < 0.6: return [junk(depth + 1) for _ in range(rnd.randint(0, 3))]
    return {rnd.choice(list(SECTIONS) + [KEY, "x"]): junk(depth + 1) for _ in range(rnd.randint(0, 4))}
outcomes = {"loaded": 0, "rejected": 0, "blocked": 0}
for _ in range(3000):
    doc = junk() if rnd.random() < 0.3 else {k: (junk(1) if rnd.random() < 0.4 else copy.deepcopy(json.loads(first).get(k)))
                                              for k in list(SECTIONS) + [KEY] if rnd.random() < 0.85}
    text = json.dumps(doc)
    r1, r2 = [], []
    for out in (r1, r2):
        s = Systems(); sm = SaveManager({"save.json": text}); ok = sm.load(s)       # a TypeError here = a crash in the game
        out.append((ok, sm.blocked, json.dumps(s.state, sort_keys=True)))
    assert r1 == r2, "deterministic"
    outcomes["blocked" if r1[0][1] else "loaded" if r1[0][0] else "rejected"] += 1
print(f"save_version {SAVE_VERSION}, migration steps {STEPS}, sections {sorted(SECTIONS)}: current round-trip, legacy stamp, "
      f"newer refused and kept, malformed rejected, bad sections defaulted, dispatch; 3000 random saves {outcomes}")
print("ALL SAVE VERSIONING SIMULATIONS PASSED")
