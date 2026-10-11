#!/usr/bin/env python3
"""Old-save fixtures through the model (M15.3) — a Python port of today's SaveManager (read from its source, as
sim_save_versioning does) fed the real fixture files in tools/fixtures/saves/. This is the model half; the real-Godot
half is tools/fixtures/run_save_fixtures.sh.
1. Every save format the game has had (v0 = unversioned … v9 = SAVE_VERSION) has a fixture written by the commit that
   introduced it (meta.json), stamped with that version (v0: no stamp), holding exactly that version's sections.
   PENDING exception (M14.1a, removed once the introducing commit exists): the current SAVE_VERSION's fixture alone may
   come from the working tree, labelled pending and not historical with no commit; it is reported as PENDING and
   every other check still applies.
2. Each loads through the port: read_version, step-by-step migration (1 -> 2 moves farm.seeds / farm.basket into
   items), section type filtering; the result equals what the old version held in memory (expected.json): points,
   discoveries, journal, movement mode, seed and produce counts per crop, farm milestones and plots (clock-derived
   plot fields within 0.05 s), inventory (v3+), the coin ledger (v4+), exploration (v5+), friendship (v6+), the
   request (v7+), world time (v8+), wildlife sightings (v9). Sections a version never saved are absent, so their
   systems start fresh.
3. newer (stamped past SAVE_VERSION) is neither loaded nor overwritten; malformed is ignored like a damaged file.
The port is tied to the source (load order, the newer-save block, every section applied). Broken ports (a skipped
step, a missing step, a newer save accepted, a missing fixture) are
shown to fail; kills by a crash are reported separately.
"""
import copy, json, math, os, re, glob

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FIX = os.path.join(REPO, "tools", "fixtures", "saves")
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
for n in range(SAVE_VERSION):
    if n != 1:
        assert re.search(rf"^\t\t\t{n}:\s*pass", _body("_migrate"), re.M), f"step {n} rewrites data: port it here"
assert re.search(r"^\t\t\t1:\s*_move_holdings_to_items\(data\)", _body("_migrate"), re.M)
# The port below follows load_game's order and its newer-save refusal; every section reaches its system.
LG = _body("load_game")
assert LG.find("read_version(parsed)") < LG.find("if version > SAVE_VERSION:") < LG.find("_migrate(parsed, version)") \
    < LG.find("_valid_sections(data)") < LG.find("PointsManager.set_points("), "load_game's order changed: update the port"
assert "_saving_blocked = true" in re.search(r"if version > SAVE_VERSION:(.*?)return false", LG, re.S).group(1), "a newer save must block saving"
assert re.search(r"if _saving_blocked:\s*push_warning\([^)]*\)\s*return", _body("save_game")), "save_game must honour the block"
assert all(f'data.get("{k}"' in LG for k in SECTIONS), "every saved section is handed to its system on load"
def _item_vals(f): return dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', open(f, encoding="utf-8").read(), re.M))
ITEM_OF = {(v.get("crop_id", ""), v.get("category", "seed")): v["id"] for v in map(_item_vals, sorted(glob.glob(os.path.join(REPO, "data", "items", "*.tres"))))}
# Which version introduced each section (sections a fixture of that version must hold, and no others).
INTRODUCED = {"points": 0, "discovered_ids": 0, "journal_entries": 0, "daily_discovery": 0, "farm": 0, "settings": 0, "items": 2,
              "wallet": 4, "exploration": 5, "relationships": 6, "requests": 7, "world_time": 8, "wildlife_sightings": 9}
assert sorted(INTRODUCED) == sorted(SECTIONS), "a section was added: record the version that introduced it"
CLOCK_FIELDS = ("stage_time_left", "thirsty_for", "longest_thirst")

# ---------------------------------------------------------------- 2. port
def godot_json(text):
    """JSON.parse_string: numbers become floats; None when the text does not parse."""
    def conv(x):
        if isinstance(x, bool): return x
        if isinstance(x, int): return float(x)
        if isinstance(x, list): return [conv(v) for v in x]
        if isinstance(x, dict): return {k: conv(v) for k, v in x.items()}
        return x
    try: return conv(json.loads(text))
    except ValueError: return None
