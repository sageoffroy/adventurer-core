#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

# Prepare the DB rollback snapshot before any source/client/runtime mutation.
python3 "$ROOT/tools/database.py" prepare "$@"

status=0
python3 "$ROOT/tools/adventurer.py" apply "$@" || status=$?

# If apply created Adventurer state, attach the snapshot to it. If apply failed
# before mutating anything, finalize safely removes the temporary snapshot.
finalize_status=0
python3 "$ROOT/tools/database.py" finalize "$@" || finalize_status=$?

if (( status != 0 )); then
    exit "$status"
fi
if (( finalize_status != 0 )); then
    exit "$finalize_status"
fi

printf '%s\n' "Database rollback snapshot is attached and verified for this installation."
