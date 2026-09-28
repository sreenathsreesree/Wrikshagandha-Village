#!/usr/bin/env python3
"""Model checks for the M03.2 area loader (Python port, not the engine).
1. The rules the model relies on are read from the GDScript: Main's swap
   order, FarmManager's duplicate-plot rule, Player.place_at(), the Meadow's
   entries and the boot position.
2. Swapping areas: exactly one area afterwards (first among Main's children);
   the old area's nodes are gone from every group and registry before the new
   one registers, so every new plot registers (a queue_free() or add-before-
   remove order would get them rejected as duplicates — shown below).
3. The swap is deferred: a load asked for from inside the current area's own
   callback never frees that area while the callback runs.
4. Entries: the named one, else the lowest id (deterministic), else the
   player stays put; placement ends the walk, drops momentum, faces the
   marker; the camera snaps to the player.
5. Farm plots across a reload (M03.3): captured by id before the area goes,
   restored when the next instance registers — every field capture() saves
   (read from farm_plot.gd), no recount of ready crops, nothing lost by a save
   made after the reload or while the area is away; empty / one / many /
   partial farms, reload twice, old references dropped.
"""
import math, os, random, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
def _body(src, name):
    m = re.search(rf"^func {name}\(.*?(?=^func |\Z)", src, re.M | re.S)
    assert m, f"{name}() not found"
    return m.group(0)

# ---------------------------------------------------------------- 1. rules
MAIN, PLAYER, FARM = _src("scripts", "main.gd"), _src("scripts", "player", "player.gd"), _src("scripts", "autoload", "farm_manager.gd")
MEADOW, MAIN_TSCN = _src("scenes", "world", "Meadow.tscn"), _src("scenes", "Main.tscn")
SWAP = _body(MAIN, "_swap_area")
ORDER = ["FarmManager.cancel_seed_choice()", "FarmManager.release_plots_in(old)", "remove_child(old)", "old.free()", "add_child(area)", "move_child(area, 0)",
         "area.attach_player(player)", "_find_entry(area, entry_id)", "player.place_at(entry.global_transform)",
         "follow_camera.global_position = player.global_position"]
idx = [SWAP.find(k) for k in ORDER]
assert -1 not in idx and idx == sorted(idx), f"swap order in main.gd: {dict(zip(ORDER, idx))}"
assert "queue_free" not in SWAP and "_swap_area.call_deferred(scene, entry_id)" in _body(MAIN, "load_area")
assert re.search(r"if is_instance_valid\(existing\) and existing != plot:\s*push_warning", _body(FARM, "register_plot")), \
    "FarmManager rejects a plot id still held by a live node"
PA = _body(PLAYER, "place_at")
assert re.search(r"_stop_navigation\(\)\s*velocity = Vector3\.ZERO\s*global_position = spot\.origin", PA)
assert "_facing_angle = atan2(forward.x, -forward.z)" in PA and "FACE_TARGET_MIN_DISTANCE" in PA
FACE_MIN = float(re.search(r"^const FACE_TARGET_MIN_DISTANCE := ([0-9.]+)", PLAYER, re.M).group(1))
ENTRIES = {}
for chunk in MEADOW.split("\n[")[1:]:
    if 'ExtResource("entry")' in chunk:
        eid = re.search(r'entry_id = "([^"]+)"', chunk).group(1)
        x, y, z = [float(v) for v in re.search(r"position = Vector3\(([^)]*)\)", chunk).group(1).split(",")]
        ENTRIES[eid] = (x, y, z)
assert ENTRIES, "the Meadow has entries"
BOOT = tuple(float(v) for v in re.search(r'\[node name="Player" parent="\." [^\n]*\]\nposition = Vector3\(([^)]*)\)', MAIN_TSCN).group(1).split(","))
assert ENTRIES["meadow_start"] == BOOT, f"boot unchanged: meadow_start {ENTRIES['meadow_start']} == player boot {BOOT}"
PLOT_IDS = re.findall(r'plot_id = "([^"]+)"', MEADOW)
assert len(PLOT_IDS) == len(set(PLOT_IDS)) >= 1

