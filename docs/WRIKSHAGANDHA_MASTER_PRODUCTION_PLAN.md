# WRIKSHAGANDHA — Master Production Plan

The single source of truth for development. Phases are locked and executed in
order; every milestone follows the rule in §3. Last audited against `main` at
`391404e` (28 commits, 124 tracked files, 49 scripts, 12 autoloads).

## 1. Status legend

| Mark | Meaning |
|---|---|
| `[x]` | Verified complete — for runtime features this means **actually run in Godot/Android** |
| `[~]` | Implemented and statically verified, **not yet playtested** in Godot/Android |
| `[ ]` | Not done |
| GREEN / YELLOW / RED / BLUE | complete / partial or untested / missing / intentionally deferred |

> **Important:** As of this audit, no build has been run to confirm any gameplay
> at runtime. The developer opened the project in Godot 4.7.2 once, which
> surfaced GDScript load errors (fixed in `ebb6f2b`); nothing since has been
> confirmed in the engine or on a device. So **no runtime feature is `[x]`**.
> Everything built is at best `[~]`.

## 2. Vision (locked)

A peaceful, touch-first exploration/life game: walk anywhere, touch interesting
things, discover, collect, farm, help people, and slowly understand the world
through the Five Elements (Prithvi, Jala, Agni, Vayu, Akasha) and the Five
Rishis. Not a quest corridor, checklist, menu game, or farming-only game.
Primary interaction: **touch something → walk to it → interact.**

Responsibilities: Claude builds systems, scripts, resources, reusable scenes,
data definitions, validation and UI logic. The developer places and composes the
world in the Godot editor (houses, trees, paths, NPC placement, interiors,
visual tuning).

## 3. Milestone procedure (every milestone)

1. Inspect current code.
2. Identify what exists and what's duplicated.
3. Identify what to reuse.
4. Identify conflicts and migrations.
5. Implement only the milestone.
6. Run static verification (see §6).
7. Run simulations where relevant.
8. Check regressions.
9. Review the git diff.
10. Commit.
11. Push to `main`.
12. Update this plan.
13. Report what changed and what still needs Godot/Android playtesting.

Never claim runtime success without a real run.

---

## 4. Current state audit (repository, not previous reports)

