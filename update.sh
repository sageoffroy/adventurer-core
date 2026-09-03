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

# SpellDraft runtime files are loaded through Worldserver's DataDir, not through
# the bundle's --server-data-dir argument. Our installed server is launched from
# env/dist/bin and currently uses DataDir=".", so resolve that setting here and
# install the catalog where the running worldserver actually reads it.
spelldraft_data_dir="$server_data_dir"
worldserver_conf="$core_dir/env/dist/etc/worldserver.conf"
if [[ -f "$worldserver_conf" ]]; then
    configured_data_dir="$(sed -nE 's/^[[:space:]]*DataDir[[:space:]]*=[[:space:]]*"?([^"#;]+)"?.*$/\1/p' "$worldserver_conf" | head -n1 | xargs || true)"
    if [[ -n "$configured_data_dir" ]]; then
        if [[ "$configured_data_dir" == "." ]]; then
            spelldraft_data_dir="$core_dir/env/dist/bin"
        elif [[ "$configured_data_dir" == /* ]]; then
            spelldraft_data_dir="$configured_data_dir"
        else
            spelldraft_data_dir="$core_dir/env/dist/bin/$configured_data_dir"
        fi
    fi
fi

# Structural SpellDraft data is source-owned. Never let an old runtime copy of
# cards/metadata/subclass mappings survive a repository update; only
# spelldraft.conf remains intentionally editable/mergeable at runtime.
runtime_dir="$spelldraft_data_dir/spelldraft"
rm -f \
  "$runtime_dir/cards.csv" \
  "$runtime_dir/catalog_metadata.csv" \
  "$runtime_dir/subclasses.json" \
  "$runtime_dir/card_subclasses.csv"

# Remove stale structural copies from the bundle data directory when it differs
# from Worldserver's actual DataDir, so there is only one authoritative runtime
# catalog to inspect and maintain.
if [[ "$spelldraft_data_dir" != "$server_data_dir" ]]; then
    stale_runtime_dir="$server_data_dir/spelldraft"
    rm -f \
      "$stale_runtime_dir/cards.csv" \
      "$stale_runtime_dir/catalog_metadata.csv" \
      "$stale_runtime_dir/subclasses.json" \
      "$stale_runtime_dir/card_subclasses.csv"
fi

# Keep all original install arguments (notably --dbc-src), then append the
# resolved core/DataDir values so argparse's final occurrence wins.
python3 "$ROOT/tools/spelldraft_runtime.py" install \
  "${args[@]}" \
  --core-dir "$core_dir" \
  --server-data-dir "$spelldraft_data_dir"

if (( has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_runtime.py" install --core-dir "$core_dir"
fi

python3 "$ROOT/tools/world.py" install --core-dir "$core_dir"

if (( has_playerbots == 1 )); then
    printf '%s\n' "Adventurer Core update staged with Playerbots integration."
else
    printf '%s\n' "Adventurer Core update staged for stock AzerothCore; Playerbots integration skipped."
fi
printf '%s\n' "SpellDraft runtime installed in Worldserver DataDir: $spelldraft_data_dir"
printf '%s\n' "Rebuild worldserver when core source changed; runtime-only SpellDraft config changes require only a restart."
