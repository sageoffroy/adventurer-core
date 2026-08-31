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

python3 "$ROOT/tools/database.py" prepare "$@"

status=0
python3 "$ROOT/tools/adventurer_apply_v3.py" apply "$@" || status=$?

if (( status == 0 )); then
    python3 "$ROOT/tools/spell_rank_tabs_v3.py" install "$@" || status=$?
fi

if (( status == 0 && has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_source_patch.py" install --core-dir "$core_dir" || status=$?
fi

if (( status == 0 )); then
    python3 "$ROOT/tools/spelldraft_runtime.py" install "$@" || status=$?
fi

if (( status == 0 && has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_runtime.py" install --core-dir "$core_dir" || status=$?
fi

if (( status == 0 )); then
    python3 "$ROOT/tools/world.py" install --core-dir "$core_dir" || status=$?
fi

finalize_status=0
python3 "$ROOT/tools/database.py" finalize "$@" || finalize_status=$?

if (( status != 0 )); then
    exit "$status"
fi
if (( finalize_status != 0 )); then
    exit "$finalize_status"
fi

if (( has_playerbots == 1 )); then
    printf '%s\n' "Playerbots detected: compatibility source/profile installed."
else
    printf '%s\n' "Stock AzerothCore detected: Playerbots integration skipped."
fi
printf '%s\n' "SpellDraft v3 icon bundle staged through the normal Adventurer client pipeline."
printf '%s\n' "Database rollback snapshot is attached and verified for this installation."
