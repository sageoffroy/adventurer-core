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
SPELL_PATCHER="$ROOT_DIR/tools/khadgar_gauntlet/patch_spell_dbc.py"
STASH_ADDON_SOURCE="$ROOT_DIR/tools/khadgar_gauntlet/AdventurerGauntletStash.lua"
MINIMAP_FIX_SOURCE="$ROOT_DIR/tools/khadgar_gauntlet/AdventurerMinimapFix.lua"
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

for required in "$CATALOG_BUILDER" "$ITEM_GENERATOR" "$SET_GENERATOR" "$DBC_PATCHER" "$SPELL_PATCHER" "$STASH_ADDON_SOURCE" "$MINIMAP_FIX_SOURCE"; do
  if [[ ! -f "$required" ]]; then
    echo "ERROR: required Gauntlet file not found: $required" >&2
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

if [[ -f "$SERVER_DATA_DIR/dbc/Item.dbc" && -f "$SERVER_DATA_DIR/dbc/Spell.dbc" && -d "$CLIENT_DIR" ]]; then
  python3 "$DBC_PATCHER" \
    --catalog "$ITEM_CATALOG" \
    --dbc "$SERVER_DATA_DIR/dbc/Item.dbc"

  python3 "$SPELL_PATCHER" \
    --dbc "$SERVER_DATA_DIR/dbc/Spell.dbc"

  python3 "$ROOT_DIR/tools/sync_item_dbc.py" \
    --core-dir "$CORE_DIR" \
    --server-data-dir "$SERVER_DATA_DIR" \
    --client-dir "$CLIENT_DIR"
else
  echo "WARNING: runtime DBC/client not found; Gauntlet client metadata was not installed." >&2
fi

ADDON_DIR="$CLIENT_DIR/Interface/AddOns/AdventurerGauntlet"
mkdir -p "$ADDON_DIR"
cat > "$ADDON_DIR/AdventurerGauntlet.toc" <<'EOF'
## Interface: 30300
## Title: Adventurer Gauntlet
## Notes: Account stash and minimap integration for Aventureros de Azeroth.
AdventurerGauntletStash.lua
AdventurerMinimapFix.lua
EOF
cp "$STASH_ADDON_SOURCE" "$ADDON_DIR/AdventurerGauntletStash.lua"
cp "$MINIMAP_FIX_SOURCE" "$ADDON_DIR/AdventurerMinimapFix.lua"

echo
echo "Adventurer Gauntlet installed into: $DST_DIR"
echo "Khadgar template entry: 910000"
echo "Expedition reward chest entry: 910001"
echo "Account stash entry: 910002"
echo "Controlled custom rewards: 300 (230 rare, 50 epic, 20 legendary)"
echo "Early epic/legendary discovery pool: levels 3-15"
echo "Green rewards: random stock world pool"
echo "Custom item range used: 911100-911399"
echo "Account stash + minimap integration installed into Interface/AddOns/AdventurerGauntlet"
echo "Next: build with make -j2, make install, then start worldserver to apply pending migrations."
