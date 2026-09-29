# Design Decisions Registry

Every design question that affects production, and its state. **Open items
must not be decided in code.** Implementation that depends on an open item is
blocked (`[!]`) until the developer records a decision here.

- **OPEN**: undecided; do not invent an answer.
- **DECIDED**: locked by the developer. The source is noted.
- **PROPOSED**: a production recommendation from the audit, awaiting approval.

## Decided

| ID | Decision | Source |
|---|---|---|
| D-01 | Wrikshagandha is a peaceful exploration/life game; farming is one part of a larger living world, not the core identity | Master production direction |
| D-02 | Core loop: explore → discover → collect → return → tend → unlock → world changes → explore again | Master production direction |
| D-03 | The world is organized around five elemental experiences, each eventually a gameplay system (environment, interactions, mechanic, wildlife, discoveries, progression, secrets, atmosphere, world-state changes), not just a biome | Master production direction |
| D-04 | **Element themes.** Earth/Prithvi: soil, plants, farming, forests, physical life, stability. Water/Jala: ponds, rivers, flow, aquatic life, reflection, healing, water discoveries. Fire/Agni: warmth, transformation, cooking, craft, sacred fire, transformation of materials. Air/Vayu: wind, movement, sound, birds, height, freedom. Space/Akasha: silence, mystery, ancient knowledge, stars, hidden places, deep exploration | Master production direction |
| D-05 | The current Meadow/Garden is the first Earth prototype; elements are prototyped one at a time in the order Earth, Water, Fire, Air, Space | Master production direction |
| D-06 | Conceptual relationship: **Element = what the world expresses; Rishi = wisdom/understanding associated with that element.** Nothing beyond this is decided | Master production direction |
| D-07 | Two movement modes, Tap-to-Move and Joystick, on one shared movement system | Master production direction |
| D-08 | Tap-to-interact (touch the object itself) is the interaction direction; no permanent Interact button | Master production direction |
| D-09 | Interaction verbs are generic capabilities: Inspect, Collect, Harvest, Talk, Open, Enter, Exit, Use, Give, Plant, Water, Feed, Read. No crop/discovery/NPC-specific hacks in player or input code | Master production direction |
| D-10 | Coins are an internal reward system. **1000 coins = ₹10** is a long-term *reference* for a separate future redemption backend only: configuration/business logic, never gameplay logic. No real-money redemption, payments or crypto now | Master production direction |
| D-11 | Farming feature expansion is frozen; farming will be integrated with inventory, economy, saving, exploration, NPC requests and progression; FarmManager to be reduced so inventory/economy don't live in it | Master production direction |
| D-12 | Small vertical slice first (meadow, garden, pond, forest edge, path, simple house, simple NPC, wildlife, discoveries, basic elemental prototype, farming, inventory, coins, journal, saving); no large world expansion before the Vertical Slice Gate | Master production direction |
| D-13 | Placeholder art until the gameplay architecture is proven; final art/world building is a dedicated later phase | Master production direction |
| D-14 | Crop count stays at 4 (no more crops before the farming loop is proven fun) | Developer instruction (farm depth milestone) |
| D-15 | **The world itself is the control.** Tap ground → walk there; tap an object → walk to it and interact. Taps work in both movement modes. The movement-mode setting only chooses whether the joystick is shown. Joystick/keyboard input always takes over from a tap-started walk; a new tap replaces the current target. Refines D-07 | Developer instruction (touch interaction fix) |
| D-16 | Interaction range for tapped objects is the existing player interaction range (the InteractionZone), not a separate reach: the player walks toward the object and interacts once it's in range. No per-object distances. Resolves O-08 | Developer instruction (touch interaction fix) |
| D-17 | **Save versioning (was P-01).** The save file carries a top-level integer `save_version` (1 since M04.0; absent = 0 = written before M04.0). A load migrates older saves one step at a time (one step per version in `SaveManager._migrate()`); refuses a save from a newer build and never overwrites it that session; treats a version that isn't a whole number ≥ 0 like a corrupted file; passes a section to its system only if its JSON type is the expected one (else that section's default). **Rule:** any change to what is saved (new section, renamed or reshaped field) bumps `SAVE_VERSION` and adds its step — the bump is what stops an older build from silently dropping newer data. `farm.version` stays as FarmManager's own (unused) field | Developer instruction (M04.0) |
| D-18 | **Quality is an attribute of held produce, not an item identity (was O-13).** One produce item per crop; the ItemStore keeps one count per quality level (`ItemDefinition.quality_levels`, produce = FarmManager's Plain / Good / Fine). Quality is decided at ripening and only scales points and size; everywhere the player sees produce it is one crop with a quality split | M04.2 audit recommendation, implemented on the developer's instruction (M04.2) |
| D-19 | **The player's items have one owner: the `Inventory` autoload (was O-14).** It holds the one `ItemStore` (never handed out) and is saved as `items`. FarmManager changes it only through its seed/basket rules; Inventory gives **one collectible per discovery collection, first or repeat** — an `ItemDefinition` with category `collectible` and that `discovery_id` (named as the discovery); a discovery without one gives nothing. Items have no value or use yet; caps on repeat rewards belong to Phase 05 (A4) | Developer instruction (M04.3) |
| D-20 | **Coins live in a `Wallet` autoload, separate from Wriksha Points.** Points stay the score (`PointsManager`); coins are the future buying/selling currency (D-10). The Wallet's **append-only ledger is the truth**: every change is one `{amount, reason}` entry, the balance is their sum and never negative, and only the ledger is saved. Only `credit`/`debit` change it. Until earn rules (M05.3) and selling (M06.2), nothing credits or debits coins; how points and coins relate: closed by D-24 (independent) | Developer instruction (M05.1) |
| D-21 | **Exploration rewards are once ever (was P-02).** Places reached, secret places found, the "every secret found" bonus and the curiosity bonus are saved (`exploration` section) and pay once ever; a load restores them without paying or announcing anything, and a malformed saved bonus flag counts as paid. Deliberately left repeatable/session-scoped: discovery collection (points + collectible every time, M04.3), the daily bonus (once per day), the discovery-count thresholds (bounded by first-ever discoveries) and session beats. Caps/diminishing returns on repeatable rewards are rates → with the earn rules (M05.3, O-01) | Developer instruction (M05.2) |
| D-22 | **Reward amounts are data; never-respawning discoveries are once-ever.** Flat Wriksha Points rewards are `RewardRule`s in `data/rewards/` (points only; per-definition amounts stay on discoveries/crops; the harvest quality scale stays FarmManager's rule, D-11). Repeat collection of respawning discoveries stays unlimited (no caps/diminishing returns — O-01 open). A discovery with `respawn_seconds <= 0` (the Ancient Seed) is claimed by its first collection — the saved `discovered_ids` is the record, no new save field — so it never spawns, pays or becomes the daily target again. Respawn timers are still not saved; no daily anti-clock logic (offline design) | Developer instruction (M05.3: D1 a, D2 b, D3 keep, D4 points only, D5 keep) |
| D-23 | **Economy configuration is data read by no gameplay code.** `EconomyConfig` (`data/economy/economy_config.tres`) holds D-10's redemption reference exactly — 1000 coins = 10 INR (`redemption_reference_coins`, `_amount`, `_currency`) — for a future backend/redemption phase; nothing in scripts, scenes or UI reads or shows it, and it is not wired to the Wallet or to points. FarmManager's `QUALITY_POINT_SCALE [0.75, 1.0, 1.5]` stays in FarmManager as a frozen farm-quality rule (not an economy rate). Crop `points_value` keeps also setting crop display order (documented, unchanged). `RewardRule`s stay separate in `data/rewards/` | Developer instruction (M05.4: E1 keep, E2 reference only, E3 keep, E4 separate) |
| D-24 | **Wriksha Points and coins are permanently independent (closes O-02).** Points stay the progression/achievement score (`PointsManager`), earned by all the existing reward sources, saved and shown exactly as before; coins stay the Wallet's future gameplay currency with no current sources or sinks (balance 0 until a later milestone adds legitimate coin rewards). Points are never converted to or from coins and never mirrored into them; no reward pays both; no rate exists (`EconomyConfig`'s 1000 coins = ₹10 is a redemption reference only, D-23). Of O-02's documented options this is "keep both" | Developer instruction (M05.5) |

## Open — Five Rishis (pending final design decision)

> **Five Rishis — pending final design decision.** Nothing about the Rishis may be implemented, named or described as final until these are DECIDED.

| ID | Question | Needed by |
|---|---|---|
| R-01 | The five Rishis' identities (names) | Phase 12 |
| R-02 | Exact element ↔ Rishi pairing (is it one per element?) | Phase 12 |
| R-03 | Each Rishi's personality and teachings | Phase 12 |
| R-04 | Each Rishi's location/region | Phase 12 |
| R-05 | Visual identity | Final art phase |
| R-06 | Progression role (what "understanding" a Rishi means in play) | Phase 12 / 13 |
| R-07 | How the player first learns of the Rishis (present characters, remembered figures, traces in the world…) | Phase 12 |

## Open — other design decisions

| ID | Question | Needed by | Notes |
|---|---|---|---|
| O-01 | Final economy details: earn rates, caps, sinks, what coins buy | Phase 05 | — |
| O-03 | Redemption go/no-go, thresholds, markets, legal/compliance approach | Future backend phase | Only after the gameplay economy is proven |
| O-04 | Final progression structure: how discovery → understanding → world change → new access is expressed | Phase 13 | — |
| O-05 | Final area structure: which areas, how they connect, elemental regions' layout | After Phase 16 | The vertical-slice layout is enough until then |
| O-06 | Default movement mode: joystick shown or hidden by default (taps work either way, D-15) | Phase 01 | Decide after the Android movement playtest |
| O-07 | Is water (the pond) walkable? | Phase 07 (M07.3, slice navigation) | Currently walkable: the pond has no collision. Does not block Phase 01 |
| O-09 | Each element's distinct gameplay mechanic | Phase 11, per element | Themes are decided (D-04); mechanics are not |
| O-12 | Should an area's camera bounds keep the whole *view* inside the area (the plan's "camera never shows beyond the area"), or only the camera's focus? | Before the first interior (M08.2) | M03.4 bounds the focus (the point the camera follows) to the area rectangle, which keeps the Meadow's framing as before; keeping the whole view inside would hold the camera ~9 m inside the Meadow's edges and needs frustum-aware bounds. Not decided |
| O-11 | Should farm time pass while the farm's area is unloaded (e.g. while the player is inside a house)? | M08.1 (first real area transition) | Found in M03.3: an unloaded plot is paused — growth and thirst resume where they were, the same rule as time away from the app. Not decided; changing it is a farm-rules decision (D-11) |
| O-10 | Which verb names preparing an empty farm plot (tilling)? A new verb, or one of D-09's (e.g. Use)? | When verbs are first shown to the player | Found in M02.2: preparing soil is existing gameplay but no D-09 verb names it, so an EMPTY plot offers no verb yet (a tap still prepares it). Farming is frozen (D-11) |

## Proposed — production recommendations awaiting approval

| ID | Proposal | Why |
|---|---|---|
| P-03 | **Zoom range 7–15 m** (camera distance = spring-arm length; the scene's 11 m stays the starting value) and a **1.1× distance change per mouse-wheel notch**. Provisional values in `follow_camera.gd` / `input_manager.gd`, to be tuned or approved after the Android playtest (M01.6, "M03.5 zoom") | The plan (M03.5) asks for clamped zoom but gives no limits; nothing in the project defined any. The range keeps the current view in the middle (≈ ±35 % distance) |
