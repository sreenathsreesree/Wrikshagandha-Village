# A0 — Village World Design Lock (documentation and layout model)

Status: **design lock — approved by the developer on 2026-10-19 with two conditions (South Ridge, render baselines;
both reflected below) — planning and model only.** Nothing here builds anything. **No world construction is
authorised before the Phase 16 vertical-slice gate passes on an exported Godot 4.7.x Android build** (plan §7, §8).
Builds on `docs/VILLAGE_BLUEPRINT_A0.md` (the A0 blueprint, kept as written) and corrects it where the geometry below
shows it can't work. The planned coordinates are the ```village-plan block at the end, checked by
`tools/sims/sim_village_plan.py` (run by `tools/run_all.sh`) against the real Meadow and the real camera.

Coordinates are world metres: **x east, z south** — the camera always looks **north (−z)**.

Every item is marked **LOCK** (approved as the planning baseline: the principles of §1, recorded as D-64, and the
checked figures and corrections of §2–§5) or **OPEN** (a decision that still needs the developer; the options and a
recommendation are given, and **a recommendation is not a decision**). Items marked *provisional* in the plan block
are candidates the model checks for fit, not locked designs. A LOCK item is a planning baseline only: building any of
it waits for the Phase 16 gate and its own approved milestone. Where a LOCK item depends on an open decision, it says
so (§4: OD-1, OD-2).

---

## 1. Principles (LOCK — approved, D-64)

1. **A place to stay, not a hub of objectives.** The village invites the player to wander, listen and rest. No
   counters, timers, streaks or "visit all" rewards for its places; the existing once-ever rewards apply only where
   they already do (secret places, D-21/D-22, D-45).
2. **One social heart, several quiet edges.** The Great Tree is peace among people (D-53); water and edges are peace alone.
3. **The world carries the life.** Time, weather, wildlife and villager routines (D-41–D-44, D-51, D-52) — no new
   simulation for the village.
4. **The Meadow is untouched.** Growth is west and north only; no existing coordinate, save, routine spot or
   interaction moves (blueprint §2, §7).
5. **Every seat is a `RestSpot` with Rest Mode as built** (D-48, D-57, D-62): its framing data only, no camera change.
6. **Seated views are close views** (§3): a seat looks at something within about 3–9 m of it, low enough to be framed.
7. **Thresholds of nature:** zone changes happen through narrowings in tree lines, bends and gaps — never doors or loading.
8. **Measure before growing:** world size and navigation strategy follow device measurements (§9), not estimates.
9. **The Phase 16 gate stands:** this lock authorises planning only.

---

## 2. Bounds and dimensions (LOCK the relationship; OPEN the staging, OD-1)

| Rectangle | x | z | Size | Area |
|---|---|---|---|---|
| Today's ground (Meadow) | −32 … 32 | −32 … 32 | 64 × 64 m | 4,096 m² |
| **Stage A — first village** (proposed) | **−64 … 32** | **−32 … 32** | **96 × 64 m** | **6,144 m² (1.50×)** |
| Long-term target (blueprint) | −96 … 32 | −64 … 32 | 128 × 96 m | 12,288 m² (3.00×) |

- Stage A shares today's east, north and south edges: it adds one 32 m-wide strip **west** of the Meadow (x −64 … −32),
  which holds the square, the Great Tree and the south village. It is half of the long-term target.
- The target then adds a further 32 m west (x −96 … −64: lotus pond, western forest, waterfall) and 32 m north
  (z −64 … −32: north village, sanctuary slot) — **Stage B**, after Stage A is accepted on the phone.
- **Edge bands (LOCK as a rule, OPEN as an art choice):** each outer edge of a stage gets a 4 m forest band inside its
  rim (west x −64 … −60; north x −60 … −32, z −32 … −28, continuing the existing north strip), so no village feature
  sits against the rim. The bands do not hide everything beyond the rim: at the default arm the frame's top corners
  reach ~22 m to each side and ~20 m ahead of the player (§3), so near the edges the ground's end can show, as it does
  today (O-12). A visual-only backdrop beyond the rim is a Stage A art task (A1), not decided here.

