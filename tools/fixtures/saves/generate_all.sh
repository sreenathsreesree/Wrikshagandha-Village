#!/usr/bin/env bash
# Regenerates the old-save fixtures (M15.3) from the project's own history.
# Each save format is written by the commit that introduced it, running that
# commit's own code: the tree is exported read-only (git archive) into a
# temporary folder, imported, and generate_save_fixture.gd plays a short
# scripted session through its public API and saves with its own SaveManager.
# Nothing in the working tree is touched except tools/fixtures/saves/v<N>/.
# Usage: GODOT=/path/to/Godot_v4.7.2 tools/fixtures/saves/generate_all.sh [v0 v1 ...]
set -uo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
repo="$(cd "$here/../../.." && pwd)"
godot="${GODOT:-godot}"
# version  commit   milestone (the commit that introduced that save format)
COMMITS="v0:b76e49c:M03.6 v1:c8bca2a:M04.0 v2:b14b77a:M04.2 v3:a4939ed:M04.3 v4:da04f52:M05.1 v5:b1891cf:M05.2 v6:8f77507:M08.5 v7:5416083:M08.6 v8:adb284c:M09.2 v9:bcdf2ed:M14.1a"
want="${*:-}"
failed=0
for entry in $COMMITS; do
  v="${entry%%:*}"; rest="${entry#*:}"; commit="${rest%%:*}"; milestone="${rest#*:}"
  if [ -n "$want" ] && ! [[ " $want " == *" $v "* ]]; then continue; fi
  tmp="$(mktemp -d)"; data="$(mktemp -d)"
  (cd "$repo" && git archive "$commit") | tar -x -C "$tmp"
  cp "$here/generate_save_fixture.gd" "$tmp/generate_save_fixture.gd"
  timeout 600 "$godot" --headless --editor --quit --path "$tmp" > "$tmp/import.log" 2>&1
  out="$here/$v"; mkdir -p "$out"; rm -f "$out/save.json" "$out/expected.json" "$out/calls.json"
  XDG_DATA_HOME="$data" timeout 600 "$godot" --headless --path "$tmp" -s res://generate_save_fixture.gd -- "out=$out" > "$tmp/gen.log" 2>&1
  errors=$(grep -c "SCRIPT ERROR" "$tmp/gen.log")
  if grep -q "FIXTURE_GEN OK" "$tmp/gen.log" && [ "$errors" -eq 0 ] && [ -s "$out/save.json" ]; then
    printf '{"version": "%s", "commit": "%s", "milestone": "%s", "subject": "%s", "generator": "tools/fixtures/saves/generate_save_fixture.gd", "godot": "%s"}\n' \
      "$v" "$commit" "$milestone" "$(cd "$repo" && git log -1 --format=%s "$commit" | sed 's/"/\\"/g')" "$("$godot" --version 2>/dev/null | head -1)" > "$out/meta.json"
    echo "OK   $v $commit ($milestone)"
  else
    echo "FAIL $v $commit ($milestone): script errors $errors; $(grep -E 'FIXTURE_GEN|SCRIPT ERROR' "$tmp/gen.log" | head -3 | tr '\n' ' ')"
    cp "$tmp/gen.log" "$out/generator_failure.log"
    failed=1
  fi
  rm -rf "$tmp" "$data"
done
exit $failed
