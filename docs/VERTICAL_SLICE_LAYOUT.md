# Vertical slice layout plan (M07.1)

Status: **approved by the developer as proposed** (M07.1 `[x]`).
Nothing in the game has changed: `scenes/world/Meadow.tscn` is untouched. Placing anything is M07.2;
navigation, bounds and the pond decision are M07.3; the house interior is M08.1.

## Scope (decided)
- The whole vertical slice stays **inside the existing 64 × 64 m Meadow** (camera bounds `CameraBounds`, ±32 m). No larger world, no second area (D-12; O-05 keeps the final area structure open until Phase 16).
- **House:** only the exterior footprint and its door/entry point are reserved. The interior is a separate area entered through the door in M08.1.
- **NPC:** only an exterior standing spot near the house and the path is reserved. No NPC is implemented.
- **Forest edge:** a zone is defined along the Meadow's rim; no trees are added yet.
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
- The Meadow's geometry digest below must still match the scene, so any change to `Meadow.tscn` (M07.2 onward) is made deliberately together with this plan.

## Not decided here
- **O-07** — is the pond walkable? (M07.3; the plan keeps every proposed element and path out of the pond either way.)
- **O-12** — camera bounds for interiors (before M08.2).
- The house's look, the NPC's identity and dialogue (Phase 08), and the forest edge's trees (M07.2 placement).

## Machine-readable plan

```slice-layout
digest 89878544adee7640
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
# proposed (M07.1)
house -24 0 6 5
door -21 0
npc -19.5 2.2
forest west -31 -31 -28 31
forest north -31 -31 4 -24
trailhead -24 -22.5
path to_house 0.5,3.2 -4,2.6 -10,-0.4 -16,-0.6 -21,0
path to_forest -21,0 -20.4,-0.5 -20,-8 -22,-15 -24,-22.5
```
