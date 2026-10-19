# Wrikshagandha — Device Playtest Pack (T1)

The runtime checks that the master production plan still owes, regrouped into short sessions that can be run on a
phone (and, for the visual sessions, on a PC). Nothing here is new behaviour or a new acceptance rule: every test
restates a milestone's **Runtime test** / **Done when** text from `docs/WRIKSHAGANDHA_MASTER_PRODUCTION_PLAN.md` (the
plan), a decision in `docs/DESIGN_DECISIONS.md`, or the M01.6 checklist, and names its source. Where the source is
missing or ambiguous, the test says so (**⚠ open decision** or **⚠ open procedure**, all gathered under *Open decisions*
below) instead of guessing.

- **Authoritative list:** the plan. A milestone marked `[~]` (implemented, needs runtime testing), the M01.6 gate and the
  organic art stages B0/B0.1 must each appear in the coverage index at the end; `tools/playtest/check_pack.py`
  (run by `tools/run_all.sh`) fails if one is missing or if the index names a milestone the plan doesn't have.
- **The full gate takes several sittings.** Each session is meant to take 15–30 minutes. Run S0 once, S1 at the start
  of every sitting, then any of S2–S7 in any order.
- **Godot / Android only.** Desktop runs already done (headless probes, simulations, `run_all.sh`) are recorded in the
  plan; they are *not* device acceptance and are not repeated here.
- **The checker checks coverage only.** `check_pack.py` proves every owed milestone has a test listed here; it never
  marks anything verified. Only the developer's reported results do (plan §7).

## How to record results

Copy this file (or the session you are running), fill in each test's **Result** line, and send it back. For every test:

- **Result:** `Pass`, `Fail` or `Not tested` — never leave it blank. *Not tested* is the honest answer when the device,
  the editor or the time didn't allow it.
- **Notes:** what you saw, especially for a Fail (what you did, what happened, how often).
- **Evidence (when practical):** a screenshot or short screen recording for anything visual or intermittent; the
  build/commit you ran (S0.3); the phone model and Android version (S0.1).

**When can a milestone move from `[~]` to `[x]`?** Only on the developer's report (plan §7), and only when **every**
test that lists it in the coverage index is `Pass` on the device the milestone names (Android for the Phase 16 gate;
PC as well where a test says so). **Android means an exported Godot 4.7.x Android build installed on the phone**
(Route B below, plan §7 policy); results from a Godot editor running on the phone (Route A) are **preliminary** and
never count as final acceptance — record the route with every result. A `Fail` keeps it `[~]` with the failure noted in the plan; a `Not tested` keeps it
`[~]`. A milestone touched by an **⚠ open decision** needs the developer to settle it first. M01.6 itself
is done when its results are reported and the default movement mode is recorded in `DESIGN_DECISIONS.md` (O-06).

## Where each test can run

Every test has a **Needs:** line. Run a test only if you have everything it needs; otherwise record
`Not tested — needs <what is missing>`. Never record `Pass` for a part you could not check.

| Tag | What it means |
|---|---|
| **Phone** | The game running on an Android phone. **Final acceptance:** an APK exported with Godot 4.7.x and installed on the phone (Route B). **Preliminary only:** the game run inside a Godot 4.7.x editor on the phone (Route A). Once the build is on the phone, the phone alone is enough. |
| **Editor output** | The Godot editor's Output panel for the running game (on the phone's editor, or on a PC). An installed APK shows no output. |
| **PC editor** | The Godot **4.7.2** editor on a PC (keyboard and mouse tests; PC-GPU visuals; temporary prints). |
| **Remote debugger** | The editor's debugger attached to the running game (Remote scene tree, Monitors, the ability to call a method). Available when the game is run from a PC editor — on the PC itself, or deployed to the phone over USB/Wi-Fi (which also needs the **Export environment**); whether the phone's own editor offers it is **not established** here — check before relying on it. |
| **Save access** | Reading or editing `user://save.json`. On a PC: the editor's *Project → Open User Data Folder*. No on-phone procedure is established (see S0.5). |
| **Export environment** | A PC with Godot 4.7.2, its export templates and the Android SDK, to build APKs (including older builds for upgrade tests). |

---

## S0 — Setup (once; ~20 min plus import time)

Downloading the GitHub ZIP is **not enough by itself**: the project needs a Godot **4.7.x** editor (it declares 4.7 in
`project.godot`, `config/features`; every desktop check ran on **4.7.2**) or an APK built with Godot 4.7.2. An older
editor (for example 4.3) is not supported and must not be used for results. There are two routes:

- **Route B — exported APK (required for final acceptance):** export with the project's Android preset
  (`export_presets.cfg`: arm64-v8a, `com.wrikshagandha.village`, `build/android/Wrikshagandha.apk`, version 0.1.0) using
  Godot 4.7.x (4.7.2 was used for every desktop check), its export templates and the Android SDK (**Export
  environment**), then install the APK on the phone. The project has never been exported; the first export is itself
  unverified.
- **Route A — Godot editor on the phone (preliminary only):** a Godot 4.7.x editor for Android opens the project folder
  and runs it on the phone. Useful for early findings, but by the developer's policy (plan §7) it **never counts as
  final Android acceptance**. Whether a 4.7.x Android editor build is available to you is **not established by this
  repository** — confirm the exact version first (S0.2); an older editor must not be used at all.
- **Record the route (A or B) with every result.** A Route A `Pass` is written as `Pass (preliminary, Route A)` and leaves
  the milestone `[~]`.

**S0.1 Device facts** (all)
- Needs: Phone.
- Steps: note the phone model, Android version, screen size/aspect, and whether it has a notch/cut-out or gesture bar.
- Expected: recorded.
- Result: ______ Notes: ______

**S0.2 Godot version and route** (M00.5)
- Needs: Route A — the phone's editor; Route B — PC editor and Export environment.
- Steps: note the route (A or B) and the exact Godot version (the editor's About screen, or the version used to export).
- Expected: Godot 4.7.x (record the exact version; 4.7.2 was used for every desktop check). Any other version: stop and
  record the phone sessions as *Not tested*.
- Result: ______ Route: ______ Version: ______

**S0.3 Get the project** (all)
- Needs: Route A — the phone; Route B — the PC.
- Steps: on GitHub open branch `prototype/organic-world` → **Code → Download ZIP**; note the commit hash GitHub shows
  for the branch; extract the ZIP (Route A: to phone storage; Route B: on the PC).
- Expected: the folder contains `project.godot`. The Living Pond Edge (W1, S6) is included from commit `ca9b3b0` on.
- Result: ______ Commit tested: ______

**S0.4 First import** (M00.5)
- Needs: Editor output (Route A on the phone, or the PC editor).
- Steps: open the folder as a project in the Godot editor; wait for the first import to finish; open the Output panel.
- Expected: the project opens with **no errors** (M00.5's runtime test; M01.6's first item).
- Evidence: a screenshot of the Output panel after import; the import time.
- Result: ______ Notes: ______

**S0.5 Fresh start vs. existing save** (all)
- Needs: Phone (to note it); Save access to inspect or reset it.
- Steps: note whether this is a first run (no save) or continues a save from an earlier build.
- Facts: the game keeps one save, `user://save.json`, in app-private storage on Android (`scripts/autoload/save_manager.gd`);
  the game has **no in-game "new game" or reset** button.
- ⚠ **Open procedure (developer):** the plan gives no on-phone way to inspect or reset the save. For an installed APK
  (Route B), Android's own *Settings → Apps → (the game) → Storage → Clear storage* removes the app's private data and
  so starts a fresh game — an Android feature, not one the project provides; it deletes **all** progress. For Route A
  the game's data lives inside the editor app, and no reset procedure is established. Tests that need a fresh game or
  an edited save: record *Not tested — needs Save access* when you can't do it.
- Result: ______ Notes: ______

---

## S1 — Smoke test (start of every sitting; ~15 min)

**S1.1 Launch** (M00.5, M03.1)
- Needs: Phone; Editor output for the "no errors" part.
- Steps: run the main scene (`Main.tscn`).
- Expected: no errors or warnings in Output (no missing nodes, no "node not found"); the player starts at the spawn;
  the camera follows; the HUD shows (M03.1's walk-through, first items).
- If the game runs as an APK there is no Output: record the "no errors or warnings" part as *Not tested — needs Editor
  output* and the rest from what you see.
- Result: ______ Notes: ______

**S1.2 Landscape and safe area** (M07.4, M06.3)
- Needs: Phone.
- Steps: hold the phone landscape one way, then the other.
- Expected: the game turns with it (sensor landscape); nothing overlaps the notch, status bar or gesture bar; thumb
  controls are clear of cut-outs (M07.4's runtime test).
- Note: M06.3 was built for the portrait canvas of its time; **D-30** (locked product decision, M07.4) states "no
  portrait design" and supersedes D-26's "1080 × 1920 portrait canvas". The plan's M06.3 row now says "landscape" with
  that history, and M06.3 is checked in landscape here.
- Result: ______ Notes: ______

**S1.3 Move and tap** (M01.2, M01.3)
- Needs: Phone.
- Steps: drag the floating joystick on the left half; then tap the ground a few metres away.
- Expected: the player walks and turns smoothly; a ground tap walks there.
- Result: ______ Notes: ______

**S1.4 Collect one discovery** (M02.1, M04.3)
- Needs: Phone.
- Steps: tap a flower or mushroom.
- Expected: the player walks to it and collects it: windup, burst, points, journal entry, removal (M02.1).
- Result: ______ Notes: ______

**S1.5 Quick frame-rate note** (S7)
- Needs: Phone.
- Steps: watch the meadow for 30 s.
- Expected: record the impression (smooth / occasional stutter / slow); exact numbers go in S7.
- Result: ______ Notes: ______

---

## S2 — Movement (core of M01.6; ~25 min)

Source: the M01.6 checklist and the movement milestones' runtime tests.

**S2.1 Joystick** (M01.6, D-58)
- Needs: Phone.
- Steps: drag on the left half, push in all directions, release.
- Expected: moves and turns smoothly; the ring appears where the finger landed once the drag passes ~24 px; releasing
  stops (D-58).
- Result: ______ Notes: ______

**S2.2 Movement toggle** (M01.6, D-15/D-58)
- Needs: Phone.
- Steps: switch the Movement mode with its HUD button and back.
- Expected: modes switch; in Tap to Move no joystick appears.
- Result: ______ Notes: ______

**S2.3 Tap-to-move routes** (M01.3, M07.3, M08.2a)
- Needs: Phone.
- Steps: tap distant ground behind trees, rocks, logs and the monolith; tap the house door and the NPC spot from the start.
- Expected: paths go around obstacles and reach every destination without stalls (M08.2a); mound steps are climbable;
  the pond has a walkable shallow edge and a blocked core (D-28, M07.3).
- Note (known issue, M01.6): the player occasionally gets stuck or spins — note when, it belongs to a later pass.
- Result: ______ Notes: ______

**S2.4 Retarget and cancel** (M01.4)
- Needs: Phone.
- Steps: tap ground, then tap elsewhere while walking; tap the player while walking; tap the player while it walks to
  an object; tap ground just beside the player.
- Expected: a tap while walking retargets; tapping the player stops the walk and cancels the pending interaction; no
  jitter step beside the player (M01.4).
- Result: ______ Notes: ______

**S2.5 Taps that must not move the player** (M01.6, M03.5)
- Needs: Phone.
- Steps: tap HUD buttons, open screens and the seed picker; drag on the world (outside the joystick); pinch.
- Expected: none of these move the player; a pinch never moves the player (M03.5).
- Result: ______ Notes: ______

**S2.6 Facing on arrival** (M02.3)
- Needs: Phone.
- Steps: tap a distant discovery; a distant farm plot; an object beside the player; targets behind, left and right;
  cancel before arrival; replace the target while walking.
- Expected: the M01.6 "M02.3 facing" list — stops in range, faces the target, interacts; no sideways movement or new
  spinning; a cancelled target is never faced; only the final target is faced.
- Result: ______ Notes: ______

**S2.7 Tap feedback and small objects** (M02.4)
- Needs: Phone.
- Steps: tap a flower and a plot; an unavailable object (locked plot, mid-harvest); exact, off-centre and near-miss taps
  on small objects, between two objects, beside a rock.
- Expected: the M01.6 "M02.4" lists — the indicator shows at once and stays until the interaction starts; no misleading
  feedback on unavailable objects; no unexpected target selected; note misses on mushrooms/flowers (tolerance 0.45 m).
- Result: ______ Notes: ______

**S2.8 Camera bounds and zoom** (M03.4, M03.5)
- Needs: Phone.
- Steps: walk to each of the four ground edges; pinch in and out to both limits; zoom at an edge.
- Expected: the camera's focus stops at each edge without lurch, jitter or drift; pinch is smooth and stops firmly at
  7 m and 15 m; zooming at an edge doesn't move the focus. Note how much lies beyond the ground at each edge.
- Result: ______ Notes: ______

**S2.9 Animation states** (M01.5)
- Needs: Remote debugger (or the PC editor for a temporary print).
- Steps: watch the player's state — M01.5's runtime test connects a temporary print to `animation_state_changed` or
  watches `get_animation_state()` in the remote inspector.
- Expected: IDLE standing; WALK moving; INTERACT when collecting or tapping a plot; no IDLE/WALK flicker; pushing a rock reads IDLE.
- The state is not shown on screen (the plan names no visible cue), so it can't be judged by eye. Without the Remote
  debugger (or a PC editor for the temporary print, which must not be committed), record *Not tested — needs Remote
  debugger*.
- Result: ______ Notes: ______

**S2.10 Keyboard** (M01.2)
- Needs: PC editor (keyboard).
- Steps (desktop editor only): WASD/arrows, diagonals, release; after clicking a HUD button; in Tap to Move a key press.
- Expected: M01.2's desktop runtime test.
- Result: ______ Notes: ______

**S2.11 Load time** (M01.6)
- Needs: Phone (a stopwatch).
- Steps: note the time from pressing Run to being able to walk (the navigation mesh bakes at load).
- Result: ______ Seconds: ______

---

## S3 — Everyday systems (~30 min; split across sittings if needed)

**S3.1 Discoveries and respawn** (M02.1, M04.3, M05.3, M10.2)
- Needs: Phone.
- Steps: collect each of the 9 discoveries you can find; wait for a respawning one to return and collect it again.
- Expected: same windup, burst, sound, points, journal entry and removal; respawning ones respawn; reward cards show
  the amounts listed in M01.6's "M05.3 rewards" item.
- Result: ______ Notes: ______

**S3.2 Farm loop** (M02.1, M04.2, M04.4, M06.1, M06.4)
- Needs: Phone.
- Steps: prepare, plant (seed picker), water, wait, harvest at different qualities; try a locked plot and a plot mid-harvest.
- Expected: the M01.6 "M04.2" and "M04.4" items — seed counts drop, planting refused at 0, one seed back on harvest,
  basket rows/quality split update; locked and mid-harvest plots can't be tapped; first-seed / first-harvest / all-crops
  milestone cards as before (M06.4).
- Result: ______ Notes: ______

**S3.3 Inventory, basket and screens** (M04.5, M06.3, M07.4a, M07.4b)
- Needs: Phone.
- Steps: open 🎒 Inventory, 🧺 Basket, Collection, Journal, Daily and the seed picker; scroll; read at arm's length.
- Expected: readable landscape screens on the shared theme, touch targets usable by thumb, scrolling works, nothing
  under a notch or gesture bar; the picker docks between the thumb zones with the player in view.
- Result: ______ Notes: ______

**S3.4 Coins and selling** (M05.1, M05.5, M06.2)
- Needs: Phone.
- Steps: harvest; open the Basket; sell one quality.
- Expected: the harvest card shows points and "+1 seed", **no coins**; the Basket shows "Coins 0" before selling; selling
  adds coins (M06.2); points and coins never mix (M05.5).
- Result: ______ Notes: ______

**S3.5 Places and exploration rewards** (M03.6, M05.2, M10.1, M10.3)
- Needs: Phone.
- Steps: open the Journal's Places list; reach the Overlook and a secret place; find the Hidden Hollow by following its
  clue trail from the Secluded Pond Nook.
- Expected: the same places in the same order ("???" until visited); arrival cards and once-ever bonuses as in M01.6's
  "M05.2" item; the Hollow is found by observation (M10.3) and pays only its once-ever secret reward (M10.2).
- Result: ______ Notes: ______

**S3.6 House, interior and NPC** (M08.1, M08.2, M08.3, M08.4)
- Needs: Phone.
- Steps: tap the house door, walk the interior, leave; tap the villager and read the conversation (Next, Goodbye).
- Expected: the fade; enter/exit with world, farm and progress intact (M08.1); every interior spot reachable (M08.2);
  the speech panel shows the lines in order (M08.3/M08.4).
- Result: ______ Notes: ______

**S3.7 Request and service** (M08.5, M08.6, M08.7)
- Needs: Phone.
- Steps: collect 2 River Stones; accept and complete the villager's request; then trade 3 River Stones.
- Expected: offer → pending → "Give" → 20 points once (M08.6); afterwards the villager buys 3 stones for 6 coins,
  repeatably (M08.7); friendship rises once a day for a completed conversation (M08.5).
- Result: ______ Notes: ______

**S3.8 Routines, weather and reactions** (M09.1, M09.3, M09.4)
- Needs: Phone (about 10 minutes of watching).
- Steps: watch a full day (600 s) near the pond path and the NPC spot; note any rain.
- Expected: the villager is by the pond path morning/afternoon and at its spot dawn/evening/night (M09.1); weather is
  visible (M09.3); when rain begins, birds flee (M09.4).
- Result: ______ Notes: ______

**S3.9 Earth — Nurture** (M11.1)
- Needs: Phone.
- Steps: use the Earth plant by tap and by joystick approach; watch the full cycle; try a second interaction during it.
- Expected: M11.1's runtime test — the cycle plays, a second interaction during the cycle starts nothing, no change to
  points, coins, items, discoveries or the Journal. (Android was "deferred under the existing workflow" in the plan.)
- Result: ______ Notes: ______

**S3.10 Wildlife Journal** (M14.1a)
- Needs: Phone.
- Steps: walk up to a rabbit, a small bird and a butterfly; open the Journal's wildlife section.
- Expected: each species is recorded once, with no reward (D-59).
- Result: ______ Notes: ______

**S3.11 Regression-only milestones** (M01.1, M02.2, M02.5, M05.4, M05.6, M02.6)
- Needs: Nothing of its own — it is settled by the decisions below and the S1–S4 results.
- Expected: nothing to see of their own — the plan lists no runtime test (M01.1, M02.2, M02.5), "regression only"
  (M05.4) or "model only" (M05.6). They pass when S1–S4 pass with no regression.
- ⚠ **Open decision (developer) — M02.6:** its fixtures (`tools/fixtures/inspect_fixture.gd`, `open_fixture.gd`,
  `read_fixture.gd`) are never imported by Godot (`tools/.gdignore`) and are placed in no scene, so the plan's
  "Godot: tap each fixture" cannot be run on a phone or in the editor as the project stands; their verification so far
  is static (`check_project.py`) and modelled (`sim_interaction.py`). The plan calls M02.6 "an architecture proof, not
  player-facing gameplay". Whether that is enough, or a desktop test harness should be built first, is the developer's call.
- ⚠ **Open decision (developer) — regression-only and model-only rows:** plan §6 allows `[x]` without a runtime test
  only for milestones "with no runtime component (documentation, tooling)". M01.1, M02.2 and M02.5 change code but
  say "no runtime test of its own"; M05.4 is "regression only"; M05.6 is "model only". Whether each moves to `[x]` when
  S1–S4 pass with no regression, or under §6's no-runtime rule, is not settled in the plan.
- Result: ______ Notes: ______

---

## S4 — Persistence (~20 min)

**S4.1 Relaunch keeps progress** (M02.1, M04.2, M04.3, M05.2, M05.3, M08.5, M09.2, M14.1a)
- Needs: Phone.
- Steps: make progress (points, a collectible, a planted plot mid-growth, a visited place, a seen species, a
  conversation); close the app normally; relaunch.
- Expected: everything restored; the world time continues from where it was (M09.2, no time passes while closed);
  reaching the same places again pays nothing (M05.2); the Ancient Seed pays once ever (M05.3).
- Result: ______ Notes: ______

**S4.2 Force-stop keeps the moment** (M15.4, M14.1a, M05.6)
- Needs: Phone (Route B for Android's Force stop; or a PC with adb).
- Steps: reach a landmark (or collect a repeat discovery, or claim the daily bonus) and immediately force-stop the app
  (Android *Settings → Apps → (the game) → Force stop* — Route B; or `adb shell am force-stop com.wrikshagandha.village`
  from a PC); relaunch. On Route A, force-stopping stops the editor app itself; record what you did.
- Expected: the moment is kept with no double payment (M15.4); a species seen just before is still seen (M14.1a).
- Result: ______ Notes: ______

**S4.3 Area reload round-trip** (M03.2, M03.3)
- Needs: Remote debugger.
- Steps: M01.6's "M03.2/M03.3" item — from the remote debugger call `load_area(...)` on `/root/Main` with plots in
  different states.
- Expected: no errors; one Meadow; the player at the start; the camera snapped; every plot exactly as it was.
- The project has no in-game way to trigger this reload: the house door parks the Meadow and returns the same instance
  (D-33) — it does **not** unload and reload it — so a house trip is not a substitute. Without the Remote debugger,
  record *Not tested — needs Remote debugger*.
- Result: ______ Notes: ______

**S4.4 Old and malformed saves** (M04.0, M04.1, M05.1)
- Needs: (a) Export environment and an older APK with a save; (b)–(e) Save access (PC).
- Steps: M01.6's "M04.0 save versioning" items (a)–(e) and the M04.1/M05.1 regression lines.
- Expected: as listed there (old saves load; newer versions refused untouched; malformed sections start empty with a warning).
- (a) installs this build over an older (pre-M04.0) build that has a save, so it needs that older APK (**Export
  environment**) — not possible with Route A. (b)–(e) open or edit `user://save.json` (**Save access**), which the plan
  describes on desktop only. Record each part you can't do as *Not tested* with what it needs.
- Result: ______ Notes: ______

---

## S5 — Rest Mode (~25 min)

Source: E1 (D-48–D-57), the D-56 occupied-seat fix, D-58, and Rest Mode R1–R4 (D-62). Rest Mode is complete in
silence; the ambience heard is a **temporary technical placeholder** (`docs/AUDIO_ASSETS.md`).

**S5.1 Sit** (E1, D-62 R1/R2)
- Needs: Phone.
- Steps: tap the Pond Rest Spot from the path; also approach with the joystick and tap it.
- Expected: the player walks to the seat and sits facing the pond; the camera eases closer to 8 m; the non-essential HUD
  quiets; the Stand Up button and the mute button appear; the joystick hides.
- Result: ______ Notes: ______

**S5.2 Seated view controls** (D-62 R2/R3)
- Needs: Phone.
- Steps: pinch in and out; drag one finger on the world left and right (also on the left half of the screen).
- Expected: zoom stays within 7–10 m; the view turns at most ±45°; pitch never changes; a drag never stands the player.
- Result: ______ Notes: ______

**S5.3 Movement locked** (D-62 R1)
- Needs: Phone; PC editor for the keyboard part.
- Steps: while seated, try the joystick (none should appear) and, on desktop, the keyboard.
- Expected: no movement and no standing.
- Result: ______ Notes: ______

**S5.4 Exits** (D-62 R1, D-56)
- Needs: Phone.
- Steps: stand with the Stand Up button; sit again and stand by tapping the player; sit again and stand by tapping
  another interactable; sit again and tap the ground; sit again and tap the seat itself.
- Expected: Stand Up, the player tap and another object each stand the player; a ground tap is ignored; a tap on the
  occupied seat changes nothing (D-56 Option A). Known limit: the seat's shape wraps the seated player's lower body, so
  a tap there is a no-op, not a stand.
- Result: ______ Notes: ______

**S5.5 Restore before moving** (D-62 R1/R3)
- Needs: Phone.
- Steps: after standing, try to move immediately.
- Expected: movement and the joystick return only once the camera is fully back (distance, framing, angle), then
  directions match the screen.
- Result: ______ Notes: ______

**S5.6 Every sit starts fresh** (D-62 R2/R3)
- Needs: Phone.
- Steps: sit, zoom and turn the view, stand, sit again.
- Expected: each sit starts again at 8 m and the default angle.
- Result: ______ Notes: ______

**S5.7 Ambience and mute** (D-62 R4)
- Needs: Phone (sound on).
- Steps: sit and listen; mute and unmute; stand; sit again while muted; stand and sit again during the fade-out; force
  a relaunch.
- Expected: the ambience fades in on sitting and out on standing; mute silences and restores it; the mute lasts for the
  session (also across sits) but a relaunch starts unmuted; sitting again mid-fade continues the same sound.
- ⚠ **Open decision (blocked on an asset):** **listening acceptance is not possible yet** — the placeholder is not the intended sound and no
  licensed recording exists. Record whether the mechanics work; leave "sounds right" for the licensed recording.
- Result: ______ Notes: ______

**S5.8 The world carries on; nothing saved** (D-48, D-51, D-52, D-62)
- Needs: Phone.
- Steps: stay seated for a minute; then relaunch.
- Expected: time, weather, wildlife and the villager carry on while seated; no reward; the relaunch starts standing.
- Result: ______ Notes: ______

**S5.9 Floating joystick details** (D-58)
- Needs: Phone.
- Steps: a short (<24 px) drag on the left half; a long drag; a second finger during a joystick drag; switch mode mid-drag.
- Expected: a short drag shows nothing and a tap walks; past 24 px the ring appears at the touch-down point; a second
  finger doesn't become a second joystick; a mode switch ends the joystick. Note any problem with cut-outs or the left-half split.
- Result: ______ Notes: ______

---

## S6 — Visual review: Pond Edge (W1) and the organic art (B0, B0.1) (~20 min; phone **and** PC)

Source: D-63, D-60, D-61. These criteria are visual judgements: the plan gives **no numeric visual threshold**, and this
pack adds none — the developer's judgement decides (⚠ open decision). The PC results need the **PC editor** (a PC GPU);
the phone results need **Phone**. Record each separately; one doesn't stand in for the other.

**S6.1 Shoreline** (W1)
- Needs: Phone and PC editor (separate results).
- Steps: stand by the pond at the default zoom and at 7 m and 15 m, in daylight and at dusk.
- Expected: the pond's edge reads as a natural, irregular wet-earth shore; no hard circular rim; the path runs into the
  bank with no visible seam.
- Evidence: screenshots.
- Result (phone): ______ Result (PC): ______ Notes: ______

**S6.2 Shimmer and flicker** (W1)
- Needs: Phone and PC editor (separate results).
- Steps: walk slowly round the pond and zoom in and out.
- Expected: no shimmer, flicker or z-fighting along the lip at the water's edge or where the bank meets the path.
- Result (phone): ______ Result (PC): ______ Notes: ______

**S6.3 Seated view** (W1, E1)
- Needs: Phone and PC editor (separate results).
- Steps: sit at the Pond Rest Spot; turn the view to −45°, 0° and +45°.
- Expected: the water stays open from the seat; the reeds, tufts and stones read as a far bank; the near (south) side stays low.
- Known limit (D-63): the bank stands up to 0.085 m above the ground at the water's edge, so feet sink slightly there.
- Result (phone): ______ Result (PC): ______ Notes: ______

**S6.4 Organic trees, rocks, ground and paths** (B0, B0.1)
- Needs: Phone and PC editor (separate results).
- Steps: look over the meadow and the forest edges.
- Expected: the organic props, ground patches and worn paths read well at the game camera (D-60/D-61 "visual review").
- Result (phone): ______ Result (PC): ______ Notes: ______

---

## S7 — Performance notes (~15 min)

No numeric frame-rate, load-time or battery target exists in the plan (risk A8: "runtime navmesh bake cost unknown on
device — Phase 01 test, Phase 16"), and this pack adds none (⚠ open decision for the developer). Record what you
observe; the figures inform a later target, they don't pass or fail anything yet. Figures from a Route A (editor on the
phone) run are preliminary and may differ from an exported build.

**S7.1 Frame rate** (M01.6, A8, W1)
- Needs: Phone for an impression; Remote debugger for figures.
- Steps: note the frame rate at the spawn, by the pond, while seated, in the house, and during rain.
- The game has **no built-in frame-rate display**; figures need the editor debugger's Monitors (**Remote debugger**). On
  the phone alone, record only your impression (smooth / occasional stutter / slow) and mark the figures *Not tested*.
- Result: ______ Figures: ______

**S7.2 Load and import times** (M01.6, A8)
- Needs: Phone (a stopwatch); Editor output for the import time.
- Steps: note the first-import time (S0.4) and the run-to-walkable time (S2.11).
- Result: ______ Figures: ______

**S7.3 Heat and battery** (A8)
- Needs: Phone.
- Steps: after 15 minutes of play, note whether the phone is warm and the battery drop.
- Result: ______ Notes: ______

---

## Open decisions and unsupported procedures

Nothing below is guessed or settled by this pack. Each item names who or what must resolve it; until then the tests it
touches stay *Not tested* (or are recorded with the route used) and their milestones stay `[~]`.

| # | Item | Affects | Evidence | Resolved by |
|---|---|---|---|---|
| 1 | ~~Does a run inside the Android editor count as acceptance?~~ **Resolved:** final Android acceptance needs an exported Godot 4.7.x build (Route B); editor-on-phone runs (Route A) are preliminary only | All phone tests; S7 | Plan §7 "Android acceptance" policy (developer, T1) | Resolved by the developer |
| 2 | Whether a Godot 4.7.x editor for Android is available to the tester | Route A (preliminary runs only) | Not established by the repository | Tester confirms the version (S0.2) |
| 3 | No on-phone way to inspect or reset `user://save.json`; the game has no reset; Android's *Clear storage* works only for an installed APK (Route B) | S0.5, S4.4 and any "fresh game" step | `save_manager.gd` (`user://save.json`); no reset in `scripts/` | Developer: accept *Clear storage* for Route B, or provide a procedure/tool |
| 4 | Remote-debugger-only checks; whether the phone's editor offers the debugger is not established | S2.9 (M01.5), S4.3 (M03.2, M03.3), S7.1 figures | M01.5 and M03.2/M03.3 runtime tests; the house door parks the Meadow (D-33), so it can't replace the reload | Run from a PC editor (on PC or deployed to the phone), or the developer accepts another method |
| 5 | M04.0 save tests need an older APK (a) and desktop save editing (b)–(e) | S4.4 (M04.0, M04.1, M05.1) | M01.6 "M04.0 save versioning" item: "Android for (a) only" | Export environment + PC; else *Not tested* |
| 6 | ~~M06.3's row said "portrait"~~ **Resolved:** the row now reads "landscape", noting it was built for the portrait canvas of the time and that D-30 superseded it | S1.2, S3.3 | D-30 text; the plan's M06.3 row | Resolved by the developer (wording corrected; no implementation change) |
| 7 | M02.6 fixtures can't be tapped anywhere as the project stands | S3.11 | `tools/fixtures/*_fixture.gd`, `tools/.gdignore`; M02.6 "architecture proof" | Developer: accept the static/model verification, or commission a desktop harness |
| 8 | Regression-only / model-only milestones (M01.1, M02.2, M02.5, M05.4, M05.6) have no stated verification method for `[x]` | S3.11 | Plan §6 status rules; their rows | Developer decision |
| 9 | No numeric frame-rate, load-time or battery targets | S7 | Risk A8 ("Phase 01 test, Phase 16") | Developer sets targets after the first figures |
| 10 | No numeric visual thresholds for W1, B0, B0.1 | S6 | D-60, D-61, D-63 ("visual review") | Developer's visual judgement |
| 11 | Rest Mode listening acceptance needs a licensed nature recording (a temporary technical placeholder plays) | S5.7 | D-62 R4, `docs/AUDIO_ASSETS.md` | Developer obtains a recording with verified source and licence |
| 12 | M11.1's plan text defers Android "under the existing workflow" | S3.9 | M11.1 runtime-test requirement | Developer: whether its `[x]` needs the device test |

---

## Coverage index

Every milestone the plan still owes a runtime test, and where it is tested. `tools/playtest/check_pack.py` reads this
block.

```playtest-coverage
M00.5 S0.2 S0.4 S1.1
M01.1 S3.11
M01.2 S1.3 S2.10
M01.3 S1.3 S2.3
M01.4 S2.4
M01.5 S2.9
M01.6 S0 S1 S2 S3 S4 S7
M02.1 S1.4 S3.1 S3.2 S4.1
M02.2 S3.11
M02.3 S2.6
M02.4 S2.7
M02.5 S3.11
M02.6 S3.11
M03.1 S1.1
M03.2 S4.3
M03.3 S4.3
M03.4 S2.8
M03.5 S2.5 S2.8
M03.6 S3.5
M04.0 S4.4
M04.1 S4.4
M04.2 S3.2 S4.1
M04.3 S1.4 S3.1 S4.1
M04.4 S3.2
M04.5 S3.3
M05.1 S3.4 S4.4
M05.2 S3.5 S4.1
M05.3 S3.1 S4.1
M05.4 S3.11
M05.5 S3.4
M05.6 S3.11 S4.2
M06.1 S3.2
M06.2 S3.4
M06.3 S1.2 S3.3
M06.4 S3.2
M07.2 S2.3
M07.3 S2.3
M07.4 S1.2
M07.4a S3.3
M07.4b S3.3
M08.1 S3.6
M08.2 S3.6
M08.2a S2.3
M08.3 S3.6
M08.4 S3.6
M08.5 S3.7 S4.1
M08.6 S3.7
M08.7 S3.7
M09.1 S3.8
M09.2 S4.1
M09.3 S3.8
M09.4 S3.8
M10.1 S3.5
M10.2 S3.1 S3.5
M10.3 S3.5
M11.1 S3.9
M14.1a S3.10 S4.1 S4.2
M15.4 S4.2
E1 S5.1 S5.4 S6.3
W1 S6.1 S6.2 S6.3 S7.1
B0 S6.4
B0.1 S6.4
```
