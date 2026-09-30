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
- **Still reset by a reload** (by design until later phases): discovery respawn timers (a reload respawns every respawning discovery; since M05.3 a never-respawning one — the Ancient Seed — is a once-ever claim and never comes back, D-22), one-time environmental events, time of day.
- **Direction (Phase 03):**
  - Area-safe world state by stable id (M03.3), then player-facing transitions (M08.1 door).
  - Each area owns its NavigationRegion3D.
  - World state is restored by stable id when an area registers, as FarmPlot already does.

## 3. Autoloads (15 — do not add more without a documented reason; Inventory added by M04.3, D-19; Wallet by M05.1, D-20; Market by M06.2, D-25)
| Autoload | Role |
|---|---|
| PointsManager | "Wriksha Points" score (one int); `add_points` / `points_changed` |
| DiscoveryDatabase | Loads `DiscoveryDefinition` `.tres` from `data/discoveries/` |
| DiscoveryManager | Discovered ids (saved); `discover()` → `discovery_made` / `discovery_repeated`; awards points |
| JournalManager | Discovery journal entries (saved) |
| CollectionManager | Read-only grouping of discoveries for the Collection screen |
| DailyDiscoveryManager | One target discovery per calendar day (saved) |
| Inventory | The player's items (M04.3, D-19): one `ItemStore` — seeds, produce (a count per quality), collectibles; saved as `items`; gives a collectible per discovery collected. After DiscoveryManager, before FarmManager and GameState |
| Wallet | The player's coins (M05.1, D-20): balance + append-only ledger (the balance is its sum, never negative); `credit`/`debit` only; saved as `wallet`. Coins are earned only through the Market (M06.2); nothing spends them yet. Before SaveManager/GameState |
| Market | Selling produce for coins (M06.2, D-25): `get_unit_price`, `sell(item_id, quality, quantity)` — the one `Wallet.credit()` caller; prices from `ItemDefinition.sell_value` × `SellRules` (`data/market/`); emits `produce_sold` (GameState saves). After Inventory and Wallet, before GameState |
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
  - `FarmManager` owns: crops loaded from `data/crops/`; the seed and basket *rules* (the counts are items in the `Inventory` autoload — M04.2, M04.3); quality rules (soil rotation + care → Plain/Good/Fine); farm milestones and plot unlocks; garden interest for wildlife; seed choice; persistence (`get_save_data`/`apply_save_data`, plot states restored in `register_plot`).
  - `FarmPlot` holds one plot's state and memory; `CropDefinition` holds the data; `CropVisual` the presentation.
  - **Crop order = `points_value` (documented coupling, M05.4 E3):** `_sort_crops()` orders crops by `points_value` then id, so a crop's points also decide its place in the seed picker, basket, Journal and Inventory; changing a crop's points can re-order them.
  - **Seed invariant:** seeds in hand + crops in the ground = starting seeds + exploration seeds found (ever).
  - **Farm milestones (M06.4, D-27):** `_reach(id, message)` is the one path — once ever (saved `farm.milestones`) → the id's reward from `data/rewards/<id>.tres` (`RewardRules.has()` / `points()`; no rule = nothing) → plots with `unlock_on_milestone == id` open → `milestone_reached(id, message, bonus)` (GameState saves; HUD card; `MilestoneReveal`s grow in). Called only from planting, ripening and harvesting. The registry is `get_milestones()` (6 named milestones + "grown:<crop>" per starter crop, Journal order); every scene hook and farm reward rule must name one of its ids.
- **Direction:**
  - Seeds and basket are items since M04.2, held by the `Inventory` autoload since M04.3.
  - Rewards move to the economy (Phase 05).
  - Farming is integrated, then frozen again (Phase 06). Rules, plots and crops stay in FarmManager.

