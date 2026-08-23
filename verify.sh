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

# Database verification needs the runtime/config arguments supplied by the
# caller. The package-state verifier only accepts --core-dir, so do not forward
# unrelated client/server-data/locale options to it.
python3 "$ROOT/tools/database.py" verify "$@"
python3 "$ROOT/tools/adventurer.py" verify --core-dir "$core_dir"
python3 "$ROOT/tools/world.py" verify --core-dir "$core_dir"
