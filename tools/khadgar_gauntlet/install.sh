#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE_DIR="${CORE_DIR:-$HOME/aventurerosdeazeroth}"
SRC_DIR="$ROOT_DIR/modules/mod-adventurer-gauntlet"
DST_DIR="$CORE_DIR/modules/mod-adventurer-gauntlet"
ITEM_CATALOG="$SRC_DIR/data/items/early_items.csv"
ITEM_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/generate_items.py"
ITEM_SQL="$DST_DIR/data/sql/db-world/updates/2026_08_29_10_adventurer_gauntlet_items.generated.sql"

if [[ ! -d "$CORE_DIR/modules" ]]; then
  echo "ERROR: AzerothCore modules directory not found: $CORE_DIR/modules" >&2
  exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "ERROR: module source not found: $SRC_DIR" >&2
  exit 1
fi

if [[ ! -f "$ITEM_CATALOG" ]]; then
  echo "ERROR: gauntlet item catalog not found: $ITEM_CATALOG" >&2
  exit 1
fi

if [[ ! -f "$ITEM_GENERATOR" ]]; then
  echo "ERROR: gauntlet item generator not found: $ITEM_GENERATOR" >&2
  exit 1
fi

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required to generate gauntlet items" >&2
  exit 1
fi

rm -rf "$DST_DIR"
cp -a "$SRC_DIR" "$DST_DIR"

python3 "$ITEM_GENERATOR" \
  --input "$ITEM_CATALOG" \
  --output "$ITEM_SQL"

echo
echo "Adventurer Gauntlet installed into: $DST_DIR"
echo "Khadgar template entry: 910000"
echo "Expedition chest entry: 910001"
echo "Custom item range: 911000-911999"
echo "Item catalog: $ITEM_CATALOG"
echo "Next: rerun CMake if needed, build with make -j2, then make install."
