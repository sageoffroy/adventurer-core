#!/usr/bin/env python3
"""Install, verify and clean Adventurer Core world maintenance updates."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

from database import _run_mysql, query_scalar, read_database_info


ROOT = Path(__file__).resolve().parent.parent
PENDING_WORLD_RELATIVE = Path("data/sql/updates/pending_db_world")
DEFAULT_CONF_RELATIVE = Path("env/dist/etc/worldserver.conf")


@dataclass(frozen=True)
class WorldUpdate:
    source: Path
    name: str

    @property
    def relative(self) -> Path:
        return PENDING_WORLD_RELATIVE / self.name


WORLD_UPDATES: tuple[WorldUpdate, ...] = (
    WorldUpdate(
        ROOT / "sql" / "world" / "002_guardian_last_bastion.sql",
        "rev_1787446800000000000.sql",
    ),
    WorldUpdate(
        ROOT / "sql" / "world" / "003_adventurer_chassis.sql",
        "rev_1787446800000000001.sql",
    ),
)

# Kept as aliases for older callers/tests that referenced the single-update API.
WORLD_UPDATE_SOURCE = WORLD_UPDATES[0].source
WORLD_UPDATE_NAME = WORLD_UPDATES[0].name
WORLD_UPDATE_RELATIVE = WORLD_UPDATES[0].relative


class WorldUpdateError(RuntimeError):
    pass


def validate_core(core: Path) -> Path:
    core = core.expanduser().resolve()
    pending = core / PENDING_WORLD_RELATIVE
    if not pending.is_dir():
        raise WorldUpdateError(
            f"AzerothCore pending world-update directory not found: {pending}"
        )
    if not (core / "src" / "server" / "game").is_dir():
        raise WorldUpdateError(f"Not an AzerothCore source root: {core}")
    return core


def source_payload(update: WorldUpdate = WORLD_UPDATES[0]) -> bytes:
    if not update.source.is_file():
        raise WorldUpdateError(f"Bundled world update missing: {update.source}")
    return update.source.read_bytes()


def install_one(core: Path, update: WorldUpdate) -> tuple[Path, bool]:
    target = core / update.relative
    payload = source_payload(update)

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


def install(core: Path) -> list[tuple[Path, bool]]:
    core = validate_core(core)
    return [install_one(core, update) for update in WORLD_UPDATES]


def verify_one(core: Path, update: WorldUpdate) -> Path:
    target = core / update.relative
    if not target.is_file():
        raise WorldUpdateError(f"World update is not installed: {target}")
    if target.read_bytes() != source_payload(update):
        raise WorldUpdateError(f"World update differs from Adventurer Core: {target}")
    return target


def verify(core: Path) -> list[Path]:
    core = validate_core(core)
    return [verify_one(core, update) for update in WORLD_UPDATES]


def remove_one(core: Path, update: WorldUpdate) -> tuple[Path, bool]:
    target = core / update.relative
    if not target.exists():
        return target, False
    if not target.is_file():
        raise WorldUpdateError(f"World update target is not a file: {target}")
    if target.read_bytes() != source_payload(update):
        raise WorldUpdateError(
            f"Refusing to remove world update with different contents: {target}"
        )
    target.unlink()
    return target, True


def remove(core: Path) -> list[tuple[Path, bool]]:
    core = validate_core(core)
    return [remove_one(core, update) for update in reversed(WORLD_UPDATES)]


def cleanup_database(core: Path, conf: Path | None = None) -> None:
    """Remove only DB rows uniquely owned by maintenance updates 002+.

    The main database rollback snapshot already restores every class-10 stat
    range touched by 001/003. This cleanup covers the extra Last Bastion script
    binding and the AzerothCore update markers, which older snapshots could not
    have known about when they were created.
    """
    core = validate_core(core)
    conf = (
        conf.expanduser().resolve()
        if conf
        else (core / DEFAULT_CONF_RELATIVE).resolve()
    )
    db = read_database_info(conf, "WorldDatabaseInfo")
    names = ", ".join("'" + update.name.replace("'", "''") + "'" for update in WORLD_UPDATES)
    sql = f"""
DELETE FROM `spell_script_names`
WHERE `spell_id` = 290050
  AND `ScriptName` = 'spell_warr_last_stand';

DELETE FROM `updates`
WHERE `name` IN ({names});
""".encode()
    _run_mysql(db, sql)

    binding_count = int(query_scalar(
        db,
        "SELECT COUNT(*) FROM `spell_script_names` "
        "WHERE `spell_id`=290050 AND `ScriptName`='spell_warr_last_stand'",
    ))
    marker_count = int(query_scalar(
        db,
        f"SELECT COUNT(*) FROM `updates` WHERE `name` IN ({names})",
    ))
    if binding_count or marker_count:
        raise WorldUpdateError(
            "Maintenance DB cleanup did not converge: "
            f"binding={binding_count}, update_markers={marker_count}"
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="world.py")
    sub = result.add_subparsers(dest="command", required=True)

    for name in ("install", "verify", "remove"):
        command = sub.add_parser(name)
        command.add_argument("--core-dir", required=True, type=Path)

    cleanup = sub.add_parser("cleanup-db")
    cleanup.add_argument("--core-dir", required=True, type=Path)
    cleanup.add_argument("--worldserver-conf", type=Path)

    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            results = install(args.core_dir)
            changed = sum(1 for _target, was_changed in results if was_changed)
            print(
                f"Adventurer world updates installed: {changed} changed, "
                f"{len(results) - changed} already current."
            )
            for target, was_changed in results:
                state = "installed" if was_changed else "already current"
                print(f"  {state}: {target}")
            print("  AzerothCore will apply pending updates on the next worldserver startup.")
        elif args.command == "verify":
            targets = verify(args.core_dir)
            print(f"Adventurer world updates verify cleanly: {len(targets)}.")
            for target in targets:
                print(f"  {target}")
        elif args.command == "remove":
            results = remove(args.core_dir)
            removed = sum(1 for _target, was_removed in results if was_removed)
            print(
                f"Adventurer world updates removed: {removed}; "
                f"{len(results) - removed} were already absent."
            )
            for target, was_removed in results:
                state = "removed" if was_removed else "already absent"
                print(f"  {state}: {target}")
        else:
            cleanup_database(args.core_dir, args.worldserver_conf)
            print("Adventurer maintenance DB rows cleaned.")
        return 0
    except (WorldUpdateError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