def gd_type(v): return bool if isinstance(v, bool) else type(v)
def step_1(data):  # SaveManager._move_holdings_to_items (M04.2)
    items, farm = {}, data.get("farm")
    if isinstance(farm, dict) and farm:
        seeds, basket = farm.get("seeds", {}), farm.get("basket", {})
        farm["starter_seeds"] = list(seeds) if isinstance(seeds, dict) else []
        for c, n in (seeds.items() if isinstance(seeds, dict) else []):
            if (c, "seed") in ITEM_OF: items[ITEM_OF[(c, "seed")]] = [n]
        for c, k in (basket.items() if isinstance(basket, dict) else []):
            if (c, "produce") in ITEM_OF: items[ITEM_OF[(c, "produce")]] = k
        farm.pop("seeds", None); farm.pop("basket", None)
    data["items"] = items
def read_version(save):
    if KEY not in save: return 0
    v = save[KEY]
    if gd_type(v) not in (int, float): return -1
    n = float(v)
    if n < 0 or n != math.floor(n): return -1
    return int(n)
def load(text, P):
    """SaveManager.load_game: -> (sections dict | None, saving_blocked)."""
    parsed = godot_json(text)
    if not isinstance(parsed, dict): return None, False
    v = read_version(parsed)
    if v < 0: return None, False
    if v > SAVE_VERSION and not P.get("accept_newer"): return None, True
    data = copy.deepcopy(parsed)
    while v < SAVE_VERSION:
        if v not in P["steps"]: return None, False
        if v == 1 and not P.get("skip_step_1"): step_1(data)
        v += 1; data[KEY] = float(v)
    if P.get("no_filter"): return {k: data[k] for k in SECTIONS if k in data}, False
    return {k: data[k] for k in SECTIONS if k in data and gd_type(data[k]) in SECTIONS[k]}, False

# ---------------------------------------------------------------- 3. checks
def plots_match(a, b):
    if not isinstance(a, dict) or not isinstance(b, dict) or sorted(a) != sorted(b): return False
    for pid in b:
        if sorted(a[pid]) != sorted(b[pid]): return False
        for k in b[pid]:
            if k in CLOCK_FIELDS:
                if abs(float(a[pid][k]) - float(b[pid][k])) > 0.05: return False
            elif godot_json(json.dumps(a[pid][k])) != godot_json(json.dumps(b[pid][k])): return False
    return True
