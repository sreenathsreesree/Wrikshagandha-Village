#!/usr/bin/env python3
"""Wildlife Journal (M14.1a, D-59): the real WildlifeActor._process, WildlifeController's relay and JournalManager's
sighting functions, each translated from its GDScript with gd_port, run against a small model of the engine (frames,
signals that refuse a second identical connection as Godot does, the save as GameState triggers it and SaveManager
writes / reads the "wildlife_sightings" section, both read from their sources).
1. Data: exactly the three species (rabbit, small bird, butterfly) in data/wildlife/, each creature scene naming its
   species, and every Meadow creature resolving to one (2 rabbits, 5 birds, 7 butterflies).
2. Approach: an actor reports its species the first frame the player is inside its alert_distance — not at or beyond
   it (the same strict test it already uses to turn and watch) — and, when the player appears inside flee_distance at
   once, in that same frame. Leaving and coming back, or staying for minutes, never reports again.
3. The Journal keeps a known species once ever: wildlife_sighted only the first time; a second creature of the same
   species, an unknown id or an empty species changes nothing.
4. Saved at once: GameState saves on wildlife_sighted, with the species already in the saved data; one save per new
   species, none for a repeat. After a restart the species is still seen and nothing is saved again.
5. Old saves: a save without the section (v0..v8) loads with no species seen; junk in the section (non-strings,
   duplicates) is dropped, an id no longer in the data is kept.
6. No reward: no points, coins, items or reward call anywhere on the path (every such call is recorded).
7. Wiring the actors twice relays each sighting once.
Broken designs (mutated sources) are shown to fail; kills by a crash are reported separately, and equivalent mutants
are named.
"""
import glob, json, math, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gd_port

REPO = gd_port.REPO
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
SOURCES = {"actor": _src("scripts", "world_simulation", "wildlife_actor.gd"),
           "butterfly": _src("scripts", "world_simulation", "wildlife_butterfly.gd"),
           "ctl": _src("scripts", "world_simulation", "wildlife_controller.gd"),
           "jm": _src("scripts", "autoload", "journal_manager.gd"),
           "gs": _src("scripts", "autoload", "game_state.gd"),
           "sm": _src("scripts", "autoload", "save_manager.gd"),
           "meadow": _src("scenes", "world", "Meadow.tscn")}
DT = 1 / 60

# ---------------------------------------------------------------- engine model
class GArray(list):
    def has(s, v): return v in s
    def duplicate(s): return GArray(s)
    def size(s): return len(s)
    def is_empty(s): return len(s) == 0
class OneOf:  # a match case with several patterns ("idle", "pause":)
    def __init__(s, *v): s.v = v
    def __eq__(s, o): return o in s.v
class Signal(gd_port.Signal):
    def connect(s, fn, flags=0):
        if fn in s.handlers: raise RuntimeError("Signal already connected")   # Godot: an error, the call fails
        s.handlers.append(fn)
    def is_connected(s, fn): return fn in s.handlers
gd_port.Signal = Signal
class Ledger:  # every points / coins / items / reward call, from anywhere on the path
    def __init__(s): s.calls = []
    def __getattr__(s, k):
        if k.startswith("__"): raise AttributeError(k)
        return lambda *a: s.calls.append((k, a))
class SIM:
    journal = None
    ledger = Ledger()
gd_port.HELPERS.update({"GArray": GArray, "OneOf": OneOf, "TYPE_STRING": 4, "SIM": SIM, "INF": math.inf,
                        "_typeof": lambda v: 4 if isinstance(v, str) else gd_port._typeof(v)})
REWARD_EXT = {n: "SIM.ledger" for n in ("PointsManager", "Wallet", "Inventory", "Market", "CollectionManager", "FarmManager",
                                       "ExplorationManager", "DailyDiscoveryManager", "SaveManager")}

def prep(src):
    """The GDScript constructs gd_port leaves alone: typed for loops, empty arrays, multi-pattern match cases."""
    src = re.sub(r"\bfor (\w+): [\w\[\]]+ in ", r"for \1 in ", src)
    src = re.sub(r"(?<![\w\]])\[\](?!\w)", "GArray()", src)
    src = re.sub(r'^(\t+)("[^"\n]*"(?:, "[^"\n]*")+):$', lambda m: f"{m.group(1)}OneOf({m.group(2)}):", src, flags=re.M)
    return src.replace("node is WildlifeActor", "isinstance(node, WildlifeActor)")