## 9. Inventory (Phase 04)
- **Current (M04.1–M04.3):** items are data — `ItemDefinition` (`id`, `display_name`, `category` seed/produce/collectible, `crop_id`, `quality_levels`, `discovery_id`) in `data/items/`: one seed item and one produce item per crop, one collectible per discovery (named as the discovery). `ItemStore` (a RefCounted class) counts items by id with **one count per quality level** — quality is an attribute of held produce, not a separate item (D-18). Only `add()`/`remove()`/`apply_save_data()` change counts; `add`/`remove` refuse unknown ids, levels and amounts below 1; `remove()` is all or nothing; counts never go negative; no stack limit; malformed saved entries are dropped with a warning.
- **Ownership (M04.3, D-19):** the `Inventory` autoload holds the player's one store and forwards its methods; the store is never handed out. Who changes it: FarmManager's seed/basket rules (starting seeds, planting, harvest, found seeds, a fresh farm's seeds) and Inventory's discovery reward — every collection of a discovery, first or repeat, gives one of its collectible (data: the item's `discovery_id`; none = nothing). Anything may read it; only SaveManager saves/loads it. FarmManager keeps the rules and farm state (crops in the ground, plots, found-seed origins, `starter_seeds`, grown crops, milestones, counts); its getters (`get_seed_count`, `get_produce_count/total`, `get_basket`) read the Inventory, so the seed picker, HUD, Journal and Basket screen are unchanged. Screens read items through `Inventory.get_view(category)` (M04.4): the seed picker (seed view, one card per known crop) and the Basket screen (produce view, in crop order) keep no counts and still refresh on FarmManager's `seeds_changed` / `produce_changed`. The **Inventory screen** (M04.5) shows everything held — Seeds, Produce (quality split), Collectibles — from `get_view()` only, rebuilt on open and on `Inventory.items_changed` (emitted by the Inventory after every real change; only this screen listens).
- **Planned:**
  - More item fields only with the item that needs them (glyph for crop-less items, element id, value).
  - One inventory screen; seed picker and basket become filtered views.
  - Save migration for the old `farm.seeds` / `farm.basket` keys.

## 10. Economy (Phase 05; selling M06.2)
- **Today:** Wriksha Points (`PointsManager`, one saved int) are the **score** — earned by discoveries, harvests, farm milestones, exploration and the daily discovery; never spent. **Coins** (M05.1, D-20) are the future currency, in the `Wallet` autoload: an append-only ledger of `{amount, reason}` entries whose sum is the balance (never negative); `credit`/`debit` refuse amounts below 1, empty reasons and overdrafts; a load replays the saved ledger and keeps its valid prefix. Coins are earned **only by selling produce** (M06.2, D-25 — see *Selling* below); nothing spends them (no sinks yet); points and coins are **permanently independent** (O-02 closed, D-24): no conversion, no mirroring, no reward paying both.
- **Repeat-reward protection (M05.2, D-21):** exploration progress is saved (places reached, secrets found, the "every secret found" and curiosity bonuses), so each exploration bonus pays once ever; loading pays nothing. Session-only by design: the discovery-count thresholds (bounded — they count first-ever discoveries, which are saved), the first/rare discovery beats, the session summary (its "places explored" now counts all places ever visited). Already once-ever: first-ever discoveries and Journal entries, farm milestones, found seeds; once per day: the daily bonus.
- **Reward rules as data (M05.3, D-22):** every flat Wriksha Points reward is a `RewardRule` (`id`, `points`, optional `threshold`) in `data/rewards/` — landmark, secret place, every secret, curiosity, the two discovery-count thresholds, the daily bonus, the four farm milestone bonuses — read through `RewardRules` (a plain class each paying system builds). Per-definition amounts stay on their definitions (discovery / crop `points_value`; the harvest quality scale is FarmManager's rule). Points are paid only at the 9 known sites; points only (coins are independent of points, D-24). A never-respawning discovery (the Ancient Seed) is a **once-ever claim**: its first collection (recorded in the saved `discovered_ids`) means it never spawns, pays or becomes the daily target again.
- **Economy configuration (M05.4, D-23):** `EconomyConfig` (`scripts/economy/economy_config.gd`, one file `data/economy/economy_config.tres`) holds D-10's redemption reference — `redemption_reference_coins = 1000`, `redemption_reference_amount = 10`, `redemption_reference_currency = "INR"` (1000 coins = ₹10) — as configuration for a future backend/redemption phase only: no script, scene, UI or autoload reads it; it is not the Wallet's and not a points ↔ coins rate (O-02). Earn amounts stay where they are: `RewardRule`s in `data/rewards/` (separate), discovery/crop `points_value`. **No economy rate lives in gameplay code** except FarmManager's `QUALITY_POINT_SCALE [0.75, 1.0, 1.5]`, a frozen farm-quality rule (D-11, pinned by the M04.2 quality contract), used only by `get_harvest_points()`.
- **Selling (M06.2, O-01 closed → D-25):** harvest → produce in the Inventory → the player sells it on the Basket screen → coins in the Wallet. Only `category == "produce"` items with `sell_value ≥ 1` sell (seeds and collectibles never). Prices: `ItemDefinition.sell_value` (wild carrot 5, meadow herb 6, golden sunflower 8, elderbloom 12 — the Good price, independent of `points_value`) × the quality's percent from `SellRules` (`data/market/sell_rules.tres`: Plain 80 / Good 100 / Fine 140 — not `QUALITY_POINT_SCALE`): `unit = (sell_value × percent + 50) div 100`, `total = unit × quantity`. `Market.sell()` validates (item, produce, price, quality, quantity ≥ 1, held, total ≥ 1), removes the items, credits the Wallet once (`sell:<item_id>:<quality>` — one ledger entry per confirmed sale), puts exactly those items back if the credit is refused, then emits `produce_sold`; GameState saves on it, so items and wallet are written together. UI: the Basket shows "Coins N" (its own label, never ✿ or ₹), a Sell button per held quality, and a confirm panel with a − / + quantity stepper (1..held) and the coins it pays; the HUD shows "+N Coins". The Inventory screen stays read-only. No caps, no sinks, no retroactive coins; `SAVE_VERSION` 5 unchanged.
- **Economy flows (M05.6, modelled by `tools/sims/sim_economy.py`; selling since M06.2):**

| Player action | Calculation | State change | Saved |
|---|---|---|---|
| Collect a discovery | its `points_value` | points; +1 collectible; first time: `discovered_ids`, Journal | first time: autosave (`discovery_made`); repeat: next save |
| 3rd / 5th first-ever discovery of a session | reward rule (threshold) | points | with that discovery's autosave |
| Reach a landmark / secret place; every secret; curiosity | reward rule | points; `exploration` claim | next save |
| Collect today's target | reward rule | points; `completed_date` | with a first-ever discovery's autosave, else next save |
| Harvest | crop `points_value` × FarmManager's quality scale | points; seed back; produce item — **no coins** | autosave (`crop_harvested`) |
| Farm milestone | reward rule | points; `farm.milestones` | autosave (`milestone_reached`) |
| Sell produce (Basket, confirmed) | `(sell_value × quality percent + 50) div 100` × quantity | produce removed; coins: one `sell:<item_id>:<quality>` ledger entry | autosave (`produce_sold`) — items and wallet together |
| (anything else) | — | no coins: discoveries, daily, exploration, thresholds, milestones, collectibles, seeds, points | — |

  Bounded: once-ever (landmarks, secrets, every secret, curiosity, farm milestones, the Ancient Seed) and the per-session thresholds — 500 points in a lifetime. Unbounded, by decision (D-22; D-25 keeps coins off every one of these): repeat collection (~4,450 points/hour naturally; 187 points + 8 collectibles per relaunch, because a relaunch respawns every respawning discovery), the daily bonus under clock changes, and harvests (rate-limited by growth timers, 7 plots and the seed invariant). Coins are bounded exactly like harvests: selling every harvest yields at most ≈ 3,500 / 4,390 / 6,090 coins/hour at Plain / Good / Fine (walking, watering and replanting ignored).
- **Known limitation — autosave gaps (current behaviour, unchanged):** repeat collections, landmarks/secrets/every-secret/curiosity and a daily bonus completed by a repeat collection are saved only at the next autosave or on app pause/close. A crash before then loses those points together with their claims (the reward can be earned again) — never duplicated.
- **Known faucet (deliberate; D-22, O-01 closed by D-25 without caps):** every collection of a respawning discovery pays its full points and a collectible (M04.3), and a relaunch resets respawn timers. It is points only — collectibles don't sell and discoveries pay no coins — so it cannot become a coin faucet.
- **Planned:**
  - Coin sinks (what coins buy) — a later milestone and decision; M06.2 is earn-only.
- Real money, payments and backend come later, as a separate phase.

## 11. Saving
- **Current:**
  - One JSON file, `user://save.json`, written and read only by SaveManager, with keys `save_version`, `points`, `discovered_ids`, `journal_entries`, `daily_discovery`, `farm` (FarmManager's own `version: 1`, unused), `settings`, `items` (M04.2: `{item_id: [count per quality level]}`; since M04.3 the `Inventory`'s, loaded before `farm`), `wallet` (M05.1: `{"ledger": [{amount, reason}, ...]}`), `exploration` (M05.2: `{landmarks, secrets, all_secrets_bonus, curiosity_bonus}` — restored without paying anything; unknown or wrong-kind places dropped; a malformed bonus flag counts as paid).
  - **Versioning (M04.0, D-17):** `save_version` (currently 5 — M05.2 added `exploration`; M05.1 `wallet`; M04.2 moved `farm.seeds`/`farm.basket` into the `items` section; M04.3 lets `items` hold collectibles; absent = 0 = pre-M04.0). Load order: parse → must be a dictionary → read the version (malformed → ignored like a corrupted file) → newer than the build → not loaded, and saving is blocked for the session so the file survives → `_migrate()` one step per version on a copy → `_valid_sections()` (only sections of the expected JSON type, `SECTION_TYPES`) → each system's apply. Changing what is saved = bump `SAVE_VERSION` + add a migration step. Steps: 0 → 1 nothing to rewrite; 1 → 2 seeds/basket → `items`, `farm.starter_seeds`; 2 → 3 nothing to rewrite (the bump stops an M04.2 build dropping collectibles); 3 → 4 nothing to rewrite (an older save has no wallet = an empty one); 4 → 5 nothing to rewrite (no exploration section = nothing reached yet — each place can pay once more after the update, then never).
  - Every section is read with a default, so older saves load and a wrongly typed section only resets itself.
  - Autosave on: new discovery, plant, harvest, found seed, farm milestone, movement-mode change, app paused/closed.
  - **Not saved:** time of day, player position, camera zoom, discovery respawns, environmental events; exploration's session-only beats and thresholds (M05.2).
  - The farm save format is documented in `docs/farming_persistence_plan.md`.
- **Direction:**
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
  - **One notification card language** (`DiscoveryNotification`: discovery, compact, message) for every event.
  - **Modal screens** (Collection, Journal, Daily, Basket, Inventory) share one pattern: dim background, a sheet, a close button, rebuilt on open. Basket and Inventory use the M06.3 language below; Collection, Journal, Daily and the SeedPicker (non-modal) keep the older parchment layout until a later UI pass.
- **UI language and layout rules (M06.3, D-26):**
  - **Design space:** the 1080 × 1920 portrait canvas (`canvas_items` / `expand`); sizes are canvas pixels. **Touch targets are at least 120 px** (≈ 48 dp on a 1080-px-wide phone). Body text 34, captions 28, headers 48, big figures 60–64.
  - **One shared theme,** `scenes/ui/wriksha_theme.tres` — the existing parchment / bark / leaf palette. Variations: `HudPill` (points), `CoinChip` + `ChipLabel` (coins — amber, square-cornered, never the points pill), `PrimaryButton` (leaf green), `SecondaryButton` (parchment, bark border), `HudButton` (round, translucent), `RowCard`, `SheetPanel`, `IconBadge`, `Caption`, `Header`, `Figure`, `CoinFigure`, `HudText`, `HudCaption`.
  - **HUD:** `TopArea` is anchored top-wide and grows down to its content — the top bar can never be stretched by a full-screen container (the pre-M06.3 tall-column bug: a full-rect MarginContainer filled the bar vertically). The bar holds the ✿ points pill, the discovery count and the secondary screens 📚 📖 ⭐ 🕹; notifications flow in `NotificationRoot` just under it. `ScreenButtons` (🧺, shown only while produce is held, and 🎒) is anchored bottom-right in the thumb zone; the joystick stays bottom-left. Both clusters add the display's safe area (`DisplayServer.get_display_safe_area()`, converted to canvas pixels) to a 24 px edge margin, re-applied when the viewport resizes. HUD containers ignore the mouse, so only their buttons catch taps.
  - **Sheets:** anchored to screen proportions (5 % side margins, 10–90 % height) — no fixed pixel offsets. Header = `Header` title (+ the `CoinChip` on the Basket) + a 120 px close button; rows are `RowCard`s with a 96–104 px icon, name `×total`, a `Caption` detail.
  - **Basket:** one card per crop — icon, name ×total, quality split, a wrapping row of `PrimaryButton` "Sell <Quality> · N each" (price from `Market.get_unit_price()`). The sell panel reads *what* (name, quality, held) → *how many* (120 px − / + around a big figure) → *how many coins* ("You receive" / "+N Coins") → Cancel / Sell. Empty: 🧺, "Nothing harvested yet.", a one-line hint.
  - **Inventory:** the same sheet and cards, read-only — no Sell, no Market, no Wallet. Collectibles show a glyph for their discovery's category.
  - **Cards:** lines title / name / optional note / amount / optional detail; empty lines are hidden; the height follows the text. Harvest: "✦ HARVESTED ✦" / "Wild Carrot · Fine" / "watered with care" / "+18 Wriksha Points" / "+1 Seed". Sale: "WILD CARROT" / "Fine ×2" / "+14 Coins" — values come from the signals, never recomputed.
- **Direction:** bring Collection, Journal, Daily and the SeedPicker onto the shared theme; a settings screen (movement, later audio and accessibility). The pattern stays the same.

## 14. Data-driven definitions
| Resource | Location | Loaded by |
|---|---|---|
| `DiscoveryDefinition` | `data/discoveries/*.tres` | DiscoveryDatabase via `ResourceDirectory` (handles `.tres.remap` in exports) |
| `CropDefinition` | `data/crops/*.tres` | FarmManager via `ResourceDirectory` |
| `PlaceDefinition` (M03.6) | `data/places/*.tres` | ExplorationManager via `ResourceDirectory`, ordered by `order` |
| `EconomyConfig` (M05.4) | `data/economy/economy_config.tres` | **nothing** — configuration only (D-10 redemption reference, D-23) |
| `RewardRule` (M05.3) | `data/rewards/*.tres` | `RewardRules` via `ResourceDirectory` (ExplorationManager, DailyDiscoveryManager, FarmManager) |
| `ItemDefinition` (M04.1) | `data/items/*.tres` | `ItemStore.load_definitions()` via `ResourceDirectory` (Inventory, FarmManager's crop→item maps, SaveManager's 1 → 2 step) |

- Adding a crop or discovery is a new `.tres` (plus a visual scene for crops), with no code change.
- **Places (M03.6, A5):** a `PlaceDefinition` holds `id`, `display_name`, `arrival_text`, `order` (the Journal's list order), `secret`, `garden` (exactly one) and `curiosity_discovery_id`. ExplorationManager derives the "Places" list, names/arrival text, the curiosity pairing, the "every secret found" count and `get_garden_place_id()` (used by FarmManager, HUD and Journal) from them. Adding a place = a `.tres` plus an `ExplorationLandmark` with the same `location_id` in its area (the toolkit checks the one-to-one match, secret flags against landmark kinds, curiosity discoveries and crops' found-seed places). No place id or name may appear in a script. (UI copy that mentions the Meadow as an area — "The Meadow is waking up." — is not place data and is unchanged; area names become data if/when areas get definitions.)
- **Direction:** NPC definitions (Phase 08), element definitions (Phase 11), Rishi definitions (Phase 12, **blocked on design**).

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
