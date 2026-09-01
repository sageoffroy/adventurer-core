#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE_DIR="${CORE_DIR:-$HOME/aventurerosdeazeroth}"
SERVER_DATA_DIR="${SERVER_DATA_DIR:-$CORE_DIR/env/dist/data}"
DBC_SRC="${DBC_SRC:-$HOME/dbc-clean-esMX/dbc/esMX}"
CLIENT_DIR="${CLIENT_DIR:-/mnt/c/Games/World of Warcraft 3.3.5a}"
SRC_DIR="$ROOT_DIR/modules/mod-adventurer-gauntlet"
DST_DIR="$CORE_DIR/modules/mod-adventurer-gauntlet"
ITEM_CATALOG="$DST_DIR/data/items/early_items.csv"
SET_CATALOG="$DST_DIR/data/items/sets.csv"
CATALOG_BUILDER="$ROOT_DIR/tools/khadgar_gauntlet/build_catalog.py"
ITEM_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/generate_items.py"
SET_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/generate_sets.py"
CLIENT_V3_INSTALLER="$ROOT_DIR/tools/khadgar_gauntlet/install_client_v3.py"
BANK_ADDON_SOURCE="$ROOT_DIR/tools/khadgar_gauntlet/AdventurerGauntletBank.lua"
BOOK_ADDON_SOURCE="$ROOT_DIR/tools/khadgar_gauntlet/AdventurerGauntletBook.lua"
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

for required in "$CATALOG_BUILDER" "$ITEM_GENERATOR" "$SET_GENERATOR" "$CLIENT_V3_INSTALLER" "$BANK_ADDON_SOURCE" "$BOOK_ADDON_SOURCE" "$MINIMAP_FIX_SOURCE"; do
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

printf '%s\n' "$(realpath -m "$SERVER_DATA_DIR")" > "$DST_DIR/.server-data-dir"

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

if [[ -f "$SERVER_DATA_DIR/dbc/Item.dbc" && -f "$SERVER_DATA_DIR/dbc/Spell.dbc" && -d "$DBC_SRC" && -d "$CLIENT_DIR" ]]; then
  python3 "$CLIENT_V3_INSTALLER" \
    --core-dir "$CORE_DIR" \
    --dbc-src "$DBC_SRC" \
    --server-data-dir "$SERVER_DATA_DIR" \
    --client-dir "$CLIENT_DIR" \
    --locale esMX

  # One authoritative final DBC pass. sync_item_dbc.py rebuilds the 300
  # Gauntlet Item.dbc rows directly from build_catalog.py, reapplies Gauntlet
  # Spell.dbc rows, and then writes the exact same final DBC payloads to the
  # runtime server directory and both owned Z client archives.
  python3 "$ROOT_DIR/tools/sync_item_dbc.py" \
    --core-dir "$CORE_DIR" \
    --server-data-dir "$SERVER_DATA_DIR" \
    --client-dir "$CLIENT_DIR"
else
  echo "WARNING: runtime DBC/client/clean DBC source not found; Gauntlet client metadata was not installed." >&2
fi

ADDON_DIR="$CLIENT_DIR/Interface/AddOns/AdventurerGauntlet"
mkdir -p "$ADDON_DIR"
rm -f "$ADDON_DIR/AdventurerGauntletStash.lua"
cat > "$ADDON_DIR/AdventurerGauntlet.toc" <<'EOF'
## Interface: 30300
## Title: Adventurer Gauntlet
## Notes: Gauntlet account bank, item collection and client integration for Aventureros de Azeroth.
AdventurerGauntletBank.lua
AdventurerGauntletBook.lua
AdventurerMinimapFix.lua
EOF
cp "$BANK_ADDON_SOURCE" "$ADDON_DIR/AdventurerGauntletBank.lua"
cp "$BOOK_ADDON_SOURCE" "$ADDON_DIR/AdventurerGauntletBook.lua"
cp "$MINIMAP_FIX_SOURCE" "$ADDON_DIR/AdventurerMinimapFix.lua"

echo
echo "Adventurer Gauntlet installed into: $DST_DIR"
echo "Runtime data dir pinned for final DBC patch: $(cat "$DST_DIR/.server-data-dir")"
echo "Khadgar template entry: 910000"
echo "Account bank entry: 910002"
echo "Lone Wolf aura: 910501"
echo "Account item book: /libro or /objetos"
echo "Custom item discovery range: 911100-911399"
echo "Gauntlet addon installed into Interface/AddOns/AdventurerGauntlet"
echo "Next: build with make -j2, make install, then start worldserver to apply pending migrations."