class Player:
    def __init__(p, x=100.0): p.global_position = gd_port.Vector3(x, 0.0, 0.0)

def build(S):
    ACT, _ = gd_port.translate(prep(S["actor"]), "WildlifeActorGD", {**REWARD_EXT, "Vector3.ZERO": "Vector3()", "position": "self.position"}, ["_process"])
    class Actor(ACT):
        """The translated _process, with the movement helpers it calls reduced to their state changes."""
        def __init__(a, species, alert, flee):
            ACT.__init__(a)
            a.species_id, a.alert_distance, a.flee_distance = species, alert, flee
            a.position, a._state_timer, a._target_position = gd_port.Vector3(), 2.0, gd_port.Vector3()
        def _enter_flee(a): a.state, a._state_timer = "flee", 1.0
        def _enter_idle(a): a.state, a._state_timer = "idle", 2.0
        def _enter_wander(a): a.state, a._target_position = "wander", a.position
        def _enter_pause(a): a.state, a._state_timer = "pause", 2.0
        def _move_toward(a, *x): pass
        def _face_player(a, *x): pass
        def _idle_look_around(a, *x): pass
        def _flee_target(a): return a.position
    CTL, _ = gd_port.translate(prep(S["ctl"]), "WildlifeControllerGD", {**REWARD_EXT, "JournalManager": "SIM.journal", "WildlifeActor": "SIM.Actor"},
                               ["wire_actors", "_on_actor_sighted"])
    SIM.Actor = Actor
    JM, _ = gd_port.translate(prep(S["jm"]), "JournalManagerGD", REWARD_EXT,
                              ["record_sighting", "has_sighted", "get_sighted_ids", "get_species", "get_sightings_save_data", "apply_sightings_save_data"])
    # GameState: the save it connects to wildlife_sighted, and how (CONNECT_DEFERRED = after the frame's handlers).
    trig = re.search(r"^\tJournalManager\.wildlife_sighted\.connect\(_save\.unbind\(1\)(, CONNECT_DEFERRED)?\)$", S["gs"], re.M)
    # SaveManager: the section's writer and reader, and the step from 8.
    sm = S["sm"]
    write = re.search(r'^\t\t"wildlife_sightings": JournalManager\.(\w+)\(\),$', sm, re.M)
    read = re.search(r'^\tJournalManager\.(\w+)\(data\.get\("wildlife_sightings", \[\]\)\)$', sm, re.M)
    typed = re.search(r'^\t"wildlife_sightings": \[TYPE_ARRAY\],$', sm, re.M)
    step8 = re.search(r"^\t\t\t8:\s*pass\b", sm, re.M)
    return dict(Actor=Actor, CTL=CTL, JM=JM, trigger=(trig.group(1) or "") if trig else None,
                write=write.group(1) if write else None, read=read.group(1) if read else None, typed=bool(typed), step8=bool(step8))

def species_data():
    out = {}
    for path in sorted(glob.glob(os.path.join(REPO, "data", "wildlife", "*.tres"))):
        vals = dict(re.findall(r'^(\w+) = "?([^"\n]*)"?$', open(path, encoding="utf-8").read(), re.M))
        out[vals["id"]] = gd_port.Mock(id=vals["id"], display_name=vals.get("display_name", ""), order=int(vals.get("order", 0)))
    return out
SPECIES = species_data()
SCENES = {"Rabbit": "rabbit", "SmallBird": "small_bird", "WildlifeButterfly": "butterfly"}
def scene_values(name):
    t = _src("scenes", "wildlife", f"{name}.tscn")
    root = t.split("\n[node", 2)[1]
    vals = dict(re.findall(r"^(\w+) = (.+)$", root, re.M))
    return vals.get("species_id", '""').strip('"'), float(vals.get("alert_distance", 4.0)), float(vals.get("flee_distance", 2.5))

