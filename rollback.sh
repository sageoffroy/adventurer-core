#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Refuse before touching anything if the snapshot is damaged, the configured
# databases changed, or recoverable class-10 characters still exist.
python3 "$ROOT/tools/database.py" can-rollback "$@"
python3 "$ROOT/tools/adventurer.py" verify "$@"

# Restore DB first while every rollback artifact still exists. The restore SQL
# is idempotent, so an interrupted file rollback can be retried safely.
python3 "$ROOT/tools/database.py" restore "$@"

python3 "$ROOT/tools/adventurer.py" rollback "$@" \
    | sed '/Database rows already applied by worldserver are intentionally not modified\./d'

printf '%s\n' "Adventurer Core fully rolled back: source, DBC, client patch, and world DB restored."
