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

# Gauntlet module/catalog/addon staging is shared with apply.sh. It does not
# build or install DBC/MPQ artifacts; the final bundle is built once below.
python3 "$ROOT/tools/khadgar_gauntlet/stage.py" "$@"

# One authoritative client/server build for Aventurero + SpellDraft v3 +
# Gauntlet. Every DBC transform and external icon is applied before the final
# server DBCs and client Z patches are installed.
python3 "$ROOT/tools/build_client_bundle.py" "$@"

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