# ---------------------------------------------------------------- 2. model
class Node:
    def __init__(n, kind, **kw): n.kind, n.valid, n.in_tree, n.__dict__["extra"] = kind, True, False, kw
class Area:
    def __init__(a, entries=ENTRIES):
        a.valid, a.in_tree = True, False
        a.plots = [Node("plot", plot_id=pid) for pid in PLOT_IDS]
        a.entries = [Node("entry", entry_id=e, pos=p, yaw=0.0) for e, p in entries.items()]
    def nodes(a): return a.plots + a.entries
class World:  # Main + SceneTree groups + FarmManager registry + Player + camera
    def __init__(w, order="real"):
        w.order, w.children, w.groups, w.plots, w.rejected, w.deferred = order, [], {"area_entry": []}, {}, [], []
        w.player = dict(pos=BOOT, nav=True, approach="x", selected="x", velocity=(1.0, 0, 0), facing=0.7)
        w.camera = BOOT; w.picker_open = True; w.area = None
        w.add_area(Area(), at_boot=True)
    def enter(w, area):
        area.in_tree = True
        for e in area.entries: e.in_tree = True; w.groups["area_entry"].append(e)
        for p in area.plots:                                    # FarmPlot._ready -> register_plot
            p.in_tree = True
            existing = w.plots.get(p.extra["plot_id"])
            if existing is not None and existing.valid and existing is not p: w.rejected.append(p.extra["plot_id"]); continue
            w.plots[p.extra["plot_id"]] = p
    def exit(w, area):
        area.in_tree = False
        for e in area.entries: e.in_tree = False; w.groups["area_entry"].remove(e)
        for p in area.plots: p.in_tree = False
    def kill(w, area):
        area.valid = False
        for n in area.nodes(): n.valid = False
    def add_area(w, area, at_boot=False):
        w.children.insert(0, area); w.enter(area); w.area = area
    def load_area(w, area, entry_id): w.deferred.append((area, entry_id))   # call_deferred
    def flush(w):
        while w.deferred:
            area, entry_id = w.deferred.pop(0); w.swap(area, entry_id)
    def swap(w, new, entry_id):
        w.picker_open = False
        old = w.area
        if w.order == "real":            # remove_child, free(), add_child, move_child(0)
            w.children.remove(old); w.exit(old); w.kill(old); w.add_area(new)
        elif w.order == "queue_free":    # freed only at the end of the frame
            w.children.remove(old); w.exit(old); w.add_area(new); w.kill(old)
        elif w.order == "add_first":     # new area added before the old one leaves
            w.add_area(new); w.children.remove(old); w.exit(old); w.kill(old)
        entry = w.find_entry(new, entry_id)
        w.place_at(entry.extra["pos"] if entry else w.player["pos"], entry.extra["yaw"] if entry else None)
        w.camera = w.player["pos"]
    def find_entry(w, area, entry_id):
        mine = [e for e in w.groups["area_entry"] if e in area.entries]
        named = [e for e in mine if e.extra["entry_id"] == entry_id]
        if named: return named[0]
        return min(mine, key=lambda e: e.extra["entry_id"]) if mine else None
    def place_at(w, pos, yaw):
        p = w.player; p.update(pos=pos, nav=False, approach=None, selected=None, velocity=(0.0, 0.0, 0.0))
        if yaw is not None: p["facing"] = yaw

w = World(); first = w.area
assert len(w.plots) == len(PLOT_IDS) and not w.rejected
w.load_area(Area(), "meadow_start")
assert w.area is first and first.valid, "deferred: nothing happens until the frame's deferred calls run"
w.flush()
assert w.children == [w.area] and w.area is not first and not first.valid, "exactly one area, the new one, first child"
assert not w.rejected and all(p.valid and p in w.area.plots for p in w.plots.values()), "every new plot registered"
assert all(e in w.area.entries for e in w.groups["area_entry"]), "no old entry left in the group"
assert w.player["pos"] == ENTRIES["meadow_start"] and not w.player["nav"] and w.player["approach"] is None \
    and w.player["selected"] is None and w.player["velocity"] == (0.0, 0.0, 0.0) and w.camera == w.player["pos"]