---

## 3. What the camera can show (model, LOCK as constraints)

The model (`sim_village_plan.py`) rebuilds the real rig from its sources: `FollowCamera.tscn` (spring arm 1.4 m up,
pitched −42°, 11 m; Camera3D fov 50° vertical), `rest_spot.gd` (seated arm 8 m, framing offset (2, −2) — Camera3D's
h/v offsets, which Godot adds to the camera's position along its own axes), `project.godot` (16:9 canvas).
**Validation:** against the W1 captures of the Pond Rest Spot (commit `ca9b3b0`), the model places the seated player
at pixel (689, 349) where the capture shows it at about (690, 355); at yaw −45° it places the pond centre at
(1438, 290) and the large rock at (9, −6) at (1779, 466), where the capture shows them at about (1430, 300) and
(1750, 455). The model is exact geometry; the captures were read by eye.

**Where these figures come from:** the validation above and the table below were computed in a separate scratch
analysis (not committed) with the same rig equations, and re-derived during the A0 review with the committed model's
own functions (`rig`, `project`, `ground_hit`). `sim_village_plan.py` does **not** print or assert the table; it uses
the same equations only for the seated frame at 8 m (the seat checks) and the crown's reveal at the 11 m default arm
(§4). The zoomed-out rows are not checked by the model at all. None of these figures is a runtime measurement.

| View | Camera above / behind the player | Ground in frame (from the player) | Tallest thing in frame, by distance ahead |
|---|---|---|---|
| Standing, 11 m (default) | 8.8 m / 8.2 m | 4.5 m behind → 20.5 m ahead; ±22.5 m wide at the top | 5 m: 4.7 m · 10 m: 3.2 m · 15 m: 1.7 m · 20 m: 0.1 m |
| Standing, 15 m (zoomed out; not checked by the model) | 11.4 m / 11.1 m | 6.3 m behind → 26.3 m ahead | 10 m: 5.0 m · 20 m: 1.9 m |
| Seated, 8 m (Rest Mode) | 5.3 m / 7.3 m | 5.0 m behind → 9.9 m ahead | 5 m: 1.5 m · 10 m: 0 m |
| Seated, 10 m (zoomed out; not checked by the model) | 6.6 m / 8.8 m | 6.0 m behind → 12.8 m ahead | 5 m: 2.4 m · 10 m: 0.9 m |

**Consequences (LOCK):**
- **No vistas from seats.** A seat frames only what is within ~9 m ahead and low (≤ ~1.5 m at 5 m). Tall or distant
  things — the Great Tree's crown (4.6–9.4 m up), a cliff waterfall, the village seen from a ridge — **cannot** be
  framed from a seat with the current fixed pitch. The blueprint's "Hill View" and the draft's "South Ridge viewpoint"
  are therefore **not buildable as vistas**: no panoramic or distant view is possible without a future, separately
  approved camera change (OD-5).
- **Landmarks are discovered close, not seen from afar.** The blueprint's "the Great Tree … seen from the square" does
  not hold at the default arm: 20 m ahead, only things below ~0.1 m are in frame. The tree reveals itself as its crown
  enters the top of the frame (§4).
- **The seat's direction is not the rule — the frame is.** The existing Pond Rest Spot looks at a pond that lies
  south-east of it and still frames it, because the seated camera sits behind and the framing offset shifts the view.
  The model checks each seat's actual subjects in the actual frame at yaw 0 (the view every sit starts with).

---

## 4. The Great Tree — the social heart (LOCK position and seats, conditional on OD-1 and OD-2; OPEN details)

| Item | Value | Evidence |
|---|---|---|
| Position | **(−48, −14)** — moved 4 m east of the blueprint's (−52, −14) | at x −52 its 10 m keep-clear circle overlaps the 4 m west band by 2.0 m and its crown clears it by 0.14 m; at x −48 the keep-clear circle clears the band by 2.0 m and the crown by 4.1 m (model) |
| Asset figures | trunk collider r 1.3 m; crown reach 7.86 m, 4.62–9.43 m up; katte r 4.0 m (visual only); keep-clear r 10 m | B0.1 measurements; generator (`_platform_ring` 4.0 m); blueprint §5 |
| Distance from the square | 19.1 m (square centre (−41.5, 4) to the trunk) | model |
| Approach | the **tree road** (2 m) from the square's north-west edge (−44.2, −3.5) to the katte's apron (−46.2, −8.9), 5.4 m from the trunk | model: stops 4.4 m from the trunk (katte + 0.3 m clear) |
| Reveal | walking north, the crown's underside is in the frame top by **12 m** south of the trunk at the default arm (the model's check; its centre-line estimate first shows the crown at about 13 m); zoomed out it shows earlier (not checked by the model); the square's north-west edge, where the tree road starts, is 11.1 m from the trunk — so the crown is in view as the player leaves the square | model, default arm only — a geometric estimate that ignores other trees in the line of sight |
| Seats | three `RestSpot`s 4.6 m from the trunk, facing it: **katte_west** (−50.64, −10.23) yaw −35°, **katte_south** (−48.80, −9.47) yaw −10°, **katte_east** (−44.48, −11.04) yaw 50° | model: the trunk base (0.5 m and 1.2 m) is in each default seated frame; no seat on a path; the crown is never between the camera and the seated player |
| What a seat sees | the trunk's base, roots, the katte's stones and lamps at the top of the frame; the crown stays above the frame (it shades the scene instead) | §3 |
| Gathering | evening routine spots for villagers around the katte, as data (`NpcRoutineSpot`, D-41) — no new NPC behaviour | D-41, D-53 |

