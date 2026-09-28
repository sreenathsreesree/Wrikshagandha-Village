#!/usr/bin/env bash
# Downloads Godot 4.7.2 API data (TypeScript bindings generated from Godot's
# extension_api.json, npm package @ringozz/godot) into tools/.cache/ for
# tools/check_gdscript.py. Data only: nothing from the package is executed.
# The package is a third-party build with no declared license, so it is
# fetched on demand and never committed (tools/.cache/ is git-ignored).
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
dest="$here/.cache/godot-api"
version="${GODOT_API_VERSION:-4.7.2-626}"
mkdir -p "$dest"
curl -sSfL --max-time 180 -o "$dest/godot.tgz" \
  "https://registry.npmjs.org/@ringozz/godot/-/godot-${version}.tgz"
tar xzf "$dest/godot.tgz" -C "$dest"
rm -f "$dest/godot.tgz"
echo "Godot API data ready in $dest/package/gen"