assert not w.picker_open, "an open seed picker is closed before its plot goes"
for bad in ("queue_free", "add_first"):
    wb = World(order=bad); wb.load_area(Area(), "meadow_start"); wb.flush()
    assert sorted(wb.rejected) == sorted(PLOT_IDS), f"{bad}: new plots would be rejected as duplicates"
print(f"swap: one area, {len(PLOT_IDS)} plots re-registered, entries {sorted(ENTRIES)}; "
      "queue_free/add-first orders shown to reject every new plot")

# 3. deferred: a load asked for from inside the current area's callback
w = World(); caller = w.area.plots[0]
def area_callback():  # e.g. a future door's interact()
    w.load_area(Area(), "meadow_start")
    assert caller.valid and w.area.valid, "the calling area must survive its own callback"
area_callback(); w.flush(); assert not caller.valid and w.area.valid

# 4. entries: named, fallback lowest id, none
two = {"zeta_gate": (5.0, 0.2, 5.0), "alpha_gate": (1.0, 0.2, 1.0)}
w = World(); w.load_area(Area(two), "zeta_gate"); w.flush()
assert w.player["pos"] == two["zeta_gate"] and w.camera == two["zeta_gate"], "placed on the entry; camera snapped there"
stray = Node("entry", entry_id="aaa_stray", pos=(99.0, 0.0, 99.0), yaw=0.0)   # an entry outside the area (e.g. in the shell)
w = World(); w.groups["area_entry"].append(stray); w.load_area(Area(two), "missing"); w.flush()
assert w.player["pos"] == two["alpha_gate"], "only the loaded area's entries count"
w = World(); w.load_area(Area(two), "missing"); w.flush(); assert w.player["pos"] == two["alpha_gate"], "fallback: lowest id"
w2 = World(); w2.load_area(Area(dict(reversed(list(two.items())))), "missing"); w2.flush()
assert w2.player["pos"] == two["alpha_gate"], "independent of tree order"
w = World(); before = w.player["pos"]; w.load_area(Area({}), "any"); w.flush()
assert w.player["pos"] == before and not w.player["nav"] and w.camera == before, "no entry: stays put, walk ended"

# place_at facing (port): faces the marker's -Z; an up/down-only basis keeps the facing
def facing_from(basis_z, old):
    fx, fz = -basis_z[0], -basis_z[2]
    return old if math.hypot(fx, fz) < FACE_MIN else math.atan2(fx, -fz)
assert facing_from((0, 0, 1), 0.3) == 0.0 and abs(facing_from((1, 0, 0), 0.3) + math.pi / 2) < 1e-9
assert facing_from((0, 1, 0), 0.3) == 0.3, "no horizontal forward: facing kept"

# random sequences
rnd = random.Random(9)
for _ in range(2000):
    w = World()
    for _ in range(rnd.randint(1, 6)):
        ents = {f"e{k}": (float(k), 0.2, 0.0) for k in rnd.sample(range(5), rnd.randint(0, 3))}
        w.player.update(nav=rnd.random() < 0.5)
        w.load_area(Area(ents or {}), rnd.choice(list(ents) + ["nope"]) if ents else "nope"); w.flush()
        assert len(w.children) == 1 and w.children[0] is w.area and not w.rejected
        assert all(p.valid for p in w.plots.values()) and not w.player["nav"]
print("area loader: deferred swap, entries (named/fallback/none), placement + camera snap, 2000 random sequences OK")

