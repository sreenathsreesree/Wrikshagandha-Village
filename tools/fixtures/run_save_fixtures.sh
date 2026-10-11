#!/usr/bin/env bash
# Old-save compatibility in real Godot (M15.3): every fixture in
# tools/fixtures/saves/ is loaded by the current game at boot, exactly as a
# player's save would be, and checked against what the old version held.
#   v0..vN     (N = SAVE_VERSION) pass 1: load (migrated by SaveManager), compare, save again;
#              pass 2: a new launch loads that re-saved file and compares again
#   newer      stamped past SAVE_VERSION: not loaded, and the file is left byte-for-byte as it was
#   malformed  ignored like a damaged file (a new game), no crash
# Any SCRIPT ERROR in a run fails it. Each run uses its own data folder
# (XDG_DATA_HOME), so the developer's own save is never touched.
# Usage: GODOT=/path/to/Godot_v4.7.2 [PROJECT=<project dir>] tools/fixtures/run_save_fixtures.sh
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
project="${PROJECT:-$repo}"
godot="${GODOT:-godot}"
saves="$here/saves"
work="$(mktemp -d)"
failed=0; passes=0
if [ ! -d "$project/.godot" ]; then timeout 600 "$godot" --headless --editor --quit --path "$project" > "$work/import.log" 2>&1; fi
run() {  # run <data dir> <log> <args...>
  local data="$1" log="$2"; shift 2
  XDG_DATA_HOME="$data" timeout 300 "$godot" --headless --path "$project" -s res://tools/fixtures/save_fixture_check.gd -- "$@" > "$log" 2>&1
  local rc=$?
  local errs; errs=$(grep -c "SCRIPT ERROR" "$log")
  passes=$((passes + $(grep -c "FIXTURE_CHECK PASS" "$log")))
  grep "FIXTURE_CHECK FAIL" "$log" | sed 's/^/  /'
  if [ $rc -ne 0 ] || [ "$errs" -ne 0 ]; then echo "  run failed: exit $rc, script errors $errs ($log)"; failed=1; fi
}
place() {  # place <data dir> <fixture file>: where Godot keeps this project's user:// (app_userdata/<config/name>)
  mkdir -p "$1/godot/app_userdata/Wrikshagandha"; cp "$2" "$1/godot/app_userdata/Wrikshagandha/save.json"
}
mkdir -p "$work/fresh"
run "$work/fresh" "$work/fresh.log" mode=fresh "out=$work/fresh.json"
# Every format from v0 to the build's SAVE_VERSION must have its fixture.
current=$(grep -oE '^const SAVE_VERSION := [0-9]+' "$project/scripts/autoload/save_manager.gd" | grep -oE '[0-9]+$')
for n in $(seq 0 "$current"); do
  v="v$n"; dir="$saves/$v"
  [ -f "$dir/save.json" ] && [ -f "$dir/expected.json" ] || { echo "  FIXTURE_CHECK FAIL MISSING $v (save.json / expected.json)"; failed=1; continue; }
  grep -q '"pending": true' "$dir/meta.json" 2>/dev/null && echo "$v: PENDING fixture — from the uncommitted working tree, NOT historical (M15.3 exception, current SAVE_VERSION only)"
  d="$work/$v"; place "$d" "$dir/save.json"
  run "$d" "$work/$v.1.log" mode=fixture "expected=$dir/expected.json" "fresh=$work/fresh.json" "origin=$n" resave=1
  run "$d" "$work/$v.2.log" mode=fixture "expected=$dir/expected.json" "fresh=$work/fresh.json" "origin=$n" again=1
  echo "$v: $(grep -c 'FIXTURE_CHECK PASS' "$work/$v.1.log") + $(grep -c 'FIXTURE_CHECK PASS' "$work/$v.2.log") checks passed, $(cat "$work/$v.1.log" "$work/$v.2.log" | grep -c 'FIXTURE_CHECK FAIL') failed"
done
d="$work/newer"; place "$d" "$saves/newer/save.json"
before=$(sha256sum < "$saves/newer/save.json")
run "$d" "$work/newer.log" mode=newer
after=$(sha256sum < "$d/godot/app_userdata/Wrikshagandha/save.json")
if [ "$before" = "$after" ]; then echo "newer: not loaded, file unchanged"; passes=$((passes + 1)); else echo "  FIXTURE_CHECK FAIL newer file was overwritten"; failed=1; fi
d="$work/malformed"; place "$d" "$saves/malformed/save.json"
run "$d" "$work/malformed.log" mode=malformed "fresh=$work/fresh.json"
echo "malformed: $(grep -c 'FIXTURE_CHECK PASS' "$work/malformed.log") checks passed"
echo "logs: $work"
if [ $failed -eq 0 ]; then echo "ALL SAVE FIXTURES PASSED IN GODOT ($passes checks)"; else echo "SAVE FIXTURE CHECK FAILED"; fi
exit $failed
