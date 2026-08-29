#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CORE_DIR="${CORE_DIR:-$HOME/aventurerosdeazeroth}"
DBC_SRC="${DBC_SRC:-}"
CLIENT_DIR="${CLIENT_DIR:-}"
LOCALE="${LOCALE:-esMX}"
SRC_DIR="$ROOT_DIR/modules/mod-adventurer-gauntlet"
DST_DIR="$CORE_DIR/modules/mod-adventurer-gauntlet"
ITEM_CATALOG="$SRC_DIR/data/items/early_items.csv"
SET_CATALOG="$SRC_DIR/data/items/sets.csv"
ITEM_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/generate_items.py"
SET_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/generate_sets.py"
CLIENT_GENERATOR="$ROOT_DIR/tools/khadgar_gauntlet/client_items.py"
ITEM_SQL="$DST_DIR/data/sql/db-world/updates/2026_08_29_10_adventurer_gauntlet_items.generated.sql"
SET_INCLUDE="$DST_DIR/src/GeneratedGauntletSets.inc"

if [[ ! -d "$CORE_DIR/modules" ]]; then
  echo "ERROR: AzerothCore modules directory not found: $CORE_DIR/modules" >&2
  exit 1
fi

if [[ ! -d "$SRC_DIR" ]]; then
  echo "ERROR: module source not found: $SRC_DIR" >&2
  exit 1
fi

for required in "$ITEM_CATALOG" "$SET_CATALOG" "$ITEM_GENERATOR" "$SET_GENERATOR"; do
  if [[ ! -f "$required" ]]; then
    echo "ERROR: required gauntlet catalog/generator not found: $required" >&2
    exit 1
  fi
done

if ! command -v python3 >/dev/null 2>&1; then
  echo "ERROR: python3 is required to generate gauntlet items and sets" >&2
  exit 1
fi

rm -rf "$DST_DIR"
cp -a "$SRC_DIR" "$DST_DIR"

python3 "$ITEM_GENERATOR" \
  --input "$ITEM_CATALOG" \
  --output "$ITEM_SQL"

python3 "$SET_GENERATOR" \
  --items "$ITEM_CATALOG" \
  --sets "$SET_CATALOG" \
  --output "$SET_INCLUDE"

if [[ -n "$DBC_SRC" || -n "$CLIENT_DIR" ]]; then
  if [[ -z "$DBC_SRC" || -z "$CLIENT_DIR" ]]; then
    echo "ERROR: DBC_SRC and CLIENT_DIR must be supplied together for client item installation" >&2
    exit 1
  fi
  if [[ ! -f "$CLIENT_GENERATOR" ]]; then
    echo "ERROR: client item generator not found: $CLIENT_GENERATOR" >&2
    exit 1
  fi

  python3 "$CLIENT_GENERATOR" \
    --items "$ITEM_CATALOG" \
    --sets "$SET_CATALOG" \
    --dbc-src "$DBC_SRC" \
    --client-dir "$CLIENT_DIR" \
    --locale "$LOCALE"
fi

echo
echo "Adventurer Gauntlet installed into: $DST_DIR"
echo "Khadgar template entry: 910000"
echo "Expedition chest entry: 910001"
echo "Custom item range: 911000-911999"
echo "Item catalog: $ITEM_CATALOG"
echo "Set catalog: $SET_CATALOG"
if [[ -n "$CLIENT_DIR" ]]; then
  echo "Gauntlet client patch: $CLIENT_DIR/Data/patch-X.MPQ"
  echo "Gauntlet set tooltip addon installed into client Interface/AddOns."
fi
echo "Next: rebuild only when C++ changed; CSV/SQL/client-only changes need a restart."
