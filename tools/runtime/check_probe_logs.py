#!/usr/bin/env python3
"""Verdicts for the Rest Spot runtime probe (P0.2), from the logs run_rest_spot_probe.sh writes.

The probe itself (rest_spot_probe.gd.in) only reports: each phase prints "R <id> | <facts>" lines and never decides
pass or fail. This script adds the verdicts, in two layers:

1. Contract checks (pass/fail). For each phase: the log exists, the phase finished ("R done"), no SCRIPT ERROR, and a
   few of its existing R lines carry the E1 rest-spot contract (D-48–D-58) as recorded in the plan's E1 results —
   e.g. the camera settles to the spot's preset and restores the exact base distance and offset after standing at
   7, 9.3, 11, 13.7 and 15 m and after every interruption order; a ground tap and the wheel change nothing while
   seated; the occupied seat is a no-op; sitting saves nothing and pays nothing; a relaunch starts standing. Only
   facts that hold run to run are checked; timing-sensitive details are not (see layer 2).
2. Baseline comparison (information). With --baseline <logs>, each phase's R lines are compared with a run of the
   same probe on another tree, numbers ignored (as in the earlier regressions). Differences are listed, not failed:
   some steps vary with timing at the probe's ~7.5 fps (E1E's second tap, E1I's trace, E1K taps held past the
   450 ms tap limit registering as "none").

The expectations describe today's contract: a milestone that changes it deliberately updates them — R1 (D-62, Rest
Mode controls) did: E1A/E1B/E1K expect seated movement ignored, the joystick hidden and Stand Up; E1T is new. R2 (D-62,
closer view and bounded pinch) did too: the settled preset is 8 m (E1A, E1C), the seated wheel zooms within 7–10 m (E1A),
E1E names whichever object it tapped (the closer view leaves the villager off screen) and requires its interaction to run;
E1Z is new. R3 (D-62, seated yaw) adds E1Y. R4 (D-62, rest ambience) adds E1M and a mute before E1S's save, checked
unmuted after E1R's relaunch.
Usage: check_probe_logs.py <log dir> [--phases "E1A E1C …"] [--baseline <log dir>]   (exit 1 when any check fails)
"""
import os, re, sys

PHASES = ["E1A", "E1B", "E1C", "E1D", "E1E", "E1F", "E1G", "E1H", "E1I", "E1J", "E1K", "E1T", "E1Z", "E1Y", "E1M", "E1S", "E1R"]
N = r"-?\d+(?:\.\d+)?"
SETTLED = r"zoom 8\.0000 offset \(2\.0000, -2\.0000\)"           # the Pond Rest Spot's preset (D-49; 8 m since D-62 R2)
BASE = r"zoom 11\.0000 offset \(0\.0000, 0\.0800\)"              # the default follow camera

