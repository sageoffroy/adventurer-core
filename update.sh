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

python3 "$ROOT/tools/adopt_source.py" \
  --core-dir "$core_dir" \
  --path "src/server/game/Spells/SpellEffects.cpp"

python3 "$ROOT/tools/upgrade_apply.py" "$@"

# SpellDraft v3 rebuilds the final client/server DBC bundle in one pass: normal
# Adventurer transforms, server rank-tab/component normalization, SpellIcon.dbc
# expansion and every BLP from the external icon pack.
python3 "$ROOT/tools/spelldraft_v3_icons.py" "$@"

# Keep the already-owned Item.dbc byte-identical in both Z archives after the
# v3 rebuild. This is an in-place sync and does not rebuild the icon payload.
python3 "$ROOT/tools/sync_item_dbc.py" "$@"

if (( has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_source_patch.py" install --core-dir "$core_dir"
fi

python3 "$ROOT/tools/spelldraft_runtime.py" install "$@"

if (( has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_runtime.py" install --core-dir "$core_dir"
fi

python3 "$ROOT/tools/world.py" install --core-dir "$core_dir"

if (( has_playerbots == 1 )); then
    printf '%s\n' "Adventurer Core update staged with Playerbots integration."
else
    printf '%s\n' "Adventurer Core update staged for stock AzerothCore; Playerbots integration skipped."
fi
printf '%s\n' "Rebuild worldserver when core source changed; runtime-only SpellDraft config changes require only a restart."
