#!/usr/bin/env python3
"""Install, verify and clean Adventurer Core world SQL."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import sys

import adventurer_items
from database import _run_mysql, query_scalar, read_database_info

ROOT = Path(__file__).resolve().parent.parent
PENDING_WORLD_RELATIVE = Path("data/sql/updates/pending_db_world")
DEFAULT_CONF_RELATIVE = Path("env/dist/etc/worldserver.conf")
GAUNTLET_GENERATED_ITEMS_RELATIVE = Path(
    "modules/mod-adventurer-gauntlet/data/generated/gauntlet_items.sql"
)

LEGACY_FIXED_TALENT_SPELL_MIN = 290000
LEGACY_FIXED_TALENT_SPELL_MAX = 299999
LEGACY_FIXED_TALENT_UPDATE_NAMES = (
    "rev_1787446800000000000.sql",
    "rev_1787779800000000000.sql",
)
LEGACY_GAUNTLET_GENERATED_UPDATE_NAMES = (
    "000_gauntlet_items.generated.sql",
)
LEGACY_WORLD_UPDATE_NAMES = tuple(
    f"rev_1787446800000000{index:03d}.sql" for index in range(1, 15)
)


@dataclass(frozen=True)
class WorldUpdate:
    source: Path
    name: str

    @property
    def relative(self) -> Path:
        return PENDING_WORLD_RELATIVE / self.name


# Authoritative execution order:
# 000 = every custom item definition (fixed catalog + generated Gauntlet items)
# 001 = Adventurer class
# 002 = Goldshire / Remen
# 003 = Gauntlet templates/spells
# 004 = Gauntlet world placement/gossip
# 005 = Gauntlet loot policy
WORLD_UPDATES: tuple[WorldUpdate, ...] = (
    WorldUpdate(adventurer_items.CATALOG, "rev_1789000000000000000.sql"),
    WorldUpdate(ROOT / "sql/world/001_adventurer.sql", "rev_1789000000000000001.sql"),
    WorldUpdate(ROOT / "sql/world/002_adventurer_goldshire.sql", "rev_1789000000000000002.sql"),
    WorldUpdate(
        ROOT / "modules/mod-adventurer-gauntlet/data/sql/world/001_gauntlet_core.sql",
        "rev_1789000000000000003.sql",
    ),
    WorldUpdate(
        ROOT / "modules/mod-adventurer-gauntlet/data/sql/world/002_gauntlet_world.sql",
        "rev_1789000000000000004.sql",
    ),
    WorldUpdate(
        ROOT / "modules/mod-adventurer-gauntlet/data/sql/world/003_gauntlet_loot.sql",
        "rev_1789000000000000005.sql",
    ),
)

WORLD_UPDATE_SOURCE = WORLD_UPDATES[0].source
WORLD_UPDATE_NAME = WORLD_UPDATES[0].name
WORLD_UPDATE_RELATIVE = WORLD_UPDATES[0].relative


class WorldUpdateError(RuntimeError):
    pass


def validate_core(core: Path) -> Path:
    core = core.expanduser().resolve()
    pending = core / PENDING_WORLD_RELATIVE
    if not pending.is_dir():
        raise WorldUpdateError(f"AzerothCore pending world-update directory not found: {pending}")
    if not (core / "src/server/game").is_dir():
        raise WorldUpdateError(f"Not an AzerothCore source root: {core}")
    return core


def source_payload(update: WorldUpdate, core: Path | None = None) -> bytes:
    if update == WORLD_UPDATES[0]:
        payload = adventurer_items.generate_world_sql()
    else:
        if not update.source.is_file():
            raise WorldUpdateError(f"Bundled world update missing: {update.source}")
        payload = update.source.read_bytes()

    if update == WORLD_UPDATES[0] and core is not None:
        generated = core / GAUNTLET_GENERATED_ITEMS_RELATIVE
        if not generated.is_file():
            raise WorldUpdateError(
                "Generated Gauntlet item SQL is missing; stage the Gauntlet module before world SQL: "
                f"{generated}"
            )
        payload += b"\n\n-- Generated Gauntlet item definitions.\n" + generated.read_bytes()
    return payload


def remove_legacy_pending(core: Path) -> list[Path]:
    pending = core / PENDING_WORLD_RELATIVE
    removed: list[Path] = []
    for name in LEGACY_WORLD_UPDATE_NAMES:
        target = pending / name
        if target.is_file():
            target.unlink()
            removed.append(target)
    return removed


def install_one(core: Path, update: WorldUpdate) -> tuple[Path, bool]:
    target = core / update.relative
    payload = source_payload(update, core)
    if target.exists():
        if not target.is_file():
            raise WorldUpdateError(f"World update target is not a file: {target}")
        if target.read_bytes() == payload:
            return target, False
        target.write_bytes(payload)
        return target, True
    target.write_bytes(payload)
    return target, True


def invalidate_changed_update_markers(
    core: Path,
    results: list[tuple[Path, bool]],
    conf: Path | None = None,
) -> list[str]:
    changed_names = [
        update.name
        for update, (_target, was_changed) in zip(WORLD_UPDATES, results)
        if was_changed
    ]
    if not changed_names:
        return []

    conf = conf.expanduser().resolve() if conf else (core / DEFAULT_CONF_RELATIVE).resolve()
    db = read_database_info(conf, "WorldDatabaseInfo")
    names = ", ".join("'" + name.replace("'", "''") + "'" for name in changed_names)
    _run_mysql(db, f"DELETE FROM `updates` WHERE `name` IN ({names});\n".encode())

    remaining = int(query_scalar(
        db,
        f"SELECT COUNT(*) FROM `updates` WHERE `name` IN ({names})",
    ))
    if remaining:
        raise WorldUpdateError(
            f"Failed to invalidate {remaining} changed Adventurer world update marker(s)"
        )
    return changed_names


def install(
    core: Path,
    conf: Path | None = None,
) -> tuple[list[Path], list[tuple[Path, bool]], list[str]]:
    core = validate_core(core)
    removed = remove_legacy_pending(core)
    results = [install_one(core, update) for update in WORLD_UPDATES]
    invalidated = invalidate_changed_update_markers(core, results, conf)
    return removed, results, invalidated


def verify_one(core: Path, update: WorldUpdate) -> Path:
    target = core / update.relative
    if not target.is_file():
        raise WorldUpdateError(f"World update is not installed: {target}")
    if target.read_bytes() != source_payload(update, core):
        raise WorldUpdateError(f"World update differs from Adventurer Core: {target}")
    return target


def verify(core: Path) -> list[Path]:
    core = validate_core(core)
    pending = core / PENDING_WORLD_RELATIVE
    legacy = [pending / name for name in LEGACY_WORLD_UPDATE_NAMES if (pending / name).exists()]
    if legacy:
        raise WorldUpdateError(
            "Legacy Adventurer pending world updates still exist: "
            + ", ".join(str(path) for path in legacy)
        )
    return [verify_one(core, update) for update in WORLD_UPDATES]


def remove_one(core: Path, update: WorldUpdate) -> tuple[Path, bool]:
    target = core / update.relative
    if not target.exists():
        return target, False
    if not target.is_file():
        raise WorldUpdateError(f"World update target is not a file: {target}")
    if target.read_bytes() != source_payload(update, core):
        raise WorldUpdateError(f"Refusing to remove world update with different contents: {target}")
    target.unlink()
    return target, True


def remove(core: Path) -> list[tuple[Path, bool]]:
    core = validate_core(core)
    return [remove_one(core, update) for update in reversed(WORLD_UPDATES)]


def cleanup_database(core: Path, conf: Path | None = None) -> None:
    core = validate_core(core)
    conf = conf.expanduser().resolve() if conf else (core / DEFAULT_CONF_RELATIVE).resolve()
    db = read_database_info(conf, "WorldDatabaseInfo")

    update_names = (
        tuple(update.name for update in WORLD_UPDATES)
        + LEGACY_WORLD_UPDATE_NAMES
        + LEGACY_FIXED_TALENT_UPDATE_NAMES
        + LEGACY_GAUNTLET_GENERATED_UPDATE_NAMES
    )
    names = ", ".join("'" + name.replace("'", "''") + "'" for name in update_names)
    sql = f"""
