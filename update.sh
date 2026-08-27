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

# Class 10 is playable in Adventurer Core but is not a native Playerbots class.
# Keep randombot generation on the ten stock WotLK classes and protect old
# class-10 bot rows from the stock zero-weight talent-spec path.
python3 "$ROOT/tools/playerbots_source_patch.py" install --core-dir "$core_dir"

# Dungeon Master normal mode belongs to the Adventurer experience: preserve the
# selected instance's native creatures/scripts/mechanics and scale them instead
# of clearing the instance and replacing it with a themed population.
python3 "$ROOT/tools/dungeon_master_source_patch.py" install --core-dir "$core_dir"
# Repair the first native-mode patch version in-place when upgrading an already
# patched development tree. New installs pass through this idempotently too.
python3 "$ROOT/tools/dungeon_master_source_fixup.py" install --core-dir "$core_dir"
# Dungeon Master is a level-1-to-80 game mode in Aventureros: bypass stock map
# entry requirements for its scripted teleport and expose its UI in Spanish.
python3 "$ROOT/tools/dungeon_master_experience_patch.py" install --core-dir "$core_dir"
# The upstream dungeon list is hard-coded in C++; localize those display names
# too so the dungeon-selection menu is consistently Spanish.
python3 "$ROOT/tools/dungeon_master_dungeon_names_patch.py" install --core-dir "$core_dir"

# Install editable SpellDraft runtime data beside DataDir. Existing live files
# are deliberately preserved; fresh package defaults are refreshed as *.dist.
python3 "$ROOT/tools/spelldraft_runtime.py" install "$@"

# Playerbots remains an external module, but the small-world runtime profile
# used by this project is versioned here. Only owned AiPlayerbot.* assignments
# are changed; every other Playerbots option remains untouched.
python3 "$ROOT/tools/playerbots_runtime.py" install --core-dir "$core_dir"

# Own only the Dungeon Master values that define the Adventurer experience:
# level-1 Novice, localized tier/theme names and no cooldown between runs.
python3 "$ROOT/tools/dungeon_master_runtime.py" install --core-dir "$core_dir"

# Maintenance migrations are versioned and copied into AzerothCore's normal
# pending world-update directory. Worldserver applies only those not already
# recorded by its database updater.
python3 "$ROOT/tools/world.py" install --core-dir "$core_dir"

printf '%s\n' "Adventurer Core update staged successfully. Rebuild worldserver when core, Playerbots, or Dungeon Master source changed; runtime-only SpellDraft/Playerbots/Dungeon Master config changes require only a restart."
