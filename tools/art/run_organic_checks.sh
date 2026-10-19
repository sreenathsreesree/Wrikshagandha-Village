#!/usr/bin/env bash
# Stage B0 organic art checks in real Godot (D-60) — not run by run_all.sh (it needs a Godot binary):
#   1. bounds        check_organic_assets.gd mode=bounds: actual triangle counts and measured bounds of every prop
#   2. colliders     the props' collision facts as Godot builds them, here and in a git archive of the baseline
#                    commit (BASELINE, default 3f2cfaf), compared exactly
#   3. reproducible  the generators (organic props, and W1's pond edge) rerun into a temporary folder; every mesh's
#                    content hash must equal the committed mesh's, and the files must be byte-identical (the generators
#                    fix each mesh's id)
#   4. pond edge     check_organic_assets.gd mode=pond: the W1 shore's measured shape, the materials and budgets
# Any SCRIPT ERROR fails. Nothing in the project is written (the generator's output goes to a temporary folder).
# Usage: GODOT=/path/to/Godot_v4.7.2 [PROJECT=<dir>] [BASELINE=<commit>] tools/art/run_organic_checks.sh
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../.." && pwd)"
project="${PROJECT:-$repo}"
godot="${GODOT:-godot}"
baseline="${BASELINE:-3f2cfaf}"
work="$(mktemp -d)"
failed=0
# A project that was never opened in the editor has no class cache yet: import it first (as run_save_fixtures.sh does).
if [ ! -d "$project/.godot" ]; then timeout 600 "$godot" --headless --editor --quit --path "$project" > "$work/import.log" 2>&1; fi
gd() { local dir="$1" log="$2"; shift 2; timeout 600 "$godot" --headless --path "$dir" -s res://tools/art/check_organic_assets.gd -- "$@" > "$log" 2>&1; local rc=$?
  # exit 1 with ORGANIC_CHECK FAIL lines is a check that failed (reported with the results); anything else — a
  # script error, a crash, no output — is a run that failed.
  local errs; errs=$(grep -c "SCRIPT ERROR" "$log")
  if [ "$errs" -ne 0 ] || { [ $rc -ne 0 ] && ! { [ $rc -eq 1 ] && grep -q "ORGANIC_CHECK FAIL" "$log"; }; }; then echo "  run failed: exit $rc, script errors $errs ($log)"; failed=1
  elif [ $rc -ne 0 ]; then failed=1; fi; }

echo "== 1. bounds"
gd "$project" "$work/bounds.log" mode=bounds "report=$work/bounds.json"
grep -E "ORGANIC_CHECK (PASS|FAIL|INFO)" "$work/bounds.log" | sed 's/^/  /'

echo "== 2. colliders vs $baseline"
mkdir -p "$work/base"
(cd "$repo" && git archive "$baseline") | tar -x -C "$work/base"
mkdir -p "$work/base/tools/art" && cp "$here/check_organic_assets.gd" "$work/base/tools/art/"
timeout 600 "$godot" --headless --editor --quit --path "$work/base" > "$work/base_import.log" 2>&1  # class cache, like any project
gd "$project" "$work/coll_now.log" mode=colliders "out=$work/colliders_now.json"
gd "$work/base" "$work/coll_base.log" mode=colliders "out=$work/colliders_base.json"
if [ -s "$work/colliders_now.json" ] && cmp -s "$work/colliders_now.json" "$work/colliders_base.json"; then
  echo "  ORGANIC_CHECK PASS colliders identical to $baseline ($(grep -c '"type"' "$work/colliders_now.json") shapes)"
else
  echo "  ORGANIC_CHECK FAIL colliders differ from $baseline:"; diff "$work/colliders_base.json" "$work/colliders_now.json" | head -20 | sed 's/^/    /'; failed=1
fi

echo "== 3. reproducibility"
mkdir -p "$work/regen"
timeout 600 "$godot" --headless --path "$project" -s res://tools/art/generate_organic_assets.gd -- "out=$work/regen" > "$work/regen.log" 2>&1
grep -q "ORGANIC_GEN OK" "$work/regen.log" && [ "$(grep -c 'SCRIPT ERROR' "$work/regen.log")" -eq 0 ] || { echo "  ORGANIC_CHECK FAIL the generator did not finish ($work/regen.log)"; failed=1; }
# W1 (D-63): the Living Pond Edge's meshes live in the same folder and are regenerated and compared the same way.
timeout 600 "$godot" --headless --path "$project" -s res://tools/art/generate_pond_edge.gd -- "out=$work/regen" > "$work/regen_pond.log" 2>&1
grep -q "POND_GEN OK" "$work/regen_pond.log" && [ "$(grep -c 'SCRIPT ERROR' "$work/regen_pond.log")" -eq 0 ] || { echo "  ORGANIC_CHECK FAIL the pond edge generator did not finish ($work/regen_pond.log)"; failed=1; }
gd "$project" "$work/hash_now.log" mode=hash "dir=$project/assets/organic/meshes" "out=$work/hash_committed.json"
gd "$project" "$work/hash_regen.log" mode=hash "dir=$work/regen" "out=$work/hash_regen.json"
if [ -s "$work/hash_committed.json" ] && cmp -s "$work/hash_committed.json" "$work/hash_regen.json"; then
  echo "  ORGANIC_CHECK PASS regenerated meshes have the committed content ($(grep -c '\.res' "$work/hash_committed.json") meshes)"
else
  echo "  ORGANIC_CHECK FAIL regenerated content differs:"; diff "$work/hash_committed.json" "$work/hash_regen.json" | head -20 | sed 's/^/    /'; failed=1
fi
same=0; diffb=0
for f in "$project"/assets/organic/meshes/*.res; do
  if cmp -s "$f" "$work/regen/$(basename "$f")"; then same=$((same + 1)); else diffb=$((diffb + 1)); echo "  bytes differ: $(basename "$f") ($(cmp "$f" "$work/regen/$(basename "$f")" | head -1))"; fi
done
if [ $diffb -eq 0 ]; then echo "  ORGANIC_CHECK PASS byte-identical files: $same of $same"; else echo "  ORGANIC_CHECK FAIL byte-identical files: $same, differing: $diffb"; failed=1; fi
echo "== 4. pond edge (W1)"
gd "$project" "$work/pond.log" mode=pond
grep -E "ORGANIC_CHECK (PASS|FAIL)" "$work/pond.log" | sed 's/^/  /'
echo "logs: $work"
if [ $failed -eq 0 ]; then echo "ALL ORGANIC ART CHECKS PASSED IN GODOT"; else echo "ORGANIC ART CHECK FAILED"; fi
exit $failed
