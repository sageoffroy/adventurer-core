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

# Upgrade only Adventurer-owned source/runtime/client state. The original clean
# installation backups remain untouched, so rollback still returns all the way
# to the pre-Adventurer server rather than merely to the previous package build.
python3 "$ROOT/tools/upgrade.py" "$@"

# Maintenance migrations are versioned and copied into AzerothCore's normal
# pending world-update directory. Worldserver applies only those not already
# recorded by its database updater.
python3 "$ROOT/tools/world.py" install --core-dir "$core_dir"

printf '%s\n' "Adventurer Core update staged successfully. Rebuild worldserver and restart it to activate the new core/database state."