# ---------------------------------------------------------------- 5. farm plots across a reload (M03.3)
PLOT_SRC = _src("scripts", "farming", "farm_plot.gd")
CAP_KEYS = sorted(set(re.findall(r'"(\w+)":', _body(PLOT_SRC, "capture"))))
assert {"state", "soil_memory", "crop", "stage", "needs_water", "stage_time_left", "thirsty_for", "longest_thirst",
        "soil", "care", "quality"} <= set(CAP_KEYS), CAP_KEYS
REL, REG, SAVE = _body(FARM, "release_plots_in"), _body(FARM, "register_plot"), _body(FARM, "get_save_data")
assert "_unloaded_plot_states[plot_id] = plot.capture()" in REL and "_plots.erase(plot_id)" in REL
assert REG.find("_plots[plot.plot_id] = plot") < REG.find("if _unloaded_plot_states.has(") < REG.find("if _saved_plot_states.has(")
assert "plots.merge(_unloaded_plot_states.duplicate(true), true)" in SAVE
STATES = ["EMPTY", "SOIL", "PLANTED", "GROWING", "READY"]

class Plot:
    def __init__(p, pid):
        p.pid, p.valid, p.state, p.memory, p.crop, p.f = pid, True, "EMPTY", [], "", {}
        p.harvesting = p.paid = False
    def capture(p):  # port of FarmPlot.capture()
        state, crop = p.state, p.crop
        if p.harvesting and p.paid: state, crop = "SOIL", ""
        d = {"state": state, "soil_memory": list(p.memory)}
        if crop == "": return d
        d.update({"crop": crop, **{k: p.f[k] for k in CAP_KEYS if k not in ("state", "soil_memory", "crop")}})
        return d
    def restore(p, d):  # port of FarmPlot.restore() (fields only)
        p.memory = list(d.get("soil_memory", []))
        if d.get("state", "EMPTY") == "EMPTY": return None
        p.state = d["state"]
        if p.state == "SOIL" or not d.get("crop"): p.state = "SOIL"; return None
        p.crop = d["crop"]; p.f = {k: d[k] for k in CAP_KEYS if k not in ("state", "soil_memory", "crop")}
        return p.crop
class Farm:  # port of FarmManager's plot registry
    def __init__(f): f.plots, f.saved, f.unloaded, f.ready, f.rejected = {}, {}, {}, {}, []
    def register(f, plot):
        old = f.plots.get(plot.pid)
        if old is not None and old.valid and old is not plot: f.rejected.append(plot.pid); return
        f.plots[plot.pid] = plot
        if plot.pid in f.unloaded: plot.restore(f.unloaded.pop(plot.pid)); return
        if plot.pid in f.saved:
            crop = plot.restore(f.saved.pop(plot.pid))
            if crop and plot.state == "READY": f.ready[crop] = f.ready.get(crop, 0) + 1
    def release(f, area_plots):
        for pid in list(f.plots):
            n = f.plots[pid]
            if not n.valid: del f.plots[pid]
            elif n in area_plots: f.unloaded[pid] = n.capture(); del f.plots[pid]
    def save(f):
        out = {k: dict(v) for k, v in f.saved.items()}
        out.update({k: dict(v) for k, v in f.unloaded.items()})
        for pid, n in f.plots.items():
            if n.valid: out[pid] = n.capture()
        return out
class FarmWorld:  # Main + the farm area; swap in main.gd's order
    def __init__(fw, boot_save=None, order="real"):
        fw.farm, fw.order = Farm(), order
        if boot_save: fw.farm.saved = {k: dict(v) for k, v in boot_save.items()}
        fw.area = fw.new_area()
    def new_area(fw, with_plots=True):
        plots = [Plot(pid) for pid in PLOT_IDS] if with_plots else []
        for p in plots: fw.farm.register(p)
        return plots
    def reload(fw, with_plots=True):
        old = fw.area
        if fw.order == "no_snapshot": pass
        elif fw.order == "after_unload":
            for n in old: n.valid = False
            fw.farm.release(old)
        else: fw.farm.release(old)
        for n in old: n.valid = False                     # remove_child + free()
        fw.area = fw.new_area(with_plots)
