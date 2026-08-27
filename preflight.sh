#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

python3 "$ROOT/tools/database.py" preflight "$@"
exec python3 "$ROOT/tools/adventurer.py" preflight "$@"
