#!/usr/bin/env bash
# Force-stop persistence in real Godot (M15.4). For each case: a setup launch
# saves the starting state; an act launch performs the moment under test, writes
# what the game holds, and is then killed with SIGKILL (no pause or close
# notification — the app is simply gone, like `adb shell am force-stop`); a check
# launch loads the save and compares; an again launch reloads it and repeats the
# moment, which must pay nothing extra. Each case has its own data folder
# (XDG_DATA_HOME), so the developer's own save is never touched.
#   daily: after setup the saved completion date is cleared (test setup only), so
#          the act — a repeat collection of today's target — is what completes it.
#   sighting (M14.1a): a real Rabbit and WildlifeController with the player inside
#          its alert distance — the species seen through the game's own path.
# Usage: GODOT=/path/to/Godot_v4.7.2 [PROJECT=<dir>] [CASES="landmark secret ..."] tools/fixtures/run_force_stop.sh
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
project="${PROJECT:-$(cd "$here/../.." && pwd)}"
godot="${GODOT:-godot}"
cases="${CASES:-control landmark secret curiosity all_secrets repeat daily sighting}"
work="$(mktemp -d)"
failed=0; passed=0
if [ ! -d "$project/.godot" ]; then timeout 600 "$godot" --headless --editor --quit --path "$project" > "$work/import.log" 2>&1; fi
script=res://tools/fixtures/force_stop_check.gd
for c in $cases; do
  data="$work/$c"; mkdir -p "$data"; expect="$work/$c.expect.json"
  save="$data/godot/app_userdata/Wrikshagandha/save.json"
  XDG_DATA_HOME="$data" timeout 300 "$godot" --headless --path "$project" -s "$script" -- mode=setup "case=$c" > "$work/$c.setup.log" 2>&1
  grep -q "FORCE_STOP_SETUP_DONE" "$work/$c.setup.log" || { echo "FAIL $c: setup did not finish ($work/$c.setup.log)"; failed=1; continue; }
  if [ "$c" = daily ]; then
    python3 - "$save" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p)); d["daily_discovery"]["completed_date"] = ""; json.dump(d, open(p, "w"))
PY
  fi
  before=$(sha256sum < "$save")
  XDG_DATA_HOME="$data" "$godot" --headless --path "$project" -s "$script" -- mode=act "case=$c" "expect=$expect" > "$work/$c.act.log" 2>&1 &
  pid=$!
  for i in $(seq 1 600); do grep -q "FORCE_STOP_READY" "$work/$c.act.log" && break; kill -0 $pid 2>/dev/null || break; sleep 0.1; done
  if ! grep -q "FORCE_STOP_READY" "$work/$c.act.log"; then echo "FAIL $c: act never got ready ($work/$c.act.log)"; kill -9 $pid 2>/dev/null; failed=1; continue; fi
  kill -9 $pid; wait $pid 2>/dev/null
  kill -0 $pid 2>/dev/null && { echo "FAIL $c: process survived SIGKILL"; failed=1; continue; }
  after=$(sha256sum < "$save")
  written=$([ "$before" = "$after" ] && echo "not written after the act" || echo "written after the act")
  errs=$(cat "$work/$c.setup.log" "$work/$c.act.log" | grep -c "SCRIPT ERROR")
  XDG_DATA_HOME="$data" timeout 300 "$godot" --headless --path "$project" -s "$script" -- mode=check "case=$c" "expect=$expect" > "$work/$c.check.log" 2>&1
  errs=$((errs + $(grep -c "SCRIPT ERROR" "$work/$c.check.log")))
  line=$(grep -E "FORCE_STOP_(PASS|FAIL)" "$work/$c.check.log" | head -1)
  if echo "$line" | grep -q "FORCE_STOP_PASS" && [ "$errs" -eq 0 ]; then passed=$((passed + 1)); echo "PASS $c (save $written)"; else echo "FAIL $c (save $written; script errors $errs) ${line#*:: }"; failed=1; continue; fi
  # Once more: the save loads the same again, and repeating the moment pays nothing extra.
  XDG_DATA_HOME="$data" timeout 300 "$godot" --headless --path "$project" -s "$script" -- mode=again "case=$c" "expect=$expect" > "$work/$c.again.log" 2>&1
  line=$(grep -E "FORCE_STOP_(PASS|FAIL)" "$work/$c.again.log" | head -1)
  if echo "$line" | grep -q "FORCE_STOP_PASS" && [ "$(grep -c 'SCRIPT ERROR' "$work/$c.again.log")" -eq 0 ]; then passed=$((passed + 1)); echo "PASS $c again (${line#*:: })"; else echo "FAIL $c again (${line#*:: })"; failed=1; fi
done
echo "logs: $work"
if [ $failed -eq 0 ]; then echo "ALL FORCE-STOP CASES PASSED IN GODOT ($passed)"; else echo "FORCE-STOP CHECK FAILED"; fi
exit $failed
