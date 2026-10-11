#!/usr/bin/env python3
"""Session vs persistent state (M15.2) — the rules over the registry in docs/ARCHITECTURE.md §11 (```state-registry),
run on the project's real sources, then on broken copies of them held in memory. tools/check_project.py imports
violations() from here, so the checker and this model apply one set of rules.
Rules:
 1. every autoload member variable is classified exactly once (persistent:<section> / derived / session / data), and
    the registry names no variable that does not exist;
 2. every save section (SaveManager.SECTION_TYPES, written in save_game) has persistent variables, all in the autoload
    that writes it; a persistent variable is read by its section's save function (or a same-file helper it calls);
 3. a variable classified derived / session / data never appears in a save function's own body;
 4. only GameState asks SaveManager to save or load;
 5. FarmPlot is the only world object whose state is saved: no other non-autoload script defines get_save_data /
    apply_save_data / capture (except a plain data class that is the declared type of a classified persistent autoload
    variable — ItemStore, Inventory._store), only FarmManager's save function captures, and FarmPlot.capture() saves
    exactly the registered fields;
 6. every save section is in the M15.3 fixture of the current SAVE_VERSION;
 7. a deferred item (elemental / Rishi progression, world changes, player memories) has no variable or section yet —
    once implemented it must be classified, not left deferred.
"""
import glob, json, os, re, sys

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CLASSES = ("persistent", "derived", "session", "data")
DEFERRED_PATTERNS = {"elemental_progression": r"element", "rishi_progression": r"rishi", "world_changes": r"world_change",
                     "player_memories": r"memor"}

def load_sources(repo=REPO):
    """{relative path: text} for project.godot, the architecture doc, every .gd outside tools/, and the current fixture."""
    src = {}
    for rel in ["project.godot", "docs/ARCHITECTURE.md"]:
        src[rel] = open(os.path.join(repo, rel), encoding="utf-8").read()
    for path in glob.glob(os.path.join(repo, "scripts", "**", "*.gd"), recursive=True):
        src[os.path.relpath(path, repo)] = open(path, encoding="utf-8").read()
    for path in glob.glob(os.path.join(repo, "tools", "fixtures", "saves", "v[0-9]*", "save.json")):
        src[os.path.relpath(path, repo)] = open(path, encoding="utf-8").read()
    return src

