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

has_playerbots=0
if [[ -d "$core_dir/modules/mod-playerbots" ]]; then
    has_playerbots=1
fi

# Refuse before touching anything if the snapshot is damaged, the configured
# databases changed, recoverable class-10 characters still exist, or an owned
# file was edited outside Adventurer Core.
python3 "$ROOT/tools/database.py" can-rollback "$@"
python3 "$ROOT/tools/adventurer.py" verify "$@"
if (( has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_source_patch.py" verify --core-dir "$core_dir"
    python3 "$ROOT/tools/playerbots_runtime.py" verify --core-dir "$core_dir"
fi

# Restore class-10 world rows first while the original snapshot is still
# attached to .adventurer-core.
python3 "$ROOT/tools/database.py" restore "$@"

# Updates 002+ were introduced after some existing rollback snapshots had
# already been created. Their identifiers are package-owned, so clean them
# explicitly and deterministically.
python3 "$ROOT/tools/world.py" cleanup-db --core-dir "$core_dir"
python3 "$ROOT/tools/world.py" remove --core-dir "$core_dir"

# Remove unedited SpellDraft runtime defaults. User-edited live files are kept
# with a warning instead of being destroyed during rollback.
python3 "$ROOT/tools/spelldraft_runtime.py" remove "$@"

if (( has_playerbots == 1 )); then
    # Restore the exact playerbots.conf captured before Adventurer Core first
    # took ownership of its small managed key set.
    python3 "$ROOT/tools/playerbots_runtime.py" rollback --core-dir "$core_dir"

    # Restore the exact Playerbots source anchors owned by Adventurer Core.
    python3 "$ROOT/tools/playerbots_source_patch.py" rollback --core-dir "$core_dir"
fi

# Restore original source, DBCs and client patches. This understands both the
# original .adventurer-backup DBC suffix and the current package state.
python3 "$ROOT/tools/package_rollback.py" "$@"

if (( has_playerbots == 1 )); then
    printf '%s\n' "Adventurer Core fully rolled back: source, DBC, client patch, Playerbots integration, world updates, and world DB restored."
else
    printf '%s\n' "Adventurer Core fully rolled back: source, DBC, client patch, world updates, and world DB restored."
fi
