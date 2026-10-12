# Village Blueprint — Stage A0 (documentation only)

Status: **proposal for review — nothing here is implemented.** Stage A (the world expansion) has not started; this
document changes no scene, script, data file, test or digest. Written alongside Stage B0.1 (D-60, D-61) on
`prototype/organic-world`. Every figure about the current game below was read from the repository at the time of
writing (`scenes/world/Meadow.tscn`, `scenes/camera/FollowCamera.tscn`, `scripts/camera/follow_camera.gd`,
`scripts/world/game_area.gd`, `docs/VERTICAL_SLICE_LAYOUT.md`); figures about the expansion are targets.

## 1. Where we start

| Fact | Value today | Source |
|---|---|---|
| Playable ground | 64 × 64 m plane centred on the origin: x −32…32, z −32…32 | `PlaneMesh_ground`, `BoxShape3D_ground` |
| World edge | `WorldRim` StaticBody3D, four boxes just outside ±32 m | `Meadow.tscn` |
| Camera bounds | the ground plane's size (the focus point stays inside it) | `sim_camera_bounds.py`, `area_camera_bounds.gd` |
| Follow camera | pitch −42°, spring length 11 m (zoom 7–15 m), pivot 1.4 m above the player, fov 50 (+2 when running), look-ahead ≤ 1 m; camera is 8.17 m south (+z) and 8.76 m above the player at default zoom; it always looks north (−z) | `FollowCamera.tscn`, `follow_camera.gd` |
| Navigation | one `NavigationRegion3D`, **baked at area load on a thread** from static colliders in the `navigation_source` group; cell 0.25 m, agent radius 0.35 m, height 1.3 m, **max climb 0.0 m**, max slope 37° | `NavigationMesh_meadow`, `game_area.gd` |
| Current nav result | 445 vertices / 561 polygons | B0/B0.1 nav-hash runs |
| Scene size | 291 nodes in `Meadow.tscn`; ~108 organic prop instances | `Meadow.tscn` |
| Saved world state | only `FarmPlot`s (by id) and ids of discoveries, secrets, sightings; **no landmark, prop or NPC position is saved** | D-41…D-47, M15.2 |
| Layout contracts | `sim_slice_layout.py` digests (`digest`, `scene_digest`) of every node's position/rotation/scale/size/entry/radius; `existing` coordinates in `docs/VERTICAL_SLICE_LAYOUT.md` | |

Key existing places (x, z): PlayerSpawn (0, 5) · Pond (10, −9) · Quiet Garden / farm plots (11…13.6, 0.5…5.1) ·
Pond Rest Spot (4.3, −12.1) · House (−24, 0), door (−21, 0) · villager home spot (−19.5, 2.2), pond spot (4, −7) ·
Ancient Grove (−9, −12) · Mystery Grove Tree (−3, 14) · Overlook (13, 11) · Stone Ring (13.8, −1.8) ·
Secluded Pond Nook (14, −12) · Hidden Hollow (19, −24) · west forest strip x −31…−28 · north forest strip
z −31…−24 · forest trailhead (−24, −22.5).

## 2. The expanded world (target)

