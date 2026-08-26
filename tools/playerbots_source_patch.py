#!/usr/bin/env python3
"""Idempotent source compatibility patches for mod-playerbots.

Adventurer Core makes class id 10 a real playable class. Stock Playerbots treats
CLASSMASK_ALL_PLAYABLE as the set of classes it should generate for randombot
accounts, and its talent/spec tables intentionally have no class-10 entries.
Without this compatibility layer Playerbots creates Adventurer randombots and
later calls urand(1, 0) while selecting their talent spec.

The patches below do three things:
* never generate CLASS_ADVENTURER as a random/add-account population class;
* defensively skip native Playerbots talent-tree initialization if an old
  class-10 bot still exists from an earlier run;
* avoid FLUSH TABLES in the one-shot randombot account cleanup path, because
  the queues are already drained after explicit commits and FLUSH TABLES would
  unnecessarily require MySQL RELOAD/FLUSH_TABLES privileges.

All edits are exact-anchor, reversible, and preflighted before any file is
written.
"""

from __future__ import annotations

import argparse
from collections import OrderedDict
from dataclasses import dataclass
from pathlib import Path


class PlayerbotsSourcePatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class PatchSpec:
    relative_path: str
    clean: str
    patched: str
    label: str


RANDOM_FACTORY_CLEAN = """            // skip nonexistent classes
            if (!((1 << (cls - 1)) & CLASSMASK_ALL_PLAYABLE) || !sChrClassesStore.LookupEntry(cls))
                continue;

            // skip disabled with config classes
"""

RANDOM_FACTORY_PATCHED = """            // skip nonexistent classes
            if (!((1 << (cls - 1)) & CLASSMASK_ALL_PLAYABLE) || !sChrClassesStore.LookupEntry(cls))
                continue;

            // Adventurer Core makes class 10 playable, but Playerbots has no
            // native class-10 AI/spec/talent templates. Keep randombot account
            // generation restricted to the ten native WotLK classes.
            if (cls == CLASS_ADVENTURER)
                continue;

            // skip disabled with config classes
"""

TALENT_FACTORY_CLEAN = """uint32 PlayerbotFactory::InitTalentsTree(bool increment /*false*/, bool use_template /*true*/, bool reset /*false*/)
{
    uint32 specTab;
    uint8 cls = bot->getClass();
    std::map<uint8, uint32> tabs = AiFactory::GetPlayerSpecTabs(bot);
"""

TALENT_FACTORY_PATCHED = """uint32 PlayerbotFactory::InitTalentsTree(bool increment /*false*/, bool use_template /*true*/, bool reset /*false*/)
{
    uint32 specTab;
    uint8 cls = bot->getClass();

    // Compatibility guard for class-10 randombots created before Adventurer
    // was excluded from Playerbots account generation. Playerbots has no
    // RandomClassSpecProb/PremadeSpec data for class 10, so its stock path
    // would sum zero weights and call urand(1, 0).
    if (cls == CLASS_ADVENTURER)
    {
        LOG_WARN("playerbots", "Skipping native talent initialization for Adventurer bot {}", bot->GetName());
        return 0;
    }

    std::map<uint8, uint32> tabs = AiFactory::GetPlayerSpecTabs(bot);
"""

CLEANUP_FLUSH_CLEAN = """        // Flush tables to ensure all data in memory are written to disk
        LoginDatabase.Execute("FLUSH TABLES");
        CharacterDatabase.Execute("FLUSH TABLES");
        PlayerbotsDatabase.Execute("FLUSH TABLES");

"""

CLEANUP_FLUSH_PATCHED = """        // Adventurer Core: the async queues were drained above after the
        // explicit commits. FLUSH TABLES is unnecessary here and would require
        // elevated MySQL RELOAD/FLUSH_TABLES privileges from the worldserver DB
        // account, so keep the cleanup compatible with least-privilege users.

"""


PATCHES = (
    PatchSpec(
        "modules/mod-playerbots/src/Bot/Factory/RandomPlayerbotFactory.cpp",
        RANDOM_FACTORY_CLEAN,
        RANDOM_FACTORY_PATCHED,
        "randombot class-10 generation exclusion",
    ),
    PatchSpec(
        "modules/mod-playerbots/src/Bot/Factory/PlayerbotFactory.cpp",
        TALENT_FACTORY_CLEAN,
        TALENT_FACTORY_PATCHED,
        "class-10 talent initialization guard",
    ),
    PatchSpec(
        "modules/mod-playerbots/src/Bot/Factory/RandomPlayerbotFactory.cpp",
        CLEANUP_FLUSH_CLEAN,
        CLEANUP_FLUSH_PATCHED,
        "randombot cleanup privileged FLUSH removal",
    ),
)


