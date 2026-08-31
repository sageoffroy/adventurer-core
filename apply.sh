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

# Prepare the DB rollback snapshot before any source/client/runtime mutation.
python3 "$ROOT/tools/database.py" prepare "$@"

# Core compatibility is determined by exact source anchors/APIs, not a frozen
# Git SHA. The wrapper keeps the normal Adventurer transaction but also extends
# the atomic client/server DBC bundle with Item.dbc rows for our custom
# contraband equipment.
status=0
python3 "$ROOT/tools/adventurer_apply.py" apply "$@" || status=$?

# Active spell ranks are upgraded by AzerothCore from db_world.spell_ranks.
# Mirror that exact server chain into the four custom SkillLineAbility tabs so
# automatically learned higher ranks stay in the same subclass spellbook tab.
if (( status == 0 )); then
    python3 "$ROOT/tools/spell_rank_tabs.py" install "$@" || status=$?
fi

# SpellDraft v3 overlays the external BLP pack into the owned Z patch and extends
# SpellIcon.dbc for paths that do not exist in stock 3.3.5a. The default pack
# location is ~/adventurer-icons/Interface/Icons.
if (( status == 0 )); then
    python3 "$ROOT/tools/spelldraft_v3_icons.py" "$@" || status=$?
fi

# Playerbots integration is optional. A stock AzerothCore checkout has no
# modules/mod-playerbots directory and must install Adventurer Core without it.
if (( status == 0 && has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_source_patch.py" install --core-dir "$core_dir" || status=$?
fi

# SpellDraft balance/catalog data is intentionally outside the compiled C++.
# Install editable live copies only after the core/client transaction succeeded.
if (( status == 0 )); then
    python3 "$ROOT/tools/spelldraft_runtime.py" install "$@" || status=$?
fi

# Apply the versioned small-world Playerbots profile only when the module exists.
if (( status == 0 && has_playerbots == 1 )); then
    python3 "$ROOT/tools/playerbots_runtime.py" install --core-dir "$core_dir" || status=$?
fi

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

if (( has_playerbots == 1 )); then
    printf '%s\n' "Playerbots detected: compatibility source/profile installed."
else
    printf '%s\n' "Stock AzerothCore detected: Playerbots integration skipped."
fi
printf '%s\n' "Database rollback snapshot is attached and verified for this installation."
