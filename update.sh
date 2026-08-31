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

# SpellDraft now owns the narrow native Tame Beast class gate in SpellEffects.cpp.
# Existing installs created before that file was package-owned adopt it once,
# only while it is clean and still belongs to the same AzerothCore commit. The
# original bytes are stored in the normal Adventurer rollback backup first.
python3 "$ROOT/tools/adopt_source.py" \
  --core-dir "$core_dir" \
  --path "src/server/game/Spells/SpellEffects.cpp"

# Upgrade only Adventurer-owned source/runtime/client state. The original clean
# installation backups remain untouched, so rollback still returns all the way
# to the pre-Adventurer server rather than merely to the previous package build.
# The wrapper also applies the current Item.dbc contraband metadata and 75%
# universal-chassis transform as part of the same owned upgrade transaction.
python3 "$ROOT/tools/upgrade_apply.py" "$@"

# Active spell ranks are upgraded by AzerothCore from db_world.spell_ranks.
# Mirror that exact server chain into the four custom SkillLineAbility tabs so
# automatically learned higher ranks never fall back into another spell tab.
python3 "$ROOT/tools/spell_rank_tabs.py" install "$@"

# spell_rank_tabs rebuilds both owned Z archives from the installed server DBC
# bundle. Preserve the Adventurer custom Item.dbc in that final rebuilt client
# payload and refresh ownership hashes so client/server item metadata stays
# byte-identical after every update.
python3 "$ROOT/tools/sync_item_dbc.py" "$@"

# SpellDraft v3 overlays the external BLP pack into the owned Z patch and extends
# SpellIcon.dbc for icon paths that do not exist in stock 3.3.5a. The pack lives
# outside Git by default at ~/adventurer-icons/Interface/Icons.
python3 "$ROOT/tools/spelldraft_v3_icons.py" "$@"

# Class 10 needs Playerbots-specific guards only when the external module exists.
if (( has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_source_patch.py" install --core-dir "$core_dir"
fi

# Install editable SpellDraft runtime data beside DataDir. Existing live files
# are deliberately preserved; fresh package defaults are refreshed as *.dist.
python3 "$ROOT/tools/spelldraft_runtime.py" install "$@"

if (( has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_runtime.py" install --core-dir "$core_dir"
fi

# Maintenance migrations are versioned and copied into AzerothCore's normal
# pending world-update directory. Worldserver applies only those not already
# recorded by its database updater.
python3 "$ROOT/tools/world.py" install --core-dir "$core_dir"

if (( has_playerbots == 1 )); then
    printf '%s\n' "Adventurer Core update staged with Playerbots integration."
else
    printf '%s\n' "Adventurer Core update staged for stock AzerothCore; Playerbots integration skipped."
fi
printf '%s\n' "Rebuild worldserver when core source changed; runtime-only SpellDraft config changes require only a restart."
