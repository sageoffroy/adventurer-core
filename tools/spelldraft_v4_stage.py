#!/usr/bin/env python3
"""Stage SpellDraft v4 runtime code and its owned world-data update."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MODULE_SOURCE = ROOT / "modules" / "mod-adventurer-spelldraft"
WORLD_SQL_SOURCE = MODULE_SOURCE / "data" / "spelldraft_v4_world.sql"
WORLD_UPDATE_NAME = "rev_1789000000000000006.sql"


def stage(core_dir: Path) -> None:
    core = core_dir.expanduser().resolve()
    modules = core / "modules"
    pending = core / "data" / "sql" / "updates" / "pending_db_world"
    module_target = modules / "mod-adventurer-spelldraft"
    world_target = pending / WORLD_UPDATE_NAME

    if not modules.is_dir():
        raise RuntimeError(f"AzerothCore modules directory not found: {modules}")
    if not pending.is_dir():
        raise RuntimeError(f"AzerothCore pending world-update directory not found: {pending}")
    if not MODULE_SOURCE.is_dir():
        raise RuntimeError(f"SpellDraft module source not found: {MODULE_SOURCE}")
    if not WORLD_SQL_SOURCE.is_file():
        raise RuntimeError(f"SpellDraft world SQL not found: {WORLD_SQL_SOURCE}")

    if module_target.exists():
        shutil.rmtree(module_target)
    shutil.copytree(MODULE_SOURCE, module_target)
    shutil.copy2(WORLD_SQL_SOURCE, world_target)

    print(f"SpellDraft v4 module staged into: {module_target}")
    print(f"SpellDraft v4 world update staged into: {world_target}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-dir", required=True, type=Path)
    args, _unknown = parser.parse_known_args()
    try:
        stage(args.core_dir)
    except (OSError, RuntimeError) as exc:
        parser.error(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
