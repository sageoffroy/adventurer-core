#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

core_dir=""
server_data_dir=""
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
        --server-data-dir)
            if (( i + 1 < ${#args[@]} )); then
                server_data_dir="${args[$((i + 1))]}"
            fi
            ;;
        --server-data-dir=*)
            server_data_dir="${args[$i]#*=}"
            ;;
    esac
done

if [[ -z "$core_dir" ]]; then
    printf '%s\n' "ERROR: --core-dir is required" >&2
    exit 2
fi

if [[ -z "$server_data_dir" ]]; then
    server_data_dir="$core_dir/env/dist/data"
fi

has_playerbots=0
if [[ -d "$core_dir/modules/mod-playerbots" ]]; then
    has_playerbots=1
fi

python3 "$ROOT/tools/adopt_source.py" \
  --core-dir "$core_dir" \
  --path "src/server/game/Spells/SpellEffects.cpp"

python3 "$ROOT/tools/upgrade_apply.py" "$@"

# Stage owned gameplay modules before the final client/server bundle.
python3 "$ROOT/tools/khadgar_gauntlet/stage.py" "$@"
python3 "$ROOT/tools/spelldraft_v4_stage.py" --core-dir "$core_dir"

# A newly staged AzerothCore module is invisible to an already-configured build
# tree until CMake regenerates it. Reconfigure in place when this installation
# already has a build directory; cached build options are preserved.
build_dir="$core_dir/build"
if [[ -f "$build_dir/CMakeCache.txt" ]]; then
    cmake -S "$core_dir" -B "$build_dir"
fi

# One authoritative client/server build for Aventurero + SpellDraft + Gauntlet.
# Every DBC transform and external icon is applied before the final server DBCs
# and client Z patches are installed.
python3 "$ROOT/tools/build_client_bundle.py" "$@"

if (( has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_source_patch.py" install --core-dir "$core_dir"
fi

# Structural SpellDraft data is source-owned. Never let an old runtime copy of
# cards/metadata/subclass mappings survive a repository update; only
# spelldraft.conf remains intentionally editable/mergeable at runtime.
runtime_dir="$server_data_dir/spelldraft"
rm -f \
  "$runtime_dir/cards.csv" \
  "$runtime_dir/catalog_metadata.csv" \
  "$runtime_dir/subclasses.json" \
  "$runtime_dir/card_subclasses.csv"

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
