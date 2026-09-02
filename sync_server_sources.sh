#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CORE_DIR="${1:-$HOME/aventurerosdeazeroth}"
SOURCE="$ROOT/modules/mod-adventurer-gauntlet"
TARGET="$CORE_DIR/modules/mod-adventurer-gauntlet"

if [[ ! -d "$SOURCE" ]]; then
    echo "ERROR: Gauntlet module source not found: $SOURCE" >&2
    exit 1
fi

if [[ ! -d "$CORE_DIR/modules" ]]; then
    echo "ERROR: AzerothCore modules directory not found: $CORE_DIR/modules" >&2
    exit 1
fi

echo "Syncing server module:"
echo "  from: $SOURCE"
echo "  to:   $TARGET"

rm -rf "$TARGET"
cp -a "$SOURCE" "$TARGET"

echo "Server sources synchronized."
