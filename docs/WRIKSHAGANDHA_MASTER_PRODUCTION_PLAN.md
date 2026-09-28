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
| A1 | Player/camera live inside `Meadow.tscn`; interiors and area loading impossible; FarmManager assumes plots never unload | Phase 03 |
| A2 | `Interactable` base is discovery-specific | M02.1 (in code; runtime test pending) |
| A3 | FarmManager (663 lines) holds inventory-like and reward responsibilities | Phases 04–06 |
| A4 | Repeat-award problems: exploration bonuses re-award each launch (progress unsaved); repeat discoveries pay full points without limit | Phase 05 (P-02) |
| A5 | Hard-coded world data: place list, garden place id, numeric physics masks (layers are now named) | Phases 01, 03 |
| A6 | Unused interaction path (`interact_requested`) | Phase 02 |
| A7 | No top-level save versioning before inventory changes save keys | Phase 04 (P-01, proposed) → Phase 15 |
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
  - note the frame rate.
- **Done when:** the developer reports results; the default mode is recorded in `DESIGN_DECISIONS.md`.

---

### PHASE 02 — INTERACTION
Goal: one generic interaction architecture for everything touchable.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M02.1 | Split `Interactable` into a generic base + discovery behaviour, with no behaviour change (A2) | All existing interactions behave the same; toolkit passes | Tap every existing interactable | `[~]` |
| M02.2 | Generic verbs as data (Inspect, Collect, Harvest, Talk, Open, Enter, Exit, Use, Give, Plant, Water, Feed, Read) | Verb declared per interactable; Player/Input never branch on type | — | `[ ]` |
| M02.3 | Facing the object on arrival (walking to it within interaction range already done in M01.3, D-16) | Player faces what it interacts with | Android: approach feel | `[ ]` |
| M02.4 | Interaction feedback on tap (reuse the indicator); tune the small-object tolerance added in M01.3 | Small objects reliably tappable | Android: hit rate on mushrooms | `[ ]` |
| M02.5 | Remove or bind the unused `interact_requested` path (A6) | One interaction entry point | — | `[ ]` |
| M02.6 | Placeholder Inspect/Open/Read interactables as test fixtures, with zero Player changes | New types work without touching Player | Godot: tap each fixture | `[ ]` |

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

### PHASE 03 — CAMERA / WORLD SHELL
Goal: persistent Player/Camera/HUD with swappable areas.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M03.1 | Persistent shell: move Player, Camera and HUD out of `Meadow.tscn` into `Main` (A1) | Meadow loads as a child area; everything works as before | Full Meadow walk-through | `[ ]` |
| M03.2 | Area loader with named entry markers | An area can be unloaded/reloaded | Reload round-trip | `[ ]` |
| M03.3 | Area-safe world state: registration by stable id survives unload (farm plots first) | Farm state intact after area reload | Plant → reload → state kept | `[ ]` |
| M03.4 | Camera bounds per area | Camera never shows beyond the area | Walk the edges | `[ ]` |
| M03.5 | Clamped pinch zoom (+ mouse wheel) | Zoom comfortable, no conflict with taps/joystick | Android: pinch vs tap | `[ ]` |
| M03.6 | Place data out of code (place definitions replace the hard-coded list) (A5) | No place names/ids in scripts | — | `[ ]` |

### PHASE 04 — INVENTORY
Goal: one universal item model.

| Milestone | Objective | Done when | Runtime test | Status |
|---|---|---|---|---|
| M04.0 | *(Proposed P-01)* Top-level save version + migration hook | Old saves load; version recorded | Relaunch with an old save | `[!]` awaiting approval of P-01 |
| M04.1 | Item definitions (id, name, category, stackable, glyph, element id, value) + item store | Items stored and saved | — | `[ ]` |
| M04.2 | Seeds and harvests become items; migrate from FarmManager (A3) | Farming loop unchanged; seed invariant holds; old farm saves migrate | Full farm loop | `[ ]` |
| M04.3 | Discoveries and collectibles can grant items | Collect → item | Tap a collectible | `[ ]` |
| M04.4 | Inventory UI; seed picker and basket become filtered views | One inventory screen | Android: readability | `[ ]` |

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
| M02.1 | *(recorded after commit)* |

## 16. Current position
- **Current phase:** 02 — Interaction (started on the developer's instruction). M02.1 implemented (`[~]`, runtime test pending). Phase 01: M01.1–M01.5 implemented (`[~]`; all await the M01.6 playtest). Phase 00's M00.5 still awaits the Godot 4.7.2 open check.
- **Next milestone:** **M01.6 — Android movement playtest** (PLAYTEST REQUIRED; include M02.1's runtime test). In Phase 02 the next is **M02.2 — generic verbs as data**. Either starts only on the developer's instruction.
- **First runtime gate:** M01.6 — Android movement playtest.
