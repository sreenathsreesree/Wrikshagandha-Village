extends RefCounted
class_name PhysicsLayers

## The project's named 3D physics layers (Project Settings → Layer Names →
## 3D Physics) — the one place in code where layer numbers live. Scenes set
## layers in the inspector, where these names show; scripts use the masks
## below instead of numbers. tools/check_project.py fails if a *_LAYER here
## stops matching its name in project.godot, or if a script uses a numeric
## mask anywhere else.

## Layer numbers (1-based, as shown in the editor).
const WORLD_LAYER := 1
const INTERACTABLES_LAYER := 3

## Bit masks for physics queries and collision masks.
## world: the ground and everything solid the player can't walk through.
const WORLD := 1 << (WORLD_LAYER - 1)
## interactables: every Interactable Area3D (discoveries, farm plots).
const INTERACTABLES := 1 << (INTERACTABLES_LAYER - 1)
