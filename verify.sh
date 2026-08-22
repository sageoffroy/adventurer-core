#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

python3 "$ROOT/tools/database.py" verify "$@"
exec python3 "$ROOT/tools/adventurer.py" verify "$@"
