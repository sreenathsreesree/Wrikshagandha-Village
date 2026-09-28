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
| `check_project.py` | **Scenes and resources:** `load_steps` counts; missing or unused ext/sub resources; broken `res://` paths; mesh used as a collision shape; CollisionShape3D parent type; parent-before-child order; duplicate nodes; every `NodePath`, including paths into instanced scenes; `$Node` paths in scripts; exported properties set in scenes, and `.tres` fields, exist on their scripts. **Scripts:** duplicate `class_name`; parent-member redeclaration (a GDScript load error); `Autoload.x` / `ClassName.x` references and call argument counts; signal `emit()` arity; signal → handler arity (including `.unbind(n)`); typed-variable call arity. **Rules:** no hard-coded crop ids in scripts; no network APIs; `PhysicsLayers` constants match `project.godot` layer names; no numeric physics layers/masks in scripts outside `PhysicsLayers`; keyboard actions `move_up/down/left/right` keep their WASD + arrow keys; every input action a script uses is defined; no raw key polling. **Tap contracts** in the real scripts: taps are mode-independent; tapped objects are walked to and interacted with on entering the InteractionZone (no separate reach rule); joystick/keyboard cancels a walk; tapping the player requests a stop (before any movement) and the Player cancels the walk; inactive interactables never capture a tap. |
| `check_gdscript.py` | GDScript analyzer rules that Godot 4 treats as **errors by default**, checked against the Godot 4.7.2 API: `INFERENCE_ON_VARIANT` (every `:=` declaration's type is resolved; `Variant` = error), `NATIVE_METHOD_OVERRIDE`, `class_name` collisions with engine classes, `GET_NODE_DEFAULT_WITHOUT_ONREADY`, `ONREADY_WITH_EXPORT`. Also: every bare function call resolves; every method called on a native-typed variable exists on that class. Anything it cannot resolve is listed as UNKNOWN for manual review. |
| `gdparse` (gdtoolkit) | GDScript 4 syntax of every script, via an independent grammar |
| `sims/sim_farming.py` | Model of farm rules: seed invariant; ready counts; garden interest; the garden's return greeting; the rabbit keep-out geometry; soil + care quality table; plot unlocks; garden-in-bloom; new-crop flag |
| `sims/sim_persistence.py` | Multi-launch save/load model: seed invariant across launches; exploration seeds granted once ever; milestone bonuses paid once ever; mid-harvest saves never double count; capture → apply → capture is identical |
| `sims/sim_tap_movement.py` | Tap routing decision table (mode-independent; UI never leaks, drags never move, interactables and small-object tolerance win; constants read from the GDScript); player navigation state machine (retarget, joystick override, stall timeout, walk-then-interact); spawn and interactables clear of obstacles; keyboard + joystick combine into one move vector (joystick frames never erase held keys; clamped; focus-out clears) |

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
2. If you change a game rule that a simulation models (farming, saving, tap routing), update that simulation in the same commit.
3. After mutating code to test a check, confirm the check fails (every check was mutation-tested when written).
4. Report results as **"verified in code"**. Only a real run in Godot/Android counts as runtime verification.
