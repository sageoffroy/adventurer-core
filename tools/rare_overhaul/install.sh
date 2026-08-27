#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE_DIR="${CORE_DIR:-$HOME/aventurerosdeazeroth}"
MODULE_SOURCE="$REPO_ROOT/modules/mod-rare-overhaul"
MODULE_TARGET="$CORE_DIR/modules/mod-rare-overhaul"
UPSTREAM_REPO="https://github.com/StraysFromPath/mod-rare-drops.git"
UPSTREAM_COMMIT="cf6ea06d32d751328836b65d9b7270975aa3c68a"

if [[ ! -d "$CORE_DIR/modules" ]]; then
    echo "ERROR: AzerothCore modules directory not found: $CORE_DIR/modules" >&2
    exit 1
fi

if [[ ! -f "$MODULE_SOURCE/CMakeLists.txt" ]]; then
    echo "ERROR: Rare Overhaul module source not found: $MODULE_SOURCE" >&2
    exit 1
fi

TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

echo "Fetching pinned rare-loot dataset..."
git clone -q "$UPSTREAM_REPO" "$TMP_DIR/mod-rare-drops"
git -C "$TMP_DIR/mod-rare-drops" checkout -q --detach "$UPSTREAM_COMMIT"

rm -rf "$MODULE_TARGET"
mkdir -p "$MODULE_TARGET"
cp -a "$MODULE_SOURCE/." "$MODULE_TARGET/"

mkdir -p "$MODULE_TARGET/data/sql/db-world/base"
cp "$TMP_DIR/mod-rare-drops/data/sql/db-world/updates/mod rare drops final.sql" \
   "$MODULE_TARGET/data/sql/db-world/base/rare_overhaul_loot.sql"
cp "$TMP_DIR/mod-rare-drops/LICENSE" "$MODULE_TARGET/LICENSE.rare-drops"

# Keep the upstream data intact; only tag its loot comments with the installed module name.
sed -i 's/mod-rare-drops/mod-rare-overhaul/g' \
    "$MODULE_TARGET/data/sql/db-world/base/rare_overhaul_loot.sql"

echo
echo "Rare Overhaul installed into: $MODULE_TARGET"
echo "Loot source pinned at: StraysFromPath/mod-rare-drops@$UPSTREAM_COMMIT"
echo "Runtime defaults: Rare/Rare Elite health x2, damage x2"
echo
echo "Next: rerun CMake, build with make -j2, then make install."
