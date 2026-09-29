# Wrikshagandha — Architecture Overview

How the game is built today, and the agreed direction for each area.
**"Current"** describes the code on `main`; **"Direction"** is planned work
tied to a phase in `docs/WRIKSHAGANDHA_MASTER_PRODUCTION_PLAN.md`. Nothing in
a Direction note exists yet.

## 1. Project basics
- **Engine:** Godot 4.7 (feature tag `4.7`), GDScript with static typing, mobile renderer.
- **Target:** Android, portrait 1080×1920, stretch mode `canvas_items`/`expand`.
- **Main scene:** `res://scenes/Main.tscn`.
- **Physics layers** (named in `project.godot`):
  - layer 1 `world`: ground, mounds, trees, rocks, bushes, logs, monolith; everything solid.
  - layer 3 `interactables`: every Interactable Area3D. Collision value 4.
  - Scripts use the masks in `PhysicsLayers` (`scripts/data/physics_layers.gd`: `PhysicsLayers.WORLD`, `PhysicsLayers.INTERACTABLES`), the only layer numbers in code. Scenes set layers in the inspector (e.g. Player `InteractionZone` mask = interactables). `tools/check_project.py` enforces both.
- **Folders:**
  - `scenes/` — scenes, by domain (world, player, camera, ui, farming, interactables, wildlife, world_simulation)
  - `scripts/` — the same domains + `autoload/`
  - `data/` — `.tres` definitions (crops, discoveries)
  - `shaders/`, `docs/`
  - `tools/` — validation; ignored by Godot via `.gdignore`

## 2. Scene architecture
```
Main (Node3D) — persistent shell    scenes/Main.tscn, scripts/main.gd
├── Meadow (Node3D, group navigation_source) — the current area   scenes/world/Meadow.tscn, scripts/world/meadow.gd (MeadowArea)
│   ├── WorldEnvironment, DirectionalLight3D
│   ├── NavigationRegion3D          navmesh baked at load from static colliders
│   ├── Terrain / Water / Vegetation / Discoverables / Clues / SecretSpots
│   ├── Farm                         FarmPlot ×7, MilestoneReveal (GardenBloom), props
│   ├── Wildlife                     WildlifeActor instances
│   ├── Ambient / EnvironmentalEvents / ExplorationLandmarks
│   ├── WorldSimulation              TimeOfDay, Environment, Vegetation, Wildlife,
│   │                                Ambient, EnvironmentalEvents, ExplorationLandmarks controllers
│   ├── PlayerSpawn                  AreaEntry "meadow_start" (scripts/world/area_entry.gd) at the boot position
│   └── CameraBounds                 AreaCameraBounds 64 × 64 (the ground plane)
├── Player                           scenes/player/Player.tscn      (shell)
├── FollowCamera                     scenes/camera/FollowCamera.tscn (shell; the only Camera3D)
└── HUD (CanvasLayer)                scenes/ui/HUD.tscn             (shell)
    ├── TopBar, NotificationRoot, MobileControls/Joystick, ScreenButtons
    └── SeedPicker, CollectionScreen, JournalScreen, DailyDiscoveryScreen, BasketScreen
```
- **Current:**
  - World content is placed in the editor. Scripts find world objects through groups (`wildlife_actor`, `environmental_event`, `exploration_landmark`) or registration (`FarmManager.register_plot`), not hard-coded positions.
  - **Scene ownership (M03.1):** `Main` is the persistent runtime shell and owns exactly one Player, one FollowCamera (the only Camera3D) and one HUD, as direct children. The area (`Meadow`, instanced at the origin) is world content only and owns none of them. The startup scene is `Main.tscn`.
  - `main.gd` wires the shell once, after every child is ready: the camera follows the player, and `MeadowArea.attach_player()` hands the player to the area's WorldSimulation. `meadow.gd` only bakes navigation and configures its own world simulation.
  - Navigation stays with the area: the Meadow's NavigationRegion3D (settings unchanged, baked from its static colliders) and the Player's NavigationAgent3D share the one World3D navigation map.
  - Tree order keeps the old processing order: the area first, then Player, then FollowCamera, then HUD.
