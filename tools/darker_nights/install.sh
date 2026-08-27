#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="${CLIENT_DIR:-/mnt/c/Games/World of Warcraft 3.3.5a}"

python3 "$SCRIPT_DIR/build.py"
python3 "$SCRIPT_DIR/package.py" --client-dir "$CLIENT_DIR"

echo
echo "Darker Nights installed as patch-ZB.MPQ"
echo "Close and reopen WoW before testing; MPQ archives are loaded at client startup."
