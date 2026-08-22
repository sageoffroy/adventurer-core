#!/usr/bin/env python3
"""Install and verify Adventurer Core world-database maintenance updates."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
WORLD_UPDATE_SOURCE = ROOT / "sql" / "world" / "002_guardian_last_bastion.sql"
WORLD_UPDATE_NAME = "rev_1787446800000000000.sql"
WORLD_UPDATE_RELATIVE = Path("data/sql/updates/pending_db_world") / WORLD_UPDATE_NAME


class WorldUpdateError(RuntimeError):
    pass


def validate_core(core: Path) -> Path:
    core = core.expanduser().resolve()
    pending = core / "data" / "sql" / "updates" / "pending_db_world"
    if not pending.is_dir():
        raise WorldUpdateError(
            f"AzerothCore pending world-update directory not found: {pending}"
        )
    if not (core / "src" / "server" / "game").is_dir():
        raise WorldUpdateError(f"Not an AzerothCore source root: {core}")
    return core


def source_payload() -> bytes:
    if not WORLD_UPDATE_SOURCE.is_file():
        raise WorldUpdateError(f"Bundled world update missing: {WORLD_UPDATE_SOURCE}")
    return WORLD_UPDATE_SOURCE.read_bytes()


def install(core: Path) -> tuple[Path, bool]:
    core = validate_core(core)
    target = core / WORLD_UPDATE_RELATIVE
    payload = source_payload()

    if target.exists():
        if not target.is_file():
            raise WorldUpdateError(f"World update target is not a file: {target}")
        if target.read_bytes() != payload:
            raise WorldUpdateError(
                f"World update target already exists with different contents: {target}"
            )
        return target, False

    target.write_bytes(payload)
    return target, True


def verify(core: Path) -> Path:
    core = validate_core(core)
    target = core / WORLD_UPDATE_RELATIVE
    if not target.is_file():
        raise WorldUpdateError(f"World update is not installed: {target}")
    if target.read_bytes() != source_payload():
        raise WorldUpdateError(f"World update differs from Adventurer Core: {target}")
    return target


def remove(core: Path) -> tuple[Path, bool]:
    core = validate_core(core)
    target = core / WORLD_UPDATE_RELATIVE
    if not target.exists():
        return target, False
    if not target.is_file():
        raise WorldUpdateError(f"World update target is not a file: {target}")
    if target.read_bytes() != source_payload():
        raise WorldUpdateError(
            f"Refusing to remove world update with different contents: {target}"
        )
    target.unlink()
    return target, True


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="world.py")
    sub = result.add_subparsers(dest="command", required=True)

    for name in ("install", "verify", "remove"):
        command = sub.add_parser(name)
        command.add_argument("--core-dir", required=True, type=Path)

    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            target, changed = install(args.core_dir)
            print(
                "Adventurer world update installed."
                if changed
                else "Adventurer world update already installed."
            )
            print(f"  {target}")
            print("  AzerothCore will apply it on the next worldserver startup.")
        elif args.command == "verify":
            target = verify(args.core_dir)
            print("Adventurer world update verifies cleanly.")
            print(f"  {target}")
        else:
            target, changed = remove(args.core_dir)
            print(
                "Adventurer world update removed."
                if changed
                else "Adventurer world update was already absent."
            )
            print(f"  {target}")
        return 0
    except (WorldUpdateError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