**Conditional on open decisions:** the position (−48, −14) assumes Stage A's west edge at x −64 with a 4 m band —
OD-1's recommendation (b), which is not decided. The three seats, the tree road and every path south of the trunk
assume OD-2's recommendation (a), also not decided. If either decision goes another way, the position and seats are
re-planned and re-checked by the model before A3; until then they are a planning baseline, not settled design. The
model checks what each seat's default frame contains, not which way the seat faces (§12).

**Occlusion (OD-2):** the crown hides a player standing north of the trunk (B0.1 finding). Recommended: keep all
paths and seats south of the trunk (the plan does); the opt-in canopy fade stays off unless a phone playtest shows
players going north of it.

**Cultural details (OD-9):** kalava threads and clay diyas are in the preview asset; their use at a village shrine
tree deserves review before A3 (D-54's principle of review for cultural content).

---

## 5. Paths, clearings and thresholds (LOCK the corrected routes)

| Element | Plan | Evidence (model) |
|---|---|---|
| **Village road** (2.5 m) | leaves the planned `to_forest` path at (−20, −8), **north of the house**, west to (−25.5, −8.8) | starts on `to_forest`; enters no existing object's layout radius (the forest strip's canopies included); ~9 m from the villager's home spot |
| **Strip threshold** (2.0 m) | through the existing west forest strip between `ForestWest5` and `ForestWest6`, (−25.5, −8.8) → (−33, −8.9) | 0.84 m from the nearest trunk (`ForestWest6`) — the existing 0.8 m path-edge rule; at 2.5 m wide it would be 0.59 m. It starts before the canopies: a full-width road ending at x −27 would enter `ForestWest5`'s canopy radius. The road narrows here under the canopies (a threshold of nature) |
| **Square road** (2.5 m) | (−33, −8.9) → the square's north-east edge (−37.4, −2.9) | clear |
| **Village Square** | centre **(−41.5, 4)**, r 8 m — moved 1.5 m west of the blueprint's (−40, 4) | at (−40, 4) its edge enters `ForestWestBack5`'s canopy radius by 0.22 m; at (−41.5, 4) it clears every existing object by ≥ 1.28 m |
| Tree road (2 m) | §4 | clear of the katte and the seats |