# phase -> [(what, regex that some R line must match)]
EXPECT = {
    "E1A": [("the camera settles to the spot's preset", rf"^R E1 cam settle \|.*{SETTLED}"),
            ("the world carries on while seated (clock, no pause, normal speed)", r"^R E1A world \|.*paused false; time_scale 1\.00; still seated true"),
            ("a ground tap while seated keeps the player seated", r"^R E1A ground tap \|.*after: state 3;"),
            ("the wheel zooms while seated, within the seated range (D-62 R2)", r"^R E1A wheel \|.*zoom 8\.0000 -> 7\.2727"),
            ("tapping the occupied seat changes nothing (D-56)", r"^R E1A seat tap \|.*-> interact\(PondRestSpot\); after: state 3;"),
            ("the HUD is quiet, the joystick hidden, Stand Up shown and movement locked while seated (D-62)",
             r"^R E1A hud \| topbar a=0\.00 buttons a=0\.00;.*mobile controls visible false.*; stand up visible true; movement locked true$"),
            # Not "save mtime unchanged": since M14.1a a first wildlife sighting saves at once, and E1A sits 30 s by the
            # pond — the file may be written by a sighting. That sitting itself is never saved is E1S's check.
            ("sitting pays nothing (no points, coins, items or discoveries)", r"^R E1A side effects \|.*changed by sitting false;")],
    # D-62 (R1): joystick and keyboard movement no longer stand a seated player; the Stand Up button does.
    "E1B": [("joystick movement while seated neither stands nor moves the player (D-62)",
             r"^R E1B joystick \| seated before true; joystick held 32 physics frames: after 1 frame seated true; speed after 2 frames 0\.00; moved 0\.000 m; camera unchanged true; after: state 3;"),
            ("keyboard movement while seated neither stands nor moves the player (D-62)",
             r"^R E1B keyboard \| move_up while seated: seated after 2 frames true; moved 0\.000 m; camera unchanged true; after: state 3;"),
            ("the Stand Up button stands the player; its touch is no world tap", r"^R E1B stand up \| Stand Up -> pressed, world events none; after: state 0;"),
            ("the camera returns to its base after Stand Up", rf"^R E1 cam release \|.*{BASE}"),
            ("a joystick approach then a seat tap sits", r"^R E1B joystick approach \|.*seated: state 3;")],
    "E1C": [(f"exact restore after standing at {z} m", rf"^R E1C zoom {re.escape(z)} \|.*settled zoom 8\.0000 offset \(2\.0, -2\.0\); stand tap -> stop; "
             rf"restored zoom {N} \(exact true\) offset \({N}, {N}\) \(exact true\); seated false") for z in ("7.0", "9.3", "11.0", "13.7", "15.0")],
    "E1D": [("standing mid-settle restores the exact base", r"^R E1D stand mid-settle \|.*\(exact true\) offset exact true; seated false"),
            ("sitting again mid-release, then standing, ends at the exact base", r"^R E1D sit mid-release \|.*final zoom 11\.000000 \(exact true\) offset \(0\.0000, 0\.0800\) exact true; seated false"),
            ("five cycles end at the exact base", r"^R E1D 5 cycles \| zoom 11\.000000 \(exact true\) offset \(0\.000000, 0\.080000\) exact true; seated false")],
    # The probe taps the nearest available object on screen: the villager at the old 12 m view, a WildMint at R2's closer
    # 8 m view (the villager is then off screen) — so the check names whichever object was tapped and requires that very
    # object's interaction to run (INTERACT entered) after standing.
    "E1E": [("tapping another object while seated stands and carries on with it (its own interaction runs)",
             r'^R E1E other object \| tap (\w+) \([^)]*\) while seated -> interact\(\1\); seated false; events \["state 3->0@[^"]*", "seat_ended\(true\)@[^"]*",.*"state 1->2@')],
    "E1F": [("an area swap while seated stands the player; indoors uses the interior's distance", r"^R E1F swap in while seated \| area HomeInterior; seated false; zoom 7\.5000 offset \(0\.0000, 0\.0800\)"),
            ("the HUD is back indoors", r"^R E1F hud indoors \| topbar a=1\.00 buttons a=1\.00;"),
            ("back outside, the player's own zoom is exact", r"^R E1F back outside \| area Meadow; seated false; zoom 11\.0000 offset \(0\.0000, 0\.0800\) \(pre-sit zoom 11\.0 exact true\)")],
    "E1G": [("a repeated seat tap while walking keeps the sit (D3)", rf"^R E1G D3 repeat \|.*still pending true; seated after {N} s"),
            ("a ground tap while walking gives the sit up", r"^R E1G ground while pending \| pending true; .*-> seated false, pending false"),
            ("the joystick while walking gives the sit up", r"^R E1G joystick while pending \| pending true; .*-> seated false, pending false")],
    "E1H": [("the seat stays in the interaction zone while seated", r"^R E1H seated \| nearby \[PondRestSpot\]; seat available true")],
    "E1I": [],  # a trace (standing to collect a nearby discovery): compared with a baseline only
    "E1J": [("taps on the occupied seat change nothing", r'^R E1J seat taps \| 3 taps on the occupied seat -> \["interact\(PondRestSpot\)", "interact\(PondRestSpot\)", "interact\(PondRestSpot\)"\]; seated true; camera unchanged true'),
            ("the occupied seat offers nothing and refuses interact()", r"^R E1J seat verbs \| occupied: available true, verbs \[\], interact\(\) -> false"),
            ("tapping the player's upper body stands and restores the camera", rf"^R E1J upper body \|.*-> stop; seated false;.*{BASE}")],
    "E1K": [("the joystick starts past the drag threshold at the touch-down point", r"^R E1K start \|.*80 px drag: \[\"start\(500,760\)\"\]; ring visible true centre \(500\.00, 760\.00\)"),
            ("seated: a short left-half tap keeps the player seated; a joystick drag no longer stands (D-62)", r"^R E1K seated \|.*still seated true;.*joystick drag: seated true;")],
    # R1 (D-62): the Stand Up button, the hidden joystick and the movement lock until the camera has restored.
    "E1T": [("standing: no Stand Up, the joystick shown, movement free", r"^R E1T boot \| stand up visible false; joystick visible true; movement locked false;"),
            ("seated: Stand Up shown, the joystick hidden, movement locked", r"^R E1T seated \| stand up visible true; joystick visible false; movement locked true; seated: state 3;"),
            ("a real joystick drag while seated neither stands nor moves the player", r"^R E1T seated drag \| seated true; moved 0\.000 m; camera unchanged true;"),
            ("Stand Up (keyboard held) stands at once; Stand Up hides; movement stays locked and the joystick hidden",
             r"^R E1T stand up \| W held while seated: seated true, moved 0\.000 m; Stand Up -> pressed, world events none; just after: seated false; "
             r"stand up visible false; joystick visible false; movement locked true; seat available true"),
            ("nothing moves and the joystick stays hidden until the release finishes, at the exact base; one settle_ended",
             rf"^R E1T release \| movement locked for [1-9]\d* physics frames, moved while locked 0\.000 m, joystick hidden while locked true; unlocked {N} s after Stand Up; "
             rf"settle_ended 1; camera at the unlock {BASE} \(base {BASE}, exact true\);"),
            ("after the release the held key moves the player; the joystick is back",
             r"^R E1T release \|.*then W moved (?:[1-9]\d*\.\d+|0\.\d*[1-9]\d*) m; stand up visible false; joystick visible true; movement locked false$"),
            ("Tap to Move: the joystick stays hidden before, during and after; Stand Up works the same",
             r"^R E1T tap mode \| Tap to Move: before stand up visible false; joystick visible false; movement locked false; seated true: stand up visible true; "
             r"joystick visible false; movement locked true; Stand Up -> pressed, world events none; after the release stand up visible false; "
             r"joystick visible false; movement locked false; seated false$")],
    # R2 (D-62): the closer seated view and pinch bounded to 7–10 m; the exact pre-sit view before movement returns.
    "E1Z": [("a non-default pre-sit view (13.31 m), standing controls", r"^R E1Z pre-sit \| zoom 13\.3100 offset \(0\.0000, 0\.0800\); stand up visible false; joystick visible true; movement locked false$"),
            ("seated, the view starts at 8 m with the spot's framing (wheel during the settle ease ignored)",
             rf"^R E1Z settled \| seated after {N} s; two wheel notches during the settle ease; settled {SETTLED}; stand up visible true; joystick visible false; movement locked true$"),
            # The ease rewrites the distance every frame, so the end value alone cannot show a request was ignored: the
            # probe reads the distance just before and just after the camera handles each request.
            ("wheel notches while the settle eases in change nothing; it ends at exactly 8 m; the saved pre-sit view is untouched",
             rf"^R E1Z wheel while settling \| 2 requests, 2 during the ease, 0 changed the distance during the ease \[.*\]; settled {SETTLED}; "
             r"saved pre-sit view 13\.3100 \(0\.0000, 0\.0800\) \(exact true\)$"),
            ("a real two-finger pinch while the settle eases in changes nothing; it ends at exactly 8 m; the saved pre-sit view is untouched",
             rf"^R E1Z pinch while settling \| ([1-9]\d*) requests, \1 during the ease, 0 changed the distance during the ease \[.*\]; settled {SETTLED}; "
             r"saved pre-sit view 12\.3967 \(0\.0000, 0\.0800\) \(exact true\)$"),
            ("the seated wheel stops at 10 m out and 7 m in; the framing stays",
             r'^R E1Z seated wheel \| out \[(?:"(?:[7-9]\.\d{4}|10\.0000)", ){5}"10\.0000"\]; in \[(?:"[7-9]\.\d{4}", ){5}"7\.0000"\]; offset \(2\.0000, -2\.0000\); seated true$'),
            ("a real two-finger pinch zooms within 7–10 m while seated, never a tap",
             r"^R E1Z seated pinch \| pinch apart: 10\.0000 -> [7-9]\.\d{4}; wide pinch apart -> 7\.0000; pinch together -> 10\.0000; offset \(2\.0000, -2\.0000\); seated true; taps none$"),
            ("Stand Up from a pinched view: movement returns only at the exact pre-sit view",
             rf"^R E1Z stand up \| seated zoom 10\.0000; Stand Up -> pressed, world events none; unlocked {N} s later at zoom 13\.3100 offset \(0\.0000, 0\.0800\) \(pre-sit .*, exact true\); zoom exact true; stand up visible false; joystick visible true; movement locked false$"),
            ("standing, the normal 7–15 m limits apply again", r'^R E1Z standing wheel \| out \["14\.6410", "15\.0000", "15\.0000", "15\.0000"\]; then in twice -> 12\.3967; seated false$'),
            ("sitting again starts at 8 m (no seated zoom remembered)", rf"^R E1Z sit again \| pre-sit 12\.3967; seated after {N} s; settled {SETTLED}; stand up visible true"),
            ("an area swap while seated with a pinched view: indoors at the interior distance, standing, controls back",
             r"^R E1Z swap while seated \| seated view zoom 10\.0000 offset \(2\.0000, -2\.0000\); indoors: area HomeInterior; seated false; zoom 7\.5000 offset \(0\.0000, 0\.0800\); stand up visible false; joystick visible true; movement locked false$"),
            ("back outside, the exact pre-sit view", r"^R E1Z back outside \| area Meadow; seated false; zoom 12\.3967 offset \(0\.0000, 0\.0800\) \(pre-sit 12\.3967 exact true\);")],
    # R3 (D-62): seated yaw within ±45° by a one-finger drag anywhere; default yaw on every sit; restored before movement.
    "E1Y": [("standing, a drag does not turn the view", r"^R E1Y standing drag \| yaw 0\.0000 -> 0\.0000; .*stand up visible false; joystick visible true; movement locked false$"),
            ("a drag while the settle eases in turns nothing; seated, the view starts at the default yaw",
             rf"^R E1Y settled \| seated after {N} s; drag during the settle ease: ([1-9]\d*) drag events, \1 while easing, 0 turned the view while easing; settled yaw 0\.0000; {SETTLED};"),
            ("seated drags turn the view (0.15° per pixel) up to +45° and down to −45°, stopping at both limits; the left half turns it too (the joystick is off); no tap, zoom or framing change",
             r'^R E1Y seated drags \| yaw \["27\.0000", "45\.0000", "-45\.0000", "-45\.0000", "-18\.0000"\]; joystick \[\]; zoom/offset ' + SETTLED + r"; seated true; taps none$"),
            ("a seated pinch zooms and does not turn the view", r"^R E1Y seated pinch \| yaw (-?\d+\.\d{4}) -> \1; zoom [7-9]\.\d{4}$"),
            ("a quick look-around from the player's body that comes back near its start is a drag (the view turns by the net 4 px) and never a tap: still seated (R3 input audit)",
             r"^R E1Y flick back \| from the player's body at canvas \([0-9.]+, [0-9.]+\): yaw -18\.0000 -> -17\.4000; taps none; seated true$"),
            ("Stand Up from a turned view: nothing moves and drags are ignored during the release; movement returns only at the exact default yaw, distance and framing",
             rf"^R E1Y stand up \| turned 45\.0000; Stand Up -> pressed, world events none; first locked frame yaw (?!0\.0000)-?\d+\.\d{{4}}; moved while locked 0\.000 m; "
             rf"a drag during the release: ([1-9]\d*) drag events, \1 while easing, 0 turned the view while easing; unlocked at yaw 0\.0000 \(pre-sit 0\.0000, exact true\) and "
             rf"{BASE} \(pre-sit {BASE}, exact true\); stand up visible false; joystick visible true; movement locked false$"),
            ("standing again, a drag does not turn the view and a left-half drag is the joystick again",
             r'^R E1Y standing again \| a right-half drag: yaw 0\.0000 -> 0\.0000; a left-half drag: joystick \["start\(300,700\)"\]; seated false$'),
            ("every sit starts at the default yaw, also when sitting again mid-release from a turned view",
             r"^R E1Y sit again \| settled yaw 0\.0000; turned to -45\.0000; stand tap -> stop; mid-release yaw (?!-45\.0000|0\.0000)-?\d+\.\d{4}; seat tap -> routed interact\(PondRestSpot\), seated after [0-9.]+ s; settled yaw 0\.0000 \(default 0\.0000, exact true\); seated true$"),
            ("an area swap while seated with a turned view restores the yaw at once; controls back",
             rf"^R E1Y swap while seated \| turned 37\.5000; indoors: area HomeInterior; seated false; yaw 0\.0000 \(exact true\); zoom 7\.5000 offset \(0\.0000, 0\.0800\); stand up visible false; joystick visible true; movement locked false$")],
    # R4 (D-62): the rest ambience fades in on sitting and out on standing; a session-only mute; one playback at a time.
    "E1M": [("standing, no ambience; the placeholder stands in (nothing assigned)",
             r"^R E1M boot \| playing false; volume -?\d+\.\d{4} dB; muted false; mute button false 🔊; players playing 0; level -14\.0 dB, silent -60\.0 dB; rest_ambience assigned false$"),
            ("sitting starts it from silence and fades it in to its level, rising throughout; the world carries on",
             rf"^R E1M fade in \| just seated: playing true; volume -?\d+\.\d{{4}} dB; muted false; mute button true 🔊; players playing 1; stream AudioStreamWAV; "
             rf"reached -14\.0000 dB after {N} s over (?:[3-9]|[1-9]\d+) frames, rising throughout true, in between true; now playing true; volume -14\.0000 dB; .*clock advanced true; paused false$"),
            ("the mute silences it and a second press restores it, while seated, never a world tap",
             r"^R E1M mute \| mute -> pressed, world events none; silent after [0-9.]+ s: playing true; volume -60\.0000 dB; muted true; mute button true 🔇; players playing 1; "
             r"unmute -> pressed, world events none; back after [0-9.]+ s: playing true; volume -14\.0000 dB; muted false; mute button true 🔊; players playing 1; seated true$"),
            ("the stream loops: a forward loop over all its frames; after longer than one loop it still plays, within its length",
             r"^R E1M loop \| stream loop_mode 1, loop 0\.\.(\d+) of \1 frames, length [0-9.]+ s; seated playback [0-9.]+ s \(longer than one loop true\); still playing true; position [0-9.]+ s \(within the length true\)$"),
            ("muted, Stand Up: movement and the joystick return exactly at the camera's restore; the ambience stops; the mute lasts",
             r"^R E1M stand up \| Stand Up -> pressed, world events none; moved while locked 0\.000 m; unlocked after [0-9.]+ s at zoom 11\.0000 offset \(0\.0000, 0\.0800\) \(base, exact true\); "
             r"ambience stopped after [0-9.]+ s; at most 1 player\(s\) playing; now playing false; volume -60\.0000 dB; muted true; mute button false 🔇; players playing 0; "
             r"stand up visible false; joystick visible true; movement locked false$"),
            ("sitting again while muted stays silent; sitting again mid-fade-out carries on with the same playback and fades back in",
             r"^R E1M sit again \| while muted: playing true; volume -60\.0000 dB; muted true; mute button true 🔇; players playing 1; unmuted, stood, re-sat \(routed\) after [0-9.]+ s mid-fade-out: "
             r"volume -?\d+\.\d{4} -> -?\d+\.\d{4} at the sit -> -?\d+\.\d{4} 0\.4 s later \(faded out before the sit true, restarted from silence false, rising after it true\); playing throughout true; players playing 1$"),
            ("quick sit/stand cycles never play twice and leave nothing playing",
             r"^R E1M cycles \| 5 quick sit/stand cycles: at most 1 player\(s\) playing; after standing: silent after [0-9.]+ s, playing false; volume -60\.0000 dB; muted false; mute button false 🔊; players playing 0; seated false$"),
            ("an area swap while seated fades it out; the mute button goes",
             r"^R E1M swap while seated \| seated: playing true; volume -14\.0000 dB; .*; indoors: area HomeInterior; seated false; playing false; volume -60\.0000 dB; muted false; mute button false 🔊; players playing 0$")],
    "E1S": [("a save made while seated has no seat/rest key", rf"^R E1S saved while seated \| save_version {N}; sections \[.*\]; any seat/rest/seated key: false"),
            ("muted while seated when saving: the save and its settings know nothing of it (R4)",
             r'^R E1S muted when saving \| mute -> pressed, world events none; rest ambience muted true; settings \{"movement_mode":"joystick"\}; any mute/ambience key: false$')],
    "E1R": [("a relaunch after saving while seated starts standing", r"^R E1R boot \| relaunch: state 0;"),
            ("the relaunch is unmuted: the mute lasted the session only (R4)",
             r'^R E1R mute \| relaunch: rest ambience muted false; playing false; mute button visible false; settings \{"movement_mode":"joystick"\}$')],
}