DELETE FROM `spell_script_names`
WHERE (`spell_id` BETWEEN {LEGACY_FIXED_TALENT_SPELL_MIN} AND {LEGACY_FIXED_TALENT_SPELL_MAX})
   OR (`spell_id` BETWEEN {-LEGACY_FIXED_TALENT_SPELL_MAX} AND {-LEGACY_FIXED_TALENT_SPELL_MIN});
DELETE FROM `updates` WHERE `name` IN ({names});
""".encode()
    _run_mysql(db, sql)

    binding_count = int(query_scalar(
        db,
        "SELECT COUNT(*) FROM `spell_script_names` "
        f"WHERE (`spell_id` BETWEEN {LEGACY_FIXED_TALENT_SPELL_MIN} AND {LEGACY_FIXED_TALENT_SPELL_MAX}) "
        f"OR (`spell_id` BETWEEN {-LEGACY_FIXED_TALENT_SPELL_MAX} AND {-LEGACY_FIXED_TALENT_SPELL_MIN})",
    ))
    marker_count = int(query_scalar(db, f"SELECT COUNT(*) FROM `updates` WHERE `name` IN ({names})"))
    if binding_count or marker_count:
        raise WorldUpdateError(
            "Maintenance DB cleanup did not converge: "
            f"legacy_fixed_talent_bindings={binding_count}, update_markers={marker_count}"
        )


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="world.py")
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("install", "verify", "remove"):
        command = sub.add_parser(name)
        command.add_argument("--core-dir", required=True, type=Path)
        if name == "install":
            command.add_argument("--worldserver-conf", type=Path)
    cleanup = sub.add_parser("cleanup-db")
    cleanup.add_argument("--core-dir", required=True, type=Path)
    cleanup.add_argument("--worldserver-conf", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            removed, results, invalidated = install(args.core_dir, args.worldserver_conf)
            if removed:
                print(f"Removed {len(removed)} obsolete Adventurer pending world updates.")
            changed = sum(1 for _target, was_changed in results if was_changed)
            print(f"Adventurer world updates installed: {changed} changed, {len(results) - changed} already current.")
            for target, was_changed in results:
                print(f"  {'installed/updated' if was_changed else 'already current'}: {target}")
            if invalidated:
                print("  invalidated applied markers: " + ", ".join(invalidated))
            print("  AzerothCore will apply changed pending updates on the next worldserver startup.")
        elif args.command == "verify":
            targets = verify(args.core_dir)
            print(f"Adventurer world updates verify cleanly: {len(targets)}.")
            for target in targets:
                print(f"  {target}")
        elif args.command == "remove":
            results = remove(args.core_dir)
            removed = sum(1 for _target, was_removed in results if was_removed)
            print(f"Adventurer world updates removed: {removed}; {len(results) - removed} were already absent.")
            for target, was_removed in results:
                print(f"  {'removed' if was_removed else 'already absent'}: {target}")
        else:
            cleanup_database(args.core_dir, args.worldserver_conf)
            print("Adventurer maintenance DB rows and legacy fixed-talent residue cleaned.")
        return 0
    except (WorldUpdateError, OSError, RuntimeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