- **Area loader (M03.2) — infrastructure only:** `Main.load_area(scene, entry_id)` defers `_swap_area()`, which: closes the seed picker; removes the old area and `free()`s it at once (a `queue_free()` would leave its plots alive and FarmManager would reject the new plots as duplicates); adds the new area as Main's first child (processing order unchanged); `attach_player()`; places the player on the named `AreaEntry` (else the lowest id, deterministic; else the player stays put) via `Player.place_at()`; snaps the camera. Synchronous, no autoload, no transition. **Nothing in the game calls it** — no door or trigger until M08.1; for the playtest it is called from the Godot remote debugger. Boot is unchanged (the Meadow is still instanced in `Main.tscn`; `meadow_start` sits exactly where the player boots).
  - `AreaEntry` (Marker3D, group `area_entry`): `entry_id` is lower_snake_case and unique within its area; the player faces the marker's −Z.
- **Farm plots across a reload (M03.3):** `_swap_area()` calls `FarmManager.release_plots_in(old)` before removing the old area: each of its plots is captured by `plot_id` into `_unloaded_plot_states` and forgotten (no reference to freed nodes). When the next instance's plots register, each captured state is restored once — not recounted, since ready counts and garden interest keep including crops whose area is away. Saves include unloaded states, so an autosave at any point keeps the whole farm. An unloaded plot's time is paused (growth timer and thirst resume where they were), like time away from the app (open question O-11).
- **Still reset by a reload** (by design until later phases): discovery respawn timers (a reload respawns every discovery, including the non-respawning Ancient Seed — A4/Phase 05), one-time environmental events, time of day.
- **Direction (Phase 03):**
  - Area-safe world state by stable id (M03.3), then player-facing transitions (M08.1 door).
  - Each area owns its NavigationRegion3D.
  - World state is restored by stable id when an area registers, as FarmPlot already does.

## 3. Autoloads (12 — do not add more without a documented reason)
| Autoload | Role |
|---|---|
| PointsManager | "Wriksha Points" score (one int); `add_points` / `points_changed` |
| DiscoveryDatabase | Loads `DiscoveryDefinition` `.tres` from `data/discoveries/` |
| DiscoveryManager | Discovered ids (saved); `discover()` → `discovery_made` / `discovery_repeated`; awards points |
| JournalManager | Discovery journal entries (saved) |
| CollectionManager | Read-only grouping of discoveries for the Collection screen |
| DailyDiscoveryManager | One target discovery per calendar day (saved) |
| FarmManager | Farming authority (see §7) |
| ExplorationManager | Places, landmarks, secret spots, exploration bonuses (**not saved**) |
| AmbientAudioManager | Audio hooks: 10 `AudioStream` slots, all empty (no audio files yet) |
| SaveManager | Reads/writes `user://save.json` |
| GameState | Loads the save at boot; autosaves on key events and app pause/close |
| InputManager | Player intent: move vector, tap routing, movement mode |

**Load order matters:** GameState loads the save in its `_ready`, **before any world scene exists** and before InputManager's own `_ready`. Systems restore world objects when those objects register.

## 4. Player
- **Current** (`scripts/player/player.gd`, CharacterBody3D):
  - **One movement path in `_physics_process`:** a direction comes from the joystick (`InputManager.move_vector`) or, in Tap to Move, from the NavigationAgent3D path. It then runs through the same acceleration, `move_and_slide()`, facing, bob and footsteps.
  - **Joystick input cancels a path.** A new tap replaces it; a stalled path is dropped after 1 s.
  - **Interaction:**
    - `InteractionZone` (2.2 m Area3D) toggles indicators and proximity.
    - A tapped Interactable already inside `InteractionZone` is interacted with at once.
    - Otherwise the player walks toward it (NavigationAgent3D path to the nearest walkable point) and interacts on the zone's `area_entered` for that exact object. Event-driven, no distance polling.
    - With no navigation path yet (mesh still building at load), it heads straight for the target; collisions still block, and the stall timeout ends the walk.
    - `_interact_with()` is the single call site of `interact()`. It refuses unavailable objects and has a double-interaction guard for one-shot objects (`remove_on_harvest`).
    - **Facing on arrival (M02.3):** `_interact_with()` then calls `_face_target()`, before INTERACT and `interact()`. It sets `_facing_angle` from the horizontal direction to the target's position (kept if closer than 0.05 m); the existing smooth turn in `_update_facing()` does the rest. Once per interaction, never while walking, never for a cancelled or replaced target.
