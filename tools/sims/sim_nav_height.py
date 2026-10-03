#!/usr/bin/env python3
"""Navigation-mesh height accuracy (M08.2a) — the route stall near (-6, 1.4) as a model.
Source only; nothing in the game is run.

Why: the player's NavigationAgent3D advances to its next path point only when that point is
within `path_desired_distance` of the player's feet, measured in 3D. A baked navigation mesh
floats above the real walkable surface by its voxel quantisation (up to two cell heights) plus
the detail mesh's allowed error; when that height alone reaches `path_desired_distance`, a
path point can never be reached from the ground — the player circles it until the stall timer
ends the walk (seen at (-6, 1.4): the mesh 0.40-0.62 m above the ground with cell_height 0.25
and Godot's default detail error of 1 m).

Checks, with every value read from source:
1. Every area's NavigationMesh shares the same settings; the navigation map's default cell
   height (project.godot) equals the mesh's (else Godot re-quantises the map).
2. Worst-case height of a path point above the walkable surface,
   2 * cell_height + detail_sample_max_error (detail sampling on), stays at least 0.1 m under
   the agent's path_desired_distance — the pre-M08.2a settings are shown to fail it.
3. agent_max_climb is a whole number of cell heights (no silent flooring), and the mesh never
   plans over a step the player cannot take: every terraced-mound tier (read from its scene) is
   either within the capsule's step (radius x (1 - cos floor_max_angle), from Player.tscn) or
   taller than agent_max_climb plus one cell (voxelisation can shave a cell off a step: a 0.1 m
   climb still let the 0.15 m tiers through at runtime) (the pre-M08.2a 0.25 m planned over the 0.15 m tiers: every walk across
   a mound stalled, identical on the pre-M08 baseline; the joystick can't climb them either).
4. The agent's height/radius in Player.tscn equal the mesh's agent_height/agent_radius.
"""
import os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
def _src(*p): return open(os.path.join(REPO, *p), encoding="utf-8").read()
GODOT_DEFAULTS = {"detail_sample_distance": 6.0, "detail_sample_max_error": 1.0}   # NavigationMesh defaults (Godot 4.7)
MARGIN = 0.1

def nav_settings(scene):
    m = re.search(r'\[sub_resource type="NavigationMesh"[^\]]*\]\n(.*?)\n\n', _src(*scene.split("/")), re.S)
    assert m, f"{scene}: a NavigationMesh"
    d = {k: v for k, v in re.findall(r"^(\w+) = (.+)$", m.group(1), re.M)}
    out = dict(GODOT_DEFAULTS)
    out.update({k: float(v) for k, v in d.items() if re.fullmatch(r"-?[0-9.]+", v)})
    return out
AREAS = ["scenes/world/Meadow.tscn", "scenes/world/HomeInterior.tscn"]
S = [nav_settings(a) for a in AREAS]
assert all(s == S[0] for s in S), f"every area bakes with the same settings {dict(zip(AREAS, S))}"
NAV = S[0]
CFG = _src("project.godot")
map_ch = re.search(r"^3d/default_cell_height=([0-9.]+)", CFG, re.M)
map_cs = re.search(r"^3d/default_cell_size=([0-9.]+)", CFG, re.M)
assert map_ch and float(map_ch.group(1)) == NAV["cell_height"], "the navigation map's cell height matches the mesh's"
assert (float(map_cs.group(1)) if map_cs else 0.25) == NAV["cell_size"], "the navigation map's cell size matches the mesh's (default 0.25)"

PLAYER = _src("scenes", "player", "Player.tscn")
agent = re.search(r'\[node name="NavigationAgent3D"[^\]]*\]\n(.*?)\n\n', PLAYER, re.S).group(1)
PATH_D = float(re.search(r"^path_desired_distance = ([0-9.]+)", agent, re.M).group(1))
A_H = float(re.search(r"^height = ([0-9.]+)", agent, re.M).group(1)); A_R = float(re.search(r"^radius = ([0-9.]+)", agent, re.M).group(1))
assert (A_H, A_R) == (NAV["agent_height"], NAV["agent_radius"]), "the player's agent matches the mesh's agent"

def worst_height(nav):
    detail = nav["detail_sample_max_error"] if nav["detail_sample_distance"] > 0 else nav["cell_height"]
    return 2 * nav["cell_height"] + detail
W = worst_height(NAV)
assert W <= PATH_D - MARGIN, f"a path point can float {W:.2f} m above the ground — too close to the agent's {PATH_D} m reach"
OLD = dict(GODOT_DEFAULTS, cell_height=0.25)                                          # the settings before M08.2a
assert worst_height(OLD) > PATH_D - MARGIN, "the pre-M08.2a settings are shown to stall"

steps = int(round(NAV["agent_max_climb"] / NAV["cell_height"]))
assert abs(steps * NAV["cell_height"] - NAV["agent_max_climb"]) < 1e-6, "agent_max_climb is a whole number of cell heights"
import math
body = PLAYER.split('[node name="Player" type="CharacterBody3D"]', 1)[1].split("\n[", 1)[0]
FLOOR_MAX = float(re.search(r"^floor_max_angle = ([0-9.]+)", body, re.M).group(1))
CAPSULE_R = float(re.search(r'\[sub_resource type="CapsuleShape3D"[^\]]*\]\nradius = ([0-9.]+)', PLAYER).group(1))
STEP = CAPSULE_R * (1 - math.cos(FLOOR_MAX))      # the tallest ledge the capsule rides up as floor (no step-up code)
tiers = [float(h) for h in re.findall(r'\[sub_resource type="CylinderShape3D" id="CylinderShape3D_tier\d"\]\nradius = [0-9.]+\nheight = ([0-9.]+)', _src("scenes", "world", "props", "TerracedMound.tscn"))]
assert tiers, "the mound tiers"
def plans_over(h, climb, ch):   # voxelisation can shave up to one cell off a step before the climb test
    return h - ch <= climb + 1e-9
for h in tiers:   # a step is either one the player can take, or one the mesh never plans over
    assert h <= STEP or not plans_over(h, NAV["agent_max_climb"], NAV["cell_height"]), \
        f"the mesh may plan over a {h} m step the player cannot take (climb {NAV['agent_max_climb']} m + one {NAV['cell_height']} m cell, capsule step {STEP:.3f} m)"
assert any(STEP < h and plans_over(h, 0.25, 0.25) for h in tiers), "the pre-M08.2a climb (0.25 m, 0.25 m cells) is shown to plan over the mounds' tiers"
assert any(STEP < h and plans_over(h, 0.1, NAV["cell_height"]) for h in tiers), "a 0.1 m climb is shown to still let a quantised tier through (seen at runtime)"

print(f"nav height: cell {NAV['cell_size']:g} x {NAV['cell_height']:g} m (map {map_ch.group(1)}), detail {NAV['detail_sample_distance']:g} m / {NAV['detail_sample_max_error']:g} m; "
      f"worst path-point height {W:.2f} m <= {PATH_D} - {MARGIN} m (pre-M08.2a: {worst_height(OLD):.2f} m, shown to stall); "
      f"climb {NAV['agent_max_climb']:g} m = {steps} cell(s): mound tiers {sorted(set(tiers))} m are above it, the capsule's step {STEP:.3f} m below them (climb + one cell below them; pre-M08.2a 0.25 m and an interim 0.1 m planned over them); agent {A_H:g} x {A_R:g} m matches")
print("ALL NAV HEIGHT SIMULATIONS PASSED")