class Game:
    """One launch: the Journal (with its saved sightings), the controller and some actors; saves go to self.disk."""
    def __init__(g, K, disk=None):
        g.K, g.disk, g.saves, g.deferred = K, disk if disk is not None else {}, 0, []
        g.journal = K["JM"](); g.journal._species = GArray(SPECIES.values()); g.journal._sighted_species = GArray()
        SIM.journal = g.journal
        if "save" in g.disk and K["read"]:   # SaveManager.load_game at boot
            getattr(g.journal, K["read"])(g.disk["save"].get("wildlife_sightings", GArray()))
        if K["trigger"] is not None:
            g.journal.wildlife_sighted.connect((lambda *_: g.deferred.append(1)) if K["trigger"] else (lambda *_: g.save()))
        g.ctl = K["CTL"]()
        g.actors = []
    def save(g):
        g.saves += 1
        data = {"save_version": 9}
        if g.K["write"]: data["wildlife_sightings"] = getattr(g.journal, g.K["write"])()
        g.disk["save"] = gd_port.godot_json(data)
    def add(g, name, x=0.0):
        sid, alert, flee = scene_values(name)
        a = g.K["Actor"](sid, alert, flee); a.position = gd_port.Vector3(x, 0.0, 0.0); a.add_to_group("wildlife_actor"); g.actors.append(a)
        return a
    def wire(g, player):
        g.ctl.player = player; g.ctl.wire_actors()
    def frame(g):
        for a in g.actors: a._process(DT)
        for _ in g.deferred: g.save()
        g.deferred.clear()

def fresh_tree():
    gd_port.WORLD.tree = gd_port.Tree(); SIM.ledger = Ledger()