def _read(path: Path) -> str:
    if not path.is_file():
        raise PlayerbotsSourcePatchError(f"Required Playerbots source file is missing: {path}")
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise PlayerbotsSourcePatchError(f"Expected UTF-8 source: {path}") from exc


def _classify(text: str, spec: PatchSpec) -> str:
    clean_count = text.count(spec.clean)
    patched_count = text.count(spec.patched)
    if clean_count == 1 and patched_count == 0:
        return "clean"
    if clean_count == 0 and patched_count == 1:
        return "patched"
    raise PlayerbotsSourcePatchError(
        f"{spec.label}: expected exactly one clean or patched anchor; "
        f"found clean={clean_count}, patched={patched_count}"
    )


def _group_specs() -> OrderedDict[str, list[PatchSpec]]:
    grouped: OrderedDict[str, list[PatchSpec]] = OrderedDict()
    for spec in PATCHES:
        grouped.setdefault(spec.relative_path, []).append(spec)
    return grouped


def install(core_dir: Path) -> list[str]:
    plans: list[tuple[Path, str, str]] = []
    changed: list[str] = []

    # Preflight and transform every target fully in memory first. Multiple
    # Adventurer-owned patches may intentionally share one Playerbots file.
    for relative_path, specs in _group_specs().items():
        path = core_dir / relative_path
        original = _read(path)
        patched = original
        file_changed = False
        for spec in specs:
            state = _classify(patched, spec)
            if state == "clean":
                patched = patched.replace(spec.clean, spec.patched, 1)
                file_changed = True
        if file_changed:
            if original == patched:
                raise PlayerbotsSourcePatchError(f"{relative_path}: patch produced no change")
            plans.append((path, original, patched))
            changed.append(relative_path)

    for path, _original, patched in plans:
        path.write_text(patched, encoding="utf-8")

    verify(core_dir)
    if changed:
        print("Playerbots source compatibility patch applied:")
        for relative in changed:
            print(f"  {relative}")
        print("  rebuild required: yes")
    else:
        print("Playerbots source compatibility patch already applied.")
    return changed


def verify(core_dir: Path) -> None:
    cache: dict[str, str] = {}
    for spec in PATCHES:
        text = cache.setdefault(spec.relative_path, _read(core_dir / spec.relative_path))
        state = _classify(text, spec)
        if state != "patched":
            raise PlayerbotsSourcePatchError(f"{spec.label}: expected patched source")


def rollback(core_dir: Path) -> list[str]:
    plans: list[tuple[Path, str, str]] = []
    changed: list[str] = []

    for relative_path, specs in _group_specs().items():
        path = core_dir / relative_path
        original = _read(path)
        clean = original
        file_changed = False
        for spec in specs:
            state = _classify(clean, spec)
            if state == "patched":
                clean = clean.replace(spec.patched, spec.clean, 1)
                file_changed = True
        if file_changed:
            if original == clean:
                raise PlayerbotsSourcePatchError(f"{relative_path}: rollback produced no change")
            plans.append((path, original, clean))
            changed.append(relative_path)

    for path, _original, clean in plans:
        path.write_text(clean, encoding="utf-8")

    # A successful rollback must leave every target in the exact clean state.
    cache: dict[str, str] = {}
    for spec in PATCHES:
        text = cache.setdefault(spec.relative_path, _read(core_dir / spec.relative_path))
        state = _classify(text, spec)
        if state != "clean":
            raise PlayerbotsSourcePatchError(f"{spec.label}: rollback verification failed")

    if changed:
        print("Playerbots source compatibility patch rolled back.")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "verify", "rollback"))
    parser.add_argument("--core-dir", required=True, type=Path)
    args = parser.parse_args()

    core_dir = args.core_dir.expanduser().resolve()
    try:
        if args.command == "install":
            install(core_dir)
        elif args.command == "verify":
            verify(core_dir)
        else:
            rollback(core_dir)
    except PlayerbotsSourcePatchError as exc:
        print(f"ERROR: {exc}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
