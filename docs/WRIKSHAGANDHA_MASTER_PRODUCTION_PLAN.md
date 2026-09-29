# WRIKSHAGANDHA — Master Production Plan

The single source of truth for production. Every implementation belongs to a
phase and milestone below. Related documents:

- `docs/ARCHITECTURE.md`: how the game is built.
- `docs/DESIGN_DECISIONS.md`: what is decided and what is open.
- `tools/README.md`: validation.
- `docs/farming_persistence_plan.md`: farm save format.

---

## 1. Game identity

WRIKSHAGANDHA is a **peaceful exploration/life game**.

- **The player should feel:** free, comfortable, curious, connected to nature, rewarded for exploring, never rushed, never pushed through a conventional quest grind.
- **Farming is one part** of a larger living world. The long-term game combines exploration, nature, farming, wildlife, NPCs, homes, discoveries, collection, gentle progression, elemental regions, the Five Rishis, world changes, secrets and a peaceful sense of place.

## 2. Core loop

**EXPLORE → DISCOVER → COLLECT → RETURN → TEND → UNLOCK → WORLD CHANGES → EXPLORE AGAIN**

- Every system must feed this loop.
- Systems connect through shared channels: **items** (inventory), **knowledge** (journal/progression), **coins** (wallet) and **world state** (what changed).

## 3. Five Elements architecture

The eventual world is organized around five elemental **experiences**. Each becomes a gameplay system: its own environment, interactions, gameplay mechanic, wildlife, discoveries, progression, secrets, atmosphere and world-state changes. They are not just five biomes.

| Element | Themes (decided, D-04) | Status |
|---|---|---|
| Earth / Prithvi | soil, plants, farming, forests, physical life, stability | Meadow/Garden is the first Earth prototype |
| Water / Jala | ponds, rivers, flow, aquatic life, reflection, healing, water discoveries | Pond exists (no mechanic) |
| Fire / Agni | warmth, transformation, cooking, craft, sacred fire, material transformation | Not started |
| Air / Vayu | wind, movement, sound, birds, height, freedom | Not started |
| Space / Akasha | silence, mystery, ancient knowledge, stars, hidden places, deep exploration | Not started |

- Elements are prototyped **one at a time**, in the order Earth → Water → Fire → Air → Space (Phase 11).
- Each element's specific mechanic is an open decision (O-09).
- **Architecture:** element data resources, plus an optional element id on places, items, discoveries and NPCs. No bespoke per-place scripts.

## 4. Five Rishis — DESIGN DEPENDENCY

> **Five Rishis — pending final design decision.**

- **Decided:** *Element = what the world expresses; Rishi = the wisdom/understanding associated with that element* (D-06).
- **Not decided** (R-01…R-07 in `docs/DESIGN_DECISIONS.md`): names, element pairing, personality, location, teachings, visual identity, progression role, and how the player first learns of them.
- **Until then:** no Rishi names, lore, data or code. Phase 12 is blocked (`[!]`) on these decisions.

## 5. Production rules

1. **No random features.** Every change belongs to the current phase and milestone. New ideas go to *Parked ideas* (§14).
2. **Before changing code, state:**
   - the current phase and milestone
   - the exact objective
   - the files and systems affected
   - what is explicitly **not** changed
   - the verification plan
   - the definition of done
3. **After implementing:**
   1. Run `tools/run_all.sh`.
   2. Run simulations where applicable.
   3. Inspect the diff.
   4. Commit.
   5. Push to `main`.
   6. Record the commit hash here.
   7. Report **implemented** vs **verified in Godot/Android**, separately.
4. **Never claim runtime verification** without an actual run.
5. **No final assets, large environments, detailed houses, final NPC art, elaborate VFX or full-world level design** before the Vertical Slice Gate (Phase 16).
6. **Farming expansion is frozen** (D-11). Integration only.

## 6. Milestone system

Every milestone is numbered `Mpp.n` and records:

| Field | Meaning |
|---|---|
| Objective | What the milestone achieves |
| Inputs | What it builds on (existing systems, decisions) |
| Files affected | Planned files; confirmed in the report |
| Dependencies | Milestones or decisions that must be done first |
| Implementation | The approach, stated before coding |
| Verification | Static checks and simulations |
| Runtime test requirement | What must be run in Godot / on Android |
| Definition of done | Exact completion criteria |
| Commit | Hash(es) |
| Status | See below |

**Statuses:**

| Mark | Meaning |
|---|---|
| `[ ]` | Not started |
| `[~]` | Implemented, needs runtime testing |
| `[x]` | Verified in Godot/device (never set from static analysis). For milestones with **no runtime component** (documentation, tooling), `[x]` means completed and checked, and says so |
| `[!]` | Blocked |

Milestones for the current and next phase are written out in full. Later phases list objective, definition of done and runtime tests; their remaining fields are filled in **before** that phase starts.

## 7. Runtime test gates

When a milestone reaches a state that needs Godot or Android testing, implementation **stops** and the report says **"PLAYTEST REQUIRED"** with a short checklist.

- The developer runs it and reports back.
- No unrelated work continues past a gate.
- A milestone moves from `[~]` to `[x]` only on the developer's report.

## 8. Vertical-slice strategy

- **Build first:** a small playable test area.
- **It contains:**
  - meadow, garden, pond, forest edge, path
  - a simple house, a simple NPC
  - wildlife, discoveries
  - a basic elemental prototype
  - farming, inventory, coins, journal, saving
- **Placeholder geometry is expected.** The purpose is system validation.
- **The gate (Phase 16):** the small area must feel like a coherent real game. **No large world expansion before it passes.**

## 9. Assets-later strategy

- **Until Phase 16:** primitive meshes, placeholder vegetation, simple houses and NPCs, basic materials, existing lightweight props.
- **A dedicated Final Art / World Building phase after the gate covers:**
  - final houses, NPC models, animals, vegetation, furniture, rocks, temples;
  - elemental environments, Rishi characters;
  - VFX, animation polish, audio, environmental detail.

## 10. Economy direction

- **Coins are an internal reward system.**
  - A wallet with an append-only transaction ledger.
  - Earn rules as data, with repeat-reward protection (caps, diminishing returns, one-time-ever rewards).
- **1000 coins = ₹10** is a long-term *reference* only (D-10).
  - It lives in economy configuration, is read by no gameplay code, and serves a separate future backend/redemption phase.
- **No real-money redemption, payment systems or crypto** now.
  - That phase needs server-authoritative balances, anti-fraud, accounts, KYC/compliance and legal review.
- **Open:** the relationship between the existing Wriksha Points and coins (O-02).

---

## 11. Current repository status

| Area | Status | Notes |
|---|---|---|
| Movement (joystick) | `[~]` implemented | Not tested in Godot/Android |
| Tap-to-move + navigation | `[~]` implemented | Navmesh baked at runtime from static colliders; never executed |
| Tap-to-interact | `[~]` implemented | Area raycast + small-object tolerance; walk to the object, interact on entering the interaction zone (M01.3) |
| Camera | Partial | Follow + look-ahead; no bounds or zoom |
| Farming | Advanced prototype, **frozen** | 4 crops, quality, basket, 7 plots, Elderbloom, exploration seeds, milestones, persistence |
| Exploration | Partial | Landmarks, secrets, bonuses; place list hard-coded; progress not saved |
| Discovery / journal / collection | Partial | 9 discoveries, respawns, clues, daily discovery, journal, collection |
| Wildlife / day-night / events | Prototype | 14 wildlife actors, 600 s day, environmental events |
| Saving | Partial | One JSON save; farm block versioned; no top-level version |
| Inventory | Missing | Seeds/basket live inside FarmManager |
| Economy / wallet | Missing | Only Wriksha Points |
| NPCs, dialogue, houses, interiors, area loading | Missing | — |
| Audio | Hooks only | 10 empty sound slots; no audio files in the repo |
| Five Elements | Earth-like Meadow only | — |
| Five Rishis | Missing — design pending | — |
| Full world | Intentionally missing | — |
| Android build | Never built | Export preset exists |
| Runtime testing | None yet | Only one editor open, which exposed load errors (fixed `ebb6f2b`) |

## 12. Known architecture risks

| # | Risk | Resolved in |
|---|---|---|
| A1 | Player/camera live inside `Meadow.tscn`; interiors and area loading impossible; FarmManager assumes plots never unload | Resolved in code: ownership M03.1, area loading M03.2, plot unloading M03.3 (runtime test pending) |
| A2 | `Interactable` base is discovery-specific | M02.1 (in code; runtime test pending) |
| A3 | FarmManager (663 lines) holds inventory-like and reward responsibilities | Phases 04–06 (M04.2–M04.3: seeds/basket counts live in the `Inventory` autoload; FarmManager keeps only the rules; point rewards Phase 05) |
| A4 | Repeat-award problems: exploration bonuses re-award each launch (progress unsaved); repeat discoveries pay full points without limit | Phase 05 (P-02) |
| A5 | Hard-coded world data: place list, garden place id, numeric physics masks (layers are now named) | **Resolved in code:** physics layers M01.1; place list, garden place id, curiosity pairs and secret count M03.6 (`data/places/`) |
| A6 | Unused interaction path (`interact_requested`) | **Resolved in M02.5** (removed; guarded by the toolkit) |
| A7 | No top-level save versioning before inventory changes save keys | **Resolved in code:** M04.0 (P-01 → D-17: `save_version`, step migrations, newer saves refused); full save phase still Phase 15 |
| A8 | ~50 per-frame scripts; runtime navmesh bake cost unknown on device | Phase 01 test, Phase 16 |

---

## 13. Phases and milestones

### PHASE 00 — FOUNDATION — **implemented; one runtime check outstanding (M00.5)**

**M00.1 — Production plan** `[x]` (no runtime component)
- **Objective:** commit this plan as the single source of truth.
- **Inputs:** repository audit; master production direction.
- **Files:** `docs/WRIKSHAGANDHA_MASTER_PRODUCTION_PLAN.md` (replaces the v1 audit).
- **Dependencies:** none.
- **Verification:** content review against the direction's checklist.
- **Runtime test:** none.
- **Done when:** the plan is on `main`.
- **Commit:** recorded in §15.

**M00.2 — Validation toolkit** `[x]` (no runtime component; toolkit executed)
- **Objective:** move the toolkit from the temporary session workspace into the repository.
- **Files:**
  - `tools/check_project.py`, `tools/check_gdscript.py`
  - `tools/sims/sim_farming.py`, `sim_persistence.py`, `sim_tap_movement.py`
  - `tools/run_all.sh`, `tools/fetch_godot_api.sh`
  - `tools/README.md`, `tools/.gdignore`
  - `.gitignore`
- **Verification:** `tools/run_all.sh` passes on `main`; a deliberately broken copy fails.
- **Runtime test:** none.
- **Done when:** the toolkit runs from the repo.
- **Commit:** §15.

**M00.3 — Architecture overview** `[x]` (no runtime component)
- **Files:** `docs/ARCHITECTURE.md`.
- **Done when:** it documents scenes, player, camera, input, interaction, farming, inventory/economy/saving direction, area architecture, UI, data definitions and elemental direction.
- **Commit:** §15.

**M00.4 — Design decisions registry** `[x]` (no runtime component)
- **Files:** `docs/DESIGN_DECISIONS.md`.
- **Done when:** decided, open (Rishis, economy, progression, areas, controls) and proposed items are recorded, with nothing invented.
- **Commit:** §15.

**M00.5 — Repository cleanup (safe only)** `[~]` (needs the Godot 4.7.2 open check)
- **Scope:**
  - Godot feature tag `4.3` → `4.7`.
  - Physics layers named (`world`, `interactables`) in `project.godot`.
  - Stale code comments corrected (comment lines only: "session-only", "Interact button").
  - v1 plan replaced.
  - Stale branch `claude/wrikshagandha-repo-audit-afzvtu` (0 unique commits): local copy deleted; **remote deletion refused (HTTP 403) by the cloud environment's git permissions**, so the developer deletes it in the GitHub UI.
- **Not in scope:** any code, scene or data change.
- **Verification:** the diff shows comment-only `.gd` changes; the toolkit passes.
- **Runtime test:** open the project in Godot 4.7.2 and confirm there are no errors (first item of the Phase 01 playtest).
- **Commit:** §15.

---

### PHASE 01 — PLAYER — **next**

Goal: comfortable, reliable movement in both modes on a real phone.

**M01.1 — Physics layer constants** `[~]` (verified in code; no runtime-visible change — confirmed at M01.6)
- **Objective:** replace numeric masks in code with the named layers (one shared definition).
- **Inputs:** layer names (M00.5).
- **Files:**
  - new `scripts/data/physics_layers.gd` (`class_name PhysicsLayers`, constants only, not an autoload);
  - `scripts/autoload/input_manager.gd` (uses `PhysicsLayers.INTERACTABLES` / `PhysicsLayers.WORLD`; its two local numeric constants removed);
  - `tools/check_project.py` (enforcement);
  - `docs/ARCHITECTURE.md`.
  - `Player.tscn` unchanged: its InteractionZone mask stays 4.