def run(S):
    p = []
    K = build(S)
    # 1. data
    if sorted(SPECIES) != ["butterfly", "rabbit", "small_bird"]: p.append(f"species data {sorted(SPECIES)}")
    for scene, sid in SCENES.items():
        if scene_values(scene)[0] != sid: p.append(f"{scene}.tscn names species {scene_values(scene)[0]!r}, not {sid!r}")
    ids = {m.group(1): m.group(2) for m in re.finditer(r'^\[ext_resource type="PackedScene" path="res://scenes/wildlife/(\w+)\.tscn" id="(\w+)"\]', S["meadow"], re.M)}
    counts = {sid: len(re.findall(r'^\[node name="\w+" parent="Wildlife" instance=ExtResource\("%s"\)\]' % ids.get(sc, "-"), S["meadow"], re.M)) for sc, sid in SCENES.items()}
    if counts != {"rabbit": 2, "small_bird": 5, "butterfly": 7}: p.append(f"Meadow creatures per species {counts}")
    if re.search(r"^species_id = ", S["meadow"], re.M): p.append("a Meadow instance overrides species_id")
    if not re.search(r"^func _process\(delta: float\) -> void:\n\tvar was_leading := state == \"lead\"\n\tsuper\._process\(delta\)", S["butterfly"], re.M) \
       or "sighted" in S["butterfly"]:
        p.append("the butterfly reports through the shared _process, unchanged")
    if not (K["typed"] and K["step8"]): p.append("SaveManager types the section as an Array and steps 8 -> 9 without rewriting")
    # 2. approach, one actor
    for scene in SCENES:
        fresh_tree(); g = Game(K); a = g.add(scene); pl = Player(10.0); g.wire(pl)
        emitted = []
        a.sighted.connect(lambda s: emitted.append((s, pl.global_position.x)))
        for i in range(400):        # 10 m to -10 m, 5 cm a frame
            pl.global_position = gd_port.Vector3(10.0 - i * 0.05, 0.0, 0.0); g.frame()
        first = emitted[0][1] if emitted else None
        if len(emitted) != 1 or not (first is not None and a.alert_distance - 0.1 <= first < a.alert_distance):
            p.append(f"{scene}: one report, the first frame inside alert_distance {a.alert_distance} (got {emitted[:3]})")
        for _ in range(5):          # away and back, then five minutes close by
            for x in (20.0, 0.5): pl.global_position = gd_port.Vector3(x, 0.0, 0.0); g.frame()
        pl.global_position = gd_port.Vector3(1.0, 0.0, 0.0)
        for _ in range(int(300 / DT)): g.frame()
        if len(emitted) != 1: p.append(f"{scene}: reported again ({len(emitted)})")
        # exactly at alert_distance: not inside
        fresh_tree(); g = Game(K); a = g.add(scene); pl = Player(a.alert_distance); g.wire(pl)
        for _ in range(30): g.frame()
        if g.journal.has_sighted(SCENES[scene]): p.append(f"{scene}: seen at exactly alert_distance (it only watches inside it)")
        # appearing inside flee_distance at once: seen in that same frame
        fresh_tree(); g = Game(K); a = g.add(scene); pl = Player(30.0); g.wire(pl); g.frame()
        pl.global_position = gd_port.Vector3(a.flee_distance * 0.3, 0.0, 0.0); g.frame()
        if not g.journal.has_sighted(SCENES[scene]) or g.saves != 1: p.append(f"{scene}: a player appearing inside flee_distance is seen that frame (saves {g.saves})")
    # 3 + 4. the whole Meadow's creatures, one launch, then a restart
    fresh_tree(); disk = {}; g = Game(K, disk); pl = Player(500.0)
    order = [("Rabbit", 0.0), ("Rabbit", 3.0), ("SmallBird", 40.0)] + [("SmallBird", 40.0 + i) for i in range(4)] \
        + [("WildlifeButterfly", 80.0 + i) for i in range(7)]
    for scene, x in order: g.add(scene, x)
    g.wire(pl); g.wire(pl)            # wired twice (an area configured again): still one relay each
    sighted = []
    g.journal.wildlife_sighted.connect(lambda s: sighted.append((s, sorted(disk.get("save", {}).get("wildlife_sightings", [])))))
    for i in range(1400):           # -20 m to 120 m past every creature, 10 cm a frame
        pl.global_position = gd_port.Vector3(-20.0 + i * 0.1, 0.0, 0.0); g.frame()
    if [s for s, _ in sighted] != ["rabbit", "small_bird", "butterfly"] or g.saves != 3:
        p.append(f"each species once, saved once each (seen {[s for s, _ in sighted]}, saves {g.saves})")
    if sorted(disk.get("save", {}).get("wildlife_sightings", [])) != ["butterfly", "rabbit", "small_bird"]:
        p.append(f"the save holds every species seen ({disk.get('save')})")
    if g.journal.record_sighting("rabbit") or g.journal.record_sighting("dragon") or g.journal.record_sighting("") or g.saves != 3:
        p.append("a repeat, an unknown or an empty species changes nothing")
    # every save is written with the species already in it (a kill right after the save loses nothing)
    fresh_tree(); d2 = {}; g2 = Game(K, d2); pl2 = Player(0.5); g2.add("Rabbit"); g2.wire(pl2); g2.frame()
    if d2.get("save", {}).get("wildlife_sightings") != ["rabbit"]: p.append(f"the sighting's own save holds it ({d2.get('save')})")
    if SIM.ledger.calls: p.append(f"a sighting paid or rewarded something: {SIM.ledger.calls}")
    # restart: still seen; seeing them again saves nothing
    fresh_tree(); g = Game(K, disk); pl = Player(500.0)
    for scene, x in order: g.add(scene, x)
    g.wire(pl)
    for xx in range(-20, 120): pl.global_position = gd_port.Vector3(float(xx), 0.0, 0.0); g.frame()
    if not all(g.journal.has_sighted(s) for s in SPECIES) or g.saves != 0:
        p.append(f"after a restart every species is still seen and nothing is saved again (saves {g.saves})")
    # 5. old saves and junk
    fresh_tree(); g = Game(K, {"save": gd_port.godot_json({"save_version": 8, "points": 3})})
    if g.journal.get_sighted_ids() != []: p.append("a save without the section loads with no species seen")
    fresh_tree(); g = Game(K, {"save": {"wildlife_sightings": [1.0, "rabbit", "rabbit", None, "gone_species", True]}})
    if g.journal.get_sighted_ids() != ["rabbit", "gone_species"]:
        p.append(f"junk dropped, each id once, a removed species kept ({g.journal.get_sighted_ids()})")
    # 6. nothing paid on any path above
    if SIM.ledger.calls: p.append(f"a sighting paid or rewarded something: {SIM.ledger.calls}")
    return p

def mut(key, old, new):
    s = dict(SOURCES); assert old in s[key], (key, old[:60]); s[key] = s[key].replace(old, new, 1); return s
