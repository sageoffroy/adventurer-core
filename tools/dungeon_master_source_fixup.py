#!/usr/bin/env python3
"""Repair/verify compatibility issues from the first Dungeon Master native-mode patch.

The original Adventurer compatibility patch needed three small in-place repairs:
- DungeonMasterMgr::Update(): restore the brace closing `if (ref)` before auto-rez.
- dm_unit_script::ScaleDamage(): restore the brace closing `if (attacker)` before
  the environmental-damage path.
- DungeonMasterMgr::PrepareOriginalCreature(): ignore decorative creatures whose
  server-side unit is alive but whose stand state is DEAD. These are intentional
  corpse props in Blizzard instances and must never become challenge enemies.

This fixup is intentionally small and idempotent so already-patched development
trees can be repaired in place without rolling back the Dungeon Master module.
"""

from __future__ import annotations

import argparse
from pathlib import Path


MGR_REL = Path("modules/mod-dungeon-master/src/DungeonMasterMgr.cpp")
UNIT_REL = Path("modules/mod-dungeon-master/src/scripts/dm_unit_script.cpp")

MGR_PATCH_MARKER = "// ---- Original dungeon grid activation / roguelike stray cleanup ----"
MGR_FIX_MARKER = "// Aventureros source fixup v2: close active-player block before auto-rez."
MGR_LEGACY = (
    "                    }\n"
    "                // ---- Auto-rez when out of combat ----\n"
)
MGR_FIXED = (
    "                    }\n"
    "                }\n\n"
    "                // Aventureros source fixup v2: close active-player block before auto-rez.\n"
    "                // ---- Auto-rez when out of combat ----\n"
)

UNIT_PATCH_MARKER = "// Guardrail: no single hit can remove more than 35% max HP."
UNIT_FIX_MARKER = "// Aventureros source fixup v3: close attacker block before environmental damage."
UNIT_LEGACY = (
    "                return;\n"
    "            }\n"
    "        // Non-session attacker (environmental hazards, traps, etc.)\n"
)
UNIT_FIXED = (
    "                return;\n"
    "            }\n"
    "        }\n\n"
    "        // Aventureros source fixup v3: close attacker block before environmental damage.\n"
    "        // Non-session attacker (environmental hazards, traps, etc.)\n"
)

CORPSE_PATCH_MARKER = "// Aventureros: preserve and scale the dungeon's original inhabitants."
CORPSE_FIX_MARKER = "// Aventureros source fixup v4: ignore decorative dead-pose creatures."
CORPSE_ANCHOR = (
    "    if (!c || !session || !c->IsInWorld() || !c->IsAlive())\n"
    "        return false;\n"
)
CORPSE_FIXED = (
    "    if (!c || !session || !c->IsInWorld() || !c->IsAlive())\n"
    "        return false;\n"
    "    // Aventureros source fixup v4: ignore decorative dead-pose creatures.\n"
    "    // Blizzard uses alive Creature objects with UNIT_STAND_STATE_DEAD for corpse props.\n"
    "    if (c->GetStandState() == UNIT_STAND_STATE_DEAD)\n"
    "        return false;\n"
)


class FixupError(RuntimeError):
    pass


def target(core: Path, rel: Path) -> Path:
    path = core.expanduser().resolve() / rel
    if not path.is_file():
        raise FixupError(f"Dungeon Master source file not found: {path}")
    return path


def _repair(path: Path, patch_marker: str, fix_marker: str, legacy: str, fixed: str, label: str) -> bool:
    text = path.read_text(encoding="utf-8")
    if patch_marker not in text:
        raise FixupError(f"Dungeon Master {label} native-mode patch is not installed")
    if fix_marker in text:
        if legacy in text:
            raise FixupError(f"Dungeon Master {label} fix marker exists but malformed sequence remains")
        return False
    count = text.count(legacy)
    if count != 1:
        raise FixupError(f"Expected exactly one {label} legacy anchor, found {count}")
    path.write_text(text.replace(legacy, fixed, 1), encoding="utf-8")
    return True


def _repair_decorative_corpses(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if CORPSE_PATCH_MARKER not in text:
        raise FixupError("Dungeon Master original-creature native-mode patch is not installed")
    if CORPSE_FIX_MARKER in text:
        if "c->GetStandState() == UNIT_STAND_STATE_DEAD" not in text:
            raise FixupError("Dungeon Master corpse fix marker exists but stand-state guard is missing")
        return False
    count = text.count(CORPSE_ANCHOR)
    if count != 1:
        raise FixupError(f"Expected exactly one original-creature alive guard, found {count}")
    path.write_text(text.replace(CORPSE_ANCHOR, CORPSE_FIXED, 1), encoding="utf-8")
    return True


def install(core: Path) -> bool:
    mgr_path = target(core, MGR_REL)
    mgr_changed = _repair(
        mgr_path, MGR_PATCH_MARKER, MGR_FIX_MARKER,
        MGR_LEGACY, MGR_FIXED, "manager"
    )
    unit_changed = _repair(
        target(core, UNIT_REL), UNIT_PATCH_MARKER, UNIT_FIX_MARKER,
        UNIT_LEGACY, UNIT_FIXED, "unit-script"
    )
    corpse_changed = _repair_decorative_corpses(mgr_path)
    verify(core)
    return mgr_changed or unit_changed or corpse_changed


def verify(core: Path) -> None:
    checks = (
        (target(core, MGR_REL), MGR_PATCH_MARKER, MGR_FIX_MARKER, MGR_LEGACY, "manager"),
        (target(core, UNIT_REL), UNIT_PATCH_MARKER, UNIT_FIX_MARKER, UNIT_LEGACY, "unit-script"),
    )
    for path, patch_marker, fix_marker, legacy, label in checks:
        text = path.read_text(encoding="utf-8")
        if patch_marker not in text:
            raise FixupError(f"Dungeon Master {label} native-mode patch is not installed")
        if fix_marker not in text:
            raise FixupError(f"Dungeon Master {label} brace fixup is not installed")
        if legacy in text:
            raise FixupError(f"Dungeon Master {label} malformed brace sequence is still present")

    mgr = target(core, MGR_REL).read_text(encoding="utf-8")
    if CORPSE_PATCH_MARKER not in mgr:
        raise FixupError("Dungeon Master original-creature native-mode patch is not installed")
    if CORPSE_FIX_MARKER not in mgr:
        raise FixupError("Dungeon Master decorative-corpse fixup is not installed")
    if "c->GetStandState() == UNIT_STAND_STATE_DEAD" not in mgr:
        raise FixupError("Dungeon Master decorative-corpse stand-state guard is missing")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "verify"))
    parser.add_argument("--core-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "install":
            changed = install(args.core_dir)
            print(
                "Dungeon Master source fixups applied; rebuild required."
                if changed
                else "Dungeon Master source fixups already current."
            )
        else:
            verify(args.core_dir)
            print("Dungeon Master source fixups verify cleanly.")
        return 0
    except (OSError, FixupError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
