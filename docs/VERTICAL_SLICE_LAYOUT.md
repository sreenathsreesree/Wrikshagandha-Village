# Vertical slice layout plan (M07.1)

Status: **approved by the developer as proposed** (M07.1 `[x]`). **Placed in `Meadow.tscn` by M07.2**
(`[~]`: statically verified; the editor open and the runtime checks below are pending).
Navigation tuning, bounds and the pond decision are M07.3; the house interior is M08.1.

## Scope (decided)
- The whole vertical slice stays **inside the existing 64 × 64 m Meadow** (camera bounds `CameraBounds`, ±32 m). No larger world, no second area (D-12; O-05 keeps the final area structure open until Phase 16).
- **House:** only the exterior footprint and its door/entry point are reserved. The interior is a separate area entered through the door in M08.1.
- **NPC:** only an exterior standing spot near the house and the path is reserved. No NPC is implemented.
- **Forest edge:** a zone is defined along the Meadow's rim (M07.1); placeholder trees fill it (M07.2).
- **Path:** two planned extensions connect the existing path to the house and the forest edge. Every existing coordinate and landmark stays where it is.

## Orientation and units
Metres in the Meadow's ground plane: **x** to the right (east on the map below), **z** downward on the map (+z is "south", towards the bottom of the map). The ground is 64 × 64 m centred on the origin; the player starts at (0, 5).

## Map

```
            x = -32                          0                              +32
  z = -32   +--------------------------------------------------------------+
            |FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF .        (north forest edge, z ≤ -24)
            |FFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFF .                          |
            |FFF   T(-24,-22.5)                                               |
            |FFF     :                                                        |
            |FFF     :   Ancient Grove (-9,-12)                 Pond Nook     |
            |FFF     :                               Pond (10,-9) (14,-12)    |
            |FFF      :                         ...path... (8,-8)             |
            |FFF       :                    ...                               |
            |FFF        :              ...         Stone Ring (13.8,-1.8)      |
            |FFF  +-----+ D ===========  (0.5,3.2)        Garden (11–14, 0–5)  |
            |FFF  |HOUSE|  N    path      * start (0,5)    Hidden Pocket (18,-2.5)
            |FFF  +-----+   (-19.5,2.2)    Wildflower Clearing (5.3,5.5)      |
            |FFF  (-27..-21, -2.5..2.5)                                       |
            |FFF                                            Overlook (13,11)  |
            |FFF                          Mystery Grove Tree (-3,14)          |
            |FFF  (west forest edge, x ≤ -28)                                 |
  z = +32   +--------------------------------------------------------------+
   F = forest-edge zone   D = door (-21, 0)   N = NPC spot   T = trailhead
   === planned path "to_house"   :  planned path "to_forest"   ... existing path
```

## Proposed layout

| Element | Position | Notes |
|---|---|---|
| **House footprint** | centre (-24, 0), 6 m (x) × 5 m (z): x -27…-21, z -2.5…2.5 | On open ground west of the start, ~25 m from the spawn; backs onto the west forest edge |
| **Door / entry** | (-21, 0), centre of the house's east wall | Faces the start; the future interior's entry point (M08.1) |
| **NPC spot** | (-19.5, 2.2) | Beside the door, ~2.4 m off the path — seen on arrival, never in the way |
| **Forest edge, west** | x -31…-28, z -31…31 | A band along the west rim, behind the house |
| **Forest edge, north** | x -31…4, z -31…-24 | A band along the north rim, west of the pond side |
| **Trailhead** | (-24, -22.5) | Where the path reaches the forest edge (the corner of the two bands) |
| **Path "to_house"** | (0.5, 3.2) → (-4, 2.6) → (-10, -0.4) → (-16, -0.6) → (-21, 0) | Leaves the existing path at its first patch (`Patch1`, beside the start), passes south of the Bush at (-13, 2) and north of the round tree at (-16, -4), ends at the door — ~22 m |
| **Path "to_forest"** | (-21, 0) → (-20.4, -0.5) → (-20, -8) → (-22, -15) → (-24, -22.5) | From the door north along the house's east side to the trailhead — ~23 m |

