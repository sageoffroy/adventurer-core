#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

core_dir=""
args=("$@")
for ((i=0; i<${#args[@]}; i++)); do
    case "${args[$i]}" in
        --core-dir)
            if (( i + 1 < ${#args[@]} )); then
                core_dir="${args[$((i + 1))]}"
            fi
            ;;
        --core-dir=*)
            core_dir="${args[$i]#*=}"
            ;;
    esac
done

if [[ -z "$core_dir" ]]; then
    printf '%s\n' "ERROR: --core-dir is required" >&2
    exit 2
fi

# Prepare the DB rollback snapshot before any source/client/runtime mutation.
python3 "$ROOT/tools/database.py" prepare "$@"

status=0
python3 "$ROOT/tools/adventurer.py" apply "$@" || status=$?

# Versioned maintenance migrations are part of the official clean install.
# Existing development installations can run tools/world.py directly, but a
# fresh apply never depends on remembering that extra step.
if (( status == 0 )); then
    python3 "$ROOT/tools/world.py" install --core-dir "$core_dir" || status=$?
fi

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