**Corrections to the blueprint (LOCK):**
- Its village road from the house door "west through a gap at z ≈ 2" **runs through the house** (the model measures
  −1.25 m clearance): the door is on the house's east wall. The corrected road leaves the existing `to_forest` path
  north of the house instead. A southern route around the house was tested and rejected (it crosses
  `MoundNorthWest`, `Bush4` and `TreeWide1`).
- Its **South Village** extent (x −34 … −20, z 0 … 20) overlaps the existing west forest strip (x −31 … −28, trees
  every ~4 m). South-village houses go **west of the strip**, south of the square (provisional, §7).

---

## 6. Seating and quiet places

| Place | Status | Notes |
|---|---|---|
| Pond Rest Spot | exists (E1, W1) | unchanged |
| Great Tree katte (3 seats) | LOCK (Stage A) | §4 |
| South Ridge | **provisional quiet resting place (OD-5)** — not a vista | a close-view seat south of the square (e.g. a flower bank or a bench by a lamp), framing only what lies within ~9 m of it; it does **not** show the village, the Great Tree or any distant scenery, and no panoramic view is implied without a future, separately approved camera change |
| Lotus Pond ghat | **OPEN (OD-4)**, Stage B | the seat must frame the water within ~9 m; the ghat's side follows the pond's final shape — decided when the pond is laid out |
| Waterfall pool | **OPEN (OD-3, OD-5)**, Stage B | a seat frames the plunge pool and the foot of the falls only; the falls' height stays above the frame |
| Forest clearing | OPEN, Stage B | optional |

---

## 7. South village (provisional, Stage A)

Two placeholder houses (6 × 5 m) south of the square, doors on their south walls facing a lane — so the camera, which
looks north, sees each door: **south_1** (−46, 16), **south_2** (−54, 15); a 2 m **south lane** from the square's south
edge (−40.5, 11.9) south to (−40.5, 20.5) and west to (−56, 20.5). The model checks them as candidates: 1.5 m clear
of existing objects and the west band, 1.0 m from the square, 0.8 m from the lane, each door within 3 m of it. Their
number, style and inhabitants are not decided here (A4).

**Unresolved geometry (must be resolved before construction):** the provisional South Ridge area (§6; centre
(−44, 24), radius 4 m) overlaps the provisional south lane by 1.5 m — the area's edge reaches 1.5 m past the lane's
edge along z 20.5. The model does not catch this: later-stage areas are checked only against the target bounds.
Neither entry is moved here and the overlap is not judged harmless; it stays open until the South Ridge (OD-5) and
the south village (A4) are laid out.

---

## 8. Stream, waterfall and the Secret Tree Sanctuary (provisional, Stage B)

