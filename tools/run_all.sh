#!/usr/bin/env bash
# Runs every available check. Exit code is non-zero if any check fails.
# Usage: tools/run_all.sh        (from anywhere inside the repository)
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/.." && pwd)"
failed=0
step() { echo; echo "=== $1"; }

step "1/5 Scene & resource consistency (check_project.py)"
python3 "$here/check_project.py" "$repo" || failed=1

step "2/5 GDScript semantics vs Godot 4.7.2 API (check_gdscript.py)"
python3 "$here/check_gdscript.py" "$repo"; rc=$?
if [ $rc -eq 2 ]; then echo "SKIPPED: run tools/fetch_godot_api.sh first"; elif [ $rc -ne 0 ]; then failed=1; fi

step "3/5 GDScript syntax (gdtoolkit gdparse)"
if command -v gdparse >/dev/null 2>&1; then
  n=0
  while IFS= read -r f; do
    if ! gdparse "$repo/$f" >/dev/null 2>&1; then echo "FAIL $f"; gdparse "$repo/$f" 2>&1 | tail -3; n=$((n+1)); fi
  done < <(cd "$repo" && git ls-files -co --exclude-standard '*.gd')
  echo "gdparse failures: $n"; [ $n -eq 0 ] || failed=1
else
  echo "SKIPPED: pip install 'gdtoolkit==4.*'"
fi

step "4/5 Model simulations"
for sim in "$here"/sims/sim_*.py; do
  echo "--- $(basename "$sim")"
  python3 "$sim" | tail -2 || failed=1
done

step "5/5 Summary"
if [ $failed -eq 0 ]; then echo "ALL CHECKS PASSED (static + model only; not a Godot/Android run)"; else echo "SOME CHECKS FAILED"; fi
exit $failed