def func_body(text, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", text, re.M | re.S)
    return m.group(0) if m else ""

def code_only(text):
    return "\n".join(l.split("#")[0] if not l.lstrip().startswith("##") else "" for l in text.splitlines())

def violations(src):
    v = []
    doc = src.get("docs/ARCHITECTURE.md", "")
    m = re.search(r"```state-registry\n(.*?)```", doc, re.S)
    if not m:
        return ["docs/ARCHITECTURE.md has no state-registry block"]
    reg, capture_fields, deferred = {}, None, []
    for line in m.group(1).splitlines():
        parts = line.split()
        if not parts: continue
        if parts[0] == "farm_plot.capture": capture_fields = sorted(parts[1:]); continue
        if parts[0] == "deferred": deferred = parts[1:]; continue
        if len(parts) != 2: v.append(f"registry line not '<autoload>.<variable> <class>': {line}"); continue
        if parts[0] in reg: v.append(f"{parts[0]} is classified twice")
        reg[parts[0]] = parts[1]
    # the autoloads (project.godot) and their member variables
    autoloads = dict(re.findall(r'^(\w+)="\*?res://(scripts/autoload/\w+\.gd)"', src.get("project.godot", ""), re.M))
    stem_of = {name: os.path.basename(p)[:-3] for name, p in autoloads.items()}
    variables = {}
    for name, path in autoloads.items():
        for var in re.findall(r"^var (\w+)", src.get(path, ""), re.M):
            variables[f"{stem_of[name]}.{var}"] = path
    for key in sorted(set(variables) - set(reg)): v.append(f"{key} is not classified (rule 1)")
    for key in sorted(set(reg) - set(variables)): v.append(f"{key} is classified but does not exist (rule 1)")
    for key, cls in reg.items():
        if cls.split(":")[0] not in CLASSES or (cls.startswith("persistent") and ":" not in cls) or (":" in cls and not cls.startswith("persistent:")):
            v.append(f"{key}: unknown class '{cls}' (rule 1)")
    # the save sections and their owners (SaveManager.save_game)
    sm = src.get("scripts/autoload/save_manager.gd", "")
    section_types = re.findall(r'^\t"(\w+)": \[', sm, re.M)
    owners = {sec: (owner, fn) for sec, owner, fn in re.findall(r'^\t\t"(\w+)": (\w+)\.(\w+)\(\)', func_body(sm, "save_game"), re.M)}
    if sorted(owners) != sorted(section_types):
        v.append(f"save_game writes {sorted(owners)} but SECTION_TYPES lists {sorted(section_types)} (rule 2)")
    persistent = {}
    for key, cls in reg.items():
        if cls.startswith("persistent:"): persistent.setdefault(cls.split(":", 1)[1], []).append(key)
    for sec in sorted(set(persistent) - set(section_types)): v.append(f"persistent:{sec} is not a save section (rule 2)")
    save_bodies = {}
    for sec, (owner, fn) in owners.items():
        if owner not in stem_of:
            v.append(f"section {sec} is written by {owner}, not an autoload (rule 2)"); continue
        path, stem = autoloads[owner], stem_of[owner]
        text = code_only(src.get(path, ""))
        body = func_body(text, fn)
        save_bodies[stem] = save_bodies.get(stem, "") + body
        closure, seen, todo = body, {fn}, [fn]
        while todo:  # same-file helpers the save function calls
            for called in re.findall(r"\b(\w+)\(", func_body(text, todo.pop())):
                if called not in seen and re.search(rf"^func {called}\(", text, re.M):
                    seen.add(called); todo.append(called); closure += func_body(text, called)
        if not persistent.get(sec):
            v.append(f"section {sec} has no persistent variable in the registry (rule 2)")
        for key in persistent.get(sec, []):
            var_stem, var = key.split(".", 1)
            if var_stem != stem: v.append(f"{key} is persistent:{sec} but {sec} is written by {stem} (rule 2)")
            elif not re.search(rf"\b{re.escape(var)}\b", closure): v.append(f"{key} is persistent:{sec} but {stem}.{fn}() never reads it (rule 2)")
    for key, cls in reg.items():
        stem, var = key.split(".", 1)
        if not cls.startswith("persistent") and re.search(rf"\b{re.escape(var)}\b", save_bodies.get(stem, "")):
            v.append(f"{key} is {cls} but its autoload's save function reads it (rule 3)")
    # rule 4: only GameState saves or loads
    for path, text in src.items():
        if not path.endswith(".gd") or path == "scripts/autoload/save_manager.gd": continue
        if re.search(r"SaveManager\.(save_game|load_game)\(", code_only(text)) and path != "scripts/autoload/game_state.gd":
            v.append(f"{path} asks SaveManager to save or load — only GameState does (rule 4)")
    # rule 5: FarmPlot is the only saved world object. A plain data class (not a Node) may carry save functions only
    # as the declared type of a classified persistent autoload variable — it is that variable's state (ItemStore is
    # Inventory._store).
    owned_types = set()
    for key, cls in reg.items():
        if cls.startswith("persistent") and key in variables:
            t = re.search(rf"^var {re.escape(key.split('.', 1)[1])}\s*:\s*(\w+)", src.get(variables[key], ""), re.M)
            if t: owned_types.add(t.group(1))
    for path, text in src.items():
        if not path.endswith(".gd") or path.startswith("scripts/autoload/"): continue
        c = code_only(text)
        cname = re.search(r"^class_name (\w+)", c, re.M)
        data_class = re.search(r"^extends (RefCounted|Resource|Object)\b", c, re.M) and cname and cname.group(1) in owned_types
        for fn in ("get_save_data", "apply_save_data", "capture"):
            if re.search(rf"^func {fn}\(", c, re.M) and not (path == "scripts/farming/farm_plot.gd" and fn == "capture") \
               and not (data_class and fn != "capture"):
                v.append(f"{path} defines {fn}() — only FarmPlot.capture() is saved from the world (rule 5)")
    for stem, body in save_bodies.items():
        if ".capture()" in body and stem != "farm_manager": v.append(f"{stem}'s save function captures a world object (rule 5)")
    fp = func_body(code_only(src.get("scripts/farming/farm_plot.gd", "")), "capture")
    got_fields = sorted(set(re.findall(r'"(\w+)":', fp)))
    if capture_fields is None or got_fields != capture_fields:
        v.append(f"FarmPlot.capture() saves {got_fields}, the registry lists {capture_fields} (rule 5)")
    # rule 6: the current fixture holds every section
    sv = re.search(r"^const SAVE_VERSION := (\d+)", sm, re.M)
    fixture = src.get(f"tools/fixtures/saves/v{sv.group(1)}/save.json" if sv else "", "")
    try:
        keys = sorted(k for k in json.loads(fixture) if k != "save_version")
    except ValueError:
        keys = None
    if keys != sorted(section_types):
        v.append(f"the M15.3 fixture for save_version {sv.group(1) if sv else '?'} holds {keys}, not every section {sorted(section_types)} (rule 6)")
    # rule 7: deferred items stay unimplemented while deferred
    for item in deferred:
        if item not in DEFERRED_PATTERNS: v.append(f"unknown deferred item {item} (rule 7)"); continue
        pat = DEFERRED_PATTERNS[item]
        hits = [k for k in reg if re.search(pat, k.split(".", 1)[1])] + [s for s in section_types if re.search(pat, s)] \
             + [s for s in stem_of.values() if re.search(pat, s)]
        if hits: v.append(f"{item} is deferred but has state {hits} — classify it (rule 7)")
    if sorted(deferred) != sorted(DEFERRED_PATTERNS):
        v.append(f"the deferred list is {deferred}; an item leaves it only when designed and classified (rule 7)")
    return v

if __name__ == "__main__":
    S = load_sources()
    bad = violations(S)
    for b in bad: print("FAIL:", b)
    assert not bad, "state registry check failed"
    def mut(path, old, new):
        s = dict(S); assert old in s[path], (path, old[:50]); s[path] = s[path].replace(old, new, 1); return s
    PL, WA, IM, EX, FP, AR = ("scripts/autoload/points_manager.gd", "scripts/autoload/wallet.gd", "scripts/autoload/input_manager.gd",
                              "scripts/autoload/exploration_manager.gd", "scripts/farming/farm_plot.gd", "docs/ARCHITECTURE.md")
    sv = re.search(r"^const SAVE_VERSION := (\d+)", S["scripts/autoload/save_manager.gd"], re.M).group(1)
    MUTANTS = {
        "an unclassified autoload variable": mut(PL, "var points: int = 0\n", "var points: int = 0\nvar streak: int = 0\n"),
        "a registry entry for a removed variable": mut(AR, "wallet._balance derived\n", "wallet._balance derived\nwallet._gone session\n"),
        "a variable classified twice": mut(AR, "wallet._balance derived\n", "wallet._balance derived\nwallet._balance session\n"),
        "an unknown class": mut(AR, "wallet._balance derived\n", "wallet._balance cached\n"),
        "a persistent variable relabelled session": mut(AR, "wallet._ledger persistent:wallet", "wallet._ledger session"),
        "a session variable saved": mut(EX, '"curiosity_bonus": _curiosity_bonus_given,', '"curiosity_bonus": _curiosity_bonus_given,\n\t\t"beats": _summary_shown,'),
        "a persistent variable no longer saved": mut(WA, 'return {"ledger": _ledger.duplicate(true)}', 'return {"ledger": []}'),
        "a persistent variable under the wrong section": mut(AR, "wallet._ledger persistent:wallet", "wallet._ledger persistent:items"),
        "a new section with no classified state": mut("scripts/autoload/save_manager.gd", '\t"world_time": [TYPE_DICTIONARY],\n', '\t"world_time": [TYPE_DICTIONARY],\n\t"memos": [TYPE_DICTIONARY],\n'),
        "another script saves": mut("scripts/main.gd", "func _ready() -> void:\n", "func _ready() -> void:\n\tSaveManager.save_game()\n"),
        "a world object saves itself": mut("scripts/peaceful/rest_spot.gd", "func set_occupied(", "func get_save_data() -> Dictionary:\n\treturn {}\n\nfunc set_occupied("),
        "FarmPlot saves an unregistered field": mut(FP, '"state": ', '"wilt": 0, "state": '),
        "a data class saves without being persistent state": mut(AR, "inventory._store persistent:items", "inventory._store session"),
        "the current fixture lacks a section": {**S, f"tools/fixtures/saves/v{sv}/save.json": json.dumps({k: x for k, x in json.loads(S[f"tools/fixtures/saves/v{sv}/save.json"]).items() if k != "wallet"})},
        "a deferred item implemented but still deferred": mut(PL, "var points: int = 0\n", "var points: int = 0\nvar rishi_favour: int = 0\n"),
        "a deferred item dropped from the list": mut(AR, "deferred elemental_progression rishi_progression world_changes player_memories", "deferred elemental_progression rishi_progression world_changes"),
    }
    caught, survivors = 0, []
    for name, s in MUTANTS.items():
        if violations(s): caught += 1
        else: survivors.append(name)
    reg_n = len(re.findall(r"^\w+\.\w+ (?:persistent|derived|session|data)", re.search(r"```state-registry\n(.*?)```", S[AR], re.S).group(1), re.M))
    sec_n = len(re.findall(r'^\t"(\w+)": \[', S["scripts/autoload/save_manager.gd"], re.M))
    print(f"state registry (M15.2): {reg_n} autoload variables classified; {sec_n} sections each with its owner's persistent state; "
          f"only GameState saves; FarmPlot the only saved world object; current fixture holds every section; 4 items deferred")
    print(f"broken designs: {caught} caught — {caught} by behaviour, 0 by a crash []")
    if survivors:
        print("SURVIVED:", survivors); sys.exit(1)
    print("ALL STATE REGISTRY SIMULATIONS PASSED")