**Extent:** x −96…32, z −64…32 (128 × 96 m, 3× today's area). The existing meadow stays where it is and becomes the
**east side** of the village; the world grows **west and north**, so no existing coordinate, save, routine spot or
interaction moves. The west and north forest strips become the **edge between the old meadow and the new village**,
opened at two gaps.

| Zone | Centre (x, z) | Approx. extent | Character | Notes |
|---|---|---|---|---|
| East Meadow (existing) | (0, 0) | x −32…32, z −32…32 | the current meadow: spawn, pond, garden, groves, secrets | **unchanged** |
| South Village | (−27, 10) | x −34…−20, z 0…20 | the existing house plus 3–4 houses along a lane south-west of it | existing house, door and villager spots stay; new houses only south and west |
| Village Square | (−40, 4) | r ≈ 8 m | open paved earth, a well, a bench ring, market cloths | the hub all paths meet at |
| **Great Tree** (Wrikshagandha) | (−52, −14) | crown r ≈ 8 m, keep-clear r 10 m | the banyan-peepal on its katte (D-53 social place) | the landmark seen from the square |
| North Village | (−62, −34) | x −72…−52, z −42…−26 | a cluster of 5–6 houses round a small yard | approached past the Great Tree |
| Lotus Pond | (−74, 6) | r ≈ 7 m | still water, lotus, a stepped ghat on its east side | second water place; fits a future peaceful place |
| Western Forest | (−86, −10) | x −96…−78, z −40…24 | dense mixed forest with one looping trail | edges hide the world rim |
| Hill View | (−84, −52) | r ≈ 6 m | a raised clearing (visual rise only — see §5) looking back over the village | end of the forest trail |
| Stream / waterfall | from (−90, −60) to the Lotus Pond | — | **later** (needs water shader work and crossing design) | reserved corridor 6 m wide |
| Ruins | (−20, −52) | r ≈ 6 m | **reserved** for a future exploration secret | kept empty |

## 3. Paths and loops

Paths are the existing flat `CylinderMesh_path` patches with the D-61 path material (no new geometry type). Widths:
village road 2.5–3 m, lanes 2 m, forest trail 1.4 m.

1. **Village road** — house door (−21, 0) → west through a gap in the west forest strip at z ≈ 2 (−31, 2) → Village
   Square (−40, 4). The gap is the only change near the existing house; the door, its AreaEntry and the house path stay.
2. **Tree road** — Square (−40, 4) → north-west → Great Tree katte (−52, −14), arriving at its **south** side (the
   side the camera looks from, §4).
3. **North lane** — Great Tree (−52, −14) → North Village yard (−62, −34).
4. **Pond lane** — Square (−40, 4) → west → Lotus Pond ghat (−67, 6).
5. **Forest loop** — Lotus Pond (−74, 6) → Western Forest trail → Hill View (−84, −52) → east along z ≈ −48 →
   the existing north forest trailhead (−24, −22.5) through a second gap in the north strip at x ≈ −24… and back
   into the old meadow's to_forest path. This closes one large loop: meadow → village → tree → north village →
   forest → hill → meadow.
6. **South lane** — Square (−40, 4) → South Village lane (−30, 16).

Every path keeps a **2 m clearance** from colliders on each side (agent radius 0.35 m + tap-to-move tolerance), and no
path runs within 1.5 m of the world rim.

## 4. Camera implications

The follow camera is fixed in direction (always looking north from the south). With the default 11 m zoom, the line
from the camera to the player's head rises about 0.9 m per metre south of the player (1.4 m + d·tan 42°). Consequences:

- **Anything taller than ~1.4 + 0.9·d metres standing d metres south of the player hides them.** An ordinary tree
  (3.3 m) hides the player only when it is within ~2 m south; a house (≈4 m eaves) within ~3 m south.
- **The Great Tree (9.4 m tall, crown 4.6–9.4 m high, reach 7.9 m) hides the player completely whenever the player is
  under or north of its crown.** Measured in the B0.1 preview capture at the follow camera's exact angle.
  Options, in order of preference:
  1. *Landmark canopy fade* — already built in B0.1 as an **opt-in** shader parameter of the landmark foliage
     material (`fade_radius`, default 0 = off): crown fragments near the player→camera line and higher than 1.8 m
     above the player are dithered away. It reads only the existing global `wg_player_position` (already written each
     frame by the vegetation controller) and the renderer's camera position — **no new script, no camera change**.
     Enabling it is a one-value material change; it needs a PC/Android visual check (dither on small screens).
  2. Keep the katte's walkable area and its approach to the **south** of the trunk, and place the social spots there.
  3. A camera-side occlusion response — **not proposed** (would change camera behaviour; would need its own approval).
- **Zoom range 7–15 m** changes the reach: at 15 m the camera is 11.4 m high and occlusion drops; at 7 m it is 6.1 m high
  and the Great Tree hides more. Tests should cover both ends.
- **Camera bounds follow the ground plane.** Growing the plane to 128 × 96 m (centre (−32, −16)) moves the bounds with
  it automatically; `sim_camera_bounds.py` will need its expected values updated deliberately.
- Houses should face their doors **south** (towards the camera) wherever possible, so doors and NPCs are visible.

## 5. Navigation risks

- **Max climb is 0.0 m.** Any collider that rises from the ground — the Great Tree's 0.5 m katte, a ghat step, a
  "raised" Hill View — is a wall to the navmesh. Either keep those visual-only (no collider; the player walks
  through/over a flat collider), or add ramps within the 37° slope limit. The katte in the preview has no collider today.
- **Runtime bake cost** scales with area ÷ cell²: 3× the area is roughly 3× the bake work at load, on a thread.
  Measure on Android before committing to 0.25 m cells; options are a coarser cell (0.3 m) outside the village or
  **one region per zone**.
- **Gaps in the forest strips** must be ≥ 3 m wide between collider edges so the baked corridor survives agent-radius
  erosion (0.35 m each side) with room for tap-to-move snapping.
- **Big trunks** (the Great Tree, r ≈ 1.3 m) need a single simple collider; buttress roots and aerial roots stay
  visual-only so they don't fragment the navmesh.
- **Villager routines** (`villager_home`, `villager_pond`) and their paths are inside the old meadow and must keep
  working; any new NPC routes should be added as new spots, never by moving these.
- The layout digests (`digest`, `scene_digest`) will change by design in Stage A; each change should be recorded
  deliberately with the plan, as M07.2–E1 did.

## 6. Mobile performance

Reference (desktop, software renderer — relative only): the current meadow at the game camera draws ~900–1,080 draw
calls and 1.1–1.4 M primitives per frame including shadow passes (B0.1 measurement). Stage A should not multiply that by
the area factor. Targets and methods:

- **Visible budget per view** (game camera, default zoom): ≤ the current meadow's draw calls and primitives —
  the camera sees roughly the same area wherever it is, so this is achievable if distant zones cost nothing.
- **Visibility ranges** (`visibility_range_end` with fade) on props and houses so only the ~40 × 30 m around the
  camera draws; the Great Tree is the one exception (visible from the square).
- **MultiMesh** for grass tufts, flowers, pebbles and small bushes (today each is its own instance — the largest
  draw-call source).
- **Shared materials only** (already true for the organic set) so the renderer can batch.
- **Shadows:** keep one directional light; shorten `directional_shadow_max_distance` to the visible area.
- **Triangle budgets** (approved in B0.1): 2,000 per ordinary tree, 400 per rock, 12,000 for the Great Tree.
- Measure every Stage A step on the same machine before/after, and **on an Android device** before sign-off.

## 7. Protected contracts Stage A must respect

Save v9 and its fixtures; spawn (0, 5); discovery, secret and sighting ids; interaction behaviour; NPC routines and
their spots; farming (plots stay where they are — their ids are saved); house access (door, AreaEntry, interior);
`project.godot`, export presets, `sway.gdshader`, `water.gdshader`, `data/`. Stage A should be split into small,
reviewable steps (e.g. A1 ground + rim + camera bounds; A2 village road + square; A3 Great Tree placement with
collider and fade decision; A4 north village; A5 pond and forest loop), each with its own verification.

## 8. Open decisions for the developer

1. Enable the Great Tree canopy fade (§4 option 1) or design around it (option 2)?
2. One navigation region or one per zone? (needs the Android bake measurement)
3. Hill View: purely visual rise, or real terrain (would need a heightmap and `agent_max_climb` / slope review)?
4. Stream and waterfall: in Stage A, or later?
5. Ruins secret: keep reserved, or schedule?