- **Dependencies:** M00.5.
- **Implementation:** masks derived from layer numbers in one place (`1 << (layer - 1)`). Values identical to before (world 1, interactables 4), so no behaviour change.
- **Verification:**
  - `tools/run_all.sh` passes.
  - New checks: every `*_LAYER` constant must match its name in `project.godot`; any numeric layer/mask in other scripts fails.
  - Mutation-tested: a magic number in a ray query, a constant drifting from the project setting, a renamed layer, and a new numeric mask constant are all caught.
- **Runtime test:** none of its own (identical values); taps on objects and ground are exercised in the M01.6 playtest.
- **Done when:** no magic mask numbers remain in scripts, enforced by the toolkit. ✔
- **Commit:** §15.

**M01.2 — Keyboard fallback (desktop testing)** `[~]` (verified in code; needs a Godot run)
- **Objective:** WASD/arrow movement through `InputManager.move_vector`, the same path as the joystick.
- **Files:**
  - `project.godot`: new `[input]` actions `move_up`/`move_down`/`move_left`/`move_right`, with W/S/A/D and arrow keys as physical keys.
  - `scripts/autoload/input_manager.gd`.
  - `tools/check_project.py`, `tools/sims/sim_tap_movement.py`.
  - Docs.
- **Dependencies:** none.
- **Implementation:**
  - InputManager keeps the joystick's and the keyboard's contributions separately and combines them, clamped to length 1, into the one `move_vector`. This is needed because the joystick writes every frame.
  - Keys are read in `_input` (non-consuming, so a focused HUD button can't swallow a key release) and only on movement-key events. The value comes from `Input.get_vector()` over the actions.
  - Losing window focus clears the keyboard part.
  - No new `_process`; Player, joystick, tap-to-move and tap-to-interact unchanged. Keyboard input cancels a tap-to-move path, exactly like the joystick.
- **Verification:**
  - `tools/run_all.sh` passes.
  - **New checks:** the four actions must exist with both keys; every action a script uses must be defined; no raw key polling (`KEY_*`, `is_key_pressed`).
  - **Model check:** joystick frames never erase held keys; clamping; release, focus-out and mode change.
  - **Mutation-tested:** action removed, arrow key lost, undefined action (constant and literal), raw key polling, joystick-overwrites-keyboard.
- **Runtime test (Godot, desktop):**
  - WASD and arrows move the player in the expected directions (W/Up = away from the camera);
  - diagonals aren't faster;
  - releasing stops;
  - after clicking a HUD button, the arrow keys still move the player and releasing still stops;
  - keyboard + joystick drag together behave sensibly;
  - in Tap to Move, a key press stops the walk.
- **Done when:** desktop movement works without mouse emulation (awaiting the Godot run).
- **Commit:** §15.

**M01.3 — Touch interaction: tap-to-move / tap-to-interact** `[~]` (implemented `b663d76`; verified in code; **PLAYTEST REQUIRED**)
- *Numbering:* recorded as "M01.2a" until the developer's reconciliation; renumbered M01.3. The former M01.3 (cancel + water) was split: cancellation is M01.4, and the water decision (O-07) moved to M07.3.
- **Why:** a developer desktop test found that some ground taps didn't move the player, and tapped objects only worked when already within reach. This was inserted before M01.3.
- **Root causes (from the code):**
  1. Ground taps were ignored unless the mode was Tap to Move; the default is Joystick.
  2. Taps near obstacles or edges were rejected: the navmesh snap tolerance (0.35 m) equalled the agent radius the mesh keeps clear around obstacles.
  3. All taps were dropped until the runtime navmesh existed.
  4. Notification card panels blocked pointer input.
  5. A tapped object within 8 m was interacted with instantly without walking; farther ones only in Tap to Move mode.
  6. The 0.18–0.2 m discovery shapes made near misses fall through to the ground.
- **Changes:**
  - Taps are mode-independent (D-15).
  - Snap tolerance 1 m; straight-line fallback before the mesh exists.
  - Small-object selection tolerance 0.45 m around the tapped ground point.
  - Inactive interactables are ignored.
  - Interaction happens on entering the existing `InteractionZone` (D-16), event-driven; the 8 m rule is removed.
  - Cards are input-transparent.
- **Files:** `input_manager.gd`, `player.gd`, `DiscoveryNotification.tscn` (one property), `tools/check_project.py` (7 tap contracts), `tools/sims/sim_tap_movement.py`, docs.
- **Verification:**
  - `tools/run_all.sh` passes.
  - 6 GDScript bug re-creations are caught by the contracts; 5 model mutations are caught by the simulation.
- **PLAYTEST REQUIRED (Godot desktop, then Android):**
  - [ ] Tap empty ground → player walks there. Try several spots, near rocks, trees and edges, and repeatedly.
  - [ ] Tap while walking → the destination changes.
  - [ ] Tap a flower from far away → the player walks to it, stops about 2 m away, and it's collected automatically.
  - [ ] The same for a mushroom/discovery, and for a farm plot (the normal plot action or seed picker opens).
  - [ ] Double tap never interacts twice.
  - [ ] Joystick or keyboard during a walk → manual control takes over.
  - [ ] HUD buttons, open screens, the seed picker and notification cards never cause world movement (cards should let taps through).
  - [ ] Both movement modes: taps behave the same; the mode only shows/hides the joystick.
  - [ ] Feel: "I tap what I want and the character handles the rest."
- **Commit:** §15.

**M01.4 — Movement cancellation** `[~]` (verified in code; needs a Godot/Android run)
- **Objective:** a deliberate way to stop a tap-started walk (tap the player). Not blocked: pond walkability (O-07) is a separate world/navigation decision, now under M07.3.
- **Audit:**
  - A walk already stopped on joystick/keyboard input, a new tap, a mode change, arrival, the target disappearing, or the 1 s stall.
  - A touch-only player had no deliberate stop.
  - Tapping the player made a small sideways step: the player body is on the `world` layer, so the ground ray hit it and snapped to walkable ground up to 1 m away.
- **Files:** `input_manager.gd`, `player.gd`, `tools/check_project.py`, `tools/sims/sim_tap_movement.py`, docs.
- **Implementation:**
  - A tap whose world ray hits the player's body, or lands within `PLAYER_TAP_RADIUS` (0.6 m) of its feet, emits `InputManager.stop_requested`. The Player joins `InputManager.PLAYER_GROUP` and stops the walk, dropping any pending interaction.
  - An exact interactable hit still wins; a stop while idle is a no-op.
  - No scene edits, no new loops or autoloads.
- **Verification:**
  - `tools/run_all.sh` passes; 3 new tap contracts; the routing table and player model include the stop.
  - Mutation-tested: 4 GDScript and 2 model mutations caught.
- **Runtime test** (in the M01.6 checklist):
  - Tap the player while it walks → it stops.
  - Tap the player while it's heading to an object → the interaction doesn't happen.
  - Tapping ground just beside the player doesn't cause a jitter step.
- **Done when:** the player can stop a walk (and cancel a pending interaction) without joystick or keyboard. ✔ in code.
- **Commit:** §15.

**M01.5 — Animation state hooks** `[~]` Implemented — runtime testing pending (M01.6)
- **Objective:** one gameplay state for future character animation (IDLE / WALK / INTERACT) that describes movement and interaction and never drives them. The current procedural bob/squash is unchanged.
- **Audit:**
  - No animation system existed (no AnimationPlayer, AnimationTree or AnimatedSprite; no state variable). Only procedural facing, bob and footsteps, driven by speed in the existing physics step.
  - Movement state was implicit (`_navigating`, speed). `_interact_with()` is the single interaction call site.
  - Discovery `interact()` is a coroutine (a harvest beat, then it's freed); `FarmPlot.interact()` returns immediately. Interacting doesn't block movement.
  - There was nothing to reuse and nothing to duplicate.
- **Files:** `scripts/player/player.gd`, `tools/check_project.py`, `tools/sims/sim_tap_movement.py`, docs.
- **Implementation:**
  - `class_name Player`; `enum AnimState { IDLE, WALK, INTERACT }`.
  - `signal animation_state_changed(state, previous)`, emitted only on change from `_set_animation_state()`, its single emitter. `get_animation_state()` gives the current state.
  - **IDLE ↔ WALK** comes from the body's actual post-collision speed (`get_real_velocity()`), evaluated in the existing physics step, with hysteresis (start above 0.35 m/s, stop below 0.15 m/s).
  - **INTERACT** runs from just before the real `interact()` call until it returns (awaited), or until the object leaves the tree.
    - A serial makes a stale end ignored.
    - It ends in WALK if the player is moving, else IDLE.
  - No timers, loops, autoloads or scene changes. Movement and interaction behaviour are unchanged; the one-shot double-harvest guard now registers just before `interact()` instead of just after its synchronous part (same protection).
- **Verification:**
  - `tools/run_all.sh` passes.
  - 9 animation contracts on the real script; a state model in the movement simulation (full transition table, flicker, stale-end, vanished target, 50,000 random events).
  - Mutation-tested: 10 GDScript and 4 model mutations caught.
- **Runtime test (M01.6):**
  - Connect a temporary print to `animation_state_changed`, or watch `get_animation_state()` in the remote inspector:
    - standing → IDLE;
    - tap, joystick or keyboard movement → WALK;
    - arriving, cancelling, or tapping the player → IDLE;
    - collecting a flower → INTERACT, then IDLE or WALK;
    - a farm-plot tap → INTERACT, then back at once;
    - no IDLE/WALK flicker when stopping or nudging the joystick;
    - pushing against a rock reads IDLE.
- **Known note:** INTERACT is instantaneous for interactions whose `interact()` returns at once (farm-plot actions). Longer interaction beats belong to Phase 02 if needed.
- **Commit:** §15.

**M01.6 — Android movement playtest** `[ ]` → **PLAYTEST REQUIRED**
- **Objective:** confirm movement on a phone and decide the default mode (O-06).
- **Checklist:**
  - project opens in Godot 4.7.2 with no errors;
  - joystick moves and turns smoothly;
  - Movement toggle switches modes and the joystick hides;
  - tap on ground walks there and paths go around trees, rocks, logs and the monolith;
  - mound steps are climbable;
  - a tap while walking retargets;
  - tapping the player stops a walk and cancels a pending interaction;
  - the animation state reads IDLE / WALK / INTERACT correctly (see M01.5's runtime test);
  - taps on buttons, screens and the seed picker never move the player;
  - a drag does not move the player;
  - note the load time (navmesh bake);
  - note the frame rate;
  - **known issue to observe (not yet fixed):** the player occasionally gets stuck or spins while navigating toward a target. Note when it happens; it belongs to a later movement-polish pass;
  - **M02.3 facing:**
    - tap a distant flower/discovery → the player walks to it, stops at interaction range, faces it, interacts;
    - tap a distant farm plot → approaches, faces the plot, the existing plot interaction happens;
    - tap an object already beside the player → it faces the object before interacting;
    - targets behind, left and right of the player all turn correctly;
    - no sideways movement or new spinning;
    - cancel before arrival → no turn toward the cancelled target;
    - replace the target while walking → only the final target is faced;
    - the M01.5 INTERACT state still works; joystick and keyboard takeover unchanged;
  - **M02.4 tap feedback:**
    - tap a flower → its indicator shows and pulses at once; tap a farm plot → the same, immediately;
    - tap an unavailable object (a plot mid-harvest, a locked plot) → no misleading feedback; the ground behaviour is unchanged;
    - tap an object → walk → the indicator stays on it until the interaction starts (sensible throughout);
    - cancel (tap the player, joystick, keyboard) → the old indicator clears (unless the player is standing in its range);
    - retarget → only the current target shows;
  - **M02.4 small objects:**
    - exact flower tap; slightly off-centre; just outside the collision; between two nearby objects; beside a rock; an unavailable object next to an available one;
    - no unexpected target is ever selected; note any miss on mushrooms/flowers (tolerance 0.45 m);
  - after M02.4: M02.3 facing, the M01.5 INTERACT state and M01.4 player-tap cancellation still work;
  - **M03.1 persistent shell (full Meadow walk-through):**
    - the project opens and runs `Main.tscn` with no errors or warnings (no missing nodes, no "node not found");
    - the player starts where it did; the camera follows exactly as before (same angle, distance, smoothing, look-ahead);
    - the HUD shows as before (buttons, joystick, notifications, screens);
    - tap-to-move paths still work (the navigation mesh bakes); tap-to-interact, cancellation, facing and feedback unchanged;
    - wildlife, vegetation, time of day, environmental events and landmarks still react to the player;
    - discoveries, farm, saving and reloading work as before;
  - **M03.2/M03.3 area loader — reload round-trip (a copy of a real save is fine now; discoveries/events/time of day still reset):**
    - from the Godot remote debugger, call `load_area(load("res://scenes/world/Meadow.tscn"), "meadow_start")` on `/root/Main`;
    - expect: no errors; one Meadow; the player at the start, facing the marker's forward, no walk continuing; the camera snapped (no glide across the map); the HUD intact;
    - tap-to-move works again once the navigation mesh rebuilds; tap-to-interact, feedback and facing work on the new area's objects; wildlife/world simulation reacts to the player;
    - with a walk or an interaction in progress when reloading: it ends cleanly (INTERACT back to IDLE/WALK);
    - with the seed picker open when reloading: it closes;
    - an unknown entry id (e.g. `"nowhere"`): a warning, and the player lands on `meadow_start`;
    - **farm (M03.3):** before reloading, set up plots in different states — prepared soil, a thirsty crop, a growing (watered) crop part-way through a stage, a ready crop, a plot mid-harvest; after the reload each is exactly as it was (crop, stage, water/thirst, remaining growth time, quality; soil memory shown by the seed picker's soil rating); growing crops carry on and ripen; the garden's ready-crop wildlife pull is unchanged;
    - reload twice; then trigger an autosave (plant or harvest, or background the app) and relaunch: the farm is as it was;
    - expected until later milestones: discoveries respawn and one-time events/time of day reset;
  - **M03.4 camera bounds — walk the edges:**
    - away from the edges the camera looks and moves exactly as before (angle, distance, smoothing, look-ahead, FOV widening);
    - walk (joystick, keyboard and tap-to-move) to each of the four ground edges: the camera's focus stops at the edge — no lurch, no jitter, no sideways drift; turning back, it follows smoothly again;
    - note how much beyond the ground is still visible at each edge (for open question O-12);
    - after a remote-debugger `load_area(...)` round-trip: the camera snaps to the player at the start, still bounded, no glide or look-ahead jump;
  - **M03.5 pinch zoom + mouse wheel (pinch vs tap):**
    - pinch out/in on the world: the camera moves closer/farther smoothly with the fingers; it stops firmly at the nearest and farthest limits (no bounce, no drift when hammering a limit);
    - **a pinch never moves the player** — including a pinch where one finger stays still, and quick short pinches; lifting one finger mid-pinch doesn't walk or zoom; a third finger doesn't make the zoom jump;
    - single taps still walk and interact exactly as before; the joystick with a second finger on the world doesn't zoom;
    - desktop: the mouse wheel zooms (up = closer); clicking still walks/interacts; the wheel over a scrolling screen (journal) scrolls it, not the camera;
    - zoom survives a `load_area(...)` reload; zooming at a camera-bounds edge doesn't move the focus;
    - note whether 7–15 m feels right at both ends and the wheel step feels right (proposal P-03);
  - **M03.6 place data (quick regression — behaviour should be identical):** the Journal's "Places" list shows the same 8 places in the same order ("???" until visited); reaching the Overlook and the garden shows the same arrival cards ("A quiet place to grow." for the garden); finding a secret spot shows its name; finding all four secret spots still gives the "Every Secret Found" bonus; the curiosity bonus still fires for the pond nook / mystery tree before their discoveries; the garden's Journal heading and "in bloom" milestone still say "Quiet Garden"; found-seed places still grant their seeds.
  - **M04.0 save versioning** (desktop, where `user://save.json` can be opened — Godot's "Open User Data Folder"; Android for (a) only):
    - (a) install this build over a pre-M04.0 build that has a save with progress (points, journal, a planted plot mid-growth, seeds, basket, a movement mode): everything loads as before; after the next autosave (collect a discovery) the file starts with `"save_version":1` and still holds everything;
    - (b) fresh install / no save: the first save has `"save_version":1`;
    - (c) set `save_version` to `99`: launch → a fresh game, a warning "newer than this build" in the output; play, plant, pause and quit → the file is byte-for-byte unchanged (still 99);
    - (d) set `save_version` to `"abc"`, `-1` or `1.5`: launch → a fresh game and a "malformed save_version" warning (the file is replaced on the next autosave, as a corrupted file is today);
    - (e) set `"farm": []` (or `"points": "x"`): launch → everything else loads; that section starts empty; a "wrong type" warning; no script error.
  - **M04.1 items** (editor / any device): the project opens in Godot 4.7.2 with no errors for `scripts/items/*.gd` or `data/items/*.tres`; each of the 8 item files opens in the Inspector showing its id, name, category and crop; the farm loop is unchanged (seed counts on the picker, one seed back per harvest, basket rows and totals, found seeds, the save/relaunch of M04.0 (a)) — nothing uses items yet.
  - **M04.2 seeds and basket as items** (Android + desktop):
    - install over an M04.1/M04.0 build with a save holding seeds, planted crops, a basket with Plain/Good/Fine produce and a found seed: seed counts on the picker, the Basket screen (rows and quality split), the Journal's seed and basket lines and "Fine" hint are exactly as before; the next autosave writes `"save_version":2`, an `"items"` section, and a farm block without `seeds`/`basket` (desktop: check `user://save.json`);
    - full farm loop: plant (the seed count drops, planting is refused at 0), water, harvest at different qualities (one seed back, the basket row and split update, the Basket button appears after the first harvest), find an exploration seed once; relaunch — everything identical, no seed gained or lost (seeds in hand + crops in the ground unchanged);
    - fresh install: starting seeds on the picker, empty basket;
    - desktop: a v1 save with an unknown crop in `farm.seeds` loads with a "dropped" warning and nothing else lost.
  - **M04.3 inventory + collectibles** (Android + desktop):
    - the game starts with no autoload/script errors; the M04.2 farm checks above all still hold (seed counts, basket, relaunch);
    - collect a discovery (first time) and the same kind again after it respawns: points and cards as before; desktop: `user://save.json` `items` holds that collectible with a count of 2 after the next autosave/pause (e.g. `"river_stone":[2]`) and `"save_version":3`;
    - relaunch: the collectible count is still there; collecting a discovery never changes seed counts or the basket;
    - install over an M04.2 build with a save: everything loads as before and is stamped version 3; (optional) the M04.2 build refuses a version-3 save and leaves it untouched.
- **Done when:** the developer reports results; the default mode is recorded in `DESIGN_DECISIONS.md`.

---

### PHASE 02 — INTERACTION
Goal: one generic interaction architecture for everything touchable.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M02.1 | Split `Interactable` into a generic base + discovery behaviour, with no behaviour change (A2) | All existing interactions behave the same; toolkit passes | Tap every existing interactable | `[~]` |
| M02.2 | Generic verbs as data (Inspect, Collect, Harvest, Talk, Open, Enter, Exit, Use, Give, Plant, Water, Feed, Read) | Verb declared per interactable; Player/Input never branch on type | — | `[~]` |
| M02.3 | Facing the object on arrival (walking to it within interaction range already done in M01.3, D-16) | Player faces what it interacts with | Android: approach feel | `[~]` |
| M02.4 | Interaction feedback on tap (reuse the indicator); tune the small-object tolerance added in M01.3 | Small objects reliably tappable | Android: hit rate on mushrooms | `[~]` |
| M02.5 | Remove or bind the unused `interact_requested` path (A6) | One interaction entry point | — | `[~]` |
| M02.6 | Placeholder Inspect/Open/Read interactables as test fixtures, with zero Player changes | New types work without touching Player | Godot: tap each fixture | `[~]` |

**M02.1 — Generic interaction foundation** `[~]` Implemented — runtime testing pending
- **Objective:** make the existing `Interactable` a small generic contract, with all discovery behaviour moved into a discovery implementation, unchanged.
- **Audit:**
  - The base mixed generic presentation (indicator, proximity, burst scene, harvest sound) with discovery logic: `discovery_id`, the `DiscoveryDatabase` lookup in `_ready`, `DiscoveryManager.discover()`, the `harvested` signal and the category/rarity windup.
  - The 9 discovery scenes used the base script directly. A new object type (door, NPC) extending it would have inherited a discovery lookup and a discovery `interact()` that warns without a `discovery_id`.
  - Player and InputManager were already type-agnostic (`interact()`, `set_highlighted`, `update_proximity`, `remove_on_harvest`, `monitorable`). Availability was an implicit rule: `monitorable`, read directly by InputManager.
  - `FarmPlot` overrides `interact()` and uses the base's `RARITY_INTENSITY`, `_play_harvest_sound()` and `HarvestBurstScene`.
- **Files:** `scripts/interactables/interactable.gd` (generic base), new `scripts/interactables/discovery_interactable.gd`, `scripts/interactables/discovery_spawn_point.gd` (instance type), the 9 discovery scenes (script path only), `input_manager.gd` and `player.gd` (availability call), new `tools/fixtures/generic_interactable_probe.gd`, `tools/check_project.py`, new `tools/sims/sim_interaction.py`, docs.
- **Implementation:**
  - **Base `Interactable`** (Area3D): `is_interaction_available()` (= `monitorable`), `interact() -> bool` (default `false`), `get_interaction_metadata() -> Dictionary` (default empty; nothing reads it yet), `remove_on_harvest` (one-shot vs persistent), `set_highlighted()`, `update_proximity()`, and shared presentation (`HarvestBurstScene`, `RARITY_INTENSITY`, `_play_harvest_sound()`). No discovery, farm or signal code.
  - **`DiscoveryInteractable`** extends it: `discovery_id`, `harvested`, the definition lookup, `interact()`, spawn animation and harvest feedback, moved byte-for-byte (rewards, points, animations, removal, one-shot and persistence all unchanged).
  - **`FarmPlot`:** unchanged; it already implements the contract.
  - **InputManager** asks `is_interaction_available()` instead of reading `monitorable`. **Player's** single `interact()` call site also refuses an unavailable object (defence in depth: such objects can't reach it today). `@warning_ignore("redundant_await")` on the awaited call, since some implementations return at once.
  - No verb enum (verbs are M02.2). No new loops, timers, autoloads, masks, scene nodes or `.tres` changes.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - Interaction contract checks: base API present; availability backed by `monitorable`; no object-specific code in the base; every implementation has `interact() -> bool`; Player/InputManager name no implementation or discovery/farm member; one `interact()` call site; no second class hierarchy; no scene on the bare base; the probe is outside game content.
  - `sim_interaction.py`: discovery, farm plot and the probe through one Player path; unavailable objects refused; one-shot objects never interacted with twice (including a failed discovery that stays available); 2,000 random sequences.
  - Mutation-tested: 18 GDScript/scene and 6 model mutations caught.
- **Runtime test (PLAYTEST REQUIRED):**
  - The project opens with no script errors or new warnings.
  - Tap each of the 9 discoveries: same windup, burst, sound, points, journal entry and removal as before. Respawning ones respawn.
  - Farm plot: prepare, plant, water and harvest as before; a locked plot and a plot mid-harvest can't be tapped.
  - Walk-to-interact, tap cancellation and the INTERACT state behave as in M01.3–M01.5.
  - Save, quit and reload: discoveries, points and farm restored as before.
- **Commit:** §15.

**M02.2 — Generic interaction verbs as data** `[~]` Implemented — runtime testing pending
- **Objective:** an interactable advertises the verbs it offers in its current state, as data, without Player or InputManager knowing its type. Contract only: no verb UI, no new behaviour.
- **Audit:**
  - No verb representation existed, and no verb strings anywhere. The repository's convention for small closed sets is a class-scoped enum (`PlotState`, `AnimState`, `MovementMode`); `Interactable` is the one type every interactable and Player already share.
  - Discovery `interact()` does one thing, collect, and succeeds exactly when `DiscoveryDatabase.has_definition(discovery_id)`.
  - `FarmPlot.interact()` does one thing per state: EMPTY → prepare soil; SOIL → seed picker (plant, guarded by `can_plant()`); PLANTED/GROWING while thirsty → water; READY → harvest (guarded by a crop and not harvesting). Plus a 450 ms action cooldown.
  - Preparing soil is existing gameplay that no D-09 verb names (recorded as O-10).
  - `interact() -> bool` works and is the tap path; it stays the low-level execution API.
- **Decision:** `enum Verb { COLLECT = 1, PLANT = 2, WATER = 3, HARVEST = 4 }` on `Interactable`.
  - Typed and shared by every interactable with no new file, autoload or resource. Deterministic; explicit, never-reused values keep it stable if ever saved; future UI can map a verb to a label.
  - Only the D-09 verbs existing objects perform; the rest are added with their behaviours. A Resource per verb was rejected as heavier than a closed set needs; strings were rejected as easy to misspell.
- **Files:** `scripts/interactables/interactable.gd`, `scripts/interactables/discovery_interactable.gd`, `scripts/farming/farm_plot.gd` (one read-only query added), `tools/check_project.py`, `tools/sims/sim_interaction.py`, docs. Player and InputManager unchanged.
- **Implementation:**
  - `get_available_interaction_verbs() -> Array[Verb]`: the current verbs; empty whenever the object is unavailable. Subclasses override `_get_interaction_verbs()`, never the guarded wrapper.
  - `interact_with_verb(verb) -> bool`: a selected verb passed back generically; performed only if offered now, through `_perform_interaction_verb()`, which defaults to the existing `interact()`. Nothing calls it yet.
  - Discovery offers `COLLECT` when its definition exists. FarmPlot offers `PLANT` (SOIL, `can_plant()`), `WATER` (PLANTED/GROWING while thirsty) or `HARVEST` (READY with a crop, not harvesting), otherwise nothing. The probe fixture offers nothing (a valid empty list).
  - The tap path is unchanged: Player still calls `interact()`.
- **Intentionally deferred:** the verb for preparing soil (O-10); the cooldown isn't reflected in verbs; routing a UI-selected verb through Player's guarded path (INTERACT state, one-shot guard) arrives with the UI that needs it; several verbs at once per object; verb labels/UI.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - Verb checks: one `enum Verb` in the base, names from D-09, explicit unique values; nothing offered while unavailable; only offered verbs performed, via `interact()`; no subclass overrides the guarded functions; each object offers the verbs of its existing behaviour; Player/InputManager name no verb; no verb spelled as a string; no unknown `Verb.X`.
  - `sim_interaction.py`: FarmPlot's `interact()` and verb query are read from the GDScript and cross-checked state by state (same action, same guard); all 80 plot condition combinations; discovery available/unavailable; empty lists; changing verbs; the generic ask → choose → pass-back path.
  - Mutation-tested: 21 GDScript and 7 model mutations caught.
- **Runtime test:** none needed on its own (no behaviour change); covered by M02.1's checklist at the playtest gate.
- **Commit:** §15.

**M02.3 — Player faces the interactable on arrival** `[~]` Implemented — runtime testing pending (M01.6 checklist)
- **Objective:** when the player reaches a tapped object (or taps one already in range), it turns to face it, then the existing interaction begins. Orientation only.
- **Audit:**
  - Facing lives in `_update_facing(direction, delta)`, in the existing physics step: `_facing_angle` is set from the *intended* direction (joystick/keyboard input or the navigation path direction, not velocity) when it's longer than 0.1, and the visual eases toward `_facing_angle` every frame (`lerp_angle`, `TURN_SPEED` 11). With no direction, the last facing is kept.
  - Range is entered in `_on_interaction_zone_area_entered` (only the current `_approach_target` interacts), or at once in `_on_interact_target_requested` when already in range. Both stop navigation and call `_interact_with()`, the single `interact()` call site.
  - During the final approach the player faces its path direction, which usually points roughly at the object but not exactly (the path ends at the nearest walkable point). An object already in range could be behind or beside it.
  - Nothing would fight a target facing: navigation is stopped before `_interact_with()`, so the next physics step has no direction and keeps the facing. Joystick/keyboard input still overrides it (takeover unchanged).
- **Files:** `scripts/player/player.gd`, `tools/check_project.py`, `tools/sims/sim_tap_movement.py`, docs.
- **Implementation:**
  - `_face_target(target)`: horizontal direction from the player to `target.global_position` (y ignored); if shorter than `FACE_TARGET_MIN_DISTANCE` (0.05 m) the facing is kept (no NaN, no spin); otherwise it sets `_facing_angle` with the same formula `_update_facing()` uses.
  - Called once in `_interact_with()`, after the spent/availability guards and before `_begin_interaction()` (INTERACT) and `interact()`. Generic: target position only, no type or verb.
  - The turn itself is the existing smooth ease (no snap). The interaction starts on the same frame, so the turn completes during its first moments (about 0.2 s).
  - No change to range, navigation, constants (one new facing threshold only), animation states, scenes, verbs or `interact_with_verb()`.
- **Known issue (recorded, not addressed):** the occasional stuck/spinning navigation belongs to a later movement-polish pass. This milestone doesn't touch navigation.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - 12 facing contracts: the order accept → face → INTERACT → `interact()`; the target position, horizontal, with a zero-distance guard; no movement direction, type, verb, snap or waiting in the facing; called only from `_interact_with()`; `_facing_angle` written only by `_ready`/`_update_facing`/`_face_target`; no target facing in the physics step; stop and retarget drop the approach target; arrival interacts only with the current target; no `_process` in Player.
  - Movement model: ordered face/interact events; far arrival, in range, behind/left/right, underfoot; cancel and replace never face the old target; walking faces the path; 2,000 random runs where every face is immediately followed by its interaction.
  - Mutation-tested: 15 GDScript mutations (all caught by `check_project.py`) and 6 model mutations caught.
- **Commit:** §15.

**M02.4 — Interaction feedback on tap + small-object tolerance** `[~]` Implemented — runtime testing pending (M01.6 checklist)
- **Objective:** a recognised tap on an interactable gets immediate feedback on the object's existing indicator; small-object selection is audited and tuned.
- **Audit — feedback:**
  - The indicator (`DiscoveryIndicator`, `indicator_bob.gd`; one scene used by all 9 discoveries and the farm plots, tinted/scaled per use) is already generic. It has a `pulse()` acknowledgement (used by FarmPlot after actions) and a proximity reaction.
  - It was shown only by `set_highlighted()`, called when an object enters/leaves the 2.2 m InteractionZone. A tap on a distant object gave **no feedback until arrival** (delayed); a tap in range had no tap-specific acknowledgement. `update_proximity()` runs on the nearest object in range only.
  - So the indicator was sufficient; only its trigger/timing needed changing. No second mechanism needed.
- **Audit — selection:**
  - `_handle_tap`: (1) an exact ray hit on an available interactable wins; (2) otherwise the ground point, then a player tap (M01.4 stop); (3) otherwise `_interactable_near`: a 0.45 m sphere at the ground point, available candidates only, **ranked by distance to the object's centre**; (4) otherwise ground movement.
  - Shapes: discoveries are spheres of 0.18–0.2 m, farm plots cylinders of 0.55 m. At the default camera (11 m arm, FOV 50) a typical fingertip miss is roughly 0.3–0.45 m on the ground, so 0.45 m matches it.
  - Meadow spacing: the closest pairs are farm plots 1.70–2.3 m apart (0.6 m gaps), so their tolerance zones overlap (≈0.7% of simulated taps near objects fall in an overlap). The closest discoveries are 2.0 m apart (no overlap).
  - Risk found: centre ranking prefers a small object over a large one whose edge is nearer the tap (e.g. 5 cm off a plot's edge but a flower's centre closer). Equal sizes are unaffected. Query-order ties were possible.
- **Files:** `scripts/interactables/interactable.gd`, `scripts/player/player.gd`, `scripts/autoload/input_manager.gd`, `tools/check_project.py`, `tools/sims/sim_interaction.py`, docs. No scenes/resources.
- **Implementation — feedback:**
  - `Interactable.set_tap_selected(active)`: refuses unavailable objects; shows the same Indicator (visibility = in range OR tap-selected, one rule in `_refresh_indicator()`) with the existing `pulse()` (`TAP_ACK_PULSE` 0.35). `set_highlighted()` now feeds that same rule.
  - Player `_set_selected_target()`: releases the old selection and acknowledges the new. Called in `_on_interact_target_requested` at once (in range: before interacting; far: as the walk starts); released by `_stop_navigation()` (player tap, joystick/keyboard, mode change, target gone), `_start_navigation()` (retarget, ground tap) and at the start of `_interact_with()`. Re-tapping acknowledges again.
  - Generic: no object types, verbs or new UI/assets/sounds; InputManager untouched for feedback.
- **Implementation — selection:** tolerance **kept at 0.45 m** and generic. Near-miss candidates are now ranked by `_tap_distance()`: horizontal distance to the object's own collision shape (round shapes count their radius; others their centre), with ties broken by instance id. Exact hits still win; unavailable objects still never qualify; ground movement is still the fallback.
- **Known notes:**
  - A discovery's spawn glow ends by hiding its indicator (existing discovery behaviour, unchanged): a tap during that ~0.5 s respawn glow loses the highlight early. Left for a later polish pass.
  - The occasional stuck/spinning navigation is still left for the movement-polish pass.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - 18 feedback/selection contracts, including: tolerance and interaction range pinned to `ARCHITECTURE.md` (2.2 m in Player.tscn, `INTERACTION_RADIUS` and the docs); one indicator/pulse mechanism; `set_tap_selected` driven only by Player; immediate feedback, never at arrival; release on stop/start/interaction; exact → near → ground order; shape distance; deterministic ties; generic selection (no object kind or state).
  - A new rule pins the project's whole set of per-frame callbacks (13), so any new loop fails.
  - `sim_interaction.py`: the selection port (exact, off-centre, just outside, tolerance edge, between two, ties, unavailable, large vs small); 40,000 taps on the real Meadow layout (never a farther or unavailable object, order-independent); the feedback lifecycle (far, in range, arrival, cancel, retarget, ground tap, repeat, unavailable, 3,000 random runs).
  - Mutation-tested: 19 GDScript/scene mutations and 6 model mutations, all caught by the suite.
- **Commit:** §15.

**M02.5 — Remove the unused `interact_requested` path (A6)** `[~]` Implemented — covered by the combined playtest (no behaviour change)
- **Objective:** resolve A6 so there is exactly one way into interaction.
- **Audit:**
  - Declared: `signal interact_requested` in `input_manager.gd`.
  - Emitted: only by `InputManager.request_interact()` ("kept for non-touch input").
  - Callers of `request_interact()`: **none** — no script, scene connection, dynamic `call()`, or input action (the InputMap has only `move_*`; the Interact button was removed earlier, D-08).
  - Connected/listened: Player `_ready` → `_on_interact_requested()`, which interacted with the nearest in-range object via `_interact_with()` (so it never bypassed the guards, but it was a second entry that skipped the tap target and its M02.4 feedback).
  - Runtime path: unreachable. Removing it is safe; wiring it would need a new key/button (a new feature, against D-08) and would reintroduce a "nearest object" entry beside the tap target. (The old ARCHITECTURE note said nothing emitted it; in fact an emitter existed with no callers.)
- **Decision:** remove. No design decision needed (D-08 already covers it).
- **Files:** `scripts/autoload/input_manager.gd`, `scripts/player/player.gd`, `tools/check_project.py`, docs.
- **Implementation:** removed the signal, `request_interact()`, the Player connection and `_on_interact_requested()`. `_find_nearest_interactable()` stays (it drives the proximity reaction); its comment no longer mentions interaction. The tap path is untouched.
- **Verification (in code):**
  - `tools/run_all.sh` passes (all simulations included).
  - New checks: the removed names never return in scripts, scenes or `project.godot`; InputManager has exactly one interaction request signal (`interact_target_requested`), emitted by `_handle_tap` and connected in Player `_ready`; `_interact_with()` is entered only from `_on_interact_target_requested` and `_on_interaction_zone_area_entered`; one-shot protection (refuse spent; register one-shot objects before interacting) is now checked directly.
  - Mutation-tested: 18 GDScript mutations and 1 model mutation caught (restoring the dead path in full, just the signal, or a nearest-object entry under a new name; removing the target-request connection or emit; a second `interact()` call site; bypassing availability or one-shot protection, registration after interacting; interacting before facing; removing the INTERACT wrap; breaking the verb API; removing tap feedback; a new per-frame loop; a timer; a numeric mask).
- **Commit:** §15.

**M02.6 — Placeholder Inspect / Open / Read interactables (architecture proof)** `[~]` Implemented and verified in code — an architecture proof, **not** player-facing gameplay
- **Objective:** prove new interactable types work through the generic architecture with no Player change.
- **Audit:**
  - Player and InputManager reference no concrete type or verb (one code comment mentions FarmPlot) — they use only the `Interactable` contract: availability, `interact()`, highlight/proximity/tap selection, `remove_on_harvest`, and the target's position.
  - `Verb` held only COLLECT, PLANT, WATER, HARVEST. INSPECT, OPEN and READ are D-09 verbs that M02.2 deferred "until the behaviours that need them" — these fixtures are those behaviours. No other verb is needed.
  - Fixture infrastructure already existed: `tools/fixtures/` (ignored by Godot through `tools/.gdignore`; analysed by the toolkit) with the M02.1 probe.
- **Player/InputManager:** **no change needed and none made** — byte-for-byte identical (SHA-1 `45728f0…` / `4273df8…` before and after).
- **Files:** `scripts/interactables/interactable.gd` (enum only), new `tools/fixtures/inspect_fixture.gd`, `open_fixture.gd`, `read_fixture.gd`, `tools/check_project.py`, `tools/sims/sim_interaction.py`, docs.
- **Implementation:**
  - `Verb` gains `INSPECT = 5, OPEN = 6, READ = 7` (appended; existing values unchanged).
  - Three fixtures, each `extends Interactable`, no `class_name`, persistent, availability through `set_available()` → `monitorable`, deterministic record (counters, `last_action`), no UI/assets/signals/globals:
    - inspect: offers INSPECT; each interaction counts.
    - open: offers OPEN while closed, nothing once open (a state-following verb list).
    - read: **multi-verb** — offers INSPECT and READ at once; a tap (`interact()`) reads; `interact_with_verb(INSPECT)` inspects through the `_perform_interaction_verb()` override.
  - Not placed in any scene; no game code can reference them (checked).
- **Verification (in code):**
  - `tools/run_all.sh` passes; the GDScript analyzer compiles the fixtures against the real contract.
  - New checks: expected verbs per fixture; every `Verb` member is offered by some object or fixture (no speculative verbs); fixtures extend `Interactable`, have no `class_name`, switch availability only via `monitorable`, never override the guarded verb functions, never call `interact()` or reach into Player/InputManager; the multi-verb fixture dispatches the selected verb; Player/InputManager name no fixture or INSPECT/OPEN/READ and use no reflection (`has_method`, `get_script`, `call`, `get`/`get_meta` on objects); game code never loads a fixture; the per-frame baseline covers fixtures.
  - `sim_interaction.py`: the three fixtures, a discovery and a farm plot through one Player path (identical steps); repeated interaction; open → nothing more; unavailable and re-enabled; the multi-verb dispatch (read from the fixture's source).
  - Mutation-tested: 23 GDScript and 6 model mutations caught.
- **Runtime:** none — the fixtures are never loaded by Godot. The plan's "Godot: tap each fixture" would need a scene placing them; that is not done here (not needed for the proof, and out of scope).
- **Commit:** §15.

### PHASE 03 — CAMERA / WORLD SHELL
Goal: persistent Player/Camera/HUD with swappable areas.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M03.1 | Persistent shell: move Player, Camera and HUD out of `Meadow.tscn` into `Main` (A1) | Meadow loads as a child area; everything works as before | Full Meadow walk-through | `[~]` |
| M03.2 | Area loader with named entry markers | An area can be unloaded/reloaded | Reload round-trip | `[~]` |
| M03.3 | Area-safe world state: registration by stable id survives unload (farm plots first) | Farm state intact after area reload | Plant → reload → state kept | `[~]` |
| M03.4 | Camera bounds per area | Camera never shows beyond the area | Walk the edges | `[~]` |
| M03.5 | Clamped pinch zoom (+ mouse wheel) | Zoom comfortable, no conflict with taps/joystick | Android: pinch vs tap | `[~]` |
| M03.6 | Place data out of code (place definitions replace the hard-coded list) (A5) | No place names/ids in scripts | — | `[~]` |

**M03.1 — Persistent Main scene (shell)** `[~]` Implemented — runtime testing pending (M01.6 checklist)
- **Objective:** Main owns the persistent Player, Camera and HUD; the Meadow is world content only.
- **Audit:**
  - `scenes/Main.tscn` already existed and was already the startup scene (`run/main_scene`). It held `Meadow` and `HUD`. **HUD was already in Main**; **Player** and **FollowCamera** (plus `PlayerSpawn`) were children of `Meadow.tscn`.
  - The only structural dependency: `meadow.gd` used `$Player` and `$FollowCamera` to set the camera's target and position and to call `WorldSimulation.configure(player, light, environment)`.
  - No script uses `owner`, `%Unique` names, `current_scene`, root paths, `find_child` or `PlayerSpawn`. InputManager finds the player through `PLAYER_GROUP` and the camera through `get_viewport().get_camera_3d()` — both hierarchy-independent. Player's `get_parent().add_child()` (destination marker) works under Main (a Node3D). SaveManager/GameState/HUD hold no scene paths; HUD's `_ready` only connects autoload signals.
  - Navigation: NavigationRegion3D in the Meadow, navmesh baked at load from **static colliders** of the `navigation_source` group (the Meadow root). The Player (a CharacterBody3D) never contributed geometry; its NavigationAgent3D uses the same World3D map. No relocation needed.
  - One Camera3D in the project (FollowCamera). 12 autoloads, none scene-bound.
  - Tools: `sim_tap_movement.py` read the player spawn from Meadow's `Player` node.
- **Files:** `scenes/Main.tscn`, `scenes/world/Meadow.tscn`, `scripts/world/meadow.gd`, new `scripts/main.gd`, `tools/check_project.py`, `tools/sims/sim_tap_movement.py`, docs.
- **Implementation:**
  - `Main.tscn`: `Main` (script `main.gd`) → `Meadow` (at the origin), `Player` and `FollowCamera` (both at their old position (0, 0.2, 5) — identical world coordinates), `HUD`. Tree order keeps the old processing order (area, then Player, then camera).
  - `Meadow.tscn`: the Player and FollowCamera nodes and their two ext_resources removed; nothing else touched (`PlayerSpawn` kept as world content).
  - `main.gd`: once, in `_ready` (after all children): `follow_camera.target = player`, `follow_camera.global_position = player.global_position`, `area.attach_player(player)`.
  - `meadow.gd` (`class_name MeadowArea`): `_ready` bakes navigation; `attach_player(player)` configures the WorldSimulation. The configure call now runs at the end of the same ready pass (after Player, camera and HUD are ready) instead of in the Meadow's `_ready` — no frame passes in between, and nothing read it earlier.
  - **Player, InputManager, camera, HUD: byte-for-byte unchanged** (and now pinned).
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: startup scene is `Main.tscn`; in the fully expanded Main tree (822 nodes) exactly one Player, FollowCamera and HUD, each a direct child of Main; exactly one Camera3D (inside FollowCamera); no SubViewport; the Meadow instanced once at the origin; the expanded Meadow tree owns no Player/camera/HUD/joystick; `main.gd` wiring; `meadow.gd` gets the player only via `attach_player()`; navigation mesh settings, region placement, bake and the Player's agent pinned; the 12 autoloads pinned; **deliberate-change pins** (content hashes) for `player.gd`, `input_manager.gd`, `follow_camera.gd`, `FollowCamera.tscn`, `Player.tscn`, `HUD.tscn`. Existing `$`/NodePath checks cover `main.gd` and `meadow.gd`.
  - `sim_tap_movement.py` reads the spawn from `Main.tscn` (and checks the Meadow sits at the origin); geometry: spawn and 16 interactables clear of obstacles.
  - Mutation-tested: 29 GDScript/scene mutations and 3 model mutations caught.
- **Runtime:** no Godot executable in this environment, so no headless load — **the scene change is verified statically only**. PLAYTEST REQUIRED (M01.6 checklist, "M03.1 persistent shell").
- **Commit:** §15.

**M03.2 — Area loader with named entry markers** `[~]` Implemented — infrastructure only, runtime testing pending (M01.6 checklist)
- **Objective:** an area can be unloaded and reloaded into the persistent shell, entering at a named marker. Not player-accessible.
- **Audit (reported before changes):** no loading code existed (Main instanced the Meadow statically); one marker (`PlayerSpawn`, unscripted, unused); risks on unload: farm plot state lost (FarmManager captures only live plots; saved states are erased on registration) and the next autosave persists it — **M03.3**; `register_plot()` rejects a plot id held by a still-valid node, so the old area must be `free()`d, not `queue_free()`d, and the swap must be deferred; discovery respawns/one-time events/time of day live in the area and reset; landmarks/secrets are safe (ExplorationManager); Player references are guarded; the camera needs a snap.
- **Decisions (developer):** keep M03.2 narrow (no farm snapshot; M03.3 follows immediately, before any real transition); add a minimal public `Player.place_at(transform)`; trigger the runtime round-trip from the Godot remote debugger (no debug action or gameplay trigger).
- **Files:** `scripts/main.gd`, new `scripts/world/area_entry.gd`, `scenes/world/Meadow.tscn` (PlayerSpawn → AreaEntry `meadow_start`, moved to the boot position (0, 0.2, 5)), `scripts/player/player.gd` (`place_at()` only; pin updated deliberately), `tools/check_project.py`, new `tools/sims/sim_area_loader.py`, docs.
- **Implementation:**
  - `Main.load_area(scene, entry_id)` → deferred `_swap_area()`: cancel seed picker → `remove_child(old)` → `old.free()` → `add_child(new)` → `move_child(new, 0)` → `attach_player()` → `_find_entry()` (named, else lowest id, else stay) → `player.place_at()` → camera snap. Rejects a non-area scene.
  - `AreaEntry` (Marker3D, group `area_entry`, `entry_id`).
  - `Player.place_at(spot)`: `_stop_navigation()`, `velocity = 0`, position, facing from the spot's −Z (snapped).
  - Boot unchanged; no player-facing transition; no input action; FarmManager/FarmPlot/SaveManager/GameState untouched (now pinned).
- **Verification (in code):**
  - `tools/run_all.sh` passes (all 5 simulations).
  - New checks: AreaEntry script and group; entry ids lower_snake_case, non-empty, unique per area; the Meadow has an entry; `meadow_start` equals the boot position; `load_area()` only defers; `_swap_area()` order (no `queue_free`/`await`); `_find_entry()` scoped and deterministic; nothing calls the loader (scripts or scenes); input actions closed to `move_*`; `place_at()` minimal/generic (walk stopped, velocity zeroed, position, guarded facing; no area/Main/InputManager/interaction knowledge) and called only by Main; Main uses only `place_at()` and the player's transform; no script touches Player's private members; content pins for FarmManager, FarmPlot, SaveManager, GameState; Player pin updated deliberately.
  - `sim_area_loader.py`: swap order and rules read from source; one area after a swap; all 7 plots re-register (a `queue_free` or add-first order rejects them all — shown); deferred swap keeps the calling area alive through its callback; entries named/fallback/none, stray entries outside the area ignored; placement and camera snap; 2,000 random sequences.
  - Mutation-tested: 28 GDScript/scene/config mutations, all caught by `check_project.py` (15 also by the loader model); 4 of them re-run with the Player pin disabled to prove the `place_at()` content rules alone; 6 mutations of the model itself caught.
- **Runtime:** no Godot executable here — static and model only. PLAYTEST REQUIRED (M01.6 checklist, "M03.2 area loader", on a throwaway save).
- **Commit:** §15.

**M03.3 — Farm plots survive an area reload** `[~]` Implemented — runtime testing pending (M01.6 checklist)
- **Objective:** an area reload can never wipe farm state; farm plots only (discoveries, events and time of day are out of scope).
- **Audit:**
  - Save format: `farm.plots[plot_id]` = `FarmPlot.capture()` — `state`, `soil_memory`, and with a crop `crop`, `stage`, `needs_water`, `stage_time_left`, `thirsty_for`, `longest_thirst`, `soil`, `care`, `quality` (a paid mid-harvest captures as SOIL). `restore()` reads every field back. Unlocking is derived (starter/milestones), not saved.
  - Lifecycle before M03.3: boot — `SaveManager.load_game()` → `FarmManager.apply_save_data()` fills `_saved_plot_states`; each FarmPlot registers in `_ready` → restored → its entry **erased**; restored READY plots counted into `_ready_by_crop`/garden interest. Autosave (discovery, plant, harvest, found seed, farm milestone, movement mode, app paused/closed) → `get_save_data()` = remaining saved states + captures of **live** plots only. Unload (M03.2) captured nothing: the plots' state existed nowhere, and the next autosave would have written fresh plots.
  - Minimum change: capture by id just before unload; restore on the next registration without recounting ready crops; include captured-but-unloaded states in saves.
- **Files:** `scripts/autoload/farm_manager.gd` (pin updated deliberately), `scripts/main.gd` (one call), `tools/check_project.py`, `tools/sims/sim_area_loader.py`, docs; `docs/DESIGN_DECISIONS.md` (open question O-11). FarmPlot, SaveManager, GameState and the save format unchanged.
- **Implementation:**
  - `FarmManager.release_plots_in(area)`: every registered plot inside the area → `_unloaded_plot_states[plot_id] = plot.capture()` and forgotten; stale (freed) references purged.
  - `Main._swap_area()` calls it after closing the seed picker and **before** `remove_child(old)`.
  - `register_plot()`: after tracking the plot, an `_unloaded_plot_states` entry is restored once (erased) and returns — **not recounted** (the crops never stopped existing, so ready counts and garden interest already include them; they also stay counted while their area is away). Boot-save path unchanged.
  - `get_save_data()` merges unloaded states (live captures win); `apply_save_data()` clears them.
  - Time does not pass for an unloaded plot (growth timer and thirst resume where they were) — the same rule as time away from the app; whether it should is open question **O-11**.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: the swap captures plots before removing the old area; `release_plots_in()` captures every plot of the area and drops old references; `register_plot()` tracks, then restores the captured state once, without recounting, before the boot path; saves include unloaded states; boot clears them; only these four functions touch them; Main never restores farm state itself; every farm field is captured and read back; content pins show discovery respawns, environmental events and time of day untouched.
  - `sim_area_loader.py` (farm section): capture/restore ported with the field list read from `farm_plot.gd`; empty / one / many / partial farms; reload once to three times; away in an area without plots with a save meanwhile; autosave right after a reload identical to before; ready counts unchanged; no duplicates, no old references; 1,500 random runs (with and without a boot save). The no-snapshot and snapshot-after-unload orders are shown to lose the farm.
  - Mutation-tested: 19 GDScript mutations caught by `check_project.py` (12 also re-run with the farm pins disabled — the content rules alone catch them) plus 7 model mutations.
- **Runtime:** no Godot executable here — static and model only. PLAYTEST REQUIRED (M01.6 checklist, "M03.2/M03.3 area loader").
- **Commit:** §15.

**M03.4 — Camera bounds per area** `[~]` Implemented — runtime testing pending (M01.6 checklist)
- **Objective:** each loaded area gives the persistent camera its own bounds; replacing an area replaces (or clears) them.
- **Audit:**
  - `FollowCamera` (Main-owned since M03.1): smooth exponential follow of the target + velocity look-ahead (≤ 1 m), FOV widening; SpringArm3D −42°, 11 m, FOV 50. **No bounds, no limits, no area knowledge.**
  - Meadow bounds were not represented anywhere as camera data; the Meadow's only extent is its ground: `PlaneMesh_ground` 64 × 64 and `BoxShape3D_ground` 64 × 0.2 × 64 at the origin (±32 m). No edge walls.
  - Camera references: `main.gd` (target, snap at start and after a swap); InputManager (`get_viewport().get_camera_3d()`, read-only); none in Player, HUD, Meadow.
  - Plan: "Camera never shows beyond the area — walk the edges". Keeping the whole view inside the Meadow would hold the camera ~9 m inside every edge (11 m arm, −42°, FOV 50) — not "visually equivalent". So bounds limit the camera's **focus** (the point it follows); the full-view reading is recorded as **O-12**.
- **Files:** new `scripts/world/area_camera_bounds.gd`; `scenes/world/Meadow.tscn` (a `CameraBounds` node, size 64 × 64 at the origin); `scripts/camera/follow_camera.gd` (bounds, clamp, snap; pin updated deliberately); `scripts/main.gd`; `tools/check_project.py`, new `tools/sims/sim_camera_bounds.py`, `tools/sims/sim_area_loader.py` (order list); docs; `docs/DESIGN_DECISIONS.md` (O-12).
- **Implementation:**
  - `AreaCameraBounds` (Node3D, group `area_camera_bounds`, `size: Vector2`, zero = none, `get_rect()` in X/Z centred on the node).
  - `FollowCamera`: `set_bounds(rect)`, `clear_bounds()`, `snap_to_target()` (onto the target, inside the bounds, look-ahead restarted); `_physics_process` clamps `target + look_ahead` before the unchanged smoothing. No area reference, no lookups, no sizes.
  - `Main._apply_camera_bounds()` (scoped to the current area): `set_bounds()` or `clear_bounds()`; called in `_ready` and in `_swap_area()` after the new area is added, attached and the player placed, followed by `snap_to_target()` (replaces the M03.1/M03.2 direct `global_position` snap).
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: AreaCameraBounds script/group/no default size; exactly one bounds node, in the area (never in Main); the Meadow's equals its ground plane (origin, unrotated, same size); the camera has no Meadow/area/lookup/hard-coded size; `_physics_process` clamps with stored bounds and never looks them up; the clamp keeps X in [min, max] and Z in [min, max]; snap clamps; only `set_bounds`/`clear_bounds` write bounds; Main applies or clears for the current area only, in `_ready` and `_swap_area` (after installation); the camera's follow/look-ahead/smoothing/FOV lines unchanged. Existing: one Camera3D under Main, Meadow owns none, Player/InputManager/farm pins.
  - `sim_camera_bounds.py`: parameters and order read from source; inside the Meadow the bounded camera equals the pre-M03.4 camera exactly; each of the four edges (focus stops at the edge; difference ≤ the 1 m look-ahead); a player beyond the edge; swaps to smaller/other bounds, to no bounds and back; old bounds never leak; 2,000 random swap runs; same target throughout; no look-ahead jump after a snap.
  - Mutation-tested: 23 GDScript/scene mutations plus 2 more camera-behaviour mutations (look-ahead threshold, FOV), all caught by `check_project.py` (the camera ones also with the camera pin disabled); 6 model mutations caught.
- **Runtime:** no Godot executable here — static and model only. PLAYTEST REQUIRED (M01.6 checklist, "M03.4 camera bounds").
- **Commit:** §15.

**M03.5 — Clamped pinch zoom (+ mouse wheel)** `[~]` Implemented — runtime testing pending (M01.6 checklist)
- **Objective:** clamped camera zoom by two-finger pinch on mobile and the mouse wheel on desktop, one zoom path, no conflict with taps or the joystick.
- **Audit:**
  - Camera distance is the SpringArm3D's `spring_length = 11.0` (`FollowCamera.tscn`); FOV 50 is the speed-widening effect (±2). **No zoom, no range defined anywhere**; the plan gives none → provisional 7–15 m and a 1.1 wheel step, recorded as proposal **P-03**.
  - Touch: InputManager reads world touches in `_unhandled_input` and treats **every touch index as an independent tap candidate** — a pinch's still pivot finger (< 24 px, < 450 ms) would have tapped and walked the player. No `InputEventScreenDrag`, magnify or pan handling existed; Android sends no magnify gestures, so a pinch must be built from raw touches. The joystick consumes its own touches in the GUI (never unhandled).
  - Desktop: `emulate_touch_from_mouse=true` — clicks arrive as touch index 0; wheel events stay mouse buttons and were ignored.
  - No camera/zoom references in Main (besides wiring), Player, HUD or input actions; M03.4 bounds act on the focus, independent of distance.
- **Files:** `scripts/autoload/input_manager.gd` (touch tracking, pinch, wheel, multi-touch tap suppression — pin updated deliberately; tap routing unchanged and pinned by content), `scripts/camera/follow_camera.gd` (zoom API — pin updated deliberately), `scripts/main.gd` (one connection), `tools/check_project.py`, new `tools/sims/sim_camera_zoom.py`, docs; `docs/DESIGN_DECISIONS.md` (P-03).
- **Implementation:**
  - InputManager: `signal zoom_requested(factor)`; `_world_touches` (world fingers only); `_track_touch()` restarts the pinch on every finger change; `_track_pinch()` on drag emits `old / new` two-finger distance (exactly two fingers); with ≥ 2 world fingers all tap candidates are cleared (no finger of a pinch taps); the wheel emits `1/1.1` (up) or `1.1` (down) on press, before and separate from click/tap handling.
  - FollowCamera: `ZOOM_MIN_DISTANCE = 7.0`, `ZOOM_MAX_DISTANCE = 15.0`; `zoom_by(factor)` (rejects non-finite/≤ 0) → `set_zoom_distance()` = the only writer of `spring_length`, clamped; `get_zoom_distance()`. No input handling and no per-frame zoom in the camera; smoothing, look-ahead, FOV and bounds untouched.
  - Main: `InputManager.zoom_requested.connect(follow_camera.zoom_by)` once, in `_ready`.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: explicit limits around the scene's arm length; the clamp; `zoom_by` validation; one arm-length writer; no zoom per frame; the camera reads no input; only InputManager reads wheel/gesture events and emits `zoom_requested` (two sites), connected once by Main; FOV written only by the speed widening; pinch direction, two-finger rule, restart on finger change, tracked fingers only; two world fingers never tap; wheel on press, up = closer, never a tap; **InputManager's tap-routing functions pinned by content** (unchanged). Existing: one Camera3D under Main, M03.4 bounds rules, Player and farm pins, closed input-action list.
  - `sim_camera_zoom.py`: limits/between; repeated and limit-crossing pinch and wheel; hammering a limit; pinch → single finger; third finger; tap-to-move without zoom; joystick + world finger; wheel release; invalid factors; zoom after area reload; zoom at each M03.4 edge; 2,000 random input sequences (limits always held; taps only when the last finger lifts; a finger that was part of a pinch never taps; only two fingers zoom).
  - Mutation-tested: 29 GDScript/scene/config mutations caught by `check_project.py` (run with the InputManager and camera pins disabled, so the content rules alone catch them) and 7 model mutations.
- **Runtime:** no Godot executable here — static and model only. PLAYTEST REQUIRED (M01.6 checklist, "M03.5 pinch zoom + mouse wheel").
- **Commit:** §15.

**M03.6 — Place data out of code (A5)** `[~]` Implemented and verified in code — runtime regression pending (M01.6 checklist; behaviour should be identical)
- **Objective:** place-specific values move from scripts into the existing data layer; runtime behaviour identical.
- **Audit:**
  - Data layer: `DiscoveryDefinition` (`data/discoveries/`, DiscoveryDatabase) and `CropDefinition` (`data/crops/`, FarmManager), both `.tres` resources loaded through `ResourceDirectory` (export-safe). Reused as the pattern — no new architecture.
  - Hard-coded place data found: `ExplorationManager.PLACES` (8 ids, display names, one arrival text — the Journal's ordered list and arrival names); `ExplorationManager.CURIOSITY_PAIRS` (place → discovery); the secret-location count `>= 4` (equal to the 4 SECRET_LOCATION landmarks in `Meadow.tscn`); `FarmManager.GARDEN_PLACE_ID = "quiet_farm"` (garden found; read by HUD and Journal); the garden's name "Quiet Garden" inside FarmManager's "in bloom" milestone text.
  - Already data: the landmarks' `location_id`s (scene), crops' found-seed places (`data/crops`).
  - Not place data (left unchanged): UI copy naming the Meadow as an area; exploration thresholds/bonuses.
- **Files:** new `scripts/world_simulation/place_definition.gd`; new `data/places/*.tres` (8, written from the old constants); `scripts/autoload/exploration_manager.gd`; `scripts/autoload/farm_manager.gd` (garden id and name only — pin updated deliberately; M03.3 persistence untouched); `scripts/ui/hud.gd`, `scripts/ui/journal_screen.gd` (one call each); `tools/check_project.py`; new `tools/sims/sim_places.py`; docs.
- **Implementation:** `PlaceDefinition` (`id`, `display_name`, `arrival_text`, `order`, `secret`, `garden`, `curiosity_discovery_id`); ExplorationManager `_load_places()` at startup (ordered by `order`), all place lookups from it, the "every secret found" threshold = the number of secret places, `get_garden_place_id()`; FarmManager/HUD/Journal ask ExplorationManager for the garden id; the milestone text uses the garden's display name ("The Quiet Garden is in bloom." — unchanged).
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: PlaceDefinition's exact fields; every place file valid (script, lower_snake id = file name, display name), unique orders, exactly one garden, curiosity discoveries exist; places ↔ area landmarks one to one with secret flags matching landmark kinds; crops' found-seed places exist; ExplorationManager loads `data/places/` via ResourceDirectory, sorted, at startup; the secret threshold and curiosity come from data; FarmManager recognises the garden by the data flag; **no place id, display name or arrival text as a string in any script, and `PLACES`/`CURIOSITY_PAIRS`/`GARDEN_PLACE_ID`/a numeric secret threshold can't return.**
  - `sim_places.py`: the data-driven port reproduces the pre-M03.6 constants exactly — list and order, names, arrival texts, unknown-id fallback, garden, secret count — and 3,000 random sessions give identical events and points (landmarks, secrets, curiosity bonus, every-secret bonus, garden found).
  - Mutation-tested: 25 code/data/scene mutations caught by `check_project.py` (the three FarmManager ones also with the farm pin disabled) and 5 parity/model mutations caught by the simulation.
- **Runtime:** no Godot executable here — static and model only; the quick regression is in the M01.6 checklist ("M03.6 place data").
- **Commit:** §15.

### PHASE 04 — INVENTORY
Goal: one universal item model.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M04.0 | Top-level save version + migration hook (P-01 → D-17) | Old saves load; version recorded | Relaunch with an old save | `[~]` |
| M04.1 | Item definitions + item store (fields limited to what today's items need; saving moves to M04.2, when the store first holds items) | Items defined as data; store rules verified | Project opens; farm loop unchanged | `[~]` |
| M04.2 | Seeds and harvests become items; migrate from FarmManager (A3); the store's save section + migration 1 → 2 (D-17); O-13 → D-18 (quality is an attribute) | Farming loop unchanged; seed invariant holds; old farm saves migrate | Full farm loop | `[~]` |
| M04.3 | Inventory autoload (O-14 → D-19); discoveries grant collectible items | Collect → item | Tap a collectible | `[~]` |
| M04.4 | Inventory UI; seed picker and basket become filtered views | One inventory screen | Android: readability | `[ ]` |

**M04.0 — Save versioning (P-01)** `[~]` Implemented and verified in code — runtime testing pending (M01.6 checklist, "M04.0 save versioning")
- **Objective:** an explicit save schema version, deterministic validation, safe handling of newer saves and a migration path, before M04.2 changes save keys; M03.3 farm persistence unchanged.
- **Audit (before):**
  - One writer/reader, `SaveManager` → `user://save.json`: `points`, `discovered_ids`, `journal_entries`, `daily_discovery`, `farm`, `settings`. No top-level version; only `farm.version = 1`, written by FarmManager and never read.
  - Autosave (GameState): discovery, plant, harvest, found seed, farm milestone, movement-mode change, app paused/closed; load once at boot.
  - Missing sections defaulted, extra keys ignored; a corrupted file ignored and later overwritten. **Risks:** a section of the wrong type reached a system's typed `apply` (script error part-way through a load); a save from a newer build loaded partially and the next autosave dropped what the older build didn't know.
  - Not saved (unchanged): exploration progress (P-02), time of day, player position, camera zoom, respawns, events.
- **Files:** `scripts/autoload/save_manager.gd` (pin updated deliberately); `tools/check_project.py`; new `tools/sims/sim_save_versioning.py`; docs. Nothing else.
- **Implementation:** `SAVE_VERSION := 1` and `save_version` written first in every save; `read_version()` (absent → 0 = a pre-M04.0 save; not a whole number ≥ 0 → malformed, ignored like a corrupted file); a newer version is not loaded and sets `_saving_blocked` so the session never overwrites it; `_migrate()` walks one `match` step per version on a copy (step 0 = pre-M04.0: nothing to rewrite) and rejects a missing step; `SECTION_TYPES` + `_valid_sections()` pass only correctly typed sections to the systems (a wrong type falls back to that section's default). The six apply calls and `farm` (incl. M03.3 plot states) are unchanged. M04.2 adds the first real step (1 → 2).
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: integer `SAVE_VERSION` ≥ 1 and the `save_version` key; `save_game()` refuses while blocked and always writes the version; `load_game()` order (parse → dictionary → version → malformed → newer, blocking saves → migrate → validate → apply) with nothing applied from the unvalidated data and nothing applied for a newer save; `read_version()` rules; exactly one migration step per older version, step 0 changes nothing, unknown step rejected, stamped copy; the six pre-M04.0 sections keep their types and are written, type-checked and read back as one set; `_valid_sections()` passes only listed types; no other script does file/JSON/`user://` persistence or touches SaveManager internals.
  - `sim_save_versioning.py` (a port using Godot's float-only JSON numbers and typed system applies): current save round-trips identically (farm plots included); a pre-M04.0 save loads identically and is stamped on its next save; newer saves are neither loaded nor overwritten; malformed versions/files ignored; wrongly typed sections defaulted without affecting the others; migration dispatch in order, a missing step rejects; 3,000 random/garbage saves never reach a system with a wrong type, and loading is deterministic.
  - Mutation-tested: 42 GDScript mutations (missing/wrong version, newer save accepted/applied/overwritten, malformed version/file accepted, migration skipped/missing/unknown/unstamped/dropping `farm`, validation removed or bypassed, M03.3 `farm` section dropped or retyped, second file writers, reaching into SaveManager) all caught by `check_project.py` with the SaveManager pin removed; 7 model mutations caught by the simulation; one allowed control (another script calling `save_game()`) correctly passes.
- **Runtime:** no Godot executable here — static and model only. PLAYTEST REQUIRED (M01.6 checklist, "M04.0 save versioning").
- **Commit:** §15.

**M04.1 — Item definitions + item store** `[~]` Implemented and verified in code — runtime check pending (M01.6 checklist, "M04.1 items")
- **Objective:** the data/runtime foundation of the inventory: items as data, one small store with safe counts. No UI, no gameplay change, no save change.
- **Audit:**
  - Data layer: `CropDefinition`, `DiscoveryDefinition`, `PlaceDefinition` — `.tres` in `data/<kind>/`, loaded through `ResourceDirectory` (export-safe); reused as the pattern.
  - Item-like state today lives only in FarmManager: `_seeds` (crop id → count: starting seeds, −1 per planting — refused at 0, +1 per harvest, +1 per found seed once ever), `_produce` (the basket: crop id → [plain, good, fine]), saved as `farm.seeds` / `farm.basket`; `found_seeds` / `grown` are farm *progress*, not holdings. Read by HUD (seed left after planting, basket button), SeedPicker (counts), BasketScreen and Journal (seed and basket summaries) — all through FarmManager getters; no script writes these counts but FarmManager.
  - Discoveries are knowledge (ids, Journal), not items; PointsManager is a score, not an item. No inventory, no item ids in any script, no item dictionaries elsewhere.
  - Farm state vs player holdings: seeds in hand and the basket are the player's holdings (move to the store in M04.2); crops in the ground, plot states, found-seed origins, grown crops, milestones and counts stay farm state in FarmManager.
- **Design (fields justified by today's items only):** `ItemDefinition` = `id` (lower_snake = file name), `display_name`, `category` (`seed` / `produce` — the two kinds of item that exist), `crop_id` (M04.2 maps crops to their seed and produce items). Not added: glyph, colour and value (a crop's items read them from the `CropDefinition`), element id (no element system yet, Phase 11), coin value (Phase 05), stackable / max stack (no current design caps anything; the seed invariant already bounds seeds). 8 files: one seed and one produce item per crop (`<crop>_seed`, `<crop>`).
- **Item Store:** `ItemStore` (RefCounted, not an autoload — no `project.godot` change): `load_definitions()` (data/items via ResourceDirectory), `_init(definitions)`, `is_valid_item`, `get_definition`, `get_quantity`, `has(id, amount)`, `add(id, amount)`, `remove(id, amount)` (all or nothing), `get_quantities()` (a copy). Only `add`/`remove` change counts; both refuse unknown ids and amounts below 1; counts never go negative; an emptied item is removed.
- **Not changed:** FarmManager (still owns seeds and basket), SaveManager (no new section, `SAVE_VERSION` stays 1 — nothing holds items yet, so there is nothing to save; M04.2 adds the section, the bump and the 1 → 2 migration together), all UI, scenes, Player, InputManager, camera, Main, FarmPlot, DiscoveryManager, GameState, `project.godot`, export settings.
- **Files:** new `scripts/items/item_definition.gd`, `scripts/items/item_store.gd`, `data/items/*.tres` (8), `tools/sims/sim_items.py`; `tools/check_project.py`; docs.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: ItemDefinition's exact fields and categories; every item file valid (ItemDefinition, lower_snake id = file name, display name, known category, existing crop), exactly one seed and one produce item per crop; the store loads data/items through ResourceDirectory and skips unusable files; its API and state are exactly as above; only `add`/`remove` write counts and only `_init` writes definitions; the guard and write lines of `add`/`remove` (no cap, all or nothing, no negatives); reads and the copy; no other script reaches into a store, loads item data or spells an item id or name. Existing: FarmManager / SaveManager / GameState / FarmPlot pins, the autoload list, the save-section contracts.
  - `sim_items.py`: add, remove, insufficient (nothing taken), zero/negative amounts, unknown ids, no stack limit, copies, 1,000 repeated pairs, 20,000 random operations against a reference ledger; parity: FarmManager's seed rules replayed through the crops' seed items give the same counts and keep the seed invariant over 3,000 random farm sessions, and basket totals match the produce items.
  - Mutation-tested: 44 code/data/config mutations caught by `check_project.py` (two with the FarmManager/SaveManager pins removed, so the item rules alone catch them) and 6 model mutations caught by the simulation.
- **Runtime:** no Godot executable here — static and model only (M01.6 checklist, "M04.1 items").
- **Commit:** §15.


**M04.2 — Seeds and harvests become items** `[~]` Implemented and verified in code — runtime testing pending (M01.6 checklist, "M04.2 seeds and basket as items")
- **Objective:** one source of truth for what the player holds: seeds and harvested produce are items in the ItemStore; FarmManager keeps the farm rules and farm state; old saves migrate; the farming loop is unchanged.
- **Audit — produce quality (O-13):**
  - Decided once per crop when it ripens: `FarmPlot` reports soil (rotation, rated at planting) and care (longest thirst vs the crop's tolerance); `FarmManager.combine_quality()` → soil + care 4 = Fine, 2–3 = Good, 0–1 = Plain. Until then a plot reads Good.
  - Effects: harvest points (×0.75 / 1.0 / 1.5), the mature crop's size (0.9 / 1.0 / 1.1), the HUD harvest card ("Wild Carrot · Fine"), the `first_fine` milestone (which gates "garden in bloom"), the basket's per-quality counts (`_produce[crop] = [plain, good, fine]`, index clamped to 0–2), the Basket screen's split ("Good 3 · ✦ Fine 1"), the Journal ("×3 (1 Fine)") and its Fine hint (`get_produce_total(QUALITY_FINE) == 0`). Saved as `farm.basket`, loaded only for known crops with exactly 3 counts, negatives read as 0. Nothing consumes produce.
  - Readers of the basket all go through FarmManager (`get_produce_count/total`, `get_basket`); the only writer was `notify_crop_harvested`. Two stale comments say "this session" (the basket is saved) — left as they are.
  - **Finding:** quality is an attribute of a harvest, not an identity: one name per crop everywhere, one basket row per crop with a quality split, and quality only scales points/size. → Option A (one produce item per crop, a count per quality level) — D-18.
- **Audit — seeds:** starting seeds set for every crop at startup; planting refused at 0 and the seed taken only after the plot planted; one seed back per harvest; each found seed once ever (`found_seeds` saved); on load a crop missing from `farm.seeds` got its starting seeds; SeedPicker, HUD and Journal read `get_seed_count()` only. Invariant: seeds in hand + crops in the ground = starting seeds + seeds found.
- **Design:** `ItemDefinition.quality_levels` (1 = none; produce 3 = FarmManager's scale, checked); the store keeps one count per level (`add/remove(id, amount, quality)`, `get_quantity(id, quality = -1 → all)`), `get_save_data()` / `apply_save_data()` (malformed entries dropped with a warning). FarmManager's `_seeds` and `_produce` are gone; its getters (`get_seed_count`, `get_produce_count/total`, `get_basket`) forward to the store, so SeedPicker, HUD, Journal and Basket screen are unchanged. FarmManager holds the player's store (it is the only system holding items; a dedicated owner needs an autoload → `project.godot`, out of scope — O-14). Starting seeds are given once ever and recorded (`starter_seeds`), which keeps "a crop the save hasn't seen gets its starting seeds" exact.
- **Save (D-17):** `SAVE_VERSION` 2; new section `"items": {item_id: [count per quality level]}`; farm drops `seeds` / `basket`, gains `starter_seeds`. Step 1 → 2 (`_move_holdings_to_items`): `farm.seeds[crop] = n` → `items[<crop's seed item>] = [n]`; `farm.basket[crop] = [p, g, f]` → `items[<crop's produce item>] = [p, g, f]`; `farm.starter_seeds` = the crops `farm.seeds` listed; entries for crops without items dropped with a warning; no other section or farm field touched. Load: the items section is applied by FarmManager together with the farm (an empty farm = a fresh farm, as before).
- **Files:** `scripts/items/item_definition.gd`, `scripts/items/item_store.gd`, `data/items/*.tres` (produce: `quality_levels = 3`), `scripts/autoload/farm_manager.gd` and `scripts/autoload/save_manager.gd` (pins updated deliberately), `tools/check_project.py`, `tools/sims/sim_items.py`, `tools/sims/sim_save_versioning.py`, `tools/sims/sim_persistence.py`, docs. UI, FarmPlot, GameState, scenes, Player, InputManager, camera, Main, discovery code, `project.godot` untouched.
- **Known differences (malformed saves only):** a seed count that isn't a number (old: coerced by `int()`, or a script error) is now dropped with a warning; a hand-edited save whose farm is empty but whose items aren't loads a fresh farm (as an empty farm always did).
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: `quality_levels` per item (produce = the quality scale, seeds 1); the store's API, writers (`add`/`remove`/`apply_save_data`), per-quality guards, all-or-nothing removal, copies, and load validation that never drops silently; FarmManager has no seed/basket state besides the store and id maps, creates the store once and never hands it out, changes it only in the seed/basket rule functions (exact call map), reads counts from it, keeps the seed rules (refuse at 0, take after planting, one back per harvest, found once, starting once) and the harvest's clamped quality; quality rule functions pinned by body hash; farm save without seeds/basket, with `starter_seeds`; migration step 1 exists, moves every seed and basket row as-is, records `starter_seeds`, warns on drops, writes only `items`, erases only `seeds`/`basket`; the items section saved and loaded; only SaveManager reads/loads the player's items; no other script creates a store.
  - `sim_items.py`: store rules per quality + 20,000 random operations; old (pre-M04.2) vs new farm parity over 3,000 random sessions (seed counts, per-quality produce, basket rows, found seeds, invariant); save cases 1–12 (fresh, v1 with seeds / basket / both / empty seeds / empty basket / all qualities / many crops / malformed, repeated load–save, migration then autosave, unrelated sections and farm fields incl. plots unchanged), v0 and farm-less saves, a crop added later, malformed v2 items; 2,000 random v1 saves load to the same farm as the old code loaded them and stay stable. `sim_save_versioning.py` and `sim_persistence.py` updated to the v2 layout.
  - Mutation-tested with the FarmManager and SaveManager content pins **removed**: 62 code/data/config mutations (duplicate seed/basket state, the store handed out or recreated, counts not read from the store, every seed rule, quality dropped/unclamped/collapsed, quality rules and constants, farm save still holding seeds or missing `starter_seeds`, no or wrong 1 → 2 step, seeds/basket not moved or kept twice, silent drops, other sections or farm fields touched, items not saved/loaded/type-checked, store validation and copies, outside access) — all caught by `check_project.py`'s contracts; 13 model mutations caught by the simulations (one gap found and closed: the quality constants, and `sim_persistence` now checks the basket survives a relaunch).
- **Runtime:** no Godot executable here — static and model only. PLAYTEST REQUIRED (M01.6 checklist, "M04.2 seeds and basket as items").
- **Commit:** §15.


**M04.3 — Inventory autoload + discovery item rewards** `[~]` Implemented and verified in code — runtime testing pending (M01.6 checklist, "M04.3 inventory + collectibles")
- **Objective:** resolve O-14 (one owner for the player's items), then let collecting discoveries grant items — data-driven, smallest change, farming behaviour unchanged.
- **Audit:**
  - Collection: `DiscoveryInteractable` → `DiscoveryManager.discover(id)` (its only caller) → points, then `discovery_made` (first time ever) or `discovery_repeated`. All 9 discoveries are picked up (harvestable, respawning except the Ancient Seed). Listeners: Journal, Collection, Daily, Exploration, FarmManager (found seeds, both signals), HUD cards, GameState (autosave on `discovery_made` only).
  - Items: only crop seeds/produce, in FarmManager's store (M04.2). `ItemDefinition` had no link to a discovery. Nothing shows items yet (M04.4).
  - Autoload order: an Inventory must connect to DiscoveryManager (so after it), serve FarmManager's starting seeds in its `_ready` (so before it) and be filled before GameState's autosave for a first discovery (before GameState; signal handlers run in connection order).
  - Save: M04.2's `items` shape fits collectibles unchanged; but an M04.2 build loading a save with collectibles would drop them and overwrite — D-17 → bump.
- **Design:** new autoload `Inventory` (a Node holding the one `ItemStore`, forwarding its methods, never handing it out) between DailyDiscoveryManager and FarmManager — `project.godot` changed for this, deliberately (D-19). `ItemDefinition` gains `discovery_id` and the category `collectible`; 9 collectible items, one per discovery, named as the discovery (checked). Inventory connects `discovery_made` and `discovery_repeated` and adds one collectible per collection (none if the discovery has no collectible). FarmManager: no store of its own; its rules call `Inventory.add/remove/get_quantity` (same call sites); `apply_save_data(farm)` only — for an empty farm section, seeds in hand are reset to the starting seeds (`_start_fresh_seeds`), as a fresh farm always had. No UI change; no new autosave point (a repeat collection's item is saved by the next autosave or app pause, like its points).
- **Save:** `SAVE_VERSION` 3; step 2 → 3 rewrites nothing. `items` is written from and loaded into `Inventory`, before `FarmManager.apply_save_data(farm)`.
- **Known differences:** a hand-edited/corrupted save with an empty farm but items now keeps its produce and collectibles (seeds still reset to the starting seeds); M04.2 ignored its items entirely.
- **Files:** new `scripts/autoload/inventory.gd`, `data/items/<discovery>.tres` (9); `project.godot` (autoload line only); `scripts/items/item_definition.gd`; `scripts/autoload/farm_manager.gd`, `scripts/autoload/save_manager.gd` (pins updated deliberately); `tools/check_project.py`; `tools/sims/sim_items.py`, `tools/sims/sim_save_versioning.py`; docs. DiscoveryManager, DiscoveryInteractable, UI, FarmPlot, GameState, Player, InputManager, camera, Main, scenes, export settings untouched.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: the autoload list with Inventory between DiscoveryManager and FarmManager/GameState; Inventory is a plain Node with a fixed API, one store created in `_ready`, never handed out, every method a one-line forward, the store changed only by those forwards and the reward; the reward map from `collectible` items' `discovery_id`, both collection signals connected, exactly one item per collection; collectible items: existing discovery, no crop, the discovery's name, one level, at most one per discovery; seed/produce items name no discovery; no other script creates a store, changes the Inventory (only FarmManager's rules and the reward), or saves/loads items; FarmManager holds no store or copy, calls the Inventory only at the rule sites (exact map), fresh-farm seeds exactly the starting seeds; SaveManager step 2 → 3 rewrites nothing, items loaded before the farm.
  - `sim_items.py`: collectibles one per collection (first/repeat), none for a discovery without one, never touching seeds/basket, 1,000 random sessions interleaving collections and farming round-trip exactly; a v2 save loads identically through 2 → 3; empty-farm-with-items case; everything from M04.2 (store, old/new farm parity, save cases 1–12, 2,000 random v1 saves) still passes with the Inventory owner and v3. `sim_save_versioning.py` covers v3's steps.
  - Mutation-tested with the FarmManager and SaveManager pins **removed**: 40 code/data/config mutations (autoload missing or misordered, a second store or copy, the store handed out/recreated, forwards altered, outside writers/loaders, rewards on one signal only, two per collection, not data-driven, wrong category, map overwrite, extra side effects, collectible data invalid, FarmManager rewarding discoveries or mishandling a fresh farm, no bump, step 2 rewriting, wrong load order, items not saved/loaded) — all caught by `check_project.py`; 6 model mutations caught by `sim_items.py`.
- **Runtime:** no Godot executable here — static and model only. PLAYTEST REQUIRED (M01.6 checklist, "M04.3 inventory + collectibles").
- **Commit:** §15.

### PHASE 05 — ECONOMY
Goal: an internal coin economy with repeat-reward protection.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M05.1 | Wallet + append-only transaction ledger (saved) | Every coin change has a ledger entry | — | `[ ]` |
| M05.2 | Repeat-reward protection: persist exploration progress (P-02); one-time-ever rewards; caps/diminishing returns (A4) | Relaunch never re-awards; no unbounded faucet | Relaunch test | `[ ]` |
| M05.3 | Reward architecture: earn rules as data | Rewards configurable without code | — | `[ ]` |
| M05.4 | Economy configuration (incl. redemption reference as unused config) | No rate in gameplay code | — | `[ ]` |
| M05.5 | Points ↔ coins relationship per O-02 | Decision implemented | — | `[!]` blocked on O-02 |
| M05.6 | Economy simulation in `tools/sims/` | Earn/spend balances and abuse loops modelled | — | `[ ]` |

### PHASE 06 — FARMING INTEGRATION
Goal: connect the existing farming to inventory, economy, saving and progression, then freeze it.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M06.1 | Farming uses inventory items end to end | No seed/produce storage left in FarmManager | Farm loop on device | `[ ]` |
| M06.2 | Harvest/sell rewards through the economy | Coins via ledger | — | `[ ]` |
| M06.3 | Farm milestones through progression hooks | One reward path | — | `[ ]` |
| M06.4 | FarmManager reduced to farm rules/plots; farming frozen | Responsibilities documented in ARCHITECTURE.md | — | `[ ]` |

### PHASE 07 — VERTICAL SLICE WORLD
Goal: the small playable test area (placeholders).

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M07.1 | Slice layout plan (meadow, garden, pond, forest edge, path, house slot, NPC spot) | Developer-approved layout | — | `[ ]` |
| M07.2 | Reusable placeholder scenes for the developer to place in the editor | Placement needs no code | Godot: place and run | `[ ]` |
| M07.3 | Navigation, bounds and entry points for the slice, including the pond walkability decision (O-07) | Whole slice reachable; the pond behaves as decided | Walk everything | `[ ]` (O-07 open) |

### PHASE 08 — HOUSES / NPCS
| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M08.1 | Enterable house: Door (Enter/Exit) via the area loader | Enter/exit with state intact | Android: transition | `[ ]` |
| M08.2 | Interior area (placeholder) with its own navmesh and camera bounds | Interior playable | Walk the interior | `[ ]` |
| M08.3 | NPC framework: NPC definition + scene, idle/wander on navmesh, Talk | NPC placed in editor, no NPC-specific code | Tap NPC | `[ ]` |
| M08.4 | Minimal data dialogue (conditions, outcomes) | One conversation with an outcome | Read on device | `[ ]` |
| M08.5 | Relationships (saved value per NPC) | Survives relaunch | Relaunch | `[ ]` |
| M08.6 | Requests (world-driven: problem → explore → solution → response) | One request completable without quest markers | Complete it | `[ ]` |
| M08.7 | Services (e.g. a trade/gift) | One service works via economy/inventory | Use it | `[ ]` |

### PHASE 09 — LIVING WORLD
| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M09.1 | NPC routines on time-of-day phases | NPC follows a daily routine | Watch a day | `[ ]` |
| M09.2 | Save time of day | Survives relaunch | Relaunch | `[ ]` |
| M09.3 | Simple weather | Weather visible, event-driven | Watch | `[ ]` |
| M09.4 | Environmental reactions to NPCs/weather (reuse event layer) | One reaction | Observe | `[ ]` |

### PHASE 10 — EXPLORATION
| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M10.1 | Discoveries/secrets/hidden locations as data | New ones need no code | — | `[ ]` |
| M10.2 | Collectibles via inventory; exploration rewards via economy (capped) | No unbounded rewards | Explore | `[ ]` |
| M10.3 | Hidden location in the slice with a clue trail | Found by observation | Find it on device | `[ ]` |

### PHASE 11 — FIVE ELEMENTS (one at a time)
| Milestone | Objective | Done when | Status |
|---|---|---|---|
| M11.0 | Element definitions + element ids on places/items/discoveries | Data only | `[ ]` |
| M11.1 | Earth prototype mechanic (decision O-09) | Distinct mechanic playable | `[!]` O-09 |
| M11.2 | Water prototype | 〃 | `[!]` O-09 |
| M11.3 | Fire prototype | 〃 | `[!]` O-09 |
| M11.4 | Air prototype | 〃 | `[!]` O-09 |
| M11.5 | Space prototype | 〃 | `[!]` O-09 |

### PHASE 12 — FIVE RISHIS — `[!]` blocked on R-01…R-07
- Only after the Rishi design is formally locked. Milestones will be written from the decisions.

### PHASE 13 — PROGRESSION
| Milestone | Objective | Done when | Status |
|---|---|---|---|
| M13.1 | Unify farm milestones, exploration bonuses and future rewards into one progression record | One path; paid once ever | `[ ]` |
| M13.2 | Discovery → Understanding → World Change → New Access → New Discovery (per O-04) | One full chain in the slice | `[!]` O-04 |

### PHASE 14 — JOURNAL / COLLECTION
| Milestone | Objective | Done when | Status |
|---|---|---|---|
| M14.1 | Journal sections: discoveries, crops, wildlife, places, secrets, player memories | All sections fed by data | `[ ]` |
| M14.2 | Elements and Rishis sections | After Phases 11–12 | `[!]` |

### PHASE 15 — SAVE SYSTEM
| Milestone | Objective | Done when | Status |
|---|---|---|---|
| M15.1 | Full versioned persistence: inventory, crops, discoveries, coins, NPC relationships, world changes, elemental and Rishi progression | Everything important survives close/reopen/update | `[ ]` |
| M15.2 | Session vs persistent state documented and enforced | Doc + checks | `[ ]` |
| M15.3 | Old-save compatibility fixtures in `tools/` | Fixtures load | `[ ]` |

### PHASE 16 — VERTICAL SLICE GATE
The small area must feel like a coherent real game. All must pass **on Android**:

- [ ] enter the area
- [ ] comfortable movement (both modes)
- [ ] camera feels good
- [ ] tap an object; it responds correctly
- [ ] collect something
- [ ] receive coins and progression
- [ ] discovery appears in the journal
- [ ] farming: plant, grow, harvest
- [ ] approach and talk to an NPC
- [ ] enter the house; the interior loads
- [ ] a progression milestone
- [ ] one elemental prototype
- [ ] save/load
- [ ] returning feels meaningful

No large world expansion before this gate passes.

### LATER PHASES (only after Phase 16)
- Full world and complete elemental regions
- Villages and full NPC populations
- Final Art / World Building: houses, NPCs, animals, vegetation, props, temples, elemental environments, Rishi characters, VFX, animation
- Audio
- Polish and optimization
- Android production and QA
- Backend
- Real-money redemption infrastructure: server-authoritative wallet, anti-fraud, accounts, KYC/compliance, legal review

---

## 14. Parked ideas (not scheduled)
- Seasons
- Fishing/observation (Water)
- Cooking/crafting depth (Fire)
- Wildlife photography journal
- More crops (frozen at 4, D-14)
- Camera rotation

## 15. Commit log for milestones
| Milestone | Commit |
|---|---|
| M00.1–M00.5 | `9da18a6` |
| M01.1 | `e678d45` |
| M01.2 | `d316ecc` |
| M01.3 (was M01.2a) | `b663d76` |
| M01.4 | `443503f` |
| M01.5 | `9ec60f1` |
| M02.1 | `1a6b2cd` |
| M02.2 | `3a26ee4` |
| M02.3 | `0f0dded` |
| M02.4 | `0dfbdbe` |
| M02.5 | `f0003dd` |
| M02.6 | `c067fe3` |
| M03.1 | `d000146` |
| M03.2 | `6991da1` |
| M03.3 | `5cd8692` |
| M03.4 | `32c98b8` |
| M03.5 | `44e3bb5` |
| M03.6 | `b76e49c` |
| M04.0 | `c8bca2a` |
| M04.1 | `3532b14` |
| M04.2 | `b14b77a` |
| M04.3 | `a4939ed` |

## 16. Current position
- **Current phase:** 04 — Inventory. M04.0 (save versioning, P-01 → D-17) M04.1 (item definitions + item store), M04.2 (seeds and basket held as items; save v2) and M04.3 (Inventory autoload, collectibles from discoveries; save v3) implemented (`[~]`, runtime test pending). Phase 03: M03.1–M03.6 implemented (`[~]`; complete in code; the area loader is still infrastructure only — no player-facing transition until M08.1). Phase 02: M02.1–M02.6 implemented (`[~]`; M02.6 is an architecture proof). Phase 01: M01.1–M01.5 implemented (`[~]`; all await the M01.6 playtest). Phase 00's M00.5 still awaits the Godot 4.7.2 open check.
- **Next milestone:** **M01.6 — Android movement playtest** (PLAYTEST REQUIRED; include M02.1's, M02.3's, M02.4's, M03.1's, M03.2/M03.3's, M03.4's, M03.5's, M03.6's and M04.0–M04.3's runtime tests). Next in code: **M04.4 — inventory UI; seed picker and basket become filtered views**, only on the developer's explicit instruction.
- **First runtime gate:** M01.6 — Android movement playtest.
