# Farming persistence — readiness audit and migration plan

Status: **not implemented.** Farming is session-only by design today;
`SaveManager` is untouched. This document records exactly what would need
saving, what must *not* be saved, and the hazards to fix first, so turning
persistence on later is additive and doesn't reshape `FarmManager`.

## How saving works today

- `SaveManager` writes one JSON file (`user://save.json`) with `points`,
  `discovered_ids`, `journal_entries`, `daily_discovery`. Every field is
  read with a default, so a new top-level key is backwards compatible.
- `GameState._ready()` calls `load_game()` (autoloads are ready, **no world
  scene or FarmPlot exists yet**) and autosaves only on
  `DiscoveryManager.discovery_made`.

## State inventory

### FarmManager — save (source of truth)

| Field | Type | Save as | Notes |
|---|---|---|---|
| `_seeds` | crop_id → int | `seeds` | Only known crop ids; drop unknown on load. |
| `_found_seed_crop_ids` + `_found_seed_origins` | crop_id → {source, source_id} | `found_seeds` | One map replaces both (ids = keys). Needs the semantics change below. |
| `_grown_crop_ids` | [crop_id] | `grown` | |
| `_produce` | crop_id → [plain, good, fine] | `basket` | Exactly the basket foundation; future consumers read/write here. |
| `_milestones_reached` | [milestone_id] | `milestones` | **Must be saved together with points** (hazard 1). |
| `_planted_count`, `_harvested_count` | int | `counts` | |
| `_harvested_plot_ids` | [plot_id] | `harvested_plots` | Stable plot ids make this safe. |
| `_garden_found` | bool | `garden_found` | Or derive from ExplorationManager if places become persistent. |

### FarmManager — do NOT save (derived or transient)

| Field | Why |
|---|---|
| `_crops` | Loaded from `res://data/crops/`. |
| `_ready_by_crop`, `_garden_interest` | Rebuilt from restored plots in READY (recompute, don't replay `notify_crop_ready`, which would re-fire milestones and cards). Bloom interest is derived from `milestones`. |
| `_last_ripened_msec` | Session clock (`Time.get_ticks_msec`). Reset to -1 on load; the "ripened while away" greeting is a per-session moment. |
| `_plots`, `_starter_plot_ids` | Rebuilt by `register_plot()`. |
| plot unlocked flags | **Derived from `milestones`** via `unlock_on_milestone` — `register_plot()` already opens a locked plot whose milestone is reached. Never save `unlocked`. |
| `_pending_plot` | UI transient. |

### FarmPlot — save per plot_id (under `plots`)

| Field | Save as | Notes |
|---|---|---|
| `plot_state` | `state` | Enum name as a string ("SOIL", …), not the int. |
| `crop_definition` | `crop` | crop_id, never a resource path. |
| `_stage_index` | `stage` | |
| `_needs_water` | `needs_water` | |
| `growth_timer.time_left` | `stage_time_left` | Seconds; the Timer node itself can't be serialized. Restart with `start(time_left)`. |
| `crop_soil` | `soil` | Rated at planting. |
| `_longest_thirst_seconds` | `longest_thirst` | Seconds, already clock-independent. |
| `_thirsty_since_msec` | `thirsty_for` | Save *elapsed* seconds (`now - since`), restore as `now - thirsty_for`. Decide whether offline time counts (recommend: it doesn't — pause the thirst clock while the app is closed, matching growth timers that also don't advance offline). |
| `crop_care`, `crop_quality` | `care`, `quality` | Only meaningful in READY; could be recomputed, but saving avoids re-deriving after rule tweaks. |
| `_recent_crop_ids` | `soil_memory` | |

Not saved: materials, tweens, `_crop_visual` (re-instanced from the crop's
`visual_scene` and snapped to its stage without appear/grow animations),
`_last_action_msec`, `_is_harvesting` (a harvest in flight completes or is
lost; never persist half a harvest).

## Hazards to fix before (or with) persistence

1. **Milestone bonus points re-award every session (exists today).**
   Points are saved; milestones aren't. Each launch can re-award First
   Harvest (10), All Starter Crops (40), Starter Garden Complete (30) and
   Garden in Bloom (50). Saving `milestones` fixes it; until then this is
   bounded (≤130/session) but real.
2. **Exploration seed rewards are once per session.** If seeds persist but
   `found_seeds` semantics stay per-session, every launch adds another seed
   and the seed invariant breaks across sessions. Persisted rule: a found
   seed is granted **once ever**; the invariant becomes
   `seeds + crops in ground = starting seeds + found seeds (ever)`.
3. **`starting_seeds` must be applied only on a fresh farm**, not on top of
   a loaded one.
4. **Save timing.** Autosave today fires only on a new discovery. Farming
   needs its own save points (after plant / harvest / milestone), and
   possibly on app pause (`NOTIFICATION_APPLICATION_PAUSED` on Android).
5. **Removed crop data.** If a saved crop_id no longer exists: drop its
   seeds/basket entries, and return a plot holding it to SOIL (refund one
   seed of nothing — the crop is gone).

## Migration plan (additive, no FarmManager redesign)

1. `FarmManager.get_save_data() -> Dictionary` and
   `apply_save_data(data: Dictionary)`, same shape as JournalManager's.
   `apply_save_data` runs from `load_game()` **before any plot exists**:
   it restores manager fields and stores `plots` as pending, keyed by
   plot_id.
2. `register_plot()` (already the per-plot entry point, and already
   applies milestone unlocks) hands a plot its pending state via a new
   `FarmPlot.restore(state: Dictionary)`; then recompute
   `_ready_by_crop` / garden interest once. `FarmPlot.capture() ->
   Dictionary` is its counterpart for saving.
3. Only then add `"farm": FarmManager.get_save_data()` to `SaveManager`
   and read it with a `{}` default — old saves load as a fresh farm.
4. Version the block: `"farm": {"version": 1, ...}` so rule changes
   (e.g. soil memory length) can migrate.
5. Verification to add: a round-trip simulation (capture → apply →
   capture is identical) and the cross-session seed invariant.

Proposed shape:

```json
"farm": {
  "version": 1,
  "seeds": {"wild_carrot": 1, "meadow_herb": 2},
  "found_seeds": {"golden_sunflower": {"source": "place", "source_id": "hidden_flower_pocket"}},
  "grown": ["wild_carrot"],
  "basket": {"wild_carrot": [0, 2, 1]},
  "milestones": ["first_seed", "first_harvest"],
  "counts": {"planted": 6, "harvested": 3},
  "harvested_plots": ["farm_plot_01"],
  "garden_found": true,
  "plots": {
    "farm_plot_01": {"state": "GROWING", "crop": "wild_carrot", "stage": 1,
                      "needs_water": false, "stage_time_left": 6.5,
                      "soil": 2, "longest_thirst": 12.0, "thirsty_for": -1,
                      "soil_memory": ["meadow_herb"]}
  }
}
```
