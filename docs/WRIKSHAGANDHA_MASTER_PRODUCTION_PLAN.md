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
- **Decided (D-24, closes O-02):** Wriksha Points (the score) and coins (the Wallet's currency) are permanently independent — no conversion, no mirroring, either way.

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
| Economy / wallet | In code (M05.1–M05.6, M06.2) | Wriksha Points = the score; coins = the `Wallet` (ledger), earned only by selling produce (`Market`, D-25; no sinks yet); reward amounts as data; points and coins independent (D-24) |
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
| A4 | Repeat-award problems: exploration bonuses re-award each launch (progress unsaved); repeat discoveries pay full points without limit | **Relaunch re-awards resolved in code:** M05.2 (D-21), the Ancient Seed M05.3 (D-22); repeat-collection caps deliberately open (O-01) |
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
  - **M04.4 filtered views** (Android): the seed picker looks and behaves exactly as before — same cards in the same order, counts, "No seeds" disabled cards, soil notes; planting from it closes it cleanly with no error and the count drops next time; a found seed shows up; the Basket screen shows the same rows in the same order (Wild Carrot, Meadow Herb, Golden Sunflower, Elderbloom) with the same Plain/Good/Fine split, and updates after a harvest while open; collecting discoveries changes neither.
  - **M04.5 inventory screen** (Android + desktop): the 🎒 button (sixth in the column, all buttons reachable) opens "Inventory"; a fresh game shows only **Seeds** (starting seeds, crop order, with swatches); after harvests **Produce** rows match the Basket screen exactly (same totals and Plain/Good/Fine split); after collecting discoveries **Collectibles** list each with its count (collect one again → +1, visible without reopening if the screen is open); planting a seed lowers its row; nothing held in a category → no section; ✕ closes; the screen scrolls with many rows and is readable on the phone; relaunch shows the same inventory; the seed picker and Basket behave exactly as before.
  - **M05.1 wallet** (desktop, `user://save.json`): the game starts with no autoload/script errors; after the next autosave the save has `"save_version":4` and `"wallet":{"ledger":[]}` (nothing earns coins yet); every M04 check above still holds (inventory, farm, relaunch); an M04.5 build refuses the v4 save and leaves it untouched (optional). (Coin credits/debits become testable with M06.2, after O-01.)
  - **M05.2 repeat rewards** (Android): reach a landmark and a secret place (bonus cards and points as before), note the points; pause/close and relaunch; reach the same places again → no card, no points; the Journal's Places list still shows them visited; a new place still pays once; collecting the same discovery again still pays its points (and a collectible); the daily bonus still pays once per day; desktop: the save has `"save_version":5` and an `"exploration"` section listing the places; after updating from an M05.1 build, each place pays once more, then never.
  - **M05.3 rewards** (Android): every reward card shows the same amount as before (landmark +15, secret +15, every secret +50, curiosity +20, 3rd/5th new discovery +20/+40 and the summary at the 5th, daily +25 on the Daily screen and card, first harvest +10, all starter crops +40, garden complete +30, in bloom +50); collect the Ancient Seed (+100, found seed as before) → relaunch → it is no longer in the world and never pays again; an area reload doesn't bring it back; other discoveries still respawn and pay every time; on a day whose target would have been the Ancient Seed, the Daily screen shows another discovery.
  - **M05.4 economy config** (regression only — nothing reads it): the project opens in Godot with no errors for `scripts/economy/economy_config.gd` / `data/economy/economy_config.tres` (the file shows 1000 / 10 / INR in the Inspector); no coin or rupee amount appears anywhere in the game; harvest points unchanged (e.g. Wild Carrot Plain 9 / Good 12 / Fine 18); every M05.3 reward amount unchanged.
  - **M05.5 points/coins** (regression only): every reward shows the same "+N Wriksha Points" and the HUD total grows exactly as before; nothing mentions coins anywhere; after a relaunch the points total is kept and the save still has `"wallet":{"ledger":[]}`.
  - **M05.6 economy lifecycle** (optional, observes current behaviour — nothing changed): reach a landmark (+15), then kill the app while it is in the foreground with no pause notification (e.g. `adb shell am force-stop <package>` from a desktop; swiping it away from recents usually pauses — and saves — first), relaunch → the landmark pays again *and* its +15 was never kept (lost together, not duplicated); harvest a crop, force-kill, relaunch → the harvest's points are kept (autosaved).
  - **M06.2 selling** (Android + desktop, `user://save.json`): harvest a crop → the card shows "+N Wriksha Points · +1 seed" and **no coins**; open the 🧺 Basket → the header shows "Coins 0" (never ✿), each quality held has "Sell <Quality> · N each" (Wild Carrot 4 / 5 / 7, Meadow Herb 5 / 6 / 8, Golden Sunflower 6 / 8 / 11, Elderbloom 10 / 12 / 17); tap one → the sell panel shows item, quality, "(n held)", a − / + stepper that stops at 1 and at the number held, and "You receive N Coins"; Cancel changes nothing; Sell → a "+N Coins" card, the header balance rises by exactly N, the row's count drops (the row and the 🧺 button disappear when nothing is left), the ✿ points total does not change; 3 Fine Wild Carrots pay 21; relaunch (and after killing the app right after a sale) → the balance and the lower counts are both kept, and the save has `"save_version":5` and one ledger entry per sale like `{"amount":21,"reason":"sell:wild_carrot:2"}`; seeds and collectibles have no Sell button (🎒 Inventory stays read-only); an M05.x save loads with 0 coins and its produce sells normally; no ₹ anywhere. *Desktop verified (M06.2 record, "Runtime"); Android pending.*
  - **M06.3 UI** (Android + desktop; landscape since M07.4, D-30): the top bar sits at the top edge (✿ points pill, "Discoveries n/9", 📚 📖 ⭐ 🕹) — never a tall column; nothing overlaps a notch or the status bar; 🧺 (after a harvest) and 🎒 sit bottom-right and are easy to reach with the right thumb, clear of the joystick; every button is comfortably tappable (≥ 120 canvas px); notifications appear just under the top bar, each fully inside its card; a harvest card reads "✦ HARVESTED ✦" / "<Crop> · <Quality>" / the care note / "+N Wriksha Points" / "+1 Seed"; a sale card "<CROP>" / "<Quality> ×n" / "+N Coins"; Basket: "BASKET" and the amber "Coins N" chip, crop cards with Sell buttons that wrap, the sell panel reads top to bottom, the empty state shows 🧺 "Nothing harvested yet."; Inventory matches the Basket's look, collectibles have icons, no Sell anywhere; points and coins never appear in the same element; Collection, Journal, Daily and the SeedPicker look as before; repeat at a ~540×960 desktop window.
  - **M06.4 milestones** (regression only — behaviour should be identical): from a fresh save the first planting shows the "first seed" card with no points; the first harvest pays +10 and opens plot 06; growing all starter crops pays +40 and opens plot 07; every starter plot harvested pays +30; the garden in bloom pays +50 and its decorations grow in; a Fine harvest shows its card with no points; the Journal's milestone list ticks them off; after a relaunch none repeats.
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
| M04.4 | Seed picker and basket become filtered views of the Inventory (`Inventory.get_view`) | Screens keep no counts; display unchanged | Android: picker + basket as before | `[~]` |
| M04.5 | Inventory screen: one read-only screen listing all held items by category — Seeds, Produce (quality split), Collectibles; picker and basket unchanged | One inventory screen | Android: readability | `[~]` |

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


**M04.4 — Seed picker and basket as filtered views** `[~]` Implemented and verified in code — runtime testing pending (M01.6 checklist, "M04.4 filtered views")
- **Objective:** the seed picker and the Basket screen read the player's items as filtered views of the `Inventory` autoload — no item state of their own, nothing else changed.
- **Audit:**
  - SeedPicker: one card per *known* crop (`FarmManager.get_known_crops()`, farm progression — including crops with 0 seeds, shown disabled), count from `FarmManager.get_seed_count()`, soil note from FarmManager; refreshes on `FarmManager.seeds_changed`; plants through `FarmManager.choose_seed()`.
  - BasketScreen: rows from `FarmManager.get_basket()` (crop order = points then id: Wild Carrot, Meadow Herb, Golden Sunflower, Elderbloom — the reverse of the item files' order), quality split via `row.plain/good/fine`; refreshes on `FarmManager.produce_changed`.
  - Both already read the one store since M04.2 (FarmManager's getters forward to it) — no duplicated state existed; what was missing is a generic, category-filtered read of the Inventory. HUD (basket button, "seeds left") and Journal also use FarmManager's getters — out of this milestone's scope, unchanged.
  - Refresh timing: `seeds_changed` fires after a planting finished and the picker closed. Refreshing on every Inventory change instead would rebuild the picker (freeing the pressed card) inside that card's own `pressed` handler — kept on FarmManager's signals, which cover every seed/produce change (plant, harvest, found seed, load); a collectible never changes either screen.
  - Collectibles are still shown nowhere; the plan's "one inventory screen" is split out as M04.5.
- **Implementation:** `Inventory.get_view(category)` — one row per held item of that category, in data order, `{item, total, counts}` (a count per quality level), built fresh from the store on each call; Inventory keeps the item definitions list for it. SeedPicker: counts from `get_view("seed")` by crop (0 if none held). BasketScreen: `_basket_rows()` from `get_view("produce")` in `FarmManager.get_crops()` order; the split reads `row.counts`. FarmManager, HUD, Journal, scenes untouched.
- **Files:** `scripts/autoload/inventory.gd`, `scripts/ui/seed_picker.gd`, `scripts/ui/basket_screen.gd`, `tools/check_project.py`, `tools/sims/sim_items.py`, docs.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: `get_view()` exact and read-only (category filter, held only, every quality level, rows built fresh; the store changed only by the existing forwards/reward); the definitions list set once; SeedPicker and BasketScreen have no member state, read items only through `get_view()` (no FarmManager seed/basket getters, no `Inventory.get_quantity`), picker = known crops with seed-view counts, basket = produce view in crop order with the quality split; both keep their FarmManager refresh signals.
  - `sim_items.py`: picker cards/counts and basket rows/order/splits built from the view equal the old getters at every step of 2,000 random sessions with collectibles mixed in (41,748 comparisons), and after save/load.
  - Mutation-tested: 20 code mutations caught by `check_project.py`; 4 model mutations caught by the simulation.
- **Runtime:** no Godot executable here — static and model only (M01.6 checklist, "M04.4 filtered views").
- **Commit:** §15.


**M04.5 — Inventory screen** `[~]` Implemented and verified in code — runtime testing pending (M01.6 checklist, "M04.5 inventory screen")
- **Objective:** one screen showing everything the player holds, across categories, as a read-only view of the `Inventory` autoload — no second store, no counts in the UI; the seed picker, basket, farming rules and save untouched.
- **Audit:**
  - Categories in data: seed (4, one per crop), produce (4, three quality levels), collectible (9, one per discovery). `Inventory.get_view(category)` already gives held rows (data order, `{item, total, counts}`).
  - HUD screen pattern: a scene instanced in `HUD.tscn`, opened by a `ScreenButtons` button wired in `hud.gd` (`button.pressed.connect(screen.open)`); the parchment modal (dim, panel, header + ✕, scroll list), hidden by default, rebuilt in `open()`, ✕ hides. Seed picker and basket refresh on FarmManager's `seeds_changed` / `produce_changed` (after a planting finished — tap safety).
  - **Gap:** collectibles change (discovery reward, load) with no signal at all — a screen showing them could not refresh while open. The fix belongs in the one owner: `Inventory.items_changed`.
- **Architecture changes:**
  - `Inventory.items_changed` — emitted by the Inventory only, exactly after a real change: `add`/`remove` when they succeed, `apply_save_data`, a discovery reward that added. Only the Inventory screen listens; the picker and basket keep FarmManager's signals (unchanged).
  - `InventoryScreen` (`scenes/ui/InventoryScreen.tscn` = the Basket's modal with the title "Inventory"; `scripts/ui/inventory_screen.gd`): sections Seeds, Produce, Collectibles, in that order, each only if something is held; rows from `Inventory.get_view()` only — crop items in FarmManager's crop order with the crop's swatch, collectibles in data order; name `×total`; items with quality levels show the basket's split ("Good 3 · ✦ Fine 1"); "Nothing carried yet." when empty. No member state. Rebuilt on open and on `items_changed` while open.
  - HUD: an "🎒" Inventory button (always shown) between Basket and Movement opens it; `ScreenButtons` made taller for the sixth button (`HUD.tscn` pin updated deliberately).
- **Unchanged:** FarmManager, SaveManager (`SAVE_VERSION` 3, same `items`), ItemStore, item data, SeedPicker, BasketScreen, Journal, all other screens, Player, InputManager, camera, Main, `project.godot`.
- **Files:** `scripts/autoload/inventory.gd`, new `scripts/ui/inventory_screen.gd`, new `scenes/ui/InventoryScreen.tscn`, `scenes/ui/HUD.tscn`, `scripts/ui/hud.gd`, `tools/check_project.py`, `tools/sims/sim_items.py`, docs.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: `items_changed` declared by the Inventory and emitted exactly four times (add/remove after success, load, reward that added) and nowhere else; only the Inventory screen listens; the screen has no state, one section per item category (the section list = the categories in data), reads items only through `get_view()` (no FarmManager getters, no other Inventory reads), skips empty sections, crop order then data order, name/total rows, a quality split identical line-for-line to the basket's covering every level, refresh on open and on `items_changed` while open; the HUD button opens the one screen, which is instanced. Existing picker/basket contracts (FarmManager refresh signals, filtered views) still hold.
  - `sim_items.py`: the screen equals an independent render straight from the store at every step of 1,500 random sessions with collections (30,000+ renders) — all three categories, no zero rows, quality splits, collectible counts; its produce section = the basket, its seeds = the picker's counts; `items_changed` fires exactly when the items changed (farm operations, rewards, refused calls); save/reload shows the same screen; an empty inventory shows nothing.
  - Mutation-tested (FarmManager, SaveManager **and HUD.tscn** pins removed): 26 code/scene mutations caught by `check_project.py`; 7 model mutations caught by the simulation (two initially survived — the expected render shared the port's section list, and refused removes were never exercised — fixed by an independent expectation and direct emit checks).
- **Runtime:** no Godot executable here — static and model only (M01.6 checklist, "M04.5 inventory screen").
- **Commit:** §15.

### PHASE 05 — ECONOMY
Goal: an internal coin economy with repeat-reward protection.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M05.1 | Wallet + append-only transaction ledger (saved) — `Wallet` autoload, D-20 | Every coin change has a ledger entry | Relaunch: empty wallet, no errors | `[~]` |
| M05.2 | Repeat-reward protection: persist exploration progress (P-02 → D-21); one-time-ever rewards (caps/diminishing returns on repeatable rewards → M05.3, rates are O-01) | Relaunch never re-awards | Relaunch test | `[~]` |
| M05.3 | Reward architecture: earn rules as data (D-22); never-respawning discoveries once-ever; caps on repeatable rewards deferred (O-01) | Rewards configurable without code; the Ancient Seed pays once ever | Relaunch after the Ancient Seed | `[~]` |
| M05.4 | Economy configuration (incl. redemption reference as unused config) — `EconomyConfig`, D-23 | No economy rate in gameplay code (only the frozen farm-quality multiplier) | — (nothing reads it; regression only) | `[~]` |
| M05.5 | Points ↔ coins relationship per O-02 → D-24: permanently independent | Decision implemented (separation enforced) | — (regression only) | `[~]` |
| M05.6 | Economy simulation in `tools/sims/` (`sim_economy.py`) | Points earn rates and abuse loops modelled; coin foundation verified at zero (coin earn/spend awaits O-01 / M06.2). | — (model only) | `[~]` |


**M05.1 — Wallet + ledger** `[~]` Implemented and verified in code — runtime check pending (M01.6 checklist, "M05.1 wallet")
- **Objective:** the foundation of the coin economy — one owner of the coin balance and an append-only, saved ledger of every change — with no earning, spending, prices or UI yet.
- **Audit:**
  - **Score, not currency:** Wriksha Points (`PointsManager`, one int, saved as `points`, shown in the HUD as "✿ N"). Earned by: every discovery collection (`DiscoveryManager`, the discovery's `points_value`), harvests (`FarmPlot`, quality-scaled), farm milestone bonuses (`FarmManager._reach`), exploration bonuses (5 sites in `ExplorationManager`), the daily discovery bonus. Never spent; `add_points` accepts any amount, including negative (unused); `set_points` only from SaveManager. Points feed no progression gate — they are a score.
  - **Currency:** none. No coin, wallet, balance or ledger anywhere; items have no value field (M04.1 deferred it to Phase 05); the Inventory holds items only.
  - Plan/decisions: coins are internal (D-10; the 1000 coins = ₹10 reference is future config, M05.4); the points ↔ coins relationship is open (O-02 → M05.5, blocked); earn rules M05.3; selling M06.2; repeat-reward protection M05.2.
  - *(Historical note added in M05.6 — this record reflects the state at M05.1. Since then: O-02 was closed by D-24 in M05.5 (points and coins permanently independent); M05.3's earn rules are points only; coin earning/spending waits for O-01 and M06.2.)*
  - So M05.1 must not turn PointsManager into the wallet or convert points: a separate owner, credited by nothing yet.
- **Decision (D-20):** a `Wallet` autoload (after Inventory, before SaveManager/GameState); the append-only ledger is the truth — the balance is its sum, never negative; only the ledger is saved.
- **Implementation:** `scripts/autoload/wallet.gd` — `get_balance()`, `can_afford(amount)`, `get_ledger()` (a copy, oldest first), `credit(amount, reason)` / `debit(amount, reason)` (refuse an amount below 1 or an empty reason with a warning; debit refuses more than the balance; a refused call records nothing), one private `_record()` that appends `{amount (signed), reason}`, moves the balance by exactly that and emits `balance_changed(balance)`; `get_save_data()` = `{"ledger": [...]}`; `apply_save_data()` replays the saved ledger from zero and keeps its longest valid prefix (whole, non-zero amounts with a reason, never below 0), warning about the rest. No caller credits or debits (M05.3 / M06.2 will).
- **Persistence (D-17):** new section `"wallet"` → `SAVE_VERSION` 4; step 3 → 4 rewrites nothing (an M04 save has no wallet and loads an empty one); an M04.5 build refuses a v4 save rather than dropping the ledger. `SECTION_TYPES` + save/load updated; every other section untouched.
- **Files:** new `scripts/autoload/wallet.gd`, `tools/sims/sim_wallet.py`; `project.godot` (one autoload line); `scripts/autoload/save_manager.gd` (pin updated deliberately); `tools/check_project.py`; `tools/sims/sim_items.py`, `tools/sims/sim_save_versioning.py` (v4); docs. PointsManager, every reward source, Inventory, FarmManager, UI, scenes untouched.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: the Wallet's exact API, state and signal; only `_record()` and a load write the balance/ledger and the ledger is only appended to; credit/debit guards and exact ±amount; `_record` = one entry + exact balance move + signal; load replays from zero, keeps the valid prefix, never negative; saved-entry validation; reads return copies; the save is the ledger only; no script credits/debits coins, reaches into the Wallet or saves/loads it (except SaveManager), or emits `balance_changed`; PointsManager/FarmManager know nothing of coins; the wallet section saved/loaded, step 3 → 4 a no-op; autoload order.
  - `sim_wallet.py`: empty start; credits, debits, refusals (insufficient, zero, negative, empty reason) recording nothing; 2,000 repeated transactions; ledger order = call order; balance = ledger sum, never negative, at every step; `get_ledger()` a copy; relaunch identical and stable; 14 malformed ledgers keep exactly their valid prefix; a v3 save → empty wallet, other sections untouched; 5,000 random sequences (77,000+ operations) equal a reference, deterministic, one signal per recorded change. `sim_save_versioning.py` round-trips a wallet ledger in the current save; `sim_items.py` unchanged in behaviour under v4.
  - Mutation-tested (SaveManager pin removed): 34 code/config mutations caught by `check_project.py`; 7 model mutations caught by `sim_wallet.py`.
- **Runtime:** no Godot executable here — static and model only (M01.6 checklist, "M05.1 wallet").
- **Commit:** §15.


**M05.2 — Repeat-reward protection** `[~]` Implemented and verified in code — runtime testing pending (M01.6 checklist, "M05.2 repeat rewards")
- **Objective:** one-time exploration progress survives a relaunch, so its one-time rewards are never paid again; repeatable rewards stay repeatable.
- **Audit — what was saved (v4):** points; first-ever discoveries (`discovered_ids` — `discovery_made` fires once ever); Journal entries; the daily discovery (`completed_date` — once per calendar day); farm milestones (+ their bonuses), found seeds (`found_seeds`, once ever), `garden_found`; items (collectibles per collection); the wallet (no coins flow).
- **Audit — what was lost on relaunch (ExplorationManager, all session-only):** `_reached_landmarks`, `_found_secret_locations`, `_all_secrets_bonus_awarded`, `_curiosity_bonus_given` (and the Journal's "Places" list built from them); also `_session_discovery_count`, `_awarded_thresholds`, the first/rare beats and the summary flag.
- **The exact repeat-reward problem:** after every relaunch, walking to the same places paid again — landmark +15 each (4), secret place +15 each (4), "Every Secret Found" +50, curiosity +20 (while its paired discovery is still undiscovered) — without limit, and the arrival cards replayed. Not a relaunch exploit: the discovery-count thresholds (3 → +20, 5 → +40) count *first-ever* discoveries, which are saved, so they are bounded by the 9 discoveries; first/rare beats and the summary pay nothing; repeat collection pays points and a collectible every time *by design* (M04.3) — its caps are rates (O-01) → M05.3.
- **Persistence design (D-21):** `ExplorationManager.get_save_data()` = `{landmarks, secrets, all_secrets_bonus, curiosity_bonus}`; `apply_save_data()` restores them at boot, **paying and announcing nothing**, keeping only known places of the right kind (landmark = non-secret, secret = secret), once each (the rest dropped with a warning); a bonus flag is unpaid only if absent (pre-M05.2) or saved `false` — anything malformed counts as paid. The once-ever checks already in `mark_landmark_reached` / `mark_secret_location_found` / `_maybe_award_curiosity_bonus` now hold across launches (the curiosity bonus becomes once ever instead of once per session). Session-only as before: thresholds, beats, summary. FarmManager needs nothing: `found_seeds` and `garden_found` were already saved.
- **Consequences:** an arrival card shows once ever; the Journal's Places list keeps what was visited; the session summary's "places explored" counts all places ever visited.
- **Save-version impact (D-17):** new section `exploration` → `SAVE_VERSION` 5; step 4 → 5 rewrites nothing — a v4 save has no record of places, so each place can pay once more after the update, then never. Points and exploration are written in the same file by every autosave, so they can never disagree.
- **Files:** `scripts/autoload/exploration_manager.gd`, `scripts/autoload/save_manager.gd` (pin updated deliberately), `tools/check_project.py`, new `tools/sims/sim_repeat_rewards.py`, `tools/sims/sim_save_versioning.py` / `sim_wallet.py` (v5), docs. DiscoveryManager, DailyDiscoveryManager, FarmManager, Inventory, Wallet, PointsManager, JournalScreen, HUD, landmarks, scenes, `project.godot` untouched.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: exploration pays points only at its 5 known sites; each once-ever reward is checked, recorded, then paid; its state is written only where it is paid and on load; the save shape; the load restores places of the right kind and both flags and pays/announces/notifies nothing; place validation; the flag rule (absent → unpaid, malformed → paid); session state stays unsaved; discovery collection stays repeatable (points at function level, every time; repeat signal); the `exploration` section saved/loaded, step 4 → 5 a no-op; only SaveManager saves/loads exploration.
  - `sim_repeat_rewards.py`: the pre-M05.2 model shown to re-pay after a relaunch; now nothing re-pays; loading pays nothing and load → save → load is stable; 1,500 players × 12 relaunches (with extra load/save cycles): every landmark, secret, every-secret and curiosity reward paid at most once, progress survives; the first session identical to the old behaviour; repeat collection still pays points + a collectible every time across relaunches; a fresh game starts empty; a v4 save starts empty and pays each reward at most once more; 3,000 malformed exploration states never re-pay a restored place or a flagged bonus. `sim_save_versioning.py` round-trips an exploration section.
  - Mutation-tested (SaveManager pin removed; ExplorationManager/DiscoveryManager unpinned): 30 code mutations caught by `check_project.py` (one initially survived — discovery points moved under "first time" — contract tightened); 8 model mutations caught by the simulation (one survived because the "all secrets found ⇒ paid" load rule was provably redundant — the rule was removed from code, contract and model rather than kept untested).
- **Runtime:** no Godot executable here — static and model only (M01.6 checklist, "M05.2 repeat rewards").
- **Commit:** §15.


**M05.3 — Reward rules as data + once-ever discoveries** `[~]` Implemented and verified in code — runtime testing pending (M01.6 checklist, "M05.3 rewards")
- **Decisions (developer, after the read-only audit):** D1 (a) repeat collection stays unlimited — no caps/diminishing returns (O-01 open); D2 (b) never-respawning discoveries become once-ever claims; D3 the harvest quality scale stays FarmManager's; D4 rules carry Wriksha Points only (no coins, no Wallet, O-02 open); D5 the daily discovery stays offline (no clock checks). Recorded as D-22.
- **Audit (summary):** 9 reward types — discovery collection (data, repeatable; relaunch respawns everything, incl. the never-respawning Ancient Seed = 100 points per launch), discovery-count thresholds (hard-coded `{3: 20, 5: 40}`, bounded), landmark/secret/every-secret/curiosity (hard-coded 15/15/50/20, once ever since M05.2), daily (hard-coded 25, once a day), harvest (crop data × FarmManager's quality scale), farm milestones (hard-coded 10/40/30/50, once ever). Once-ever discoveries by data (`respawn_seconds <= 0`): exactly `ancient_seed`, one spawn point (`AncientSeedSpawn`, Meadow).
- **Implementation:** `RewardRule` (`id`, `points`, `threshold`) + 11 files in `data/rewards/` holding exactly the old amounts; `RewardRules` (RefCounted: `points(id)` — 0 with a warning if unknown — and `thresholds()`), built in ExplorationManager, DailyDiscoveryManager and FarmManager; their bonus constants removed; the session summary shows at the highest threshold (5, as before); every signal announces the amount it paid; `DailyDiscoveryScreen` reads `get_bonus_points()`. Once-ever: `DiscoveryManager.is_claimed(id)` (never respawns and already in the saved `discovered_ids`) — `discover()` refuses it before recording or paying; `DiscoverySpawnPoint` doesn't spawn it (launch, relaunch, area reload); the daily picker skips it (the next discovery in order; every other day unchanged).
- **Save:** no change — `SAVE_VERSION` stays 5. The claim is the existing saved `discovered_ids`; a save that already found the Ancient Seed is already claimed.
- **Files:** new `scripts/rewards/reward_rule.gd`, `scripts/rewards/reward_rules.gd`, `data/rewards/*.tres` (11), `tools/sims/sim_rewards.py`; `scripts/autoload/exploration_manager.gd`, `scripts/autoload/daily_discovery_manager.gd`, `scripts/autoload/farm_manager.gd` (pin updated deliberately), `scripts/autoload/discovery_manager.gd`, `scripts/interactables/discovery_spawn_point.gd` (pin updated deliberately), `scripts/ui/daily_discovery_screen.gd`; `tools/check_project.py`; `tools/sims/sim_places.py`, `sim_repeat_rewards.py`; docs. SaveManager, PointsManager, Wallet, Inventory, FarmPlot, scenes, `project.godot` untouched.
- **Verification (in code):**
  - `tools/run_all.sh` passes.
  - New checks: RewardRule's exact fields; each rule file valid (lower_snake id = file name, whole points/threshold ≥ 0), unique thresholds; RewardRules read-only with its fixed API; every paid rule id exists and every flat rule is paid; no reward constant, literal points amount or `BONUS_POINTS` read anywhere; points paid only at the 9 known sites; thresholds and summary from data; signals carry the paid amount; daily bonus from data via the getter; `is_claimed()` exact; `discover()` refuses a claim before recording/paying; the spawn point skips a claim; the daily picker skips it; DiscoveryManager's only state is `discovered_ids`. Existing M05.2 order contracts updated to the data-driven lines; the harvest quality rules still pinned.
  - `sim_rewards.py`: the reward data equals the pre-M05.3 amounts (snapshot), thresholds and summary unchanged, rules ⇔ pay sites; the Ancient Seed pays once and never spawns or pays again over 40,000 relaunches/reloads of 2,000 players; respawning discoveries stay repeatable; a pre-M05.3 save that found it is already claimed; the daily target is never a claimed discovery and only those days move (to the next discovery). `sim_repeat_rewards.py` / `sim_places.py` read the reward data (and model the claim).
  - Mutation-tested (FarmManager and DiscoverySpawnPoint pins removed; the managers and DiscoveryManager are unpinned): 32 code/data mutations — 30 caught by `check_project.py`, the 2 data-amount changes caught by the parity snapshot (by design: amounts are data now); one gap found and closed (a second claim store in DiscoveryManager); 5 model mutations caught by the simulation.
- **Runtime:** no Godot executable here — static and model only (M01.6 checklist, "M05.3 rewards").
- **Commit:** §15.


**M05.4 — Economy configuration** `[~]` Implemented and verified in code — runtime regression pending (M01.6 checklist, "M05.4 economy config")
- **Decisions (developer, after the read-only audit):** E1 keep FarmManager's `QUALITY_POINT_SCALE [0.75, 1.0, 1.5]` where it is — a frozen farm-quality rule, not an economy rate; E2 the redemption reference as configuration only (1000 coins = 10 INR), read by no gameplay code, not wired to the Wallet, no points ↔ coins, no UI, no payments; E3 crop `points_value` unchanged, its role as crop display order documented; E4 `RewardRule`s stay separate in `data/rewards/`. Recorded as D-23.
- **Audit (summary):** after M05.3 every economy amount is data (11 reward rules, discovery and crop `points_value`) except the harvest quality multipliers; the redemption reference existed only in documents; no coin rates, prices or item values exist; UI shows only amounts passed to it; nothing in the save is affected.
- **Implementation:** `scripts/economy/economy_config.gd` — `EconomyConfig` (Resource) with exactly `redemption_reference_coins: int = 1000`, `redemption_reference_amount: int = 10`, `redemption_reference_currency: String = "INR"` and no logic; `data/economy/economy_config.tres` with exactly those values. No autoload, no consumer.
- **Save:** none — `SAVE_VERSION` stays 5 (static `res://` data).
- **Files:** new `scripts/economy/economy_config.gd`, `data/economy/economy_config.tres`, `tools/sims/sim_economy_config.py`; `tools/check_project.py`; docs. No game script, scene, data other than the new file, or `project.godot` changed.
- **Verification (in code):**
  - `tools/run_all.sh` passes (all 15 simulations).
  - New checks: EconomyConfig's exact three fields, defaults and no logic; exactly one `data/economy/` file with exactly 1000 / 10 / "INR"; no script (outside the config), scene, other data file or `project.godot` references EconomyConfig, its path, the redemption fields, "redemption", ₹ or INR; reward rules never reference it; no economy-rate constant (POINT/COIN/REWARD/BONUS/PRICE/COST/RATE/REDEMPTION/EXCHANGE) in gameplay code except FarmManager's `QUALITY_POINT_SCALE [0.75, 1.0, 1.5]`, used only by `get_harvest_points()` and nowhere outside FarmManager; no literal scaling of `points_value`. Existing: the M04.2 quality-rule contract (body hashes + constants), the Wallet and points contracts.
  - `sim_economy_config.py`: the reference is 1000 = 10 INR and read by nothing; an economy snapshot — 11 reward rules, 9 discovery and 4 crop `points_value`s, the quality scale and the full crop × quality harvest-points table — unchanged; crop order = points order (the E3 coupling).
  - Mutation-tested (FarmManager and SaveManager pins removed; FarmPlot's too for the multiplier-outside-FarmManager case): 27 code/data/config mutations caught by `check_project.py` — wrong coins/amount/currency, missing/extra fields, logic in the config, a second config, gameplay/UI/scene/Wallet/points references, an economy autoload, a reward rule referencing it, new rate constants, literal point scaling; the quality scale changed or moved and the harvest minimum removed are caught by the existing M04.2 farming contract; 3 model mutations caught by the snapshot.
- **Runtime:** nothing reads the configuration, so there is nothing new to see — a regression check only (M01.6, "M05.4 economy config").
- **Commit:** §15.


**M05.5 — Points and coins separation** `[~]` Implemented and verified in code — runtime regression pending (M01.6 checklist, "M05.5 points/coins")
- **Decision (developer, O-02 closed → D-24):** Wriksha Points and coins are permanently independent. Points stay the score (PointsManager), earned, saved and displayed exactly as before, never converted to/from or mirrored into coins; coins stay the Wallet's, with no current sources or sinks (balance 0); EconomyConfig stays an unread redemption reference, never a rate.
- **Audit:** O-02 appeared in DESIGN_DECISIONS (open list; D-20), the plan (§10 "Open", the M05.5 row, the M05.1 entry, §16) and ARCHITECTURE §10, plus comments in `wallet.gd`, `reward_rule.gd`, `economy_config.gd`; stale "coins do not exist" wording in O-02's note and the plan's status table. Code: the Wallet is used only by SaveManager (save/load); PointsManager by the 9 pay sites, the HUD and SaveManager; no bridge existed. Gaps: nothing stopped a direct write to `PointsManager.points`, a script touching both systems, a `points_changed`/`balance_changed` bridge, conversion-named logic, a Wallet referencing points, or a coins key in a reward file.
- **Implementation:** no gameplay change and no save change (`SAVE_VERSION` stays 5). Comment-only updates in `wallet.gd` and `reward_rule.gd` (their O-02 references were stale). New checker contracts; a new model simulation; documentation.
- **Files:** `scripts/autoload/wallet.gd`, `scripts/rewards/reward_rule.gd` (comments only), `tools/check_project.py`, new `tools/sims/sim_points_coins.py`, docs.
- **Verification (in code):**
  - `tools/run_all.sh` passes (16 simulations).
  - New checks: PointsManager's code never references the Wallet, coins, balance/ledger/credit/debit or the economy config, and its API/behaviour is pinned by body hashes (add/set/get, one `points` variable, the `points_changed` signal); the Wallet's code never references PointsManager or points; nobody but PointsManager writes `PointsManager.points`; no script except SaveManager touches both systems, and SaveManager never mixes them on one line; nobody listens to `balance_changed`, only the HUD to `points_changed`; no conversion/mirror/exchange-named logic anywhere; reward files carry only id/points/threshold. Existing: no Wallet credit/debit callers, RewardRule's fixed fields, EconomyConfig unread and rate constants banned, the 9-site points pay map.
  - `sim_points_coins.py`: points are paid only at the 9 audited sites and the Wallet is touched only by SaveManager's save/load (static); 2,000 random multi-launch players earn exactly the audited amounts (independent snapshot) while the wallet stays at 0 with an empty ledger; save/reload keeps both independently; 5,000 cross-mutations — points never move the wallet, the wallet never moves points.
  - Mutation-tested (FarmManager, SaveManager and FarmPlot pins removed; PointsManager/Wallet unpinned): 25 mutations — mirroring/bridges in PointsManager, Wallet, pay sites, save/load and the HUD, conversion helpers, signal bridges, direct points writes, exchange-rate constants, new/removed pay sites, coin fields in reward data, EconomyConfig as a rate — all caught by `check_project.py`; 4 model mutations caught by the simulation.
- **Runtime:** nothing changes in play — a regression check only (M01.6, "M05.5 points/coins").
- **Commit:** §15.


**M05.6 — Economy simulation** `[~]` Implemented (model only) — no runtime change
- **Scope (developer-approved after a read-only audit):** model the *current* economy only — every Wriksha Points source, bounded vs unbounded, natural repeat rates, the relaunch-respawn and daily-clock loops, harvest throughput, the save/autosave lifecycle, reload/relaunch, and the coin foundation at zero. No coin rates, prices, caps, sinks, conversion, coin UI, save fields, gameplay or GameState change; O-01 open and now M06.2's dependency; D-23 and D-24 authoritative.
- **Implementation:** `tools/sims/sim_economy.py`. (1) A source register built from the code — the 9 pay sites, their guards, what each saves — and the data (reward rules, discovery respawns, crop timings, plots). Each source is classified: once-ever (landmark, secret, every-secret, curiosity, farm milestones, the Ancient Seed), per-session bounded (discovery-count thresholds), per-day (daily), repeatable (the 8 respawning discoveries), rate-limited repeatable (harvest). A **regression snapshot** (explicitly not configuration) of classes, amounts, discovery points/respawns, crop points/cycles/starting seeds, plots, places, the quality scale and the harvest table fails on any unexpected change, missing or new source. (2) Bounded lifetime totals are computed; unbounded sources are quantified and expected (never a threshold — that would be O-01). (3) GameState's actual autosave triggers are read from the code and drive a crash/relaunch model. (4) The coin side must stay at zero.
- **Measurements (current data):** bounded lifetime totals — landmarks 60, secrets 60, every secret 50, curiosity 20, farm milestones 130, discovery thresholds at most 80, Ancient Seed 100 (500 in all). Unbounded, expected: the relaunch loop pays **187 points + 8 collectibles per relaunch** (every respawning discovery is back at launch); natural respawn farming ≈ **4,450 points/hour** (walking ignored); the daily clock loop pays **25 per clock change**; harvest throughput at most ≈ **16,285 points/hour** (upper bound: 7 plots, growth timers, seed caps wild carrot 3 / meadow herb 3 / golden sunflower 2 / elderbloom 1, best quality, tapping/walking ignored).
- **Save lifecycle (current behaviour, known limitation — unchanged):** autosaved at once: first-ever discoveries (and the threshold, daily and collectible paid with them), harvests, farm milestones, found seeds, plantings, movement-mode changes; waits for the next save (a later autosave or app pause/close): repeat discovery collections, landmarks, secret places, every-secret/curiosity, a daily bonus completed by a repeat collection. A crash before that save loses the points **together with** their claims — never one without the other — so nothing is paid twice. 3,000 random players with crashes and relaunches: no duplicate payment, reload stable.
- **Coins:** zero earn sources, zero spend sources (no `Wallet.credit/debit` caller anywhere; the Wallet touched only by SaveManager's save/load and doing nothing on its own); balance 0 and an empty ledger through every modelled loop.
- **Documentation corrected (stale since M05.3–M05.5):** O-01's "Needed by" → M06.2; D-20's wording (M05.3's earn rules are points only; M06.2 after O-01); the checker's coin-caller message; the M01.6 wallet line (M06.2); a historical note on the M05.1 record; this row's done-when; ARCHITECTURE §10 economy flows; the autosave gaps recorded as a known limitation.
- **Files:** new `tools/sims/sim_economy.py`; `tools/check_project.py` (message only); `tools/README.md`; docs. No game script, scene, data, `project.godot` or save change; `SAVE_VERSION` stays 5.
- **Verification:** `tools/run_all.sh` passes (17 simulations). Mutation-tested against the simulation alone (no content pin involved): 36 mutations — a missing pay site, an added pay site (new script or existing function), changed reward amounts/thresholds/discovery points, a new reward rule, landmark/secret/every-secret/curiosity/milestone/daily/threshold guards removed or unsaved, the Ancient Seed repeatable (claim removed or respawning data), a respawn class or rate change, harvest timers unsaved, faster growth, an extra plot, more starting seeds, the quality scale, a coin source, a coin sink, the Wallet ledger touched on load or on its own, an autosave trigger removed/added, no pause save, GameState loading before the reward systems, and model faults (reload duplication, claims not restored, wrong autosave assumptions, a crash keeping points but dropping claims) — all caught.
- **Runtime:** none required (model only); the known-limitation behaviour can optionally be observed (M01.6, "M05.6 economy lifecycle").
- **Commit:** §15.

### PHASE 06 — FARMING INTEGRATION
Goal: connect the existing farming to inventory, economy, saving and progression, then freeze it.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M06.1 | Farming uses inventory items end to end | No seed/produce storage left in FarmManager | Farm loop on device | `[~]` (achieved by M04.2–M04.3; desktop farm loop verified; device pending) |
| M06.2 | Harvest/sell rewards through the economy (O-01 → D-25: coins only by selling produce) | Coins via ledger | Sell on device | `[~]` |
| M06.3 | UI surfaces and HUD for mobile (D-26): shared theme, top-anchored top bar, thumb-zone Basket/Inventory, Basket/Inventory/notification polish | Coherent portrait layout; touch targets ≥ 120 px; points and coins visually separate; no gameplay change | Portrait layout + touch on device | `[~]` |
| M06.4 | Farm milestones through progression hooks *(was M06.3, renumbered by M06.3)* | One reward path | Milestone cards/unlocks as before on device | `[~]` |
| M06.5 | FarmManager reduced to farm rules/plots; farming frozen *(was M06.4)* | Responsibilities documented in ARCHITECTURE.md | — | `[x]` (docs + checker only; no game code changed) |

**M06.1 — Farming uses inventory items end to end** `[~]` Achieved in code by M04.2–M04.3; desktop farm loop verified (M06.2 runtime); device farm loop pending (M01.6)
- **Close-out (documentation only, approved after the post-M06.5 audit):** no farming code was changed for this record.
- **How the goal was met:** M04.2 moved the player's seeds and basket out of FarmManager into an `ItemStore` (save v2, `_move_holdings_to_items` migration); M04.3 made the `Inventory` autoload the one owner of every held item (save v3). FarmManager keeps only the seed/basket *rules* and reads/changes counts through `Inventory.get_quantity/add/remove`.
- **Evidence (static, enforced today):** `check_project.py` — FarmManager holds no store or seed/produce copy (`HOLDING_VARS`; no `ItemStore` beyond `load_definitions`/`crop_item_ids`); the Inventory is changed only at the rule sites (exact map: two adds per harvest, one per found seed, starting seeds once, one remove per planting, the fresh-farm reset); seed/produce counts read from the Inventory; the farm save holds no seeds or basket (`starter_seeds` only); the 1 → 2 migration contract; the M06.5 "farming frozen" API and save-key contracts. `sim_items.py` — old vs new farm parity over 3,000 sessions (seeds, per-quality basket, found seeds, seed invariant), the M04.2 move and v1 → v3 saves; `sim_persistence.py` — the seed invariant across launches.
- **Evidence (runtime, desktop):** the M06.2 rendered desktop run on Godot 4.7.2 played the full farm loop with item-based seeds and produce — 13 real harvests over three rounds (plant from the Inventory's seeds, water, harvest, one seed back, produce at Plain/Good/Fine into the Basket), then a SIGKILL and relaunch with the items intact.
- **Pending:** the farm loop on an Android device (M01.6) — the reason this stays `[~]`.

**M06.3 — UI surfaces and HUD for mobile** `[~]` Implemented and verified statically — runtime layout/touch check pending (M01.6 checklist, "M06.3 UI")
- **Decisions (developer, after a read-only audit; recorded as D-26):** this UI pass is M06.3 (the progression-hooks and FarmManager-reduction milestones become M06.4 and M06.5); the harvest card keeps its care note; Collection, Journal, Daily and the SeedPicker stay untouched (a later UI pass); 📚 📖 ⭐ 🕹 in the top bar, 🧺 🎒 bottom-right; static checks only — no rendered runs, builds or device tests in this milestone.
- **Audit — the tall-column HUD bug (pre-existing, seen in the M06.2 runtime run):** `TopBar` was a child of a full-screen `MarginContainer` with `size_flags_horizontal = 0` but the default vertical *fill*, so the bar stretched from the top margin to the bottom margin as a narrow translucent column and its HBox centred "✿ N · Discoveries" mid-screen, at any window size.
- **Implementation (presentation only):**
  - `scenes/ui/wriksha_theme.tres` (new): the shared theme — parchment/bark/leaf palette, default text 34 px, and the variations `HudPill`, `CoinChip`, `ChipLabel`, `PrimaryButton`, `SecondaryButton`, `HudButton`, `RowCard`, `SheetPanel`, `IconBadge`, `Caption`, `Header`, `Figure`, `CoinFigure`, `HudText`, `HudCaption`.
  - HUD (`HUD.tscn`, `hud.gd`): `TopArea` (top-wide, grows down) → `TopColumn` → `TopBar` (✿ `PointsPill`, discovery count, `MenuButtons` 📚 📖 ⭐ 🕹 at 120 px) and `NotificationRoot` beneath; `ScreenButtons` anchored bottom-right with 🧺 (still hidden until produce) and 🎒 at 144 px; containers ignore the mouse; `_apply_safe_area()` adds the display's safe area to a 24 px margin (re-applied on resize). Only node paths changed in the script; every signal connection and the 🧺 show/hide logic are as before.
  - Notification card (`DiscoveryNotification.tscn`, `discovery_notification.gd`): phone scale (640 / 520 px wide, height follows the text), five lines (title, name, optional note, amount, optional detail; empty lines hidden); `show_message()` gained optional `detail_text` / `note_text`, existing callers unchanged. Harvest: "✦ HARVESTED ✦" / "Wild Carrot · Fine" / care note / "+18 Wriksha Points" / "+1 Seed"; sale: "WILD CARROT" / "Fine ×2" / "+14 Coins".
  - Basket (`BasketScreen.tscn`, `basket_screen.gd`): proportional sheet; "BASKET" + `CoinChip` "Coins N" + 120 px ✕; `RowCard` per crop (104 px icon, name ×total, quality split, wrapping 120 px "Sell <Quality> · N each"); sell panel SELL / name / quality · held / How many? / − N + / You receive / +N Coins / Cancel · Sell; empty state 🧺 + "Nothing harvested yet." + hint. The M06.2 transaction code (`_basket_rows`, `_quality_split`, `_held`, the clamp, Confirm's disable rule, `Market.sell()` only on Confirm, "Coins %d") is unchanged.
  - Inventory (`InventoryScreen.tscn`, `inventory_screen.gd`): the same sheet and cards; section captions; crop icons; collectibles get a glyph for their discovery's category (via `DiscoveryDatabase`); still read-only.
- **Checker contracts (`check_project.py`, "UI surfaces and HUD"):** the theme defines the eight named variations on their base types; the HUD's two clusters, the Basket, the Inventory and the card use the theme, and every variation used exists; every button on the HUD, Basket and Inventory is ≥ 120 px (scenes) and every Sell button is built at `TOUCH_TARGET` 120 and priced by `Market.get_unit_price()`; `TopArea` is top-wide and grows down, `TopColumn`/`TopBar` never stretch vertically; the exact button split (📚 📖 ⭐ 🕹 top, 🧺 hidden + 🎒 bottom-right); HUD containers ignore the mouse; ✿ in its `HudPill`, coins in the Basket's `CoinChip`; the harvest and sale card calls; the safe-area hook; the HUD never touches the Wallet or prices; the card's five lines and `show_message` signature; no label or text mixes ✿/Points with Coins; the Inventory has only its close button and no Market / Wallet / price / Sell; the Basket's empty state. `HUD.tscn` re-pinned deliberately. Every M06.2 contract unchanged.
- **Verification (static only, as instructed):** `check_project.py` ALL CHECKS PASSED; `check_gdscript.py` 0 errors, 0 unknown; `gdparse` 0 failures over every script; `sim_items`, `sim_economy`, `sim_points_coins`, `sim_selling` pass. No Godot run, render, export or device test.
- **Not verified yet (needs a runtime pass):** the rendered layout at 1080×1920 and ~540×960 (text fit, wrapping, card heights, emoji glyph rendering in the Mobile renderer), safe-area insets on a notched phone, thumb reach and touch accuracy, the card height self-sizing after wrapping, and that no HUD element overlaps the joystick or the world taps.
- **Follow-up (recorded, not scheduled):** bring Collection, Journal, Daily and the SeedPicker onto the shared theme.
- **Files:** new `scenes/ui/wriksha_theme.tres`; `scenes/ui/HUD.tscn`, `scripts/ui/hud.gd`, `scenes/ui/DiscoveryNotification.tscn`, `scripts/ui/discovery_notification.gd`, `scenes/ui/BasketScreen.tscn`, `scripts/ui/basket_screen.gd`, `scenes/ui/InventoryScreen.tscn`, `scripts/ui/inventory_screen.gd`; `tools/check_project.py`, `tools/README.md`; docs. Untouched: FarmManager, FarmPlot, Player, FollowCamera, InputManager, PointsManager, Wallet, Market, SellRules, item data, SaveManager (`SAVE_VERSION` 5), GameState, discovery/exploration/daily systems, EconomyConfig, the joystick, `parchment_theme.tres` and the other modals.
- **Commit:** §15.

**M06.4 — Farm milestones through progression hooks** `[~]` Implemented and verified statically — runtime regression pending (M01.6 checklist, "M06.4 milestones")
- **Audit (read-only, before changing):** farm milestones already had one recording point, `FarmManager._reach()` (one of the 9 point pay sites), the `milestone_reached(id, message, bonus)` signal (GameState autosave, HUD card, `MilestoneReveal`), `get_milestones()` / `is_milestone_reached()` (Journal, reveals), plots' `unlock_on_milestone`, and saved `farm.milestones` — but **the reward was chosen at each of the 7 call sites** (a literal 0 for first seed / first Fine / grown, `_rewards.points(CONST)` for the four paid ones), so a milestone's reward was not tied to its id, and nothing checked that the ids used by scene hooks existed. Phase 13 (M13.1, O-04 open) will unify farm milestones with exploration bonuses; M06.4 stays farm-side.
- **Implementation (D-27):** `_reach(milestone_id, message)` — no amount parameter; inside, after the once-ever guard and recording, `var bonus_points := _rewards.points(milestone_id) if _rewards.has(milestone_id) else 0`, then pay, open waiting plots, announce (order unchanged). The 7 call sites pass only the id and message. `RewardRules.has(rule_id)` added (read-only). Amounts unchanged; no save, UI, signal or scene change; `SAVE_VERSION` stays 5.
- **Checker contracts (`check_project.py`):** `_reach` exact body and order; one `milestone_reached.emit`; `_rewards` read only in `_reach` (and built in `_ready`); no `PointsManager` in FarmManager outside `_reach`; every `_reach` call passes exactly id + message and names a registered milestone; every registered milestone is reachable; callers only `choose_seed` / `notify_crop_ready` / `notify_crop_harvested`; every scene `unlock_on_milestone` / `milestone_id` and every farm reward rule names a registered id; RewardRules API now `has`/`points`/`thresholds` (exact `has` body); farm-milestone rules count as paid through the registry. `farm_manager.gd` re-pinned deliberately. Pay sites unchanged (9).
- **Simulations:** new `sim_milestones.py` (registry, reward table by id = the pre-M06.4 amounts as a regression snapshot, data-only rewarding, scene hooks, event-only callers, `_reach` order, 3,000 random players once-ever across relaunches, announcement after payment and unlocks); `sim_economy.py` and `sim_rewards.py` now derive farm-milestone rewards from the registry instead of call-site amounts (their amount snapshots unchanged).
- **Verification (static only):** `check_project.py` ALL CHECKS PASSED; `check_gdscript.py` 0 errors / 0 unknown; `gdparse` 0 failures; all simulations pass. No Godot run.
- **Runtime still pending:** a regression pass that milestone cards, bonus points (+10 / +40 / +30 / +50), plot 06/07 unlocks and the garden-in-bloom reveal behave exactly as before on device.
- **Files:** `scripts/autoload/farm_manager.gd`, `scripts/rewards/reward_rules.gd`; `tools/check_project.py`, new `tools/sims/sim_milestones.py`, `tools/sims/sim_economy.py`, `tools/sims/sim_rewards.py`, `tools/README.md`; docs.
- **Commit:** §15.

**M06.5 — FarmManager reduced to farm rules/plots; farming frozen** `[x]` Completed and checked — documentation and tooling only (no game code, scene, data or save change; no runtime component)
- **Audit (read-only, approved):** the reduction D-11 asked for already happened across Phase 04–06 — seeds and produce are Inventory items (M04.2–M04.3), reward amounts data (M05.3), coins the Market's (M06.2), milestone rewards data-driven through one path (M06.4). What remains in FarmManager is farm rules, plots, crops, seed choice, counters, garden interest, found seeds, milestones, Journal read models and the farm save — all of which stay. Moving display texts, Journal read models, garden interest or the crop registry is possible but would touch pinned rules or signals; parked. Hidden couplings recorded (FarmPlot pays harvest points before reporting; FarmManager ↔ ExplorationManager; Inventory-before-farm load order; crop order = `points_value`; unused `unlock_plot()` not persisted; a stale "this session" comment in `notify_place_reached`, deliberately left).
- **Implementation:** `docs/ARCHITECTURE.md` §8 rewritten as the authoritative frozen boundary (responsibility table, public API, FarmPlot's calls, the exact farm save section, milestones, known couplings, parked moves); D-11 noted "frozen in M06.5".
- **Checker contracts (`check_project.py`, "farming frozen"):** FarmManager's 9 signals with exact signatures; its 37 public functions, in order; outside FarmManager only that API and 7 shared constants (`QUALITY_PLAIN/GOOD/FINE`, `CARE_CAREFUL`, `SOIL_MEMORY`, `GARDEN_IN_BLOOM`, `WILDLIFE_ATTRACTION_KEY`) are used, never a `_private` member; FarmPlot's calls into FarmManager are exactly its 12; the farm save keys are exactly `version` (1), `starter_seeds`, `found_seeds`, `grown`, `milestones`, `counts`, `harvested_plots`, `garden_found`, `plots`; `farm_manager.gd` / `farm_plot.gd` stay content-pinned (unchanged, no re-pin).
- **Verification (static only):** `check_project.py` ALL CHECKS PASSED; `check_gdscript.py` 0 errors; `gdparse` 0 failures; farming simulations (`sim_farming`, `sim_persistence`, `sim_area_loader`, `sim_items`, `sim_save_versioning`, `sim_milestones`, `sim_economy`, `sim_interaction`) pass unchanged; `git diff --stat` touches only docs and `tools/`.
- **Status:** `[x]` under §6's rule for milestones with no runtime component. Farming's own runtime checks remain under M01.6 (M04.x, M06.2–M06.4 entries).
- **Files:** `docs/ARCHITECTURE.md`, `docs/DESIGN_DECISIONS.md`, this plan, `tools/check_project.py`, `tools/README.md`.
- **Commit:** §15.

**M06.2 — Selling produce (coins through the economy)** `[~]` Implemented and verified in code — runtime test pending (M01.6 checklist, "M06.2 selling")
- **Decisions (developer, after the M06.1 / O-01 read-only audit; O-01 closed → D-25):** harvest → produce into the Inventory → the player sells it → the Wallet receives coins; harvest itself pays no coins; no coins from discoveries, the daily discovery, landmarks, secrets, curiosity, thresholds, milestones, collectibles, seeds or points; only produce with a `sell_value` sells; prices are their own data (never `points_value`, `QUALITY_POINT_SCALE` or EconomyConfig); quality changes the price through a separate coin rule; one ledger entry per confirmed sale, reason `sell:<item_id>:<quality>`; a new `Market` autoload is the one `Wallet.credit()` caller and GameState saves on its `produce_sold`; earn-only (no sinks); no caps or cap state; no retroactive coins; `SAVE_VERSION` stays 5; the Basket is the selling surface (quantity stepper, confirm first), the Inventory stays read-only.
- **Locked values:** `sell_value` wild_carrot 5, meadow_herb 6, golden_sunflower 8, elderbloom 12; quality percents Plain 80 / Good 100 / Fine 140; `unit = (sell_value × percent + 50) div 100`, `total = unit × quantity` → carrot 4/5/7, herb 5/6/8, sunflower 6/8/11, elderbloom 10/12/17 (3 Fine carrots = 21). Derived from growth time and seed scarcity (≈ 10 coins per plot-minute at Good, a premium for the single-seed Elderbloom), not from points.
- **Implementation:**
  - `ItemDefinition.sell_value: int = 0` (0 = unsellable); set only on the four produce items.
  - `SellRules` (`scripts/economy/sell_rules.gd`, Resource, exactly `quality_percents: Array[int]`) and `data/market/sell_rules.tres` = [80, 100, 140].
  - `Market` autoload (`scripts/autoload/market.gd`, after Inventory and Wallet, before GameState): `get_unit_price(item_id, quality)`, `sell(item_id, quality, quantity) -> int` — validate item → produce → sell_value ≥ 1 → quality → quantity ≥ 1 → held → price ≥ 1 → `Inventory.remove` → `Wallet.credit(coins, "sell:<item_id>:<quality>")` → on a refused credit `Inventory.add` of exactly what was removed → `produce_sold(item_id, quality, quantity, coins)`. No points, no saving, no other system.
  - GameState: `Market.produce_sold` → save (items and wallet in the same save).
  - Basket screen: "Coins N" in its header (the only `balance_changed` listener); per held quality a "Sell <Quality> · N each" button; the sell panel (item, quality, held, − / + stepper within 1..held, "You receive N Coins", Cancel / Sell, a message if a sale can't be made); refreshes on `FarmManager.produce_changed` **and** `Inventory.items_changed`.
  - HUD: the 🧺 button's visibility also refreshes on `Inventory.items_changed`; a sale shows "+N Coins" on the shared compact card.
- **Checker contracts (`check_project.py`):** ItemDefinition's fields incl. `sell_value`; only produce has `sell_value ≥ 1` and every produce item has one; SellRules' exact shape and one data file (a percent per quality level, rising, Good = 100); the Market's API, state, signal and exact `_ready`/`_unit_coins`/`get_unit_price`/`sell` order (validation → price → remove → credit → rollback → announce) and reason format; the Market never references points, `points_value`, `QUALITY_POINT_SCALE`, EconomyConfig, saving or other systems; exactly one `Wallet.credit()` call, in `Market.sell()`; no `Wallet.debit()` caller; only the Market reads `sell_value` and the sell rules; only the basket's Confirm calls `Market.sell()`; only GameState and the HUD hear `produce_sold`; exactly one Market autoload in order; GameState's sale save; the HUD's "+N Coins" (never points); the basket shows "Coins N" from the Wallet's balance only, keeps only its pending sale, clamps the stepper to 1..held and disables Confirm when it can't sell; `items_changed` heard only by the Inventory screen, the basket and the HUD's basket button; GameState re-pinned deliberately. Every M05.5 separation contract kept (no bridge, no mirror, PointsManager unchanged).
- **Simulations:** new `sim_selling.py` (the Market's GDScript translated line by line and executed; prices vs exact rationals; refusals; forced credit refusal; harvest vs sale; saves; old saves; 5,000 random sequences); `sim_economy.py` (the coin source in the source register and crash/relaunch model, the locked prices in its regression snapshot, coin throughput); `sim_points_coins.py` (the Wallet's three users, coins only from sales, points untouched).
- **Measurements:** coin ceiling if every harvest is sold ≈ 3,504 / 4,392 / 6,092 coins/hour at Plain / Good / Fine (7 plots, seed caps; walking, watering and replanting ignored — rotation makes all-Fine unsustainable).
- **Files:** `scripts/autoload/market.gd` (new), `scripts/economy/sell_rules.gd` (new), `data/market/sell_rules.tres` (new), `scripts/items/item_definition.gd`, the four produce `data/items/*.tres`, `project.godot` (autoload), `scripts/autoload/game_state.gd`, `scripts/ui/basket_screen.gd`, `scenes/ui/BasketScreen.tscn`, `scripts/ui/hud.gd`; `tools/check_project.py`, `tools/sims/sim_selling.py` (new), `tools/sims/sim_economy.py`, `tools/sims/sim_points_coins.py`, `tools/README.md`; docs. Untouched: FarmManager, FarmPlot, PointsManager, Wallet, SaveManager, discovery/exploration/daily, EconomyConfig, Player, camera, InputManager, `HUD.tscn`.
- **Verification:** `tools/run_all.sh` passes (checker, GDScript analyzer, gdparse, 17 simulations). Mutation-tested with every file-hash pin disabled (the contracts, not pins, must catch): **49 mutations, 0 survivors** — the checker caught 47, the simulations 32; all 26 mutations of `market.gd` (credit before remove, no/incorrect rollback, announce before credit or never, reason format, round down/up, a total rounded instead of the unit, no quantity factor, each validation guard removed, points/`points_value`/`QUALITY_POINT_SCALE`/EconomyConfig, saving itself, a debit, a second credit, seeds priced) are caught by `sim_selling.py` alone; data (seed/collectible priced, produce unpriced, a changed price or percent), GameState's sale save, the HUD (coins as points, a points bridge), coins from harvest/discovery/the basket, an auto-sell at harvest, the stepper clamp, Confirm, selling without confirming, the `items_changed` refreshes, the balance shown as ✿, another balance listener and the autoload order are each caught.
- **Runtime:** M01.6 checklist, "M06.2 selling". **Desktop: verified** on the real Godot 4.7.2 build at commit `09f23c8` (Linux, OpenGL/Compatibility renderer on Mesa llvmpipe under Xvfb, a 540 × 960 portrait window; a fresh `user://save.json`). A test-only probe autoload, added only to a throwaway copy of the project and never committed, drove the real game: plots through `FarmPlot.interact()` / `FarmManager.choose_seed()` (what a tap and the seed picker call); discoveries through their interactables; places through `ExplorationLandmark.mark_reached()`; the HUD 🧺 button and every Basket control through synthesized mouse clicks on the rendered buttons. It never called Market or Wallet. **All 28 checks passed:**
  - A1–A5: fresh save → 0 coins; 9 discoveries (incl. today's target and the Ancient Seed), 8 landmarks/secrets and their bonuses paid points only.
  - B1–B3, E0: 13 real harvests over three rounds — Plain (tired soil + 125 s real-time thirst), Good and Fine (rotation) — paid points and produce, never coins; the 🧺 button appears after the first harvest; the Basket lists produce only, split by quality, with "Sell <Quality> · N each".
  - C1–C2, D1, E1–E5: sales through the UI at every price seen — Fine herb 8, Fine sunflower 11, 3 × Fine carrot 21, carrot 4/5/7, herb 6, sunflower 8, Elderbloom Good 12. Each sale: panel item/quality/held/total correct; stepper stops at 1 and at the number held; nothing saved before Confirm; items −qty; wallet +exactly the price; points unchanged; exactly one ledger entry `sell:<item_id>:<quality>`; one "+N Coins" card (it shows for 1.87 s, the compact card's designed time); "Coins N" updated at once; panel closed; the autosave on disk already holding both the items and the ledger; `save_version` 5.
  - G1–G3: Cancel, Close mid-sale and a stepper pushed past held commit nothing — save file, wallet and items byte-for-byte unchanged, reopening shows the list; seeds and collectibles have no Sell button, and the Inventory screen has none; a double-press on Confirm sells once.
  - I1, VIS1: "✿ N" (HUD) and "Coins N" (Basket) stay separate, with no ₹; selling the last produce hides the 🧺 button; wallet = ledger sum.
  - F0–F6: the process was killed with SIGKILL right after the sales (no pause/close save); on relaunch the wallet (83), the 9-entry ledger (replayed once), the reduced items and the points (865) were exactly as before, the HUD and Basket rebuilt from them, no sale was replayed, and the relaunch didn't rewrite the save file.

  **Not verified:**
  - **Android:** no SDK, export templates, emulator or device in the test environment. Real touch input, Android autosave timing and an Android force-stop are still to test, so M06.2 stays `[~]` until the Android pass.
  - **A refused Wallet credit** can't happen in play: every credit check is repeated earlier in `sell()`. The rollback path (validate → remove → credit → restore on refusal → `produce_sold` → autosave) is proven by `check_project.py`'s exact-order contract and `sim_selling.py`, which executes the Market's own code with a forced refusal. The Wallet wasn't changed to force it at runtime.

  **Seen, not caused by M06.2** (identical on the pre-M06.2 commit `6825ae1`, left as they are):
  - At 540 × 960 the HUD top bar (✿ points, Discoveries) renders as a tall translucent column down the left edge.
  - The engine logs 9 `det == 0` errors (`basis.cpp`) at boot.
  - At a test-only `Engine.time_scale` of 8, farming logs `!v.is_finite()` render errors — none at normal speed.
- **Commit:** §15.

### PHASE 07 — VERTICAL SLICE WORLD
Goal: the small playable test area (placeholders).

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M07.1 | Slice layout plan (meadow, garden, pond, forest edge, path, house slot, NPC spot) | Developer-approved layout | — | `[x]` approved by the developer as proposed (`docs/VERTICAL_SLICE_LAYOUT.md`) |
| M07.2 | Reusable placeholder scenes for the developer to place in the editor | Placement needs no code | Godot: place and run | `[~]` placed; editor open + desktop runtime verified (after M07.3's fixes); Android pending |
| M07.3 | Navigation, bounds and entry points for the slice, including the pond walkability decision (O-07) | Whole slice reachable; the pond behaves as decided | Walk everything | `[~]` implemented; walked on desktop (runtime verified); Android pending — O-07 → D-28 |
| M07.4 | Landscape orientation (D-30, locked): 1920×1080 canvas, sensor landscape, the joystick in the safe area | The game runs horizontally on a 16:9 phone with every UI size unchanged and all thumb controls clear of cut-outs | Android: hold either way, notch, gesture bar, thumbs | `[~]` implemented; desktop runtime verified (16:9, 20:9, 4:3, simulated cut-out); Android pending |
| M07.4a | Landscape pass: Collection, Journal and Daily on the shared theme (D-26/D-30) | The three screens read as the same landscape game UI as the HUD, Basket and cards — readable, 120 px targets, scrolling, safe area | Android: read at arm's length, thumb scrolling, notches | `[~]` implemented; desktop runtime verified (16:9, 20:9, 4:3, simulated cut-out); Android pending |
| M07.4b | SeedPicker landscape pass: the last old-style screen on the shared theme (D-26/D-30) | The seed choice reads as the same landscape game UI, docked between the thumb zones, the player in view; seed selection unchanged | Android: thumbs, gesture bar, readability | `[~]` implemented; desktop runtime verified (16:9, 20:9, 4:3, simulated cut-out/gesture bar; real taps plant through the farm); Android pending |

**Phase 07 — milestone details** (filled in before the phase starts, per §6)
- **Scope rule (developer, M07.1):** the slice stays inside the existing 64 × 64 m Meadow — no larger world, no second area (D-12; O-05 open until Phase 16). Placeholders only (§8: no final assets before Phase 16).
- **M07.1 — Slice layout plan.** Objective: an approved plan of where the slice's parts sit. Dependencies: none (planning). Files: `docs/VERTICAL_SLICE_LAYOUT.md` (with its machine-readable block), `tools/sims/sim_slice_layout.py`. Verification: the geometry simulation; the developer's approval. Runtime: none. Risks: none to the game (no scene change).
- **M07.2 — Reusable placeholder scenes.** Objective: placeholder scenes (house exterior with its door marker, NPC stand marker, forest-edge tree clusters, path patches) the developer places in the editor at the approved positions. Dependencies: M07.1 approved. Files: new `scenes/world/props/*.tscn`, `scenes/world/Meadow.tscn` (placement), the layout plan's digest updated with the scene. Verification: checker, `sim_slice_layout`, and the simulations that read the Meadow (`sim_tap_movement`, `sim_camera_bounds`, `sim_area_loader`, `sim_places`, `sim_milestones`). Runtime: Godot — place and run. Risks: Meadow contracts (navigation settings, places ↔ landmarks, plot hooks, camera bounds, spawn entry); the farm and milestone pins must stay untouched.
  - *Developer instruction (M07.2 start):* build and statically validate everything possible without Godot — the placeholders are placed directly in `Meadow.tscn` (hand-written in its existing style) at the approved positions rather than by the developer in the editor; only genuine editor/runtime checks stay pending.
- **M07.4 — Landscape orientation (D-30).** Inserted by the developer's locked product decision (mobile-first landscape, 16:9, Android phones; no portrait). Objective: the game runs horizontally with the existing UI language intact. Dependencies: none (it supersedes the portrait canvas of D-26 before Phase 08 builds on it). Files: `project.godot`, `scripts/ui/hud.gd` (the joystick in the safe area), docs, checker. Verification: checker, desktop runtime at several aspects. Runtime: Android (orientation, notch, gesture bar, thumb reach). Risks: none to gameplay (no camera, movement, tap or world value changes).
- **M07.3 — Navigation, bounds and entry points; the pond decision (O-07).** Objective: the whole slice reachable, the pond walkable or not as decided. Dependencies: M07.2; O-07 decided. Files: `Meadow.tscn` (navigation, collision), entry markers as needed. Verification: checker, `sim_tap_movement`, `sim_area_loader`. Runtime: walk everything on desktop and device. Risks: navigation bake on device (A8), tap routing.


**M07.1 — Vertical slice layout plan** `[x]` Approved by the developer as proposed (planning milestone; no runtime component; no scene change)
- **Decisions (developer, after the post-M06.5 audit):** the slice stays inside the existing 64 × 64 Meadow; the house is an exterior footprint + door only (interior M08.1); the NPC is a reserved exterior spot only; the forest edge is a zone; path extensions join the existing path to the house and the forest edge; every existing coordinate stays; a geometry simulation checks the plan.
- **Proposal (`docs/VERTICAL_SLICE_LAYOUT.md`):** house footprint 6 × 5 m centred at (-24, 0) (x -27…-21, z -2.5…2.5) on the open west side; door (-21, 0) facing the start; NPC spot (-19.5, 2.2) beside the door; forest edge west x -31…-28 (all z) and north z -31…-24 (x -31…4); trailhead (-24, -22.5); path "to_house" from `Patch1` (0.5, 3.2) to the door (~22 m) and "to_forest" from the door to the trailhead (~23 m). The inner meadow (≈ ±18 m) is fully used, so the new parts sit in the free outer ring; garden, pond, places and the existing path are unchanged.
- **Verification (static):** `sim_slice_layout.py` — 19 existing coordinates match `Meadow.tscn`; the Meadow geometry digest `89878544adee7640` is unchanged; everything inside the bounds; house, NPC, forest zones and paths clear of plots, places, the pond and every solid object by the documented margins; the connections hold. `check_project.py`, `sim_places`, `sim_camera_bounds`, `sim_tap_movement`, `sim_area_loader` pass unchanged.
- **Done when:** the developer approves the layout (then `[x]` — no runtime component). Nothing is placed before M07.2.
- **Approval (developer):** the layout is approved exactly as proposed — no changes to the house footprint, door, NPC spot, forest-edge zones, trailhead or paths. M07.1 → `[x]`; M07.2 (placement) may start.
- **Files:** new `docs/VERTICAL_SLICE_LAYOUT.md`, new `tools/sims/sim_slice_layout.py`, this plan, `docs/ARCHITECTURE.md` §12, `tools/README.md`.
- **Commit:** §15.

**M07.2 — Vertical slice placeholders placed** `[~]` Placed and verified statically; editor open and runtime checks pending (no Godot run, per the developer)
- **Decisions (developer):** M07.1 approved as proposed; place the house exterior (6 × 5 m at (-24, 0)), its door at (-21, 0) facing the path, the NPC spot (-19.5, 2.2), the west and north forest-edge placeholders and both path extensions; keep every existing geometry, landmark, plot, discovery position, navigation setting, camera bound and contract; exterior only (interior M08.1); O-07 (pond) stays M07.3; O-12 (interior camera bounds) stays M08.2; anything needing the editor or a device is marked pending, not a reason to stop.
- **Implementation:**
  - two new placeholder scenes: `scenes/world/props/HousePlaceholder.tscn` (a plain `StaticBody3D`: 6 × 5 × 3 m box collider, walls, gabled roof, door panel, a `DoorMarker` facing east) and `scenes/world/props/NpcSpotPlaceholder.tscn` (a `Marker3D` with a flat ground disc, no collider);
  - `scenes/world/Meadow.tscn`: two `ext_resource`s (ids 41, 42; `load_steps` 48 → 50) and one appended `VerticalSlice` subtree — `House`, `NpcSpot`, 36 forest-edge trees (existing `TreeTall`/`TreeRound`/`TreeWide`, ext ids 9–11; west 15 + 8, north 8 + 5, deterministic jitter/scale/rotation, the trailhead left open) and `Path/` with 13 + 14 patches of the existing path mesh and material along the approved polylines. The only removed line in the diff is the old `load_steps` header;
  - the door is a plain `Marker3D`, **not an `AreaEntry`** — the door's entry is M08.1's, and an extra entry now would change `Main._find_entry`'s lowest-id fallback;
  - no script added or changed; no pinned file touched; `SAVE_VERSION` 5; farming, inventory, wallet, market, milestones, UI, player, camera, input and the area loader untouched.
- **Contracts (`tools/check_project.py`, new section "vertical slice placement (M07.2)"):** one `VerticalSlice` Node3D at the origin; no script on any of its nodes or in the two prop scenes, and no script naming them ("placement needs no code"); it instances only the house, NPC-spot and tree placeholders; its path patches use the existing path mesh and material; the house is a `StaticBody3D` with one collision box and a plain `DoorMarker`; the NPC spot has no collider; the Meadow's only `AreaEntry` stays `meadow_start`.
- **Simulations:**
  - `tools/sims/sim_slice_layout.py` now also checks the placement: the existing-world digest (every node outside `VerticalSlice`) is still `89878544adee7640`, so no existing node moved or changed; a new `scene_digest` `076b3a88611ba905` records the whole scene; the house sits on the footprint, unrotated, with its collider and walls exactly 6 × 5 m; the `DoorMarker` sits on the door and faces out of the east wall; the NPC spot sits on the plan; each tree stands in a forest zone, inside the bounds, its canopy clear of every existing object (≥ 4.58 m), the house, the trailhead and both paths, with no gap > 5 m along either zone; the patches are centred on their paths and cover both end to end (sampled every 0.25 m). Mutation-tested: moving an existing node (named or not), rotating the house, turning the door inwards, giving the NPC spot a collider, moving a tree onto the trailhead or out of its zone, removing a patch and shrinking the house collider each fail the simulation; adding an `AreaEntry` or a script to the slice fails the checker;
  - `tools/sims/sim_tap_movement.py` (deliberate update): the house placeholder counts as an obstacle (its half-diagonal, conservative) and the NPC spot as a point that must be reachable; the 36 trees were already counted (75 obstacles, 18 points, no problems).
- **Verification (static, all passed):** `tools/run_all.sh` — checker, `check_gdscript`, `gdparse` (no script changed), every simulation.
- **Runtime pending (developer, on PC access):** open `Meadow.tscn` and both prop scenes in the Godot 4.7.2 editor without errors; the look of the house, the forest edge and the path joins; the navigation mesh bakes at load around the house and trees and tap-to-move reaches the door front, the NPC spot and the trailhead; the roof hiding the player behind the house (camera bounds unchanged); Android frame rate and load time with the added props. Listed in `docs/VERTICAL_SLICE_LAYOUT.md` → Implementation state.
- **Runtime (M07.3 audit, desktop Godot 4.7.2):** the editor opens every scene without errors or warnings; the first run found the camera collapse behind the house, the house top baked as a walkable island, and (pre-existing) the open world rim — fixed by M07.3; after the fixes the whole slice was walked on desktop (see M07.3). Android (frame rate, load time) still pending.
- **Done when:** the runtime checks above pass (then `[x]`).
- **Files:** new `scenes/world/props/HousePlaceholder.tscn`, new `scenes/world/props/NpcSpotPlaceholder.tscn`, `scenes/world/Meadow.tscn`, `tools/check_project.py`, `tools/sims/sim_slice_layout.py`, `tools/sims/sim_tap_movement.py`, `docs/VERTICAL_SLICE_LAYOUT.md`, this plan, `docs/ARCHITECTURE.md` §12, `tools/README.md`.
- **Commit:** §15.

**M07.3 — Slice navigation, bounds and the pond decision** `[~]` Implemented; desktop runtime verified (Godot 4.7.2); Android pending
- **Runtime audit first (no change):** the first real run of M07.2 (scratch copies of HEAD and of the pre-M07.2 commit `812a48b`, real screen touches and joystick input, rendered window) found three blockers — the camera's spring arm collapsing to 0.4–1.1 m behind the house (new; already at the Overlook monolith before); taps on/behind the house sending the player to the house top, baked as a walkable island at y 3.3 (new); the joystick walking off the world on every side (pre-existing) — and that the pond was fully walkable by accident. Each fix was prototyped in a scratch copy before the developer chose.
- **Decisions (developer):** apply the three isolated fixes; camera trade-off accepted (the roof may hide the player directly behind the house; no roof fade yet) → D-29; O-07 → option B, a controlled walkable pond edge with a ~2.8 m blocked core → D-28. Nothing else moves: no Meadow object, discovery, the pond or the path; `meadow_start` stays the only entry; the door is not wired to the area loader (M08.1); the pre-existing mound jitter and `Patch7` stay as recorded issues.
- **Implementation (4 scene files, no script):**
  - `scenes/camera/FollowCamera.tscn`: `collision_mask = 0` on the `SpringArm3D` (re-pinned deliberately);
  - `scenes/world/props/HousePlaceholder.tscn`: a `NavigationObstacle3D` (footprint outline, 4.5 m, `affect_navigation_mesh` + `carve_navigation_mesh`, no avoidance) — the house and its top leave the baked mesh;
  - `scenes/world/props/PondWater.tscn`: `Core` (`StaticBody3D`, cylinder radius 2.8 m) + a matching carving `NavigationObstacle3D` (16-gon, radius 2.8) inside the 3.6 m water;
  - `scenes/world/Meadow.tscn`: `WorldRim` (`StaticBody3D`, four 1.6 m box walls whose inner faces lie on the ±32 m camera-bounds edges); camera bounds and navigation settings unchanged; the existing-world digest `89878544adee7640` unchanged (it now excludes `VerticalSlice` and `WorldRim`); new `scene_digest` `6d460e2222d7ccc0`.
- **Contracts (`tools/check_project.py`, new section "slice navigation and bounds (M07.3)"):** the spring arm ignores geometry; the house and the pond each carry one carving obstacle; the pond has exactly one blocked `Core` (never a solid pond); one `WorldRim` with four walls, no script. `FollowCamera.tscn` re-pinned.
- **Simulations:** `sim_slice_layout.py` — rim walls on the bounds' edges, spanning each side, ≥ 1.2 m; the house carve = its footprint; the pond core = its carve, a walkable shallow edge left (0.45 m), every discovery in the water within the Player's `INTERACTION_RADIUS` − 0.3 m of the walkable edge (Wild Mint 1.28 m, River Stone 1.03 m). `sim_tap_movement.py` — the pond core is an obstacle; a discovery inside it must be in interaction reach of the edge. Mutation-tested (a solid 3.6 m core, the arm's collision back on, the house carve off, a rim wall moved or too low each fail).
- **Runtime (desktop Godot 4.7.2, rendered window, after the fixes):** start → garden → pond → Quiet Farm → Wildflower Clearing → house; door-front tap walks to (-20.4, 0); the door is a plain marker (not an `AreaEntry`, triggers nothing; entries `["meadow_start"]`); the joystick stops at all four house walls and walks round it; walking round by tapping works; 14 taps on the roof/walls do nothing (0 navigation polygons in the footprint; the mesh routes round the house); the camera stays at 11 m behind the house and the monolith (the roof then hides the player — accepted); the NPC spot reached by tap and crossed at full speed; both paths and the trailhead by tap and joystick; the joystick stops at ±31.68 on all four sides and the corner, never falls, walks back freely; the pond edge stops the joystick 3.12 m from the centre (south, west), the shallow edge is tappable, the core tap does nothing; Wild Mint and River Stone collected from the edge; tap replacement, joystick takeover and mode switches unchanged; the places route as before. The editor opens all changed scenes without errors or warnings.
- **Pre-existing (identical on the pre-M07.2 baseline; not fixed here):** tap-walks toward the NW mound ((-10.4, 1.2), (-13.5, 3.0)) and the NE mound (Overlook approach, (8.6, 9.0)) jitter at the first terrace edge until the next input; `Patch7` drawn into the pond; 9 `det == 0` engine errors at boot. (The audit's River Stone doubt was a probe artifact: collected in isolation before and after.)
- **Future polish:** roof fade / cutaway behind tall objects; a framed forest edge hiding the ground's rim (Phase 16 art); wading visuals at the pond edge.
- **Done when:** the whole slice is walked on Android too (then `[x]`, with M07.2).
- **Files:** `scenes/camera/FollowCamera.tscn`, `scenes/world/props/HousePlaceholder.tscn`, `scenes/world/props/PondWater.tscn`, `scenes/world/Meadow.tscn`, `tools/check_project.py`, `tools/sims/sim_slice_layout.py`, `tools/sims/sim_tap_movement.py`, `docs/VERTICAL_SLICE_LAYOUT.md`, `docs/DESIGN_DECISIONS.md` (D-28, D-29; O-07 closed), `docs/ARCHITECTURE.md` §12, `tools/README.md`, this plan.
- **Commit:** §15.

**M07.4 — Landscape orientation** `[~]` Implemented; desktop runtime verified; Android pending
- **Decision (developer, locked → D-30):** Wrikshagandha is a mobile-first landscape game — horizontal, composed for 16:9, Android phones first; desktop only for development/testing; no portrait design and no separate portrait gameplay. Chosen as the next milestone because every later camera, HUD, control and world decision (Phase 08 onward) must be made on the landscape canvas, and it is safe without a device.
- **Survey first:** HEAD run unchanged at 1920×1080 — the HUD (top-anchored bar, bottom-left joystick, bottom-right 🎒), the seed picker, the notification card and the Basket already work in landscape, because every D-26 size is in canvas pixels on the short side, which stays 1080. One gap: the joystick (bottom-left) did not follow the safe area, which in landscape holds side cut-outs and the gesture bar.
- **Implementation (no gameplay change):** `project.godot` — canvas 1920×1080 (was 1080×1920), `window/handheld/orientation` = 4, sensor landscape (either way up; was portrait); stretch `canvas_items` / `expand` unchanged. `scripts/ui/hud.gd` — `_apply_safe_area()` also moves the joystick's touch zone in by the left and bottom insets, keeping its size (no change where the window is all safe). Comments that named the 1080×1920 canvas updated (`basket_screen.gd`, `discovery_notification.gd`). Unchanged: camera values (FOV, arm, bounds), movement, tap tolerances, joystick size/feel (a thumb test on a device, M01.6), every scene and the world.
- **Contracts (`tools/check_project.py`, new section "landscape orientation (M07.4, D-30)"):** the canvas is 1920×1080, sensor landscape, `canvas_items` / `expand`; `_apply_safe_area()` keeps the joystick (its size unchanged) clear of the left and bottom insets. Mutation-tested (portrait orientation, the joystick line removed).
- **Desktop runtime (Godot 4.7.2, rendered window):** screenshots at 16:9 (960×540), 20:9 (1200×540) and 4:3 (800×600) — the HUD, Collection, Journal, Daily, Basket, Inventory, seed picker and a notification card all fit (the wider screen simply shows more world); with a simulated cut-out (48 px left, 24 px right) and gesture bar (30 px) the top bar, the 🎒 button and the joystick all move clear by exactly the insets; the real on-screen joystick, dragged by touch, walks right/up/diagonally and releases to zero, with and without the simulated insets. The M07.3 walk repeated in landscape: routes, door, house walls, walking round the house by tapping, roof taps doing nothing, the camera at 11 m, NPC spot, both paths, trailhead, the rim on every side, the pond edge and core, Wild Mint, tap replacement and mode switching — as in portrait.
- **Found while testing (pre-existing, not M07.4's):** a tap-walk from around (-6, 1.4) toward the west stalls — the navigation mesh there sits ~0.45 m above the flat ground (the same height mismatch as the NW-mound jitter); identical on the pre-M07.2 baseline and in portrait when issued directly; landscape only made that tap possible on screen. Recorded with the mound issue.
- **Pending (Android):** the app opens and stays in landscape both ways up; nothing under a notch, a punch-hole or the gesture bar; joystick and 🎒 comfortable for the thumbs; the 120 px targets feel right; Collection/Journal/Daily stay readable (still the older layout — a later UI pass, as before).
- **Files:** `project.godot`, `scripts/ui/hud.gd`, `scripts/ui/basket_screen.gd` (comment), `scripts/ui/discovery_notification.gd` (comment), `tools/check_project.py`, `docs/DESIGN_DECISIONS.md` (D-30), `docs/ARCHITECTURE.md` (§1 target, UI design space), `tools/README.md`, this plan.
- **Commit:** §15.

**M07.4a — Landscape pass: Collection, Journal and Daily** `[~]` Implemented; desktop runtime verified; Android pending
- **Why (developer, after M07.4):** the three oldest screens still used the pre-M06.3 parchment box — a fixed 520×680 px panel (Daily 440×220) with theme-default text (~20–26 px, the smallest in the game), a small unstyled ✕ under the 120 px target, long single columns, no safe area — so on a landscape phone they filled a third of the screen and did not read as the same game as the HUD, Basket and cards. Numbered M07.4a (a follow-on to M07.4, as M01.2a); no M07.5 was started.
- **Implementation (presentation only):**
  - `CollectionScreen` — the shared theme's sheet (the Basket/Inventory anchors); header "COLLECTION · n of N found" + the 120 px ✕; a grid of category cards (as many 520 px columns as fit: 3 at 16:9, 4 at 20:9), each with the category, "n of N found" / "✦ Complete" / "Nothing to find here yet.", a thin leaf progress bar and its entries ("???" until found); the grid scrolls.
  - `JournalScreen` — the same sheet; header "JOURNAL · n discoveries · m of 8 places"; two columns scrolling on their own: Places (✓ in leaf green / "???") and the garden's record card (notes as captions, milestones as whole marks that wrap) on the left, a card per discovery (name, rarity, description, "+N Wriksha Points") on the right; the empty-state line kept.
  - `DailyDiscoveryScreen` — a centred card: big ⭐ / ✓, status, the teaser ("Find something common." — the old "Find a common." read wrong) or the find, the reward from `get_bonus_points()` shown before it is earned ("+25 Wriksha Points when you find it"; after: "· a new one tomorrow"), a 360×120 "Keep exploring" button that closes it as the ✕ does.
  - `scripts/ui/hud.gd` — `_apply_safe_area()` also keeps every modal sheet (these three, the Basket, the Inventory) clear of the safe area: a sheet moves in only as far as a cut-out reaches past its designed margin (no change on a phone without one).
  - Unchanged: every data source (CollectionManager, DiscoveryManager, JournalManager, ExplorationManager, FarmManager's frozen public reads, DailyDiscoveryManager), saves, rewards, farming, inventory, wallet, movement, camera, the world, M07.4's settings, the HUD scene (pinned).
- **Contracts (`tools/check_project.py`):** the three scenes joined the M06.3 UI checks (shared theme, theme variations, every button ≥ 120 px); new section "landscape UI pass (M07.4a)": display-only screens (no reward, discovery, item, coin, seed or save call), "???" for anything undiscovered/unvisited, the Daily find named only once found and its reward from `get_bonus_points()`, "Keep exploring" closes, cards pass drags to the scrolling lists, every modal sheet in the safe area. Mutation-tested (spoilers in Collection and Daily, a 100 px ✕, a 90 px "Keep exploring", a write call, a card blocking drags, sheets left out of the safe area, the old theme back).
- **Desktop runtime (Godot 4.7.2, rendered window, real progress made through the game's APIs in a scratch save):** screenshots at 1920×1080, 2400×1080 (20:9) and 1440×1080 (4:3), empty and with progress; every ✕ measured 120×120 and "Keep exploring" 360×120 canvas px; Collection 3 columns at 16:9 and 4:3, 4 at 20:9; touch-drag scrolling moves the Collection grid and both Journal columns; a tap on "Keep exploring" closes the card; with a simulated cut-out (110 px left, 60 px right, 40 px gesture bar) the sheets' left edge moves from 96 to 134 px (cut-out + edge margin) while the others keep their larger designed margins. The editor opens all three scenes without errors or warnings.
- **Pending (Android):** reading the cards at arm's length; thumb scrolling (momentum, overscroll); the ✕ and "Keep exploring" reach on a real notched phone.
- **Files:** `scenes/ui/CollectionScreen.tscn`, `scenes/ui/JournalScreen.tscn`, `scenes/ui/DailyDiscoveryScreen.tscn`, `scripts/ui/collection_screen.gd`, `scripts/ui/journal_screen.gd`, `scripts/ui/daily_discovery_screen.gd`, `scripts/ui/hud.gd`, `tools/check_project.py`, `docs/ARCHITECTURE.md` (UI), `tools/README.md`, this plan.
- **Commit:** §15.

**M07.4b — SeedPicker landscape pass** `[~]` Implemented; desktop runtime verified; Android pending
- **Why (developer):** the SeedPicker was the last screen on the pre-M06.3 parchment theme — a fixed 740 × 350 box placed for the portrait canvas that, in landscape, sat in the middle of the screen **over the player and the plot**; theme-default 18–26 px text; a 64 × 64 grey ✕ under the 120 px target; no safe area.
- **Baseline first:** a probe on HEAD (`2612bc0`) opened the picker through real screen taps on a garden plot and recorded the behaviour to keep — 3 cards (206 × 256), a card tap plants exactly that crop (`seed_choice_closed`, `crop_planted`, the plot to PLANTED, seeds −1), the ✕ cancels without spending a seed, walking away cancels, a crop with no seeds is a disabled card that ignores taps, no seeds at all shows the hint.
- **Implementation (presentation only):** `scenes/ui/SeedPicker.tscn` — the shared theme's sheet, docked at the bottom centre (anchors bottom-centre, growing up), title "What will you plant here?", a card row with the 120 px ✕ at its end, the hint as a caption; the root still ignores the mouse and has no dim (non-modal). `scripts/ui/seed_picker.gd` — cards 240 × 270 (min 160 wide), narrowing evenly only when more crops are known than fit between the thumb zones (300 px kept clear each side); swatch, name (30), seeds left and the soil note (28, captions). `scripts/ui/hud.gd` — `_apply_safe_area()` keeps the picker above the gesture bar and centred between side insets. Unchanged: opening/closing on FarmManager's signals and on walking away, `choose_seed(crop)` / `cancel_seed_choice()`, the counts from `Inventory.get_view("seed")`, the soil note, the open animation, the HUD scene (pinned), farming, inventory, saves, rewards.
- **Contracts (`tools/check_project.py`):** the SeedPicker joined the M06.3 UI checks (shared theme, variations, 120 px ✕); new section "landscape seed picker (M07.4b)": non-modal (root ignores the mouse, no dim), docked bottom-centre growing up, code-built cards ≥ 120 px (CHOICE_SIZE, CHOICE_MIN_WIDTH) and never focused, the behaviour pinned (opens/closes on FarmManager's signals, a card calls only `choose_seed(crop)`, the ✕ only `cancel_seed_choice()`, no seeds = disabled), the HUD keeps it in the safe area. Mutation-tested (modal root, mid-screen dock, 64 px ✕, 100 px cards, a double plant, a ✕ that only hides, an enabled empty card, focusable cards, no safe area, the old theme back). The M04.4 view contracts and `sim_items` (picker counts = the old getter over 2000 sessions) still pass unchanged.
- **Desktop runtime (Godot 4.7.2, rendered window, real taps):** the same probe after the change at 1920 × 1080, 2400 × 1080 (20:9), 1440 × 1080 (4:3) and with a simulated cut-out (110 px left, 60 px right) and gesture bar (70 px): every behaviour above identical to the baseline (same signals, the same plot states and seed counts, including a fourth crop — Elderbloom, found through the Ancient Seed — planted from its card); cards 240 × 270, ✕ 120 × 120; the panel 984 px wide for 3 crops, 1244 px for 4 (x 338–1582 at 16:9, clear of the joystick and the 🎒); its top at y 645 of 1080, the player and the plot in view above it; the gesture bar lifts it by exactly its height and side insets re-centre it. One defect found and fixed during the pass: a two-line crop name ("Golden Sunflower") overflowed the card at the first card size.
- **Pending (Android):** thumb comfort on the cards and the ✕; readability at arm's length; with a tall gesture bar the panel's top meets the player's feet (seen with the simulated 70 px bar) — check on a real phone.
- **Files:** `scenes/ui/SeedPicker.tscn`, `scripts/ui/seed_picker.gd`, `scripts/ui/hud.gd`, `tools/check_project.py`, `docs/ARCHITECTURE.md` (UI), `tools/README.md`, this plan.
- **Commit:** §15.

### PHASE 08 — HOUSES / NPCS
| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M08.1 | Area transition architecture: GameArea, AreaRouter, areas as data, AreaDoor (Enter/Exit), the house door, the Meadow parked while indoors, the fade (D-31–D-35) | Enter/exit with world, farm and progress intact; a bare interior as the target | Android: transition, taps, fade | `[~]` implemented; desktop runtime verified; Android pending |
| M08.2 | Home interior (placeholder) on the M08.1 base: room layout, its navmesh and camera framing tuned | Interior playable | Walk the interior | `[ ]` |
| M08.3 | NPC framework: NPC definition + scene, idle/wander on navmesh, Talk | NPC placed in editor, no NPC-specific code | Tap NPC | `[ ]` |
| M08.4 | Minimal data dialogue (conditions, outcomes) | One conversation with an outcome | Read on device | `[ ]` |
| M08.5 | Relationships (saved value per NPC) | Survives relaunch | Relaunch | `[ ]` |
| M08.6 | Requests (world-driven: problem → explore → solution → response) | One request completable without quest markers | Complete it | `[ ]` |
| M08.7 | Services (e.g. a trade/gift) | One service works via economy/inventory | Use it | `[ ]` |

**M08.1 — Area transition architecture and the house door** `[~]` Implemented; desktop runtime verified; Android pending
- **Decisions (developer, approving the Phase 08 proposal):** keep the Meadow alive while indoors — park it outside the tree and restore the same instance (D-33); the outdoor world, farming included, pauses indoors (O-11 → D-31); interior camera bounds limit the camera's focus, with small bounds and a ~7.5 m preferred distance, no camera rewrite (O-12 → D-32); AreaRouter plus areas as data, Main the single authority that swaps, parks and restores; a relaunch from inside starts at `meadow_start`, no save change, `SAVE_VERSION` stays 5 (D-34); doors use the existing interaction flow, walking into a door never travels (D-35). M08.1 only — no interior gameplay, NPC, storage, rest, crafting or quest.
- **Implementation:**
  - `scripts/world/game_area.gd` (`GameArea`): every area's root — `area_id`, an empty `attach_player()`, the navigation bake at load (moved from `meadow.gd`); `MeadowArea` now extends it.
  - `scripts/world/area_definition.gd` (`AreaDefinition`: `id`, `display_name`, `scene_path`, `keep_alive_when_left`, `camera_distance`) and `data/areas/meadow.tres` (kept alive, free zoom), `data/areas/home.tres` (freed when left, 7.5 m).
  - `scripts/autoload/area_router.gd` (`AreaRouter`, the 16th autoload, last): loads the definitions; `travel(area_id, entry_id)` refuses mid-trip and unknown areas, then emits `travel_requested`; `notify_arrived()` / `notify_travel_failed()`; `area_changed`; `get_current_area_id()`. Never saved.
  - `scripts/world/area_door.gd` + `scenes/world/props/AreaDoor.tscn` (`AreaDoor`, an Interactable on the interactables layer that detects nothing): exports its target area, entry and verb; offers ENTER or EXIT (appended to `Interactable.Verb` as 8, 9), none mid-trip; `interact()` only asks `AreaRouter.travel()`.
  - `HousePlaceholder.tscn` instances an AreaDoor on its door (ENTER → home/home_door); `Meadow.tscn` gains `VerticalSlice/HouseDoorEntry` (`house_door`, (-19.8, 0.2, 0), facing east) and `area_id = "meadow"`.
  - `scenes/world/HomeInterior.tscn`: a bare 8 × 6 m room (GameArea "home"), its own environment, light and navigation, a low camera-side wall with full-height collision, `home_door` entry, an EXIT AreaDoor → meadow/house_door, 3 × 2 m focus bounds. The travel target only; M08.2 builds the interior on it.
  - `scripts/ui/transition_fade.gd` + `scenes/ui/TransitionFade.tscn` under Main (CanvasLayer 10): `cover()` (0.25 s) takes every touch until `reveal()` (0.3 s).
  - `scripts/main.gd`: `_on_travel_requested()` (definition → scene → cover → `_swap_area()` → reveal); `_swap_area()` reuses a parked instance, captures the old area's plots, parks it if its data keeps it alive (else frees it), re-registers a restored area's plots through `FarmManager.register_plot()` (attaching only a fresh area), applies bounds and the area's camera distance (the player's zoom kept and given back), reports the arrival; parked areas freed on exit.
  - `scripts/farming/farm_plot.gd` (re-pinned): `restore()` first replaces a crop visual the live plot already shows, so a parked plot is restored in place, never doubled.
  - `scripts/player/player.gd` (re-pinned) — **a pre-existing bug fixed because it broke the door:** `_interact_with()` pruned its spent list with `_spent_interactables = _spent_interactables.filter(...)`; `filter()` returns an untyped Array, so once a one-shot discovery had been collected every later interaction aborted with a script error (on the pre-M08 baseline too: after the flower, a farm-plot tap left the plot EMPTY). Now `_spent_interactables.assign(...filter(...))` — same contents, typed. No other Player change.
  - Unchanged: FarmManager (its frozen API), SaveManager / save format (v5), GameState, InputManager, FollowCamera, the HUD scene, rewards, inventory, wallet, the Meadow's existing geometry (digest unchanged).
- **Contracts (`tools/check_project.py`):** new section "area transitions (M08.1)" (GameArea; AreaDefinition fields; each area file and scene; no area/entry/scene named in code; AreaRouter's API, guard, arrival, never saving or touching the tree, its only callers; AreaDoor's exports, verbs, `interact()`, no walk-in reaction, its scene; the two doors lead to real entries; Main's trip, park/restore order, data-driven keep-alive, plots re-registered via `register_plot`, parked areas freed; `FarmPlot.restore()` guard; Main's children and the fade); deliberately updated: verbs (AreaDoor ENTER/EXIT), autoloads (+AreaRouter), navigation (baked by GameArea), area swap callers, camera bounds per area, camera distance only from data, the M07.2 slice rules (the door's AreaDoor and entry), `farm_plot.gd` and `player.gd` pins with the spent-list contract. A latent checker bug fixed (module-level loops rebinding the `attrs` helper). **Mutation-tested: 40 mutations, all killed.**
- **Simulations:** `sim_area_loader.py` — M08.1 section: park/restore rules read from source; one trip keeps the same Meadow, its day, a collected discovery's timer, thirst and growth; free-and-reload shown to reset the day and respawn discoveries (exploit), kept-registered plots shown to thirst indoors, an unguarded in-place restore shown to double a crop; router double requests refused; 3,000 random sessions. `sim_slice_layout.py` — the AreaDoor on the door and the `house_door` entry (out from the door, facing out, clear of the house, in range); `scene_digest` updated in `docs/VERTICAL_SLICE_LAYOUT.md` (existing-world digest unchanged).
- **Desktop runtime (Godot 4.7.2, rendered window under Xvfb, 960×540 window of the 1920×1080 canvas, real screen touches and joystick deflection; teleports only to skip the known pre-existing NW-mound stall on the way to the house):**
  - Enter by tapping the house door: the fade covers, the swap happens at alpha 1.00 with the veil taking touches (every trip, 25-round loop included), the player stands at `home_door` (0, 1.2) facing north, camera 7.5 m, focus bounds 3 × 2 m, one navigation region (the Meadow's left the map). Exit by tapping the interior door: back at `house_door` (-19.8, 0) facing east, camera 11 m; a player zoom of 13 m before entering is restored on leaving.
  - Inside: tap-walks to both corners, the joystick stops at every wall (±3.68, ±2.68), never falls (min y 0.0); a tap during the fade reaches nothing.
  - Walking into either door with the joystick for several seconds never travels; a double tap on the door starts exactly one trip; exiting after a joystick approach + tap works.
  - Repeated entry/exit: 25 / 25 clean round trips, the same Meadow instance every time, node count back to its starting level (1276–1279, no growth), 0 orphans outdoors, points / coins / inventory identical.
  - Time of day: ~30 s indoors advanced the Meadow's day by 2.1 s (the outdoor parts of the fades), not 30 s.
  - Discoveries (after the player.gd fix): a collected Meadow Flower stays gone across 4 trips of 6 s indoors each (its respawn timer moved ~1.1 s per trip, outdoor fade time only), points unchanged; after a trip its timer still fires outdoors and the flower respawns.
  - Farm: across 17.1 s away, a thirsty plot's thirst rose +1.47 s (outdoor fade time) and a growing plot's stage timer −1.08 s; each crop shows exactly one visual; a save made indoors holds both plots; afterwards watering and growth continue normally.
  - Relaunch after saving inside: the game starts in the Meadow at `meadow_start` (0, 5), router "meadow", farm and progress as saved.
  - Pre-M08 baseline (`3d0f4aa`) vs this build, the same scripted route (flower, farm plot, house door front, house wall, south along the house, joystick to the NPC area): identical positions, timings and blocks, except 8 more nodes (door, entry, fade) and — the deliberate fix — the plot tap after the flower now prepares the soil (the baseline left it EMPTY with a script error).
  - Headless editor: the project and every new or changed scene open with no error or warning; boot shows only the 9 known `det == 0` engine errors.
- **Found while testing (pre-existing, not fixed — farming is frozen, D-11):** a thirsty plot's thirst is lost across a relaunch when it is longer than the time since boot (`FarmPlot.restore()` stamps `now − thirsty_for`, which goes negative early in a session and then reads as "not thirsty"): 20.1 s saved → not thirsty after relaunch, identical on the baseline. The NW-mound/(-6, 1.4) tap-walk stall (recorded in M07.3/M07.4) still stops a tap-walk from the start to the house. For later interiors: the parked Meadow's WorldSimulation stays connected to `FarmManager.garden_interest_changed`; nothing indoors can change garden interest in M08.1, but an interior that can must make that relay tree-safe first.
- **Pending (Android):** the fade's feel and timing; tapping the doors (the interior door sits low on the screen from the entry); thumb reach to the exit; transition performance on a phone; the 7.5 m interior framing at arm's length.
- **Files:** new `scripts/world/game_area.gd`, `scripts/world/area_definition.gd`, `scripts/world/area_door.gd`, `scripts/autoload/area_router.gd`, `scripts/ui/transition_fade.gd`, `scenes/world/HomeInterior.tscn`, `scenes/world/props/AreaDoor.tscn`, `scenes/ui/TransitionFade.tscn`, `data/areas/meadow.tres`, `data/areas/home.tres`; changed `scripts/main.gd`, `scripts/world/meadow.gd`, `scripts/interactables/interactable.gd`, `scripts/farming/farm_plot.gd`, `scripts/player/player.gd`, `scenes/Main.tscn`, `scenes/world/Meadow.tscn`, `scenes/world/props/HousePlaceholder.tscn`, `project.godot`, `tools/check_project.py`, `tools/sims/sim_area_loader.py`, `tools/sims/sim_slice_layout.py`, `tools/README.md`, `docs/VERTICAL_SLICE_LAYOUT.md`, `docs/DESIGN_DECISIONS.md` (D-31–D-35; O-11, O-12 closed), `docs/ARCHITECTURE.md`, this plan.
- **Commit:** §15.

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
| M04.4 | `3e03f0f` |
| M04.5 | `cd06772` |
| M05.1 | `da04f52` |
| M05.2 | `b1891cf` |
| M05.3 | `91c6fd3` |
| M05.4 | `ff5cabd` |
| M05.5 | `c57411a` |
| M05.6 | `59194be` |
| M06.2 | `cd8a767` |
| M06.3 | `0a8ef72` |
| M06.4 | `81e26f6` |
| M06.5 | `f33c23f` |
| M06.1 (close-out) + M07.1 (proposed) | `2138eb7` |
| M07.1 (approved `[x]`) | `7ca7388` |
| M07.2 | `57183c5` |
| M07.3 | `6fd6b40` |
| M07.4 | `9e336a1` |
| M07.4a | `914c9ae` |
| M07.4b | `d888e10` |

## 16. Current position
- **Current phase:** 04 — Inventory. M04.0 (save versioning, P-01 → D-17) M04.1 (item definitions + item store), M04.2 (seeds and basket held as items; save v2) M04.3 (Inventory autoload, collectibles from discoveries; save v3) M04.4 (seed picker and basket as filtered views) and M04.5 (Inventory screen) implemented (`[~]`, runtime test pending); Phase 04 is complete in code. Phase 05: M05.1 (Wallet + ledger, save v4) M05.2 (repeat-reward protection, save v5) M05.3 (reward rules as data, once-ever discoveries) M05.4 (economy configuration) M05.5 (points and coins independent, D-24) and M05.6 (economy simulation, model only) implemented (`[~]`); Phase 05 is complete in code. Phase 06: M06.2 (selling produce for coins, O-01 → D-25; `Market` autoload) implemented (`[~]`; desktop runtime verified on Godot 4.7.2, Android pending); M06.3 (UI surfaces and HUD, D-26) implemented and verified statically (`[~]`, runtime layout check pending); M06.4 (farm milestones through one reward path, D-27) implemented and verified statically (`[~]`, runtime regression pending); M06.5 (farming frozen: ARCHITECTURE §8 boundary + checker contracts, no code change) completed `[x]`. Phase 06 is complete in code: M06.1 closed out `[~]` (achieved by M04.2–M04.3; device farm loop pending). Phase 07: M07.1 (vertical slice layout plan) approved by the developer `[x]`; M07.2 (the approved layout's placeholders placed in the Meadow) and M07.3 (slice navigation and bounds: camera arm, house carve, world rim, pond edge — O-07 → D-28, D-29) implemented and verified at runtime on desktop (`[~]`, Android pending); M07.4 (landscape orientation, D-30) implemented and verified on desktop (`[~]`, Android pending); M07.4a (landscape pass: Collection, Journal, Daily on the shared theme) implemented and verified on desktop (`[~]`, Android pending); M07.4b (SeedPicker landscape pass — no screen left on the old theme) implemented and verified on desktop (`[~]`, Android pending). Phase 08: M08.1 (area transition architecture and the house door — GameArea, AreaRouter, areas as data, AreaDoor ENTER/EXIT, the Meadow parked indoors, the fade; O-11 → D-31, O-12 → D-32, D-33–D-35) implemented and verified on desktop (`[~]`, Android pending). Phase 03: M03.1–M03.6 implemented (`[~]`; complete in code; player-facing transitions arrived with M08.1). Phase 02: M02.1–M02.6 implemented (`[~]`; M02.6 is an architecture proof). Phase 01: M01.1–M01.5 implemented (`[~]`; all await the M01.6 playtest). Phase 00's M00.5 still awaits the Godot 4.7.2 open check.
- **Next milestone:** **M01.6 — Android movement playtest** (PLAYTEST REQUIRED; include M02.1's, M02.3's, M02.4's, M03.1's, M03.2/M03.3's, M03.4's, M03.5's, M03.6's, M04.0–M04.5's, M05.1–M05.5's, M06.2's, M06.3's, M06.4's, M07.2's, M07.3's, M07.4's, M07.4a's, M07.4b's, M08.1's runtime tests). Next: the Android pass for M07.2/M07.3/M07.4 (landscape); every screen is now on the shared landscape UI; the next step waits for the developer's instruction (the Android pass for M07.2–M07.4b when a device is available). M08.1 is done in code and on desktop; **M08.2 (the home interior on the M08.1 base) waits for the developer's approval**.
- **First runtime gate:** M01.6 — Android movement playtest.