PENDING = []
def run(P):
    p_ = []
    PENDING.clear()
    present = sorted(os.path.basename(d) for d in glob.glob(os.path.join(FIX, "v[0-9]")) if os.path.isfile(os.path.join(d, "save.json")))
    present = [v for v in present if v not in P.get("hide", ())]
    want = [f"v{n}" for n in range(SAVE_VERSION + 1)]
    if present != want: p_.append(f"one fixture for every save format v0..v{SAVE_VERSION} (have {present})")
    for v in present:
        n = int(v[1:]); d = os.path.join(FIX, v)
        text = open(os.path.join(d, "save.json"), encoding="utf-8").read()
        e = godot_json(open(os.path.join(d, "expected.json"), encoding="utf-8").read())
        meta = json.load(open(os.path.join(d, "meta.json"), encoding="utf-8"))
        raw = godot_json(text)
        pending = meta.get("pending") is True and meta.get("historical") is False and meta.get("commit") is None and n == SAVE_VERSION and not P.get("no_pending")
        if pending: PENDING.append(v)
        elif meta.get("version") != v or not re.fullmatch(r"[0-9a-f]{7}", meta.get("commit") or "") or "generate_save_fixture.gd" not in meta.get("generator", "") \
           or "pending" in meta or "historical" in meta:
            p_.append(f"{v}: meta.json names the commit and the generator that wrote it")
        if not isinstance(raw, dict) or read_version(raw) != n or (n == 0 and KEY in raw) or int(e["save_version_written"]) != n:
            p_.append(f"{v}: written by a version-{n} SaveManager (stamp {raw.get(KEY) if isinstance(raw, dict) else raw})"); continue
        have = sorted(k for k in raw if k != KEY)
        if have != sorted(k for k, since in INTRODUCED.items() if since <= n):
            p_.append(f"{v}: exactly the sections version {n} saved ({have})")
        data, blocked = load(text, P)
        if data is None or blocked: p_.append(f"{v}: loads"); continue
        items, farm = data.get("items", {}), data.get("farm", {})
        checks = {
            "points": data.get("points") == e["points"],
            "discovered ids": sorted(data.get("discovered_ids", [])) == e["discovered_ids"],
            "journal": all((i in data.get("journal_entries", {})) == bool(h) for i, h in e["journal_has_entry"]),
            "movement mode": data.get("settings", {}).get("movement_mode") == e["movement_mode"],
            "seeds": all(sum(items.get(ITEM_OF.get((c, "seed"), "?"), [0.0])) == e["seeds"][c] for c in e["seeds"]),
            "produce": all((items.get(ITEM_OF.get((c, "produce"), "?"), [0.0, 0.0, 0.0]) + [0.0, 0.0, 0.0])[:3] == e["produce"][c] for c in e["produce"]),
            "milestones": sorted(farm.get("milestones", [])) == sorted(m["id"] for m in e["milestones"] if m["reached"]),
            "plots": plots_match(farm.get("plots", {}), e["plots"]),
            "old holdings gone from farm": "seeds" not in farm and "basket" not in farm,
        }
        if n >= 3: checks["inventory"] = items == e["inventory"]
        checks["wallet"] = (len(data.get("wallet", {}).get("ledger", [])) == e.get("ledger_entries", 0)
                            and sum(x["amount"] for x in data.get("wallet", {}).get("ledger", [])) == e.get("coins", 0))
        ex = data.get("exploration", {})
        checks["exploration"] = (("overlook" in ex.get("landmarks", [])) == (e["landmark_reached"] if n >= 5 else False)
                                 and ("secluded_pond_nook" in ex.get("secrets", [])) == (e["secret_found"] if n >= 5 else False))
        checks["friendship"] = data.get("relationships", {}).get("villager", {}).get("friendship", 0.0) == e.get("friendship", 0)
        checks["request"] = data.get("requests", {}).get("villager_stones", "") == (e.get("request_state", "") if n >= 7 else "")
        wt = data.get("world_time")
        checks["world time"] = (wt is None) if n < 8 else (wt["day"] == e["clock"][0] and abs(wt["fraction"] - e["clock"][1]) < 0.0005)
        ws = data.get("wildlife_sightings")
        checks["wildlife sightings"] = (ws is None) if n < 9 else sorted(ws) == e["wildlife_sighted"]
        for what, ok in checks.items():
            if not ok: p_.append(f"{v}: {what} as the old version held it")
    newer = open(os.path.join(FIX, "newer", "save.json"), encoding="utf-8").read()
    if read_version(godot_json(newer) or {}) <= SAVE_VERSION: p_.append("newer: stamped past SAVE_VERSION")
    data, blocked = load(newer, P)
    if data is not None or not blocked: p_.append("newer: not loaded, and saving blocked so the file survives")
    bad = open(os.path.join(FIX, "malformed", "save.json"), encoding="utf-8").read()
    if load(bad, P)[0] is not None: p_.append("malformed: ignored like a damaged file")
    return p_

GOOD = {"steps": STEPS}
bad = run(GOOD)
for b in bad: print("FAIL:", b)
assert not bad, "save fixture model check failed"
MUTANTS = {
    "the 1 -> 2 step skipped": {"steps": STEPS, "skip_step_1": True},
    "step 4 missing": {"steps": [s for s in STEPS if s != 4]},
    "a newer save loaded": {"steps": STEPS, "accept_newer": True},
    "the v5 fixture missing": {"steps": STEPS, "hide": ("v5",)},
    "the pending allowance withdrawn while v9 is still pending": {"steps": STEPS, "no_pending": True},
}
# Equivalent here, by construction: real saves never hold a wrongly typed section, so dropping SaveManager's type filter
# changes nothing these fixtures can show — sim_save_versioning covers it with 3,000 random malformed saves.
EQUIVALENT = {"type filter dropped": {"steps": STEPS, "no_filter": True}}
for name, P in EQUIVALENT.items(): assert not run(P), f"{name} is meant to be equivalent for real fixtures"
caught = crash = 0; survivors, crashes = [], []
for name, P in MUTANTS.items():
    try:
        if run(P): caught += 1
        else: survivors.append(name)
    except Exception as ex:
        crash += 1; crashes.append(f"{name}: {type(ex).__name__}")
bad = run(GOOD)
print(f"save fixtures (model): v0..v{SAVE_VERSION} saves (each written by the commit that introduced its format) load, "
      f"migrate and equal what the old version held; newer refused, malformed ignored")
if PENDING: print(f"PENDING (not historical, from the working tree; M15.3 exception for the current SAVE_VERSION only): {PENDING}")
print(f"broken designs: {caught + crash} caught — {caught} by behaviour, {crash} by a crash {crashes}; "
      f"{len(EQUIVALENT)} equivalent for real saves (covered by sim_save_versioning)")
if survivors:
    print("SURVIVED:", survivors); raise SystemExit(1)
print("ALL SAVE FIXTURE SIMULATIONS PASSED")