The garden, pond and existing paths are unchanged: the existing path still runs from the start to the pond (`Patch1`…`Patch7`) with its branch towards the Wildflower Clearing; the garden is reached over open ground as now.

## Clearance rules (checked by `tools/sims/sim_slice_layout.py`)
- Everything proposed lies inside the 64 × 64 bounds, at least 1 m in from the edge.
- The house footprint and the NPC spot keep **1.5 m** from solid objects (farm plots, the pond — radius 4.2 m, trees, rocks, bushes, logs, mounds, the monolith, discovery spawn points, garden flowers, the player spawn), **0.5 m** from places' trigger zones, **0.3 m** from small decoration (grass, motes, footprints).
- Forest-edge zones contain no existing object.
- Planned paths keep **0.8 m** from solid objects, never cross the pond, a plot or the house, and may pass through places' trigger zones, decoration and past the player spawn point (the existing path already starts beside it).
- Connections: "to_house" starts on an existing path patch and ends at the door; "to_forest" starts at the door and ends at the trailhead, which touches a forest zone; the NPC stands 1.2–3 m from a planned path and within 4 m of the door; the door sits on the footprint's edge.
- The existing Meadow's geometry digest below (every node outside `VerticalSlice`) must still match the scene — M07.2 added nodes without changing any existing one — and the whole scene must match `scene_digest`, so any later change to `Meadow.tscn` is made deliberately together with this plan.
- Placement (M07.2): see **Implementation state** below for the extra rules the placed nodes are checked against.

## Implementation state (M07.2)
Everything sits under one `VerticalSlice` node, a direct child of the Meadow (at the origin, unrotated), appended
after the existing nodes. No existing node, sub-resource setting, landmark, plot, discovery position, navigation
setting or the camera bounds changed: the existing-world digest `89878544adee7640` (every node outside
`VerticalSlice`) still matches; the whole scene's digest is now `scene_digest` below. No script was added or changed.

| Element | Node(s) | What it is |
|---|---|---|
| House exterior | `VerticalSlice/House` → `scenes/world/props/HousePlaceholder.tscn` at (-24, 0, 0) | A plain `StaticBody3D`: a 6 × 5 × 3 m collision box, 6 × 5 × 2.6 m walls, a gabled roof (ridge north–south, top ≈ 4.1 m), a door panel on the east wall. Exterior only — no interior, no interaction. |
| Door | `DoorMarker` inside the house scene, local (3, 0, 0) → (-21, 0) | A plain `Marker3D` facing east (+x, out of the door towards the path). **Not an `AreaEntry`**: the door's entry and the Enter/Exit transition are M08.1's, and adding an entry now would change `Main._find_entry`'s fallback (the lowest id). |
| NPC spot | `VerticalSlice/NpcSpot` → `scenes/world/props/NpcSpotPlaceholder.tscn` at (-19.5, 0, 2.2) | A `Marker3D` with a flat 0.9 m ground disc, no collider (never blocks the player or the navigation mesh). No NPC (M08.3). |
| Forest edge, west | `ForestWest1–15` (front row, x ≈ -28.8), `ForestWestBack1–8` (x ≈ -30.4) | The existing `TreeTall` / `TreeRound` / `TreeWide` props, scaled 0.9–1.15, small deterministic jitter; slim `TreeTall`s behind the house. |
| Forest edge, north | `ForestNorth1–8` (z ≈ -25.2), `ForestNorthBack1–5` (z ≈ -29.8) | As above; the front row leaves the trailhead open (trees at x -26.5 and -21.5). |
| Path "to_house" | `VerticalSlice/Path/HousePath1–13` | Patches of the existing path mesh and material every 1.7 m along the planned polyline, oriented along it, from `Patch1` to the door. |
| Path "to_forest" | `VerticalSlice/Path/ForestPath1–14` | As above, from the door to the trailhead. |

