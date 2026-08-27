#!/usr/bin/env python3
"""Repair/verify the v1 Dungeon Master native-mode source patch.

The first native-mode patch replaced the upstream stray-creature sweep but
accidentally consumed the brace that closes the surrounding `if (ref)` block in
DungeonMasterMgr::Update(). This fixup is intentionally tiny and idempotent so
existing installations can be upgraded without rolling back their source patch.
"""

from __future__ import annotations

import argparse
from pathlib import Path


REL = Path("modules/mod-dungeon-master/src/DungeonMasterMgr.cpp")
PATCH_MARKER = "// ---- Original dungeon grid activation / roguelike stray cleanup ----"
FIX_MARKER = "// Aventureros source fixup v2: close active-player block before auto-rez."
LEGACY = (
    "                    }\n"
    "                // ---- Auto-rez when out of combat ----\n"
)
FIXED = (
    "                    }\n"
    "                }\n\n"
    "                // Aventureros source fixup v2: close active-player block before auto-rez.\n"
    "                // ---- Auto-rez when out of combat ----\n"
)


class FixupError(RuntimeError):
    pass


def target(core: Path) -> Path:
    path = core.expanduser().resolve() / REL
    if not path.is_file():
        raise FixupError(f"Dungeon Master source file not found: {path}")
    return path


def install(core: Path) -> bool:
    path = target(core)
    text = path.read_text(encoding="utf-8")
    if PATCH_MARKER not in text:
        raise FixupError("Dungeon Master native-mode patch is not installed")
    if FIX_MARKER in text:
        verify(core)
        return False
    count = text.count(LEGACY)
    if count != 1:
        raise FixupError(f"Expected exactly one v1 brace anchor, found {count}")
    path.write_text(text.replace(LEGACY, FIXED, 1), encoding="utf-8")
    verify(core)
    return True


def verify(core: Path) -> None:
    text = target(core).read_text(encoding="utf-8")
    if PATCH_MARKER not in text:
        raise FixupError("Dungeon Master native-mode patch is not installed")
    if FIX_MARKER not in text:
        raise FixupError("Dungeon Master v2 brace fixup is not installed")
    if LEGACY in text:
        raise FixupError("Dungeon Master v1 malformed brace sequence is still present")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "verify"))
    parser.add_argument("--core-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "install":
            changed = install(args.core_dir)
            print(
                "Dungeon Master v2 source brace fixup applied; rebuild required."
                if changed
                else "Dungeon Master v2 source brace fixup already current."
            )
        else:
            verify(args.core_dir)
            print("Dungeon Master v2 source brace fixup verifies cleanly.")
        return 0
    except (OSError, FixupError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
