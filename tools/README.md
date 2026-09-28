# Validation toolkit

Static checks and model simulations for Wrikshagandha. They catch the classes
of mistakes that previously broke the project, without needing Godot.

> **What this is not:** none of these tools run the game. Passing them means
> **"verified in code"**, never "works in Godot" or "works on Android".
> Runtime behaviour must still be playtested (see the runtime test gates in
> `docs/WRIKSHAGANDHA_MASTER_PRODUCTION_PLAN.md`).

## Quick start

```bash
pip install "gdtoolkit==4.*"      # once: GDScript 4 syntax parser (gdparse)
tools/fetch_godot_api.sh          # once: Godot 4.7.2 API data into tools/.cache/
tools/run_all.sh                  # every time: runs everything, exit code 0 = pass
```

- Requirements: Python 3.9+, `curl`, `tar`, `git`.
- `tools/.cache/` is git-ignored. `tools/.gdignore` keeps Godot from importing anything in this folder.

## What each tool validates

| Tool | Validates |
|---|---|
| `check_project.py` | **Scenes and resources:** `load_steps` counts; missing or unused ext/sub resources; broken `res://` paths; mesh used as a collision shape; CollisionShape3D parent type; parent-before-child order; duplicate nodes; every `NodePath`, including paths into instanced scenes; `$Node` paths in scripts; exported properties set in scenes, and `.tres` fields, exist on their scripts. **Scripts:** duplicate `class_name`; parent-member redeclaration (a GDScript load error); `Autoload.x` / `ClassName.x` references and call argument counts; signal `emit()` arity; signal → handler arity (including `.unbind(n)`); typed-variable call arity. **Rules:** no hard-coded crop ids in scripts; no network APIs; `PhysicsLayers` constants match `project.godot` layer names; no numeric physics layers/masks in scripts outside `PhysicsLayers`; keyboard actions `move_up/down/left/right` keep their WASD + arrow keys; every input action a script uses is defined; no raw key polling. **Tap contracts** in the real scripts: taps are mode-independent; tapped objects are walked to and interacted with on entering the InteractionZone (no separate reach rule); joystick/keyboard cancels a walk; tapping the player requests a stop (before any movement) and the Player cancels the walk; inactive interactables never capture a tap. **Animation contracts:** exactly one `AnimState` (IDLE/WALK/INTERACT) in Player; a single emitter of `animation_state_changed`, only on change; no movement/interaction logic in the hook; speed hysteresis; INTERACT tied to the real `interact()` call and to object disappearance; no timers in Player. **Interaction contract:** the generic `Interactable` base declares the contract (availability backed by `monitorable`, `interact() -> bool`, metadata, highlight/proximity, `remove_on_harvest`) and holds no discovery/farm code; every implementation has `interact() -> bool`; Player/InputManager never name an implementation or its members; `interact()` has one call site; no second class hierarchy; no scene uses the bare base; the probe fixture stays outside game content. **Interaction verbs:** one `enum Verb` in the base, names from D-09 (read from `docs/DESIGN_DECISIONS.md`), explicit unique values; no verbs while unavailable; only offered verbs are performed, via `interact()`; the guarded functions are never overridden; discovery/farm plot offer the verbs of their existing behaviour; Player/InputManager name no verb; no verb spelled as a string; no unknown `Verb.X`. **Facing on arrival:** in `_interact_with()` the order is accept → `_face_target()` → INTERACT → `interact()`; facing uses the target position, horizontally, with a zero-distance guard, and no movement direction, type, verb, snap or waiting; `_face_target()` has one call site; only `_ready`/`_update_facing`/`_face_target` set the facing; no target facing in the physics step; stop/retarget drop the approach target; no `_process` in Player. **Tap feedback + selection:** `TAP_SELECT_TOLERANCE` and the 2.2 m interaction range (Player.tscn, `INTERACTION_RADIUS`) must match `docs/ARCHITECTURE.md`; one indicator/pulse mechanism; `set_tap_selected()` refuses unavailable objects, is never overridden and is driven only by Player; feedback given in the tap handler (never at arrival) and released on stop, retarget and interaction start; exact hit → near miss → ground; near misses ranked by distance to the object's shape with deterministic ties, never by kind or state of object. **Per-frame loops:** the set of `_process`/`_physics_process` callbacks is pinned. **One way in (A6):** `interact_requested` / `request_interact` / `_on_interact_requested` never return (scripts, scenes, `project.godot`); InputManager has one interaction request signal, `interact_target_requested`, emitted by `_handle_tap` and connected in Player; `_interact_with()` is entered only from the tap handler and zone arrival; one-shot protection is checked directly. **New object types (M02.6):** expected verbs per fixture; every `Verb` member offered by some object or fixture; fixtures extend `Interactable`, no `class_name`, availability only via `monitorable`, never override the guarded verb functions, never call `interact()` or reach into Player/InputManager; the multi-verb fixture dispatches the selected verb; Player/InputManager name no fixture/INSPECT/OPEN/READ and use no reflection; game code never loads a fixture. |
| `check_gdscript.py` | GDScript analyzer rules that Godot 4 treats as **errors by default**, checked against the Godot 4.7.2 API: `INFERENCE_ON_VARIANT` (every `:=` declaration's type is resolved; `Variant` = error), `NATIVE_METHOD_OVERRIDE`, `class_name` collisions with engine classes, `GET_NODE_DEFAULT_WITHOUT_ONREADY`, `ONREADY_WITH_EXPORT`. Also: every bare function call resolves; every method called on a native-typed variable exists on that class. Anything it cannot resolve is listed as UNKNOWN for manual review. |
| `gdparse` (gdtoolkit) | GDScript 4 syntax of every script, via an independent grammar |
| `sims/sim_farming.py` | Model of farm rules: seed invariant; ready counts; garden interest; the garden's return greeting; the rabbit keep-out geometry; soil + care quality table; plot unlocks; garden-in-bloom; new-crop flag |
| `sims/sim_persistence.py` | Multi-launch save/load model: seed invariant across launches; exploration seeds granted once ever; milestone bonuses paid once ever; mid-harvest saves never double count; capture → apply → capture is identical |
| `sims/sim_interaction.py` | Generic interaction contract model (rules read from the GDScript): a discovery, a farm plot and the non-game probe go through the same Player path; unavailable objects are refused; one-shot objects are never interacted with twice; 2,000 random sequences; verbs: FarmPlot's `interact()` and verb query read from the GDScript and cross-checked per state, all plot condition combinations, the generic ask → choose → pass-back path; tap selection (exact/near/ground ranking, ties, unavailable, large vs small; 40,000 taps on the real Meadow layout) and the tap-feedback lifecycle; the M02.6 fixtures, a discovery and a farm plot through one Player path (multi-verb dispatch read from source; unavailable/re-enabled; repeated) |
| `fixtures/*.gd` | Not checks: non-game `Interactable`s (no `class_name`; `tools/.gdignore` keeps Godot from loading them), analysed like game scripts. `generic_interactable_probe.gd` (M02.1, no verbs); `inspect_fixture.gd`, `open_fixture.gd`, `read_fixture.gd` (M02.6: INSPECT, OPEN, and INSPECT + READ multi-verb) — new object types with zero Player changes |
| `sims/sim_tap_movement.py` | Tap routing decision table (mode-independent; UI never leaks, drags never move, interactables and small-object tolerance win; constants read from the GDScript); player navigation state machine (retarget, joystick override, stall timeout, walk-then-interact); spawn and interactables clear of obstacles; keyboard + joystick combine into one move vector (joystick frames never erase held keys; clamped; focus-out clears); animation state transition table, flicker, stale-end and vanished-target handling; facing on arrival (ordered face → interact events, behind/side/underfoot, cancel and replace never face the old target, walking faces the path) |

## What it cannot validate

- Anything that needs the engine running:
  - rendering, physics, navigation-mesh baking, input delivery
  - timing and feel, performance, memory, Android behaviour
- Type rules beyond those listed above (e.g. runtime typed-array assignment errors).
- Correctness of the simulations themselves.
  - They are **Python ports** of the GDScript rules. A mismatch between port and script is possible, so keep them in sync when the rules change.
- The API data is a third-party package (`@ringozz/godot`, generated from Godot's `extension_api.json`), fetched on demand and never committed.
  - If it's ever unavailable, dump the official API with `godot --dump-extension-api` and extend `check_gdscript.py` to read it.

## Use before every commit

1. `tools/run_all.sh` must end with `ALL CHECKS PASSED`.
2. If you change a game rule that a simulation models (farming, saving, tap routing, interaction), update that simulation in the same commit.
3. After mutating code to test a check, confirm the check fails (every check was mutation-tested when written).
4. Report results as **"verified in code"**. Only a real run in Godot/Android counts as runtime verification.
