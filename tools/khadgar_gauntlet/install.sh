#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE_DIR="${CORE_DIR:-$HOME/aventurerosdeazeroth}"
SERVER_DATA_DIR="${SERVER_DATA_DIR:-$CORE_DIR/env/dist/bin}"
CLIENT_DIR="${CLIENT_DIR:-/mnt/c/Games/World of Warcraft 3.3.5a}"
SRC_DIR="$ROOT_DIR/modules/mod-adventurer-gauntlet"
DST_DIR="$CORE_DIR/modules/mod-adventurer-gauntlet"
ITEM_CATALOG="$DST_DIR/data/items/early_items.csv"
SET_CATALOG="$DST_DIR/data/items/sets.csv"
CATALOG_BUILDER="$ROOT_DIR/tools/khadgar_gauntlet/build_catalog.py"
ITEM_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/generate_items.py"
SET_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/generate_sets.py"
DBC_PATCHER="$ROOT_DIR/tools/khadgar_gauntlet/patch_item_dbc.py"
ITEM_SQL="$DST_DIR/data/sql/db-world/updates/2026_08_30_02_adventurer_gauntlet_items.generated.sql"
SET_INCLUDE="$DST_DIR/src/GeneratedGauntletSets.inc"

if [[ ! -d "$CORE_DIR/modules" ]]; then
  echo "ERROR: AzerothCore modules directory not found: $CORE_DIR/modules" >&2
  exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "ERROR: module source not found: $SRC_DIR" >&2
  exit 1
fi

for required in "$CATALOG_BUILDER" "$ITEM_GENERATOR" "$SET_GENERATOR" "$DBC_PATCHER"; do
  if [[ ! -f "$required" ]]; then
    echo "ERROR: required Gauntlet generator not found: $required" >&2
    exit 1
  fi
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required to generate Gauntlet rewards" >&2
  exit 1
fi

rm -rf "$DST_DIR"
cp -a "$SRC_DIR" "$DST_DIR"

python3 "$CATALOG_BUILDER" \
  --items "$ITEM_CATALOG" \
  --sets "$SET_CATALOG"

python3 "$ITEM_GENERATOR" \
  --input "$ITEM_CATALOG" \
  --output "$ITEM_SQL"

python3 "$SET_GENERATOR" \
  --items "$ITEM_CATALOG" \
  --sets "$SET_CATALOG" \
  --output "$SET_INCLUDE"

# The server and client must know the same custom Item.dbc rows or Gauntlet
# rewards degrade to red '?' icons. Patch the final runtime DBC and rebuild the
# already-owned Adventurer Z patches when the normal local installation exists.
if [[ -f "$SERVER_DATA_DIR/dbc/Item.dbc" && -d "$CLIENT_DIR" ]]; then
  python3 "$DBC_PATCHER" \
    --catalog "$ITEM_CATALOG" \
    --dbc "$SERVER_DATA_DIR/dbc/Item.dbc"

  python3 "$ROOT_DIR/tools/sync_item_dbc.py" \
    --core-dir "$CORE_DIR" \
    --server-data-dir "$SERVER_DATA_DIR" \
    --client-dir "$CLIENT_DIR"
else
  echo "WARNING: runtime Item.dbc/client not found; Gauntlet client item metadata was not installed." >&2
fi

echo
echo "Adventurer Gauntlet installed into: $DST_DIR"
echo "Khadgar template entry: 910000"
echo "Expedition chest entry: 910001"
echo "Controlled custom rewards: 300 (100 set pieces, blue/purple only)"
echo "Green rewards: random stock world pool"
echo "Custom item range used: 911100-911399"
echo "Generated item catalog: $ITEM_CATALOG"
echo "Generated set catalog: $SET_CATALOG"
echo "Next: build with make -j2, make install, then start worldserver to apply the new item migration."
