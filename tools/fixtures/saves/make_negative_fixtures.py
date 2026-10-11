#!/usr/bin/env python3
"""The two constructed negative fixtures (M15.3), derived deterministically from the real v8 fixture. No build has
ever written either, by design:
  newer/save.json      the v8 save stamped one version past the build's SAVE_VERSION (read from save_manager.gd) with
                       one section no build knows — a save from a newer build, which must be neither loaded nor
                       overwritten (renamed from v9_newer by M14.1a, when v9 became a real format);
  malformed/save.json  the v8 save cut off half way — a damaged file, which must be ignored without a crash.
Rerun after every SAVE_VERSION bump. Usage: python3 tools/fixtures/saves/make_negative_fixtures.py
"""
import json, os, re
here = os.path.dirname(os.path.abspath(__file__))
sm = open(os.path.join(here, "..", "..", "..", "scripts", "autoload", "save_manager.gd"), encoding="utf-8").read()
save_version = int(re.search(r"^const SAVE_VERSION := (\d+)", sm, re.M).group(1))
v8 = open(os.path.join(here, "v8", "save.json"), encoding="utf-8").read()
newer = json.loads(v8)
newer["save_version"] = save_version + 1
newer["future_section"] = {"from": "a newer build"}
os.makedirs(os.path.join(here, "newer"), exist_ok=True)
with open(os.path.join(here, "newer", "save.json"), "w", encoding="utf-8") as f:
    f.write(json.dumps(newer, separators=(",", ":"), sort_keys=True))
os.makedirs(os.path.join(here, "malformed"), exist_ok=True)
with open(os.path.join(here, "malformed", "save.json"), "w", encoding="utf-8") as f:
    f.write(v8[: len(v8) // 2])
print(f"negative fixtures written from v8/save.json (newer stamped {save_version + 1})")
