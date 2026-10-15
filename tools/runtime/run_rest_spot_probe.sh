#!/usr/bin/env bash
# Rest Spot runtime probe in real Godot (P0.2): the E1 rest-spot phases (E1A–E1K, E1S, E1R; E1T added by R1, E1Z by R2, E1Y by R3 and E1M by R4, D-62) driven through synthesized
# touches, then the contract verdicts of check_probe_logs.py. Not run by run_all.sh (it needs Godot and a display).
#
# The project (tracked and untracked, not ignored, files) is copied to a temporary folder; there the probe
# (rest_spot_probe.gd.in) is installed as probe/rest_spot_probe.gd and added as an autoload right after InputManager —
# exactly as the unversioned probe ran. The repository, its project.godot and the developer's save
# are never touched: every phase has its own data folder (XDG_DATA_HOME); E1S and E1R share one, because E1R is
# the relaunch onto the save E1S made while seated.
#
# Each phase runs as the original did: Godot 4.7.2 with --rendering-driver opengl3 at 960x540 under xvfb-run
# (screen 1300x1000x24). Needs: GODOT, xvfb-run, git (for BASELINE), python3. About 1 minute per phase.
#   GODOT=/path/to/Godot_v4.7.2 [PROJECT=<dir>] [PHASES="E1A E1C"] [BASELINE=<git ref>] tools/runtime/run_rest_spot_probe.sh
# BASELINE=<ref> also runs the same phases on `git archive <ref>` (the probe from this tree) and lists, for
# information, every phase whose R lines differ from it (numbers ignored). Exit 1 when any contract check fails.
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
project="${PROJECT:-$(cd "$here/../.." && pwd)}"
godot="${GODOT:-godot}"
phases="${PHASES:-E1A E1B E1C E1D E1E E1F E1G E1H E1I E1J E1K E1T E1Z E1Y E1M E1S E1R}"
res="${RES:-960x540}"
command -v xvfb-run > /dev/null || { echo "run_rest_spot_probe: xvfb-run is required (the probe renders and reads the viewport)"; exit 2; }
work="$(mktemp -d)"

# prepare <tree>: install the probe as an autoload in a temporary copy, then import (class cache) like any project
prepare() {
  local tree="$1"
  mkdir -p "$tree/probe"
  cp "$here/rest_spot_probe.gd.in" "$tree/probe/rest_spot_probe.gd"
  grep -q '^InputManager=' "$tree/project.godot" || { echo "run_rest_spot_probe: no InputManager autoload in $tree/project.godot"; return 1; }
  sed -i 's|^InputManager=.*|&\nRestSpotProbe="*res://probe/rest_spot_probe.gd"|' "$tree/project.godot"
  timeout 600 "$godot" --headless --editor --quit --path "$tree" > "$tree.import.log" 2>&1
}

# run_phases <tree> <log dir> <data prefix>
run_phases() {
  local tree="$1" logs="$2" data="$3" p dir
  mkdir -p "$logs"
  for p in $phases; do
    dir="$data/$p"
    [ "$p" = E1S ] || [ "$p" = E1R ] && dir="$data/E1SR"
    mkdir -p "$dir"
    (cd "$tree" && XDG_DATA_HOME="$dir" timeout 900 xvfb-run -a -s "-screen 0 1300x1000x24" "$godot" \
      --rendering-driver opengl3 --resolution "$res" --path . -- "phase=$p" > "$logs/$p.log" 2>&1)
    echo "  phase $p: exit $?"
  done
}

echo "== this tree ($project)"
if git -C "$project" rev-parse --is-inside-work-tree > /dev/null 2>&1; then
  mkdir -p "$work/tree"
  (cd "$project" && git ls-files -co --exclude-standard -z | tar --null -T - -cf -) | tar xf - -C "$work/tree"
else
  mkdir -p "$work/tree"; (cd "$project" && tar --exclude=.git --exclude=.godot -cf - .) | tar xf - -C "$work/tree"
fi
prepare "$work/tree" || exit 2
# Phases run in the order given; E1S must come before E1R (the relaunch reads the save E1S made while seated).
run_phases "$work/tree" "$work/logs" "$work/data"

args=("$work/logs" --phases "$phases")
if [ -n "${BASELINE:-}" ]; then
  echo "== baseline $BASELINE"
  mkdir -p "$work/base"
  git -C "$project" archive "$BASELINE" | tar xf - -C "$work/base" || { echo "run_rest_spot_probe: cannot export $BASELINE"; exit 2; }
  prepare "$work/base" || exit 2
  run_phases "$work/base" "$work/base_logs" "$work/base_data"
  args+=(--baseline "$work/base_logs")
fi

python3 "$here/check_probe_logs.py" "${args[@]}"
rc=$?
echo "logs: $work"
if [ $rc -eq 0 ]; then echo "ALL REST SPOT PROBE CHECKS PASSED IN GODOT"; else echo "REST SPOT PROBE CHECK FAILED"; fi
exit $rc