| Phase | System | Status | Existing files | Missing | Risk | Next action |
|---|---|---|---|---|---|---|
| 00 | Git / branches | GREEN | `main` (28 commits) | — | Stale branch `claude/wrikshagandha-repo-audit-afzvtu` (0 unique commits, 26 behind) | Delete stale branch when convenient |
| 00 | Project config | YELLOW | `project.godot`, `export_presets.cfg` (Android, arm64, portrait 1080×1920, mobile renderer) | Feature tag says `4.3`; developer uses 4.7.2. No `[input]` map. No named physics layers. | Editor will prompt to upgrade config; layer numbers are magic constants in code (1 = world, 4 = interactables) | Name physics layers; confirm 4.7.2 upgrade in editor |
| 00 | Autoloads | YELLOW | 12: Points, DiscoveryDatabase, Discovery, Journal, Collection, DailyDiscovery, Farm, Exploration, AmbientAudio, Save, GameState, Input | — | Order-dependent loading (GameState loads the save before InputManager's `_ready`); FarmManager is 663 lines / 36 public funcs | Keep count frozen; plan FarmManager split in 04/06 |
| 00 | Validation tooling | RED | **None in repo.** Suite (scene/resource checker, Godot 4.7.2 semantic checker, simulations) exists only in a temporary session directory | `tools/` with the checkers + a README on running them | Tooling is lost when the cloud session ends; future milestones can't meet §3 step 6 | **M00.4 (next milestone)** |
| 00 | Documentation | YELLOW | `docs/farming_persistence_plan.md`, this plan | README, architecture overview | Architecture knowledge lives in script header comments only | M00.5 |
| 01 | Joystick movement | YELLOW `[~]` | `player.gd`, `virtual_joystick.gd`, `VirtualJoystick.tscn`, `InputManager.move_vector` | — | — | Playtest |
| 01 | Tap-to-move + navigation | YELLOW `[~]` | `InputManager` (movement mode, ground ray), `player.gd` (NavigationAgent3D path in existing physics loop), `NavigationRegion3D` baked at runtime in `meadow.gd` | Explicit "stop" gesture; editor-baked navmesh | Runtime bake never run; pond walkable (no collider); joystick still default | Playtest; decide default |
| 01 | Camera | YELLOW | `follow_camera.gd` (smooth follow, look-ahead, FOV at speed), SpringArm3D fixed −42°, 11 m | Boundaries, zoom (pinch), bounds for world edge | Camera can show beyond the 64 m ground; no zoom on small phones | M01.3, M01.4 |
| 01 | Desktop fallback | YELLOW | Mouse → emulated touch (joystick + tap) | Keyboard movement (no input map) | Editor testing is mouse-only | M01.5 |
| 01 | Player animation hooks | RED | Procedural bob/squash on `Visual` | Animation state hooks (idle/walk/interact) for future rigs | Final character will need to replace procedural code | M01.6 |
| 02 | Tap-to-interact | YELLOW `[~]` | `InputManager` (area raycast, layer 4), `player.gd` (`_interact_with`, 8 m `TAP_REACH`, walk-then-interact in tap mode) | Interaction feedback on touch; approach stops at 8 m, not beside the object | Small colliders (mushrooms) may be hard to hit | Playtest; tune |
| 02 | Interactable base | YELLOW | `interactable.gd` (Area3D; discovery-centric: `discovery_id`, rarity windup, `DiscoveryManager.discover` in base `interact()`), `FarmPlot` overrides | Generic verbs (inspect/open/enter/talk/activate); interaction data resource | New types (NPC, door, chest) would inherit discovery-specific code | **Refactor at Phase 02 start:** split generic base from discovery behaviour |
| 02 | Legacy interact path | YELLOW | `InputManager.interact_requested` → Player nearest-in-zone | Nothing emits it any more (button removed, no key binding) | Dead path kept "for non-touch input" | Bind to a key in M01.5 or remove in Phase 02 |
| 03 | Sandbox world | YELLOW | `Meadow.tscn` (199 nodes: terrain, mounds, pond, trees, stone ring, secret spots, 7 farm plots, 9 discovery spawns, wildlife, events, landmarks) | House, NPC location, clear forest edge, paths as data | Player and camera live **inside** `Meadow.tscn` — blocks interiors (Phase 08) | Restructure before Phase 08 (see §5.1) |
| 04 | Inventory | RED | Seeds + basket inside `FarmManager`; discoveries are *knowledge* (`DiscoveryManager.discovered_ids`), not items | Universal ItemDefinition + Inventory | Migration of `seeds`/`basket` save keys | Phase 04 plan |
| 04 | Collection / Journal | YELLOW `[~]` | `CollectionManager` (derived, no state), `JournalManager` (saved), Journal/Collection/Basket screens | Item-backed collection | — | Keep; re-point at inventory in 04 |
| 05 | Economy (coins/wallet) | RED | Only "Wriksha Points" (`PointsManager`, 21 lines, a single int) | Wallet, transactions, spend, sinks, anti-abuse | **Unbounded point faucets today** (§5.2) | Design in Phase 05; points ≠ coins |
| 06 | Farming | YELLOW `[~]` | `farm_manager.gd`, `farm_plot.gd`, `crop_definition.gd`, `crop_visual.gd`, 4 crop `.tres`, `SeedPicker`, `BasketScreen`, `MilestoneReveal` | Integration with inventory/economy/NPCs | FarmManager too broad; "no scene reload" assumption (§5.3) | Frozen until Phase 06 |
| 07 | NPCs | RED | — | Everything | — | Deferred |
| 08 | Houses / interiors | RED | — | Everything | Needs world/player restructure first | Deferred |
| 09 | Living world | YELLOW `[~]` | `WorldSimulation` (TimeOfDay 600 s cycle, EnvironmentController, Wildlife actors/controller, events, landmarks), wildlife garden interest, day-phase activity | Weather, NPC schedules, seasons | TimeOfDay not saved | Deferred |
| 10 | Exploration / discovery | YELLOW `[~]` | `ExplorationManager` (landmarks, secret spots, curiosity/distance bonuses), `DiscoveryDatabase` (9 `.tres`), spawn points with respawn timers, clues, daily discovery | Data-driven places (place list is hard-coded in `exploration_manager.gd`) | Exploration progress **not saved** → bonuses re-award each launch | Save + data-drive places in 10/15 |
| 11 | Requests | RED | — | — | — | Deferred |
| 12 | Five Element prototypes | RED (Earth partial) | Meadow + farming ≈ Prithvi | Jala, Agni, Vayu, Akasha | — | Deferred |
| 13 | Five Rishis | BLUE | — | Architecture only when phase starts | — | Deferred |
| 14 | Progression | YELLOW | Scattered: FarmManager milestones, ExplorationManager bonuses, points | Unified progression model | Three separate reward systems | Phase 14 |
| 15 | Save / persistence | YELLOW `[~]` | `SaveManager` (one JSON file: points, discovered_ids, journal, daily, farm v1, settings), `GameState` autosave | Top-level save version; exploration, time of day, player position | Partial coverage causes re-awards (§5.2) | Phase 15 (hazard fix may come earlier, see §7) |
| 16–17 | Final world / assets | BLUE | Placeholder primitives only; no textures, models, fonts | — | — | Deferred |
| 18 | Audio | YELLOW | `AmbientAudioManager` with hooks for 10 sounds | **No audio files in repo** — all streams empty, game is silent | — | Deferred |
| 19 | Real-money redemption | BLUE | — | Backend, KYC, compliance, legal | Legal/regulatory | Deferred; no code until phase |
| 20–22 | Polish / testing / release | RED | Android export preset only | — | — | Deferred |
| — | Network / analytics / crypto | Correctly absent | grep: none | — | — | Keep absent |

## 5. Architectural findings

### 5.1 Conflicts to resolve before specific phases

1. **Player and camera live inside the world scene.** `Main.tscn` = Meadow + HUD, but `Player` and `FollowCamera` are children of `Meadow.tscn` and wired by `meadow.gd`.
   - Entering a house (Phase 08) needs a world-swap or streaming architecture where Player, Camera and HUD persist across areas.
   - **Resolve before Phase 08.**
2. **Interactable base is discovery-specific.**
   - The generic `interact()` calls `DiscoveryManager.discover`, and the rarity/category windup lives in the base class.
   - NPCs, doors and chests need a generic base plus a discovery subclass (or a behaviour resource).
   - **Resolve at the start of Phase 02**, before adding new interactable types. The Player side is already generic: it only calls `interact()`.
3. **FarmManager is a mega-manager.** Seeds, basket, quality rules, milestones, plots, garden interest and persistence all live in one 663-line autoload.
   - Seeds and basket move to the universal inventory in Phase 04; quality and milestones stay.
   - Don't split it before then.
4. **Hard-coded world data.**
   - The place list (ids and display names) sits in `exploration_manager.gd`.
   - `GARDEN_PLACE_ID = "quiet_farm"` is hard-coded in FarmManager.
   - Physics layers are magic numbers (1, 4).
   - Move these to data or project settings as each phase touches them.

### 5.2 Economy and persistence hazards (important before any coin work)

- **Exploration bonuses re-award every launch.**
  - Landmarks give 15, secrets 15, all secrets 50, curiosity 20, plus distance thresholds.
  - Points are saved, but `ExplorationManager` state isn't.
- **Repeat discoveries are an unbounded faucet.** Every repeat harvest pays the discovery's full `points_value`, and spawns respawn every 45–600 s.
- **Farming harvests are renewable points.** This is by design, but uncapped.
- **Conclusion:** points must not become coins 1:1.
  - Phase 05 needs a separate wallet with explicit earn rules, caps or diminishing returns, and a transaction log.
  - The re-award bug should be fixed no later than Phase 05.

### 5.3 Assumptions that will break later

- **FarmManager assumes plots register once per launch** ("no scene reload").
  - If the Meadow is unloaded (house entry), `get_save_data()` skips freed plots, and their state is lost.
  - Must be handled together with §5.1 (1).
- **Save load runs in an autoload before the world exists.** This is handled for farm plots via `register_plot()`; any new world-state system must follow the same pattern.

### 5.4 Duplicates and legacy paths

- **Two interaction entry points:** `interact_requested` (nearest-in-zone, now unused) and `interact_target_requested` (tap). Keep one.
- **Two data-definition types** (`DiscoveryDefinition`, `CropDefinition`) that both describe "things in the world". An `ItemDefinition` in Phase 04 should sit beside them, not replace them blindly.
- **Proximity:** the 2.2 m `InteractionZone` still drives indicators and proximity, while taps use an 8 m reach. That's intentional, but it's two ranges to keep coherent.

### 5.5 Things that are sound — do not touch

- **Farming's data-driven core:** `CropDefinition` owns the data, `FarmPlot` holds per-plot state, and FarmManager holds the rules.
- **The seed invariant** (seeds in hand + crops in the ground = starting seeds + found seeds), guarded by simulations.
- **WorldSimulation's coordinator pattern:** group-based discovery of actors, events and landmarks.
- **The event-driven style:** signals instead of polling, and a shared distance loop per controller.
- **The GUI-first touch pipeline:** the UI consumes its own touches before `_unhandled_input` sees the world.

## 6. Validation toolkit (to be committed in M00.4)

These tools have been run for every milestone so far, but they aren't in the repository yet:

- **Scene/resource checker:**
  - `load_steps`, ext/sub resources, paths, and node parents and paths
  - exported properties and `.tres` fields
  - class names and parent-member redeclaration
  - autoload and class member references, signal emit/handler arity, typed-call arity
  - hard-coded crop ids and network APIs
- **Godot 4.7.2 semantic checker**, driven by the engine API:
  - `INFERENCE_ON_VARIANT` and native method override
  - class_name collisions
  - `@onready` misuse
  - unresolved bare calls and missing native methods
- **gdtoolkit `gdparse`:** syntax check for every script.
- **Model simulations:**
  - farming seed invariant, care and quality, bloom
  - multi-launch persistence
  - tap and movement routing, and geometry reachability
- **Limit:** none of these replace running Godot. No Godot binary is reachable from the cloud environment (GitHub downloads are blocked by its network policy).

---

## 7. Phase plan

Each phase lists its goal, dependencies, milestones, validation, playtest requirements and completion gate.

### PHASE 00 — Project foundation — **YELLOW (closing)**
- **Goal:** a stable project base and a repeatable workflow.
- **Dependencies:** none.
- [x] Godot 4 project, Git on `main`, scene/resource/script folders, Android export preset
- [x] Autoload architecture established (12 autoloads; freeze the count)
- [x] Load-breaking GDScript errors fixed (`ebb6f2b`)
- [ ] **M00.4** Commit the validation toolkit to `tools/`, with a README on running it
- [ ] M00.5 Short `docs/ARCHITECTURE.md`: autoload responsibilities, scene tree, signal flow, save flow
- [ ] M00.6 Name physics layers in `project.godot` (1 world, 3 interactables); confirm the 4.7.2 config upgrade in the editor
- [ ] M00.7 Delete stale branch `claude/wrikshagandha-repo-audit-afzvtu`
- **Validation:** the toolkit runs green on `main`.
- **Playtest:** the developer opens the project in 4.7.2 with zero script errors in Output.
- **Gate:** the toolkit is in the repo and passing, and the editor shows no errors.

### PHASE 01 — Player experience — **YELLOW**
- **Goal:** the player can comfortably navigate the sandbox by touch.
- **Dependencies:** Phase 00.
- [~] Joystick movement (acceleration, turning, bob, footsteps hook)
- [~] Tap-to-move on a runtime-baked navmesh (`391404e`); joystick overrides; retarget on tap; stall timeout
- [~] Movement mode setting (Joystick / Tap to Move), saved
- [~] Destination marker (reused HarvestBurst)
- [~] Camera follow with look-ahead and FOV boost
- [ ] M01.1 **Android playtest of movement**: navmesh builds, paths avoid obstacles, mound steps climbable, bake time measured; decide the default mode (directive: touch-first)
- [ ] M01.2 Movement cancellation gesture (e.g. tapping the player stops); decide pond walkability
- [ ] M01.3 Camera boundaries (keep the view inside the world)
- [ ] M01.4 Camera zoom (pinch; clamped)
- [ ] M01.5 Desktop fallback: input map (WASD / arrows, E to interact) through InputManager
- [ ] M01.6 Player animation state hooks (idle / walk / interact signals) for future rigs
- **Validation:** static toolkit; routing and geometry simulations.
- **Playtest:** walk every part of the Meadow by tap and by joystick on Android, and on desktop with mouse and keyboard.
- **Gate:** comfortable navigation of the whole sandbox on a real device.

### PHASE 02 — Universal interaction — **YELLOW**
- **Goal:** one reusable interaction architecture for every touchable thing.
- **Dependencies:** Phase 01 gate.
- [~] Exact touch targeting (area raycast), tap-to-interact, walk-then-interact in tap mode
- [~] Double-harvest guard for one-shot interactables
- [ ] M02.1 Split `Interactable` into a generic base (verbs, range, feedback hooks) and discovery behaviour (§5.1.2), with no behaviour change
- [ ] M02.2 Interaction verbs as data: collect / inspect / open / enter / talk / activate / harvest
- [ ] M02.3 Approach-to-object: stop beside the object (not at the 8 m reach), face it, then interact
- [ ] M02.4 Touch feedback (reuse the indicator pulse) and a larger touch tolerance for small objects
- [ ] M02.5 Retire the unused `interact_requested` path, or bind it in M01.5
- **Validation:** a new interactable type added with zero Player changes (test fixture).
- **Playtest:** tap every interactable type on device.
- **Gate:** a new interactable doesn't require rewriting Player.

### PHASE 03 — Sandbox world — **YELLOW**
- **Goal:** a tiny placeholder world that exercises every system.
- **Dependencies:** Phase 02.
- [~] Meadow, farm, pond, mounds and overlook, stone ring, secret spots, trees and rocks
- [ ] M03.1 Restructure scenes: a persistent Player/Camera/HUD shell, with the world area as a swappable child (§5.1.1, §5.3). Prerequisite for 08.
- [ ] M03.2 Placeholder forest edge, paths, a house exterior slot, an NPC location slot
- [ ] M03.3 Data-drive place definitions (move the hard-coded `PLACES` list to resources)
- **Gate:** the player can freely explore the entire sandbox.

### PHASE 04 — Inventory & collection — **RED**
- **Goal:** universal item infrastructure.
- **Dependencies:** Phase 03.
- [ ] M04.1 Audit and migration plan: FarmManager `seeds`/`basket` → inventory; save-key migration (`farm.seeds`, `farm.basket`)
- [ ] M04.2 `ItemDefinition` resource and an inventory (stacks, categories, metadata) — placement decided in M04.1 without adding an autoload lightly
- [ ] M04.3 Seeds and crops as items; the basket screen becomes an inventory view
- **Gate:** seeds, crops and collectibles share one item architecture, and old saves still load.

### PHASE 05 — Economy — **RED**
- **Goal:** an in-game coin economy with no real money.
- **Dependencies:** Phase 04.
- [ ] M05.0 Fix the re-award and faucet hazards (§5.2), if not already fixed in Phase 15
- [ ] M05.1 Wallet and transaction log (earn and spend records); points stay separate from coins
- [ ] M05.2 Earn rules with caps and diminishing returns; first sinks
- [ ] M05.3 Balancing simulation
- **Gate:** the economy works end to end without any real-money path.

### PHASE 06 — Farming integration — **YELLOW (frozen)**
- **Goal:** connect the existing farming to the rest of the game.
- **Dependencies:** Phases 04, 05, 07.
- [~] Complete loop: prepare → plant → water → grow → harvest; renewable seeds
- [~] 4 crops (data-driven), soil rotation + care quality, basket, 7 plots (2 milestone-unlocked), exploration seeds, Elderbloom via the Ancient Seed, wildlife interest, garden in bloom
- [~] Farm persistence (v1) and milestones paid once
- [ ] M06.1 Farming on the inventory and economy
- [ ] M06.2 NPC requests for produce (after 07)
- **Rule:** no new farming features before this phase.

### PHASE 07 — NPC system — **RED**
- **Goal:** a reusable NPC framework, tested with 2–3 NPCs.
- **Dependencies:** 02, 03.
- [ ] Identity, home, navigation (reuses the navmesh), idle behaviour, talk interaction, dialogue data, relationship stub
- **Gate:** 2–3 NPCs work with no NPC-specific code.

### PHASE 08 — House / interior — **RED**
- **Goal:** one complete reusable house.
- **Dependencies:** M03.1, 07.
- [ ] Door interaction, enter/exit transition, interior scene, camera handling, bed/storage objects, farm state safe across transitions
- **Gate:** the house can be duplicated in the editor without code changes.

### PHASE 09 — Living world — **YELLOW (partial)**
- **Goal:** the world feels alive without the player triggering everything.
- **Dependencies:** 07, 08.
- [~] Day/night cycle, wildlife behaviours, environmental events
- [ ] NPC schedules, weather, saved time of day, seasons (later)

### PHASE 10 — Exploration / discovery — **YELLOW**
- **Goal:** deeper discovery and hidden-world systems.
- **Dependencies:** 03, 15 (saving).
- [~] 9 discoveries, respawns, clues, landmarks, secret spots, daily discovery, journal, collection
- [ ] Persist exploration progress; data-driven places; new discovery mechanics

### PHASE 11 — Request system — **RED**
- **Goal:** lightweight, world-driven requests (a problem to explore → a discovered solution → the world responds).
- **Dependencies:** 07, 04.

### PHASE 12 — Five Element prototypes — **RED** (Prithvi partially covered by the Meadow)
- **Goal:** one small prototype per element.
- **Dependencies:** 02–11.
- [ ] Prithvi
- [ ] Jala
- [ ] Agni
- [ ] Vayu
- [ ] Akasha

Each needs a distinct interaction identity.

### PHASE 13 — Five Rishis — **BLUE**
- **Goal:** architecture first, then narrative systems.
- **Dependencies:** 12.
- **Rule:** no lore is invented without explicit direction.

### PHASE 14 — Progression — **YELLOW (scattered)**
- **Goal:** one progression model across all activities.
- **Dependencies:** 05, 10, 11, 13.
- Unify FarmManager milestones, ExplorationManager bonuses, points/coins, knowledge, element and Rishi progress.

### PHASE 15 — Save / persistence — **YELLOW**
- **Goal:** robust, versioned persistence.
- **Dependencies:** each system as it lands.
- [~] Single JSON save: points, discoveries, journal, daily, farm v1, settings; autosave on key events and app pause/close
- [ ] Top-level save version and migration framework
- [ ] Exploration progress, time of day, player position, inventory, wallet
- [ ] Old-save compatibility tests (fixture saves)

### PHASES 16–22 — **BLUE**

| Phase | Covers | Condition |
|---|---|---|
| 16 Final world | the real map | after the sandbox passes |
| 17 Final assets | characters, NPCs, props, environment, VFX | after 16 |
| 18 Audio | ambience, music, SFX | hooks exist (10 sound slots, no files) |
| 19 Real-money redemption | backend, secure wallet, fraud prevention, accounts, KYC, payments, compliance, legal review | nothing before it |
| 20 Polish | animation, lighting, VFX, UI, camera, touch UX, performance, loading, memory, accessibility | |
| 21 Testing | internal QA, Android and low-end devices, touch, save and economy tests, performance, closed beta | |
| 22 Release | production backend, analytics, crash reporting, store listing, legal pages, soft and public launch | |

---

## 8. Next milestone

**M00.4 — Commit the validation toolkit to `tools/`.**

- **Why next:**
  - Every milestone's gate (§3 step 6) depends on these checks.
  - Today they exist only in a temporary cloud-session directory and will be lost.
  - It's pure tooling, with zero gameplay risk.
- **Depends on:** nothing.
- **Do not touch:** any `.gd`/`.tscn`/`.tres` gameplay file.

**Then:**
- M00.5 architecture overview
- M00.6 named physics layers
- M00.7 branch cleanup
- **M01.1 Android movement playtest** (developer). It's the first real runtime gate and decides the default movement mode.

**Must wait for the playtest:** camera bounds/zoom (M01.3/M01.4), and any Phase 02 refactor.

**Frozen until their phase:** farming features, NPCs, houses, inventory, economy.