Walking: the house and the 36 tree trunks are static colliders, so the navigation mesh baked at load
(from the `navigation_source` group, settings unchanged) routes around them exactly as the joystick
collides with them; the path patches and the NPC disc have no collider and change nothing.

**Static verification (done):** `tools/check_project.py` (M07.2 contracts: one `VerticalSlice`, no scripts, only the
placeholder and tree scenes, path patches use the path mesh, the house a `StaticBody3D` with one box and a plain
`DoorMarker`, the NPC spot without collider, the Meadow's only `AreaEntry` still `meadow_start`, no script names the
placeholders); `tools/sims/sim_slice_layout.py` (placement against this plan — footprint, door position and facing,
NPC spot, trees in their zones and clear of everything, gaps ≤ 5 m, path coverage end to end, existing-world digest);
`tools/sims/sim_tap_movement.py` (spawn, interactables and the NPC spot clear of every obstacle, the house and trees included).

**Runtime pending (needs the Godot editor / a device — not done):**
- [ ] Open `Meadow.tscn` and the two new prop scenes in the Godot 4.7.2 editor: no load errors or warnings (they are hand-written in the existing scene style).
- [ ] Look: the house, roof and door read as a house; the forest edge reads as an edge; the path patches join the existing path without visible gaps.
- [ ] Navigation: the mesh bakes at load with the house and trees; tap-to-move routes around the house and reaches the door front, the NPC spot and the trailhead; joystick collides with the house walls.
- [ ] Camera: the roof (≈ 4.1 m) hiding the player behind the house is acceptable or noted for M07.3; the forest canopies at the rim look right against the bounds (bounds unchanged).
- [ ] Android: frame rate and load (bake) time with 36 more trees, 27 patches and the house (shadows on).

## Not decided here
- **O-07** — is the pond walkable? (M07.3; the plan keeps every proposed element and path out of the pond either way.)
- **O-12** — camera bounds for interiors (before M08.2).
- The house's final look (Phase 16 art), the NPC's identity and dialogue (Phase 08).

## Machine-readable plan

```slice-layout
# existing Meadow (every node outside VerticalSlice) — unchanged by M07.2
digest 89878544adee7640
# the whole Meadow, VerticalSlice included (M07.2)
scene_digest 076b3a88611ba905
# existing Meadow nodes the plan relies on (checked against Meadow.tscn)
existing PlayerSpawn 0.0 5.0
existing Patch1 0.5 3.2
existing Patch7 8.0 -8.0
existing WildflowerBranch3 3.8 4.8
existing Pond 10.0 -9.0
existing FarmPlot1 11.0 0.5
existing FarmPlot7 13.6 5.1
existing QuietFarmLandmark 12.1 2.2
existing WildflowerClearingLandmark 5.3 5.5
existing AncientGroveLandmark -9.0 -12.0
existing MysteryGroveTreeLandmark -3.0 14.0
existing OverlookLandmark 13.0 11.0
existing StoneRingLandmark 13.8 -1.8
existing SecludedPondNookLandmark 14.0 -12.0
existing HiddenFlowerPocketLandmark 17.6 -2.5
existing Bush4 -13.0 2.0
existing TreeRound1 -16.0 -4.0
existing TreeWide1 -18.0 6.0
existing MoundNorthWest -11.0 7.0
# approved (M07.1), placed in Meadow.tscn under VerticalSlice (M07.2)
house -24 0 6 5
door -21 0
npc -19.5 2.2
forest west -31 -31 -28 31
forest north -31 -31 4 -24
trailhead -24 -22.5
path to_house 0.5,3.2 -4,2.6 -10,-0.4 -16,-0.6 -21,0
path to_forest -21,0 -20.4,-0.5 -20,-8 -22,-15 -24,-22.5
```
