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
| Tap-to-interact | `[~]` implemented | Area raycast, 8 m reach, walk-then-interact in tap mode |
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
| A2 | `Interactable` base is discovery-specific | Phase 02 |
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

**M01.1 — Physics layer constants** `[~]` (verified in code; no runtime-visible change — confirmed at M01.5)
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
- **Runtime test:** none of its own (identical values); taps on objects and ground are exercised in the M01.5 playtest.
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

**M01.3 — Movement cancel + water decision** `[!]` blocked on decision O-07
- **Objective:** a deliberate way to stop tap-to-move (e.g. tap the player); pond walkability per the developer's decision.
- **Files:** `input_manager.gd`, `player.gd`, possibly `Meadow.tscn`.
- **Done when:** the player can stop a walk; the pond behaves as decided.

**M01.4 — Animation state hooks** `[ ]`
- **Objective:** Player emits idle/walk/interact state changes for future character rigs; the current procedural bob/squash is unchanged.
- **Files:** `player.gd`.
- **Verification:** toolkit.
- **Done when:** signals fire on state changes (verified in code).

**M01.5 — Android movement playtest** `[ ]` → **PLAYTEST REQUIRED**
- **Objective:** confirm movement on a phone and decide the default mode (O-06).
- **Checklist:**
  - project opens in Godot 4.7.2 with no errors;
  - joystick moves and turns smoothly;
  - Movement toggle switches modes and the joystick hides;
  - tap on ground walks there and paths go around trees, rocks, logs and the monolith;
  - mound steps are climbable;
  - a tap while walking retargets;
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
| M02.1 | Split `Interactable` into a generic base + discovery behaviour, with no behaviour change (A2) | All existing interactions behave the same; toolkit passes | Tap every existing interactable | `[ ]` |
| M02.2 | Generic verbs as data (Inspect, Collect, Harvest, Talk, Open, Enter, Exit, Use, Give, Plant, Water, Feed, Read) | Verb declared per interactable; Player/Input never branch on type | — | `[ ]` |
| M02.3 | Approach point + facing: walk beside the object, then interact (reach per O-08) | Approach consistent for near/far taps | Android: approach feel | `[ ]` |
| M02.4 | Interaction feedback on tap (reuse the indicator) + touch tolerance for small objects | Small objects reliably tappable | Android: hit rate on mushrooms | `[ ]` |
| M02.5 | Remove or bind the unused `interact_requested` path (A6) | One interaction entry point | — | `[ ]` |
| M02.6 | Placeholder Inspect/Open/Read interactables as test fixtures, with zero Player changes | New types work without touching Player | Godot: tap each fixture | `[ ]` |

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
| M07.3 | Navigation, bounds and entry points for the slice | Whole slice reachable | Walk everything | `[ ]` |

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
| M01.2 | *(recorded after commit)* |

## 16. Current position
- **Current phase:** 01 — Player. M01.1 and M01.2 implemented (`[~]`); Phase 00's M00.5 still awaits the Godot 4.7.2 open check.
- **Next milestone:** **M01.3 — Movement cancel + water decision**. It is blocked on decision O-07, and starts only on the developer's instruction.
- **First runtime gate:** M01.5 — Android movement playtest.