def random_plot(rnd, p):
    p.state = rnd.choice(STATES); p.memory = rnd.sample(["wild_carrot", "meadow_herb", "elderbloom"], rnd.randint(0, 2))
    if p.state in ("PLANTED", "GROWING", "READY"):
        p.crop = rnd.choice(["wild_carrot", "meadow_herb", "elderbloom", "golden_sunflower"])
        p.f = {"stage": rnd.randint(0, 3), "needs_water": p.state != "READY" and rnd.random() < 0.5,
               "stage_time_left": round(rnd.uniform(0, 60), 3), "soil": rnd.randint(0, 2), "care": rnd.randint(0, 2),
               "quality": rnd.randint(0, 2), "longest_thirst": round(rnd.uniform(0, 90), 3),
               "thirsty_for": round(rnd.uniform(0, 30), 3) if rnd.random() < 0.5 else -1.0}
        p.harvesting = p.state == "READY" and rnd.random() < 0.2; p.paid = p.harvesting and rnd.random() < 0.5
    else: p.crop, p.f, p.harvesting, p.paid = "", {}, False, False   # EMPTY / SOIL hold no crop
def by_id(fw): return {p.pid: p for p in fw.area}

fw = FarmWorld(); before = fw.farm.save(); fw.reload()
assert fw.farm.save() == before and all(p.state == "EMPTY" for p in fw.area), "empty farm survives as empty"
fw = FarmWorld(); rnd = random.Random(1); p0 = fw.area[0]; random_plot(rnd, p0)
while p0.state not in ("GROWING", "READY"): random_plot(rnd, p0)
before = fw.farm.save(); fw.reload()
assert fw.farm.save() == before and by_id(fw)[p0.pid].capture() == before[p0.pid], "one modified plot: every field back"
assert not fw.farm.rejected and not fw.farm.unloaded and all(n in fw.area for n in fw.farm.plots.values()), \
    "no duplicate rejection; no old references; nothing left waiting"
for bad in ("no_snapshot", "after_unload"):
    fb = FarmWorld(order=bad); pb = fb.area[0]; pb.state, pb.crop, pb.f = "GROWING", "wild_carrot", {k: 1 for k in CAP_KEYS}
    saved = fb.farm.save(); fb.reload()
    assert fb.farm.save() != saved, f"{bad}: the farm would be lost (shown)"
rnd = random.Random(7)
for trial in range(1500):
    boot = None
    if rnd.random() < 0.3:  # start from a saved game (ready crops counted once at boot)
        tmp = FarmWorld()
        for p in tmp.area: random_plot(rnd, p); p.harvesting = p.paid = False
        boot = tmp.farm.save()
    fw = FarmWorld(boot)
    for p in rnd.sample(fw.area, rnd.randint(0, len(fw.area))): random_plot(rnd, p)   # empty .. fully modified
    ready_before = dict(fw.farm.ready)
    for _ in range(rnd.randint(1, 3)):                                               # reload once, twice, three times
        before = fw.farm.save()
        if rnd.random() < 0.3:                                                       # away in an area without plots,
            fw.reload(with_plots=False)                                              # autosave meanwhile keeps them
            assert fw.farm.save() == before and not fw.farm.plots, "saved while the farm area is away: nothing lost"
        fw.reload()
        assert fw.farm.save() == before, "autosave right after a reload: identical farm"
        assert not fw.farm.rejected and not fw.farm.unloaded
        assert all(n.valid and n in fw.area for n in fw.farm.plots.values()), "no reference to an old area survives"
        assert fw.farm.ready == ready_before, "ready crops are not counted again"
print(f"farm across reload: fields {CAP_KEYS}; empty/one/many/partial, reload x1-3, away-then-back, "
      "autosave after reload, 1500 random runs OK (no-snapshot / snapshot-after-unload shown to lose the farm)")
print("ALL AREA LOADER SIMULATIONS PASSED")
