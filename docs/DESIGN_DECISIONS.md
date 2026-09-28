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
| O-02 | Relationship between Wriksha Points (the existing score) and coins: keep both, fold points into progression, or retire them | Phase 05 | Points exist today; coins do not |
| O-03 | Redemption go/no-go, thresholds, markets, legal/compliance approach | Future backend phase | Only after the gameplay economy is proven |
| O-04 | Final progression structure: how discovery → understanding → world change → new access is expressed | Phase 13 | — |
| O-05 | Final area structure: which areas, how they connect, elemental regions' layout | After Phase 16 | The vertical-slice layout is enough until then |
| O-06 | Default movement mode: joystick shown or hidden by default (taps work either way, D-15) | Phase 01 | Decide after the Android movement playtest |
| O-07 | Is water (the pond) walkable? | Phase 07 (M07.3, slice navigation) | Currently walkable: the pond has no collision. Does not block Phase 01 |
| O-09 | Each element's distinct gameplay mechanic | Phase 11, per element | Themes are decided (D-04); mechanics are not |

## Proposed — production recommendations awaiting approval

| ID | Proposal | Why |
|---|---|---|
| P-01 | Pull a **minimal save-versioning step** (top-level save version + one migration hook) into Phase 04 (milestone M04.0), ahead of the full Save phase (15) | Inventory will move seeds/basket out of FarmManager, changing existing save keys; without versioning, old saves lose farm data |
| P-02 | Persist exploration progress as part of Phase 05's repeat-reward protection (milestone M05.2) | Exploration bonuses currently re-award on every launch while points are saved |