def r_lines(path):
    return [l.rstrip("\n") for l in open(path, encoding="utf-8", errors="replace") if l.startswith("R ")]

def norm(line):
    return re.sub(N, "N", line)

def main(argv):
    if not argv or argv[0].startswith("-"):
        print(__doc__); return 2
    logs = argv[0]
    base = argv[argv.index("--baseline") + 1] if "--baseline" in argv else None
    phases = argv[argv.index("--phases") + 1].split() if "--phases" in argv else PHASES
    unknown = [p for p in phases if p not in EXPECT]
    if unknown:
        print(f"PROBE_CHECK FAIL unknown phases {unknown} (known: {PHASES})"); return 1
    failed = passed = 0
    for phase in phases:
        path = os.path.join(logs, f"{phase}.log")
        if not os.path.exists(path):
            print(f"PROBE_CHECK FAIL {phase}: no log"); failed += 1; continue
        text = open(path, encoding="utf-8", errors="replace").read()
        lines = r_lines(path)
        checks = [("finished", re.search(rf"^R done \| phase {phase} finished", text, re.M) is not None),
                  ("no script errors", text.count("SCRIPT ERROR") == 0)]
        checks += [(what, any(re.search(rx, l) for l in lines)) for what, rx in EXPECT[phase]]
        for what, ok in checks:
            print(f"PROBE_CHECK {'PASS' if ok else 'FAIL'} {phase}: {what}")
            passed += ok; failed += not ok
        if base:
            bpath = os.path.join(base, f"{phase}.log")
            if not os.path.exists(bpath):
                print(f"PROBE_COMPARE {phase}: no baseline log")
            else:
                a, b = [norm(l) for l in lines], [norm(l) for l in r_lines(bpath)]
                if a == b:
                    print(f"PROBE_COMPARE {phase}: identical to the baseline (numbers aside)")
                else:
                    gone = [l for l in b if l not in a][:3]; new = [l for l in a if l not in b][:3]
                    print(f"PROBE_COMPARE {phase}: differs from the baseline (numbers aside): {len(a)} vs {len(b)} R lines")
                    for l in gone: print(f"    baseline: {l[:220]}")
                    for l in new: print(f"    this run: {l[:220]}")
    print(f"PROBE_SUMMARY {passed} passed, {failed} failed")
    return 1 if failed else 0

if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