- **Stream and waterfall (OD-3, recommended a):** a flat world for navigation (max climb 0 stays); the waterfall
  falls from a visual-only rock face standing outside the target's north-west rim into a ground-level pool
  (provisional area at (−90, −58)); a ground-level stream with W1-style banks runs south to the lotus pond, its water a
  blocked carve (like the pond's core, D-28) except at a flat ford and a flat plank bridge; a **new** flowing-water
  shader (`water.gdshader` stays the pond's). Its sound needs a licensed recording (AUDIO_ASSETS). Alternatives:
  (b) heightmap terrain, (c) stepped terraces — both rework navigation, camera bounds and budgets.
- **Secret Tree Sanctuary (OD-6, OD-7):** not in any earlier document. Proposed slot: the blueprint's reserved
  "Ruins" area north of the Meadow (provisional at (−20, −52)), reached by continuing the existing secret chain
  *Secluded Pond Nook → Hidden Hollow → Sanctuary* (D-45's pattern: existing props as clues, no marker). Its meaning,
  reward and any cultural content are **open**.

---

## 9. Rendering budgets as measurable hypotheses (no thresholds set here)

The plan has no numeric frame-rate or draw-call acceptance targets (PLAYTEST_PACK open decision 9); this lock adds
none. It states hypotheses and how each will be measured, so the developer can set targets from data.

**Baseline — desktop software-rendering figures from the W1 commit (`ca9b3b0`), relative only.** They are **not**
mobile figures and **not** acceptance thresholds. `tools/art/measure_render.gd mode=meadow` at the game camera (arm
11 m, pitch −42°, fov 50°), Godot 4.7.2, opengl3 on Mesa llvmpipe (a CPU software renderer) under Xvfb (1300 × 1000
screen), each run with a fresh user-data folder, 30 settle frames then the mean of 60 frames; mean of three runs:

| View (focus) | Draw calls | Primitives |
|---|---|---|
| meadow_start (0, 5) | 1,115.8 | 1.438 M |
| meadow_garden (12, 2.5) | 999.7 | 1.290 M |
| meadow_pond (9, −9) | 942.9 | 1.167 M |
| meadow_west_forest (−24, −8) | 1,006.3 | 1.167 M |

**Hypotheses (to measure, not to pass — none of them is a mobile acceptance threshold):**
- **H1 — view cost:** a Stage A view at the game camera (new fixed views at the square, the tree road and a katte
  seat) costs no more draw calls and primitives than the busiest baseline view (`meadow_start`), on the same machine
  and method. *Measure:* add the views to `measure_render.gd` at A1–A3 (tooling, approved with that milestone).
- **H2 — the Great Tree:** the asset stays within its approved 12,000-triangle budget (B0.1), and its view's cost is
  part of H1. *Measure:* `check_organic_assets.gd` (existing) and H1's views.
- **H3 — navigation bake:** the bake time grows with ground area (1.5× for Stage A). *Measure:* on an **exported
  Godot 4.7.x Android build** on the developer's phone (plan §7 policy), time from launch to the first walkable tap
  (PLAYTEST_PACK S2.11), today's build first as the baseline, then Stage A; a desktop timing of the bake is useful
  only as a relative check.
- **H4 — device frame rate:** Stage A views keep the frame rate the developer judges comfortable on the phone.
  *Measure:* the game has no on-screen frame-rate display; figures need the editor's remote debugger (Monitors) with
  the exported build deployed from a PC, or a debug overlay — adding one is a separate tooling decision.
- **Device/runtime needed for H3/H4:** a PC with Godot 4.7.x, its Android export templates and SDK, and the phone.
  **Android frame rate and navigation bake time are unmeasured** until an exported Godot 4.7.x build is tested on a
  device; until then only the desktop software-rendering figures above exist.

---

## 10. Open decisions (need the developer)

| # | Decision | Options | Recommendation | Why |
|---|---|---|---|---|
| OD-1 | Staging | (a) full 128 × 96 m at once; (b) Stage A (x −64 … 32) first | **(b)** | 1.5× the area, not 3×; measurable before growing further |
| OD-2 | Great Tree occlusion | (a) paths and seats south of the trunk; (b) canopy fade; (c) camera response | **(a)** | no camera change; fade needs phone checks |
| OD-3 | Stream/waterfall form | (a) flat world, visual cliff; (b) heightmap; (c) terraces | **(a)** | keeps navigation, camera and budgets |
| OD-4 | Lotus Pond ghat side | decided with the pond's layout (Stage B) | keep **open** | depends on the pond's shape and the frame check |
| OD-5 | Vista viewpoints (ridge, waterfall from afar) | (a) none — close views only; the South Ridge, if built, is a quiet resting place; (b) a per-spot seated pitch (a camera change E1 left "for a later viewpoint decision") | **(a) for Stage A**; (b) only as its own, separately approved camera decision later | the current rig cannot frame vistas (§3) |
| OD-6 | Sanctuary location | (a) reserved north slot, trail from the Hidden Hollow; (b) western forest; (c) behind the falls | **(a)**, provisional | continues the existing secret chain |
| OD-7 | Sanctuary meaning and reward | — | **open** | no source yet; D-54 review for any practice content |
| OD-8 | Navigation regions | (a) one; (b) one per zone | decide **after H3** | no device data |
| OD-9 | Cultural review of the shrine details | (a) review before A3; (b) generic details | **(a)** | respectful depiction |
| OD-10 | Long-term target and waterfall timing | — | keep 128 × 96 m; waterfall in Stage B | the heart before the far destination |
| OD-11 | Edge backdrop beyond the rim | (a) visual treeline beyond the rim (A1); (b) bands only | **(a)**, decided at A1 with screenshots | the frame reaches ~22 m sideways (§3) |

---

## 11. Implementation sequence (only after Phase 16 passes on an exported Android build)

Each step is separately approved, checked on desktop and on the phone (exported build) before the next.

**Stage A**
1. **A1 — Ground, rim, bounds, bands:** ground x −64 … 32; rim and camera bounds follow; west and north bands; the
   strip threshold opened by the path only (no existing tree moves). *Measure H1 baseline views and H3 on the phone.*
2. **A2 — Village road, threshold and square** (§5).
3. **A3 — The Great Tree, katte seats and tree road** (§4); OD-2, OD-9 settled first.
4. **A4 — South village** (§7) and the evening gathering routine spots.
5. *(No viewpoint step: the South Ridge stays a provisional quiet resting place, decided under OD-5; no vista.)*

**Stage B** (after Stage A is accepted on the phone): ground to the target; lotus pond (OD-4); forest loop and north
village; stream; waterfall (licensed audio for its sound); the Secret Tree Sanctuary if approved (OD-6, OD-7).

**Before the gate (allowed now):** this document and its model only.

---

## 12. What the model does not prove

- **Walkability:** it checks clearances by the layout rules, not a baked navigation mesh; reachability is checked when
  each step is built (`sim_tap_movement.py`, runtime probes).
- **Looks:** framing is geometry; whether a view is beautiful is for the PC and phone reviews.
- **Future meshes:** sizes come from the B0.1 measurements and the placeholder house; new assets need their own checks.
- **The edge of the world** beyond the bands (OD-11) and **performance** (§9) are measured, not modelled.
- **Seat facing:** each seat's yaw is recorded in the plan but not checked; the model checks only what the default
  seated frame contains at yaw 0 (the view every sit starts with, as the camera code works today — the model assumes
  it rather than reading it).
- **Areas against Stage A features:** provisional areas are checked only against the target bounds, so the South
  Ridge / south lane overlap (§7) is not caught.
- **The §3 camera table** is not printed or asserted by the model (§3).

---

## Machine-readable plan

```village-plan
# bounds <name> x0 z0 x1 z1 (z south; the camera looks north)
bounds stage_a -64 -32 32 32
bounds target -96 -64 32 32
band west_edge -64 -32 -60 32
band north_edge -60 -32 -32 -28
# the Great Tree: B0.1-measured crown (reach, bottom, top), blueprint keep-clear and trunk, generator katte
tree great_tree -48 -14 trunk 1.3 crown 7.86 4.62 9.43 keepclear 10 katte 4.0
clearing square -41.5 4 8
# the village road leaves the planned to_forest path north of the house; it narrows through the west strip
path village_road 2.5 -20,-8 -25.5,-8.8
threshold west_strip_gap 2.0 -25.5,-8.8 -33,-8.9
path square_road 2.5 -33,-8.9 -37.4,-2.9
path tree_road 2.0 -44.22,-3.52 -46.17,-8.92
# katte seats 4.6 m from the trunk, facing it; subjects: the trunk's base at 0.5 m and 1.2 m
seat katte_west -50.64 -10.23 -35 -48,0.5,-14 -48,1.2,-14
seat katte_south -48.80 -9.47 -10 -48,0.5,-14 -48,1.2,-14
seat katte_east -44.48 -11.04 50 -48,0.5,-14 -48,1.2,-14
reveal great_tree 12
# candidates, not locked
provisional path south_lane 2.0 -40.5,11.94 -40.5,20.5 -56,20.5
provisional house south_1 -46 16 6 5
provisional house south_2 -54 15 6 5
provisional area south_ridge -44 24 4   # a quiet resting place only — no vista (OD-5); overlaps south_lane by 1.5 m, unresolved (§7)
provisional area lotus_pond -74 6 7
provisional area waterfall_pool -90 -58 4
provisional area sanctuary -20 -52 6
```
