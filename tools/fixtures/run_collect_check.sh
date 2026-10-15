#!/usr/bin/env bash
# Discovery collection smoke test in real Godot (P0.1): walk-to-collect (the
# InteractionZone's area_entered path), a direct tap in reach, a repeat after a
# respawn, rapid repeats during each collection's animation; P0.1b adds a walk-up Earth Nurture use and a walk-up
# farm harvest with rapid repeats (one cycle, one harvest paid once), a locked plot left untouched and a harvest with no
# crop visual (one frame) that must end available; then a relaunch that
# must load what was held (save v9). Its own data folder (XDG_DATA_HOME), so the
# developer's save is never touched. Fails on any COLLECT_CHECK FAIL, any SCRIPT
# ERROR, or Godot's "Function blocked during in/out signal" in either launch.
# Usage: GODOT=/path/to/Godot_v4.7.2 [PROJECT=<dir>] tools/fixtures/run_collect_check.sh
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
project="${PROJECT:-$(cd "$here/../.." && pwd)}"
godot="${GODOT:-godot}"
work="$(mktemp -d)"
failed=0
if [ ! -d "$project/.godot" ]; then timeout 600 "$godot" --headless --editor --quit --path "$project" > "$work/import.log" 2>&1; fi
script=res://tools/fixtures/collect_check.gd
for mode in act check; do
  XDG_DATA_HOME="$work/data" timeout 300 "$godot" --headless --path "$project" -s "$script" -- "mode=$mode" "expect=$work/expect.json" > "$work/$mode.log" 2>&1
  rc=$?
  grep -E "COLLECT_CHECK (PASS|FAIL)" "$work/$mode.log" | sed "s/^/  [$mode] /"
  errs=$(grep -c "SCRIPT ERROR" "$work/$mode.log")
  blocked=$(grep -c "Function blocked during in/out signal" "$work/$mode.log")
  fails=$(grep -c "COLLECT_CHECK FAIL" "$work/$mode.log")
  passes=$(grep -c "COLLECT_CHECK PASS" "$work/$mode.log")
  if [ $rc -ne 0 ] || [ "$errs" -ne 0 ] || [ "$blocked" -ne 0 ] || [ "$fails" -ne 0 ] || [ "$passes" -eq 0 ]; then
    echo "FAIL $mode: exit $rc, script errors $errs, blocked monitorable writes $blocked, failed checks $fails ($work/$mode.log)"; failed=1
  fi
  [ $failed -ne 0 ] && break
done
echo "logs: $work"
if [ $failed -eq 0 ]; then echo "ALL COLLECTION CHECKS PASSED IN GODOT"; else echo "COLLECTION CHECK FAILED"; fi
exit $failed