- **Animation state hook** (`class_name Player`):
  - `AnimState { IDLE, WALK, INTERACT }`, read with `get_animation_state()`, announced by `animation_state_changed(state, previous)` only on change.
  - It describes gameplay; it never drives movement or interaction.
    - IDLE ↔ WALK comes from the actual post-collision speed, with hysteresis (0.35 / 0.15 m/s), in the existing physics step.
    - INTERACT spans the real `interact()` call (awaited) or ends when the object leaves the tree.
  - Future animation assets subscribe to this one signal. The procedural bob/squash/facing is separate and unchanged.
- **Facing:** `_update_facing()` faces the intended movement direction (input or path); `_face_target()` faces the object being interacted with; `place_at()` faces a placement spot's forward. Nothing else sets the facing.
- **Placement (M03.2):** `place_at(spot: Transform3D)` — the only public way to move the player: ends any tap-started walk and pending interaction (`_stop_navigation()`), zeroes velocity, sets the position, faces the spot's −Z (kept when it has no horizontal direction). Generic; called only by Main's area loader.
- **Direction:** interaction feedback (M02.4). The occasional stuck/spinning navigation is left for a later movement-polish pass.

## 5. Camera
- **Current** (`scripts/camera/follow_camera.gd`): Node3D → SpringArm3D (−42°, 11 m) → Camera3D (FOV 50); smooth follow, velocity look-ahead, FOV widening at speed.
- **Bounds per area (M03.4):** each area owns one `AreaCameraBounds` (`scripts/world/area_camera_bounds.gd`, group `area_camera_bounds`): an axis-aligned X/Z rectangle centred on the node, `size` in metres (zero = none). The Meadow's is its ground plane (64 × 64 m at the origin, from `PlaneMesh_ground`). Main's `_apply_camera_bounds()` — at start and on every area swap, after the new area is installed — gives it to the camera (`set_bounds`) or clears it (`clear_bounds`), then `snap_to_target()`. The camera clamps the point it follows (player + look-ahead) to the rectangle before its unchanged smoothing; it knows no area, keeps no area reference and never looks bounds up per frame. In the Meadow the only difference from before is that the ≤ 1 m look-ahead stops at the ground's edge. Whether bounds should keep the whole *view* inside an area is open question O-12.
- **Zoom (M03.5):** zoom is the spring arm's length (the camera's distance; 11 m in the scene, FOV untouched — it stays the speed widening). `FollowCamera.zoom_by(factor)` → `set_zoom_distance()`, the only writer of the length, clamps to `ZOOM_MIN_DISTANCE`–`ZOOM_MAX_DISTANCE` (7–15 m, provisional — P-03). The camera reads no input and does no zoom work per frame; zoom survives area reloads (the camera is Main's) and never moves the focus or its M03.4 bounds.

## 6. Input — InputManager
- **Current tap pipeline:**
  1. **The GUI consumes its own touches.** Joystick zone, buttons, seed picker and screens have `mouse_filter` STOP. Only `_unhandled_input` reaches the world.
  2. **A tap is a short, still touch** (≤ 24 px, ≤ 450 ms). Drags never issue commands.
  3. **On the next physics frame** (one-off await), a ray against `interactables` (areas only) finds an active **Interactable** → `interact_target_requested(target)`.
     - Unavailable ones (`is_interaction_available()` false: locked plots, items mid-harvest) are skipped.
  4. **Otherwise,** a ray against `world` gives the tapped ground point.
     - If an active Interactable lies within `TAP_SELECT_TOLERANCE` (0.45 m) of it, that object is selected. This covers small flowers and mushrooms.
       - Several candidates: the one whose collision shape is nearest the tap (`_tap_distance`; round shapes count their radius), ties by instance id. The same rule for every object (M02.4).
     - Otherwise the point is snapped to the nearest navigation-mesh point within 1 m → `move_target_requested(destination)`. Farther means the top of an obstacle or off the edge: ignored.
     - Before the mesh exists, the tapped point is used directly.
  5. **Tapping the player** is the deliberate stop. That's its body (on the `world` layer, so the ground ray can hit it) or the ground within `PLAYER_TAP_RADIUS` (0.6 m) of its feet → `stop_requested`. The Player (group `InputManager.PLAYER_GROUP`) cancels the walk and any pending interaction. This is checked after the exact interactable ray and before small-object selection and movement.
  6. **Taps behave the same in both movement modes** (decision D-15).
- **Desktop:** the mouse emulates touch (`emulate_touch_from_mouse`), so a click takes the same path.
- **Zoom input (M03.5):** InputManager tracks every finger on the world (`_world_touches`; GUI-consumed touches such as the joystick never reach it). Exactly two fingers pinch: the change in their distance becomes `zoom_requested(old / new)` (apart = closer); the pinch restarts from the current distance whenever a finger is added or lifted, so a third finger pauses it and nothing jumps. **Once two fingers are down, no finger is a tap** (a pinch's still pivot finger must never walk the player). The mouse wheel emits `zoom_requested(1 / 1.1)` (up, closer) or `(1.1)` (down) on press, before and apart from click handling. Main connects `zoom_requested` to `FollowCamera.zoom_by` once. Tap routing itself (`_track_tap`, `_handle_tap`, selection, snapping) is unchanged and pinned.
- **Keyboard (desktop fallback):**
  - InputMap actions `move_up/down/left/right` (W/S/A/D + arrows) are read in `_input` on key events only (non-consuming) via `Input.get_vector()`.
  - InputManager combines joystick (`set_move_vector`, every frame) and keyboard into the one `move_vector`, clamped to length 1. Player is unaware of the source.
  - Focus loss clears keys. Raw key polling is not allowed (toolkit-enforced).
- **Movement mode:** `movement_mode` (JOYSTICK default, TAP_TO_MOVE) only controls whether the joystick is shown. It's saved in `settings`.
- **Notification cards** are input-transparent, so they never swallow a world tap.
- **One way in (M02.5, A6 resolved):** `interact_target_requested(target)` is InputManager's only interaction request. The old "interact with the nearest object" path (`interact_requested` / `request_interact()`) had no callers and was removed; the toolkit keeps it from returning. Player's `_interact_with()` is entered only from a tap (`_on_interact_target_requested`) or on arriving at the tapped object (`_on_interaction_zone_area_entered`).
- **Direction:** no second input system, ever.

## 7. Interaction system
- **Current (M02.1):** one generic contract, `Interactable` (`scripts/interactables/interactable.gd`, Area3D on layer 3):
  - `is_interaction_available()`: availability, backed by `monitorable`, so the InteractionZone and tap rays agree. Implementations change it by toggling `monitorable`.
  - `interact() -> bool`: the one entry point. It may await; the Player's INTERACT state lasts until it returns.
  - `remove_on_harvest`: one-shot (gone after a successful interaction) or persistent.
  - **Verbs as data (M02.2):** `enum Verb { COLLECT = 1, PLANT = 2, WATER = 3, HARVEST = 4, INSPECT = 5, OPEN = 6, READ = 7 }` (D-09 names; explicit values, appended, never reused; never strings). Every member must be offered by some object or fixture.
    - `get_available_interaction_verbs()`: what the object offers in its current state; empty while unavailable. Implementations override `_get_interaction_verbs()`.
    - `interact_with_verb(verb)`: a selected verb passed back; performed only if offered, via `_perform_interaction_verb()` (default: `interact()`). Nothing calls it yet.
    - Today each object offers at most one verb: the action `interact()` performs. Discovery: `COLLECT`. FarmPlot: `PLANT` / `WATER` / `HARVEST` by state; an EMPTY plot offers none (O-10). The tap path still calls `interact()`.
  - `get_interaction_metadata()`: optional read-only facts, empty by default; nothing reads it yet.
  - `set_highlighted()` / `update_proximity()`: in-range presentation on the `Indicator` child.
  - `set_tap_selected()` (M02.4): tap feedback on the same Indicator — shown at once with its existing `pulse()`, even out of range; never for an unavailable object. The Indicator is visible while in range OR tap-selected. Player's `_set_selected_target()` selects on the tap and releases on stop, retarget or when the interaction starts.
  - Shared presentation: `HarvestBurstScene`, `RARITY_INTENSITY`, `_play_harvest_sound()`.
- **Implementations:**
  - `DiscoveryInteractable` (`discovery_interactable.gd`): collects a discovery through `DiscoveryManager`, emits `harvested` (used by `DiscoverySpawnPoint` to respawn), plays the category/rarity windup and removes itself.
  - `FarmPlot`: the farming state machine, persistent.
  - Non-game verification fixtures in `tools/fixtures/` (never imported by Godot, never referenced by game code): the M02.1 probe (no verbs) and the M02.6 INSPECT, OPEN and READ fixtures. The READ fixture offers INSPECT and READ at once and performs the verb passed back via `_perform_interaction_verb()`. They prove new object types need no Player/InputManager change — M02.6 left both byte-for-byte unchanged.
- **Rules (toolkit-enforced):** Player and InputManager use only the contract and never name an implementation, a fixture or a specific verb, nor tell objects apart by reflection; `interact()` has one call site (`Player._interact_with`); the base holds no object-specific code; no second interaction hierarchy.
- **Direction (Phase 02):** a verb UI and routing its choice through Player's guarded path come later; further behaviours (NPC talk, door enter/exit, container open, read, give, feed…) are new implementations of the same contract.

## 8. Farming — FarmManager (frozen, decision D-11)
- **Current:**
  - `FarmManager` (663 lines) owns: crops loaded from `data/crops/`; seed inventory; the harvest basket (produce by crop and quality); quality rules (soil rotation + care → Plain/Good/Fine); farm milestones and plot unlocks; garden interest for wildlife; seed choice; persistence (`get_save_data`/`apply_save_data`, plot states restored in `register_plot`).
  - `FarmPlot` holds one plot's state and memory; `CropDefinition` holds the data; `CropVisual` the presentation.
  - **Seed invariant:** seeds in hand + crops in the ground = starting seeds + exploration seeds found (ever).
- **Direction:**
  - Seeds and basket move to the universal inventory (Phase 04).
  - Rewards move to the economy (Phase 05).
  - Farming is integrated, then frozen again (Phase 06). Rules, plots and crops stay in FarmManager.

## 9. Inventory (direction only — Phase 04)
- There is **no inventory** today. Seeds and basket are FarmManager dictionaries; discoveries are *knowledge* (ids), not items.
- **Planned:**
  - `ItemDefinition` resources (id, name, category, stackable, glyph, element id, value).
  - One item store with stacks and metadata (e.g. quality).
  - One inventory screen; seed picker and basket become filtered views.
  - Save migration for the old `farm.seeds` / `farm.basket` keys.

## 10. Economy (direction only — Phase 05)
- **Today:** only Wriksha Points exist (one saved int).
- **Known faucets:**
  - Exploration bonuses re-award every launch (exploration progress isn't saved).
  - Repeat discoveries pay full points without limit.
- **Planned:**
  - A coin **wallet with an append-only transaction ledger**.
  - Earn rules as data, with caps, diminishing returns and one-time-ever rewards.
  - An economy configuration resource. It holds the redemption reference (1000 coins = ₹10) as configuration only, read by no gameplay code (decision D-10).
- Real money, payments and backend come later, as a separate phase.

## 11. Saving
- **Current:**
  - One JSON file, `user://save.json`, written and read only by SaveManager, with keys `save_version`, `points`, `discovered_ids`, `journal_entries`, `daily_discovery`, `farm` (FarmManager's own `version: 1`, unused), `settings`.
  - **Versioning (M04.0, D-17):** `save_version` (currently 1; absent = 0 = pre-M04.0). Load order: parse → must be a dictionary → read the version (malformed → ignored like a corrupted file) → newer than the build → not loaded, and saving is blocked for the session so the file survives → `_migrate()` one step per version on a copy → `_valid_sections()` (only sections of the expected JSON type, `SECTION_TYPES`) → each system's apply. Changing what is saved = bump `SAVE_VERSION` + add a migration step (M04.2 will add 1 → 2 when seeds/basket move to inventory).
  - Every section is read with a default, so older saves load and a wrongly typed section only resets itself.
  - Autosave on: new discovery, plant, harvest, found seed, farm milestone, movement-mode change, app paused/closed.
  - **Not saved:** exploration progress, time of day, player position.
  - The farm save format is documented in `docs/farming_persistence_plan.md`.
- **Direction:**
  - Exploration progress (P-02).
  - Full versioned persistence in Phase 15.
- **Rule:** systems expose `get_save_data()` / `apply_save_data()`; world objects restore by stable id on registration.
- **Area reloads (M03.3):** farm plot states are captured by id before their area unloads (`FarmManager.release_plots_in`) and restored on re-registration; `farm.plots` in a save = boot states not yet claimed + unloaded states + live captures. Same save format.

## 12. Area / world architecture (direction — Phase 03)
- A persistent shell with swappable areas (M03.1–M03.2). Named entry markers (`AreaEntry`). Per-area navigation mesh. Per-area camera bounds (`AreaCameraBounds`, M03.4). Farm plots survive reloads (M03.3).
- World content is always placed in the editor. Places, elements and (later) NPCs are data resources referenced by id.
- Nothing in scripts depends on exact prop positions.
- **Known hard-coded data to move:**
  - the place list in `exploration_manager.gd`;
  - `FarmManager.GARDEN_PLACE_ID`.

## 13. UI architecture
- **Current:**
  - `HUD` (CanvasLayer) wires autoload signals to presentation. It holds no gameplay state.
  - **One notification card language** (`DiscoveryNotification`: full, compact, message) for every event.
  - **Modal screens** (Collection, Journal, Daily, Basket) share one pattern: parchment theme, dim background, close button, rebuild on open.
  - **Screen buttons:** Collection, Journal, Daily, Basket (appears after the first harvest), Movement toggle.
  - The SeedPicker is non-modal.
- **Direction:** a settings screen (movement, later audio and accessibility) and an inventory screen. The pattern stays the same.

## 14. Data-driven definitions
| Resource | Location | Loaded by |
|---|---|---|
| `DiscoveryDefinition` | `data/discoveries/*.tres` | DiscoveryDatabase via `ResourceDirectory` (handles `.tres.remap` in exports) |
| `CropDefinition` | `data/crops/*.tres` | FarmManager via `ResourceDirectory` |
| `PlaceDefinition` (M03.6) | `data/places/*.tres` | ExplorationManager via `ResourceDirectory`, ordered by `order` |

- Adding a crop or discovery is a new `.tres` (plus a visual scene for crops), with no code change.
- **Places (M03.6, A5):** a `PlaceDefinition` holds `id`, `display_name`, `arrival_text`, `order` (the Journal's list order), `secret`, `garden` (exactly one) and `curiosity_discovery_id`. ExplorationManager derives the "Places" list, names/arrival text, the curiosity pairing, the "every secret found" count and `get_garden_place_id()` (used by FarmManager, HUD and Journal) from them. Adding a place = a `.tres` plus an `ExplorationLandmark` with the same `location_id` in its area (the toolkit checks the one-to-one match, secret flags against landmark kinds, curiosity discoveries and crops' found-seed places). No place id or name may appear in a script. (UI copy that mentions the Meadow as an area — "The Meadow is waking up." — is not place data and is unchanged; area names become data if/when areas get definitions.)
- **Direction:** `ItemDefinition` (Phase 04), NPC definitions (Phase 08), element definitions (Phase 11), Rishi definitions (Phase 12, **blocked on design**).

## 15. Living world
- **Current:**
  - `WorldSimulation` coordinates independent controllers.
  - `TimeOfDay` has a 600 s day with phases dawn/morning/afternoon/evening/night. `EnvironmentController` lights it.
  - **Wildlife:** `WildlifeActor` (idle/wander/pause/flee; interest points; keyed attraction; night activity; keep-out circle), relayed by `WildlifeController`.
  - **Events:** `EnvironmentalEvent`, including an arrival-only garden greeting. Controllers share one distance loop each.
- **Direction (Phase 09):** NPC routines, weather, saved time of day. Stay event-driven.

## 16. Future elemental architecture (direction — Phases 11–12)
- `ElementDefinition` resources, and an optional `element_id` on places, items, discoveries and NPCs.
- Per-element progression.
- Each element prototype adds its own mechanic as reusable components, not bespoke scripts per place.
- **Five Rishis — pending final design decision** (`docs/DESIGN_DECISIONS.md`, R-01…R-07). No Rishi code, names or data until decided.

## 17. Performance notes
- **About 50 scripts run per frame:**
  - 14 wildlife actors, 8 mote clusters, 5 drifting leaves, 1 butterfly prop;
  - interactable indicators;
  - 3 world controllers + TimeOfDay;
  - Player, Camera, Joystick.
- **Rules:** prefer signals and shared controller loops; no per-object polling; no physics bodies for decoration.
- The exact set of scripts with `_process`/`_physics_process` (13) is pinned in `tools/check_project.py`; adding one is a deliberate change to that list.
- On-device profiling is part of Phase 01/16 testing.