if __name__ == "__main__":
    bad = run(SOURCES)
    for b in bad: print("FAIL:", b)
    assert not bad, "wildlife journal simulation failed"
    MUTANTS = {
        "the actor reports every frame (no once flag)": mut("actor", "\t\t\t_sighting_reported = true\n", ""),
        "seen at flee_distance, not alert_distance": mut("actor", "player_distance < alert_distance and species_id", "player_distance < flee_distance and species_id"),
        "seen at or beyond alert_distance (<=)": mut("actor", "player_distance < alert_distance and species_id", "player_distance <= alert_distance and species_id"),
        "the sighting check after the flee step": mut("actor", "\t\tif not _sighting_reported and player_distance < alert_distance and species_id != \"\":\n\t\t\t_sighting_reported = true\n\t\t\tsighted.emit(species_id)\n\t\tif state != \"flee\" and player_distance < flee_distance:\n\t\t\t_enter_flee()\n\t\t\treturn\n",
                                                     "\t\tif state != \"flee\" and player_distance < flee_distance:\n\t\t\t_enter_flee()\n\t\t\treturn\n\t\tif not _sighting_reported and player_distance < alert_distance and species_id != \"\":\n\t\t\t_sighting_reported = true\n\t\t\tsighted.emit(species_id)\n"),
        "the Journal records a species again": mut("jm", "if _sighted_species.has(species_id) or get_species(species_id) == null:", "if get_species(species_id) == null:"),
        "the Journal accepts an unknown species": mut("jm", "if _sighted_species.has(species_id) or get_species(species_id) == null:", "if _sighted_species.has(species_id):"),
        "the signal before the species is recorded": mut("jm", "\t_sighted_species.append(species_id)\n\twildlife_sighted.emit(species_id)\n", "\twildlife_sighted.emit(species_id)\n\t_sighted_species.append(species_id)\n"),
        "a sighting pays points": mut("jm", "\twildlife_sighted.emit(species_id)\n", "\twildlife_sighted.emit(species_id)\n\tPointsManager.add_points(5)\n"),
        "a sighting pays coins": mut("ctl", "\tJournalManager.record_sighting(species_id)\n", "\tif JournalManager.record_sighting(species_id):\n\t\tWallet.credit(2, \"wildlife\")\n"),
        "saved sightings not type-checked": mut("jm", "if typeof(value) == TYPE_STRING and not _sighted_species.has(value):", "if not _sighted_species.has(value):"),
        "the controller relays nothing": mut("ctl", "\tJournalManager.record_sighting(species_id)\n", "\tpass\n"),
        "GameState does not save on a sighting": mut("gs", "\tJournalManager.wildlife_sighted.connect(_save.unbind(1))\n", ""),
        "SaveManager does not write the section": mut("sm", '\t\t"wildlife_sightings": JournalManager.get_sightings_save_data(),\n', ""),
        "SaveManager does not load the section": mut("sm", '\tJournalManager.apply_sightings_save_data(data.get("wildlife_sightings", []))\n', ""),
        "the section typed as a dictionary": mut("sm", '\t"wildlife_sightings": [TYPE_ARRAY],', '\t"wildlife_sightings": [TYPE_DICTIONARY],'),
        "the controller connects without its guard": mut("ctl", "\t\t\tif not actor.sighted.is_connected(_on_actor_sighted):\n\t\t\t\tactor.sighted.connect(_on_actor_sighted)\n", "\t\t\tactor.sighted.connect(_on_actor_sighted)\n"),
    }
    # Equivalent by design: deferring the save to the end of the frame still saves the sighting before anything else
    # can happen to it (the force-stop check in real Godot uses the synchronous trigger the game ships).
    EQUIVALENT = {"GameState saves on a sighting deferred": mut("gs", "\tJournalManager.wildlife_sighted.connect(_save.unbind(1))\n", "\tJournalManager.wildlife_sighted.connect(_save.unbind(1), CONNECT_DEFERRED)\n")}
    for name, s in EQUIVALENT.items(): assert not run(s), f"{name} is meant to be equivalent: {run(s)}"
    caught = crash = 0; survivors, crashes = [], []
    for name, s in MUTANTS.items():
        try:
            if run(s): caught += 1
            else: survivors.append(name)
        except Exception as ex:
            crash += 1; crashes.append(f"{name}: {type(ex).__name__}: {ex}")
    print(f"wildlife journal (M14.1a): {len(SPECIES)} species as data; 14 Meadow creatures; one report per creature, the first frame "
          f"inside alert_distance; each species once ever, saved at once with the species in the save; still seen after a "
          f"restart; old saves load with none seen; no points, coins, items or rewards")
    print(f"broken designs: {caught + crash} caught — {caught} by behaviour, {crash} by a crash {crashes}; "
          f"{len(EQUIVALENT)} equivalent {list(EQUIVALENT)}")
    if survivors:
        print("SURVIVED:", survivors); sys.exit(1)
    print("ALL WILDLIFE JOURNAL SIMULATIONS PASSED")
