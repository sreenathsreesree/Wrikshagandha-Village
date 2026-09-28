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
Main (Node3D)                       scenes/Main.tscn
├── Meadow (Node3D, group navigation_source)   scenes/world/Meadow.tscn, scripts/world/meadow.gd
│   ├── WorldEnvironment, DirectionalLight3D
│   ├── NavigationRegion3D          navmesh baked at load from static colliders
│   ├── Terrain / Water / Vegetation / Discoverables / Clues / SecretSpots
│   ├── Farm                         FarmPlot ×7, MilestoneReveal (GardenBloom), props
│   ├── Wildlife                     WildlifeActor instances
│   ├── Ambient / EnvironmentalEvents / ExplorationLandmarks
│   ├── WorldSimulation              TimeOfDay, Environment, Vegetation, Wildlife,
│   │                                Ambient, EnvironmentalEvents, ExplorationLandmarks controllers
│   ├── PlayerSpawn, Player          scenes/player/Player.tscn
│   └── FollowCamera                 scenes/camera/FollowCamera.tscn
└── HUD (CanvasLayer)                scenes/ui/HUD.tscn
    ├── TopBar, NotificationRoot, MobileControls/Joystick, ScreenButtons
    └── SeedPicker, CollectionScreen, JournalScreen, DailyDiscoveryScreen, BasketScreen
```
- **Current:**
  - World content is placed in the editor. Scripts find world objects through groups (`wildlife_actor`, `environmental_event`, `exploration_landmark`) or registration (`FarmManager.register_plot`), not hard-coded positions.
  - `meadow.gd` wires the camera and WorldSimulation to the Player and bakes navigation.
- **Known issue (Phase 03):**
  - Player and FollowCamera are children of `Meadow.tscn`, so an area can't be swapped (e.g. entering a house) without destroying them.
  - FarmManager also assumes plots never unload.
- **Direction (Phase 03):**
  - A persistent shell (`Main`: Player, Camera, HUD) plus swappable area scenes loaded by an area loader at named entry markers.
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
    - `_interact_with()` is the single call site of `interact()`, with a double-harvest guard for one-shot discoveries.
- **Direction:**
  - Animation-state signals for future rigs (Phase 01).
  - An approach point beside objects (Phase 02).

## 5. Camera
- **Current** (`scripts/camera/follow_camera.gd`): Node3D → SpringArm3D (−42°, 11 m) → Camera3D (FOV 50); smooth follow, velocity look-ahead, FOV widening at speed.
- **Direction (Phase 03):** camera bounds per area, clamped pinch zoom, and the camera persists across areas.

## 6. Input — InputManager
- **Current tap pipeline:**
  1. **The GUI consumes its own touches.** Joystick zone, buttons, seed picker and screens have `mouse_filter` STOP. Only `_unhandled_input` reaches the world.
  2. **A tap is a short, still touch** (≤ 24 px, ≤ 450 ms). Drags never issue commands.
  3. **On the next physics frame** (one-off await), a ray against `interactables` (areas only) finds an active **Interactable** → `interact_target_requested(target)`.
     - Non-monitorable ones (locked plots, items mid-harvest) are skipped.
  4. **Otherwise,** a ray against `world` gives the tapped ground point.
     - If an active Interactable lies within `TAP_SELECT_TOLERANCE` (0.45 m) of it, that object is selected. This covers small flowers and mushrooms.
     - Otherwise the point is snapped to the nearest navigation-mesh point within 1 m → `move_target_requested(destination)`. Farther means the top of an obstacle or off the edge: ignored.
     - Before the mesh exists, the tapped point is used directly.
  5. **Tapping the player** is the deliberate stop. That's its body (on the `world` layer, so the ground ray can hit it) or the ground within `PLAYER_TAP_RADIUS` (0.6 m) of its feet → `stop_requested`. The Player (group `InputManager.PLAYER_GROUP`) cancels the walk and any pending interaction. This is checked after the exact interactable ray and before small-object selection and movement.
  6. **Taps behave the same in both movement modes** (decision D-15).
- **Desktop:** the mouse emulates touch (`emulate_touch_from_mouse`), so a click takes the same path.
- **Keyboard (desktop fallback):**
  - InputMap actions `move_up/down/left/right` (W/S/A/D + arrows) are read in `_input` on key events only (non-consuming) via `Input.get_vector()`.
  - InputManager combines joystick (`set_move_vector`, every frame) and keyboard into the one `move_vector`, clamped to length 1. Player is unaware of the source.
  - Focus loss clears keys. Raw key polling is not allowed (toolkit-enforced).
- **Movement mode:** `movement_mode` (JOYSTICK default, TAP_TO_MOVE) only controls whether the joystick is shown. It's saved in `settings`.
- **Notification cards** are input-transparent, so they never swallow a world tap.
- **Legacy:** `interact_requested` (interact with the nearest object in the zone) is still connected in Player, but nothing emits it. Resolve in Phase 02.
- **Direction:** no second input system, ever.

## 7. Interaction system
- **Current:**
  - `Interactable` (`scripts/interactables/interactable.gd`, Area3D on layer 3) provides the indicator show/hide, a proximity reaction and a harvest presentation.
  - Its default `interact()` is **discovery-specific:** it calls `DiscoveryManager.discover(discovery_id)` and plays a rarity/category windup.
  - `FarmPlot` extends it and fully overrides `interact()` with the farming state machine.
- **Direction (Phase 02):**
  - Split into a **generic base** (range, verb, feedback, enabled state, approach point) and behaviours (discovery, farm plot, NPC talk, door enter/exit, container open, collect, read, give, feed…).
  - Verbs are data (decision D-09).
  - Player and InputManager stay type-agnostic: they only ever call `interact()` on the touched object.

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
  - One JSON file, `user://save.json`, with keys `points`, `discovered_ids`, `journal_entries`, `daily_discovery`, `farm` (versioned `version: 1`), `settings`.
  - Every key is read with a default, so older saves load.
  - Autosave on: new discovery, plant, harvest, found seed, farm milestone, movement-mode change, app paused/closed.
  - **Not saved:** exploration progress, time of day, player position.
  - The farm save format is documented in `docs/farming_persistence_plan.md`.
- **Direction:**
  - Top-level save version + migrations (proposal P-01, before inventory).
  - Exploration progress (P-02).
  - Full versioned persistence in Phase 15.
- **Rule:** systems expose `get_save_data()` / `apply_save_data()`; world objects restore by stable id on registration.

## 12. Area / world architecture (direction — Phase 03)
- A persistent shell with swappable areas. Named entry markers. Per-area navigation mesh and camera bounds.
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

- Adding a crop or discovery is a new `.tres` (plus a visual scene for crops), with no code change.
- **Direction:** `ItemDefinition` (Phase 04), place definitions (Phase 03/10), NPC definitions (Phase 08), element definitions (Phase 11), Rishi definitions (Phase 12, **blocked on design**).

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
- On-device profiling is part of Phase 01/16 testing.
