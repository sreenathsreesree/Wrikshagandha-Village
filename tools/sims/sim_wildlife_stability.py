#!/usr/bin/env python3
"""Butterfly height stability (a pre-existing numerical bug, found by M09.3's regression; not part of the weather) —
the real height step read from wildlife_butterfly.gd and executed:
    position.y = lerp(position.y, target_height, <factor>)
A lerp factor above 1 overshoots, and above 2 every step grows the error: before the fix (`4.0 * delta`) any frame
longer than 0.5 s sent the butterflies' height to infinity (the regression's 5× whole-day run saw ~19,500
non-finite transforms). With the factor clamped to 1, for every frame length — normal frames, exactly 0.5 s, just
over it, the ≈2.2 s frames of the 5× run, up to 1,000 s — and every start height and target (hover and land), the
height stays finite, never leaves the range between where it was and its target, and settles on the target. The
unclamped design is shown to break.
"""
import math, os, re

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = open(os.path.join(REPO, "scripts", "world_simulation", "wildlife_butterfly.gd"), encoding="utf-8").read()
HOVER = float(re.search(r"^@export var hover_height: float = ([0-9.]+)$", SRC, re.M).group(1))
LAND = float(re.search(r"^@export var land_height: float = ([0-9.]+)$", SRC, re.M).group(1))
lines = re.findall(r"^\tposition\.y = lerp\(position\.y, target_height, (.+)\)$", SRC, re.M)
assert len(lines) == 1, f"the butterfly's height has one lerp step (found {lines})"
FACTOR = lines[0]

def step_fn(factor_src):
    expr = factor_src.replace("minf(", "min(").replace("maxf(", "max(").replace("clampf(", "_clamp(")
    f = eval("lambda delta: " + expr, {"min": min, "max": max, "_clamp": lambda v, a, b: max(a, min(b, v))})
    return lambda y, target, delta: y + (target - y) * f(delta)     # Godot's lerp(a, b, t) = a + (b - a) * t

DELTAS = [1 / 120, 1 / 60, 1 / 30, 0.1, 0.25, 0.4999, 0.5, 0.5001, 0.6, 1.0, 2.0, 2.2, 5.0, 10.0, 100.0, 1000.0]
STARTS = [0.0, LAND, HOVER, -3.0, 25.0, 1e6]

def problems(step):
    p = []
    for target in (HOVER, LAND):
        for start in STARTS:
            for delta in DELTAS:
                y = start
                lo, hi = min(start, target), max(start, target)
                for _ in range(2000):
                    y = step(y, target, delta)
                    if not math.isfinite(y):
                        p.append(f"delta {delta}: height non-finite from {start} towards {target}"); break
                    if y < lo - 1e-9 or y > hi + 1e-9:
                        p.append(f"delta {delta}: height {y:.4g} left [{lo}, {hi}] from {start} towards {target}"); break
                else:
                    if abs(y - target) > 1e-6:
                        p.append(f"delta {delta}: height {y} never settled on {target} from {start}")
                if len(p) > 3: return p
    # alternating hover / land (pause and fly) on long frames, as the butterflies do
    y = HOVER
    for k in range(5000):
        y = step(y, LAND if k % 3 == 0 else HOVER, 2.2)
        if not math.isfinite(y) or not (min(LAND, HOVER) - 1e-9 <= y <= max(LAND, HOVER) + 1e-9):
            p.append(f"alternating targets at 2.2 s frames: height {y}"); break
    return p

bad = problems(step_fn(FACTOR))
assert not bad, f"the butterfly height step `lerp(position.y, target_height, {FACTOR})` is unstable: {bad}"
broken = problems(step_fn("4.0 * delta"))   # the line before the fix
old, y = step_fn("4.0 * delta"), HOVER
for frames_to_inf in range(1, 2001):         # at the 5x run's ≈2.2 s frames it runs away to infinity
    y = old(y, LAND, 2.2)
    if not math.isfinite(y): break
assert broken and not math.isfinite(y), "the unclamped factor is shown to break and to diverge"
print(f"butterfly height: lerp factor `{FACTOR}`; hover {HOVER} / land {LAND}; {len(DELTAS)} frame lengths up to {DELTAS[-1]:.0f} s x "
      f"{len(STARTS)} starts x 2 targets x 2000 frames, plus alternating targets at 2.2 s frames: always finite, never overshoots, settles; "
      f"the unclamped `4.0 * delta` shown to break ({broken[0]}) and to reach infinity after {frames_to_inf} frames of 2.2 s")
print("ALL WILDLIFE STABILITY SIMULATIONS PASSED")
