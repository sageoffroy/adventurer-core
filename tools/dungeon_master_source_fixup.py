#!/usr/bin/env python3
"""Repair/verify compatibility issues from the Dungeon Master native-mode patch.

The Adventurer compatibility layer is intentionally applied as small idempotent
repairs so an already-patched development tree can be upgraded in place.

Repairs owned here:
- DungeonMasterMgr::Update(): restore the brace closing `if (ref)` before auto-rez.
- dm_unit_script::ScaleDamage(): restore the brace closing `if (attacker)` before
  the environmental-damage path.
- PrepareOriginalCreature(): use AzerothCore's `getStandState()` spelling.
- PrepareOriginalCreature(): do not simply skip DB creatures that start in the
  DEAD stand pose. Some real dungeon combatants use that pose and otherwise walk
  around as crawling corpses. Remember the pose, run the normal native-creature
  eligibility checks, and stand accepted combatants up before scaling them.
- PrepareOriginalCreature(): preserve the native creature's health profile when
  down-scaling and enforce small low-level role floors so elites/bosses do not
  collapse to trivial double-digit HP at levels 1-9.
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
CORPSE_ACCESSOR_FIX_MARKER = "// Aventureros source fixup v5: AzerothCore uses getStandState()."
CORPSE_POSE_FIX_MARKER = "// Aventureros source fixup v6: stand up accepted dead-pose combatants."
CORPSE_ANCHOR = (
    "    if (!c || !session || !c->IsInWorld() || !c->IsAlive())\n"
    "        return false;\n"
)
CORPSE_BAD_ACCESSOR = "c->GetStandState() == UNIT_STAND_STATE_DEAD"
CORPSE_GOOD_ACCESSOR = "c->getStandState() == UNIT_STAND_STATE_DEAD"
CORPSE_V4_BAD_BLOCK = (
    "    // Aventureros source fixup v4: ignore decorative dead-pose creatures.\n"
    "    // Blizzard uses alive Creature objects with UNIT_STAND_STATE_DEAD for corpse props.\n"
    "    if (c->GetStandState() == UNIT_STAND_STATE_DEAD)\n"
    "        return false;\n"
)
CORPSE_V5_BLOCK = (
    "    // Aventureros source fixup v4: ignore decorative dead-pose creatures.\n"
    "    // Blizzard uses alive Creature objects with UNIT_STAND_STATE_DEAD for corpse props.\n"
    "    // Aventureros source fixup v5: AzerothCore uses getStandState().\n"
    "    if (c->getStandState() == UNIT_STAND_STATE_DEAD)\n"
    "        return false;\n"
)
CORPSE_DECL = (
    "    // Aventureros source fixup v4: ignore decorative dead-pose creatures.\n"
    "    // Aventureros source fixup v5: AzerothCore uses getStandState().\n"
    "    // Aventureros source fixup v6: stand up accepted dead-pose combatants.\n"
    "    // Some real Blizzard dungeon combatants are DB-spawned in the DEAD pose.\n"
    "    // Remember it now; non-combat/decorative creatures still fail the normal\n"
    "    // eligibility checks below, while accepted combatants are normalized later.\n"
    "    const bool nativeDeadPose = c->getStandState() == UNIT_STAND_STATE_DEAD;\n"
)
CORPSE_STAND_ANCHOR = "    const uint8 targetLevel = session->EffectiveLevel;\n"
CORPSE_STAND_BLOCK = (
    "    if (nativeDeadPose)\n"
    "        c->SetStandState(UNIT_STAND_STATE_STAND);\n\n"
    "    const uint8 targetLevel = session->EffectiveLevel;\n"
)

HEALTH_FIX_MARKER = "// Aventureros source fixup v7: preserve native health profile at target level."
HEALTH_LEGACY = (
    "    const uint8 targetLevel = session->EffectiveLevel;\n"
    "    c->SetLevel(targetLevel);\n"
    "    const uint8 unitClass = tmpl->unit_class;\n"
    "    const ClassLevelStatEntry* baseStats = GetBaseStatsForLevel(unitClass, targetLevel);\n\n"
    "    float hpMult = CalculateHealthMultiplier(session);\n"
    "    float extraHpMult = challengeBoss ? sDMConfig->GetBossHealthMult()\n"
    "        : (elite ? sDMConfig->GetEliteHealthMult() : 1.0f);\n"
    "    float finalHP = baseStats\n"
    "        ? static_cast<float>(baseStats->BaseHP) * hpMult * extraHpMult\n"
    "        : static_cast<float>(c->GetMaxHealth()) * hpMult * extraHpMult;\n"
)
HEALTH_FIXED = (
    "    // Aventureros source fixup v7: preserve native health profile at target level.\n"
    "    // The upstream class-level table is only a baseline. Native dungeon entries\n"
    "    // can be much tougher than that baseline, especially elites and bosses.\n"
    "    const uint8 originalLevel = std::max<uint8>(1, c->GetLevel());\n"
    "    const uint32 originalMaxHealth = std::max<uint32>(1, c->GetMaxHealth());\n"
    "    const uint8 targetLevel = session->EffectiveLevel;\n"
    "    const uint8 unitClass = tmpl->unit_class;\n"
    "    const ClassLevelStatEntry* originalStats = GetBaseStatsForLevel(unitClass, originalLevel);\n"
    "    const ClassLevelStatEntry* baseStats = GetBaseStatsForLevel(unitClass, targetLevel);\n"
    "    float nativeHpRatio = 1.0f;\n"
    "    if (originalStats && originalStats->BaseHP > 0)\n"
    "        nativeHpRatio = static_cast<float>(originalMaxHealth)\n"
    "            / static_cast<float>(originalStats->BaseHP);\n"
    "    nativeHpRatio = std::clamp(nativeHpRatio, 0.25f, 50.0f);\n"
    "    c->SetLevel(targetLevel);\n\n"
    "    float hpMult = CalculateHealthMultiplier(session);\n"
    "    float extraHpMult = challengeBoss ? sDMConfig->GetBossHealthMult()\n"
    "        : (elite ? sDMConfig->GetEliteHealthMult() : 1.0f);\n"
    "    float finalHP = baseStats\n"
    "        ? static_cast<float>(baseStats->BaseHP) * nativeHpRatio * hpMult * extraHpMult\n"
    "        : static_cast<float>(originalMaxHealth) * hpMult * extraHpMult;\n"
    "    // Levels 1-9 are outside the upstream module's original gameplay band.\n"
    "    // Keep trash approachable, but never let a native elite/boss collapse to\n"
    "    // a trivial double-digit-health version merely because solo+Novato stack.\n"
    "    if (baseStats && targetLevel <= 9)\n"
    "    {\n"
    "        float roleFloor = challengeBoss ? 4.0f : (elite ? 2.0f : 0.40f);\n"
    "        finalHP = std::max(finalHP,\n"
    "            static_cast<float>(baseStats->BaseHP) * nativeHpRatio * roleFloor);\n"
    "    }\n"
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


def _repair_dead_pose(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if CORPSE_PATCH_MARKER not in text:
        raise FixupError("Dungeon Master original-creature native-mode patch is not installed")

    if CORPSE_POSE_FIX_MARKER in text:
        if "const bool nativeDeadPose = c->getStandState() == UNIT_STAND_STATE_DEAD;" not in text:
            raise FixupError("Dungeon Master dead-pose v6 marker exists but pose capture is missing")
        if "c->SetStandState(UNIT_STAND_STATE_STAND);" not in text:
            raise FixupError("Dungeon Master dead-pose v6 marker exists but stand normalization is missing")
        if CORPSE_BAD_ACCESSOR in text:
            raise FixupError("Dungeon Master still uses invalid GetStandState accessor")
        return False

    # Existing v4/v5 trees used an early return. That looked right for corpse props,
    # but Deadmines demonstrates that real hostiles can also be DB-spawned in this
    # pose; skipping them leaves an alive creature crawling around on the floor.
    if CORPSE_V5_BLOCK in text:
        text = text.replace(CORPSE_V5_BLOCK, CORPSE_DECL, 1)
    elif CORPSE_V4_BAD_BLOCK in text:
        text = text.replace(CORPSE_V4_BAD_BLOCK, CORPSE_DECL, 1)
    elif CORPSE_FIX_MARKER in text:
        # Tolerate the intermediate v5 tree where the accessor was corrected but
        # its marker may have been injected with slightly different whitespace.
        if CORPSE_BAD_ACCESSOR in text:
            text = text.replace(CORPSE_BAD_ACCESSOR, CORPSE_GOOD_ACCESSOR, 1)
        guard = "    if (c->getStandState() == UNIT_STAND_STATE_DEAD)\n        return false;\n"
        if guard not in text:
            raise FixupError("Dungeon Master corpse guard is present but cannot be upgraded safely")
        start = text.rfind("    // Aventureros source fixup v4", 0, text.index(guard) + 1)
        if start < 0:
            raise FixupError("Dungeon Master corpse guard compatibility marker is missing")
        text = text[:start] + CORPSE_DECL + text[text.index(guard) + len(guard):]
    else:
        count = text.count(CORPSE_ANCHOR)
        if count != 1:
            raise FixupError(f"Expected exactly one original-creature alive guard, found {count}")
        text = text.replace(CORPSE_ANCHOR, CORPSE_ANCHOR + CORPSE_DECL, 1)

    if text.count(CORPSE_STAND_ANCHOR) != 1:
        raise FixupError("Expected exactly one original-creature target-level anchor for pose normalization")
    text = text.replace(CORPSE_STAND_ANCHOR, CORPSE_STAND_BLOCK, 1)
    path.write_text(text, encoding="utf-8")
    return True


def _repair_native_health(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    if CORPSE_PATCH_MARKER not in text:
        raise FixupError("Dungeon Master original-creature native-mode patch is not installed")
    if HEALTH_FIX_MARKER in text:
        if "nativeHpRatio" not in text or "roleFloor" not in text:
            raise FixupError("Dungeon Master native-health v7 marker exists but scaling body is incomplete")
        return False
    count = text.count(HEALTH_LEGACY)
    if count != 1:
        raise FixupError(f"Expected exactly one native-health legacy block, found {count}")
    path.write_text(text.replace(HEALTH_LEGACY, HEALTH_FIXED, 1), encoding="utf-8")
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
    pose_changed = _repair_dead_pose(mgr_path)
    health_changed = _repair_native_health(mgr_path)
    verify(core)
    return mgr_changed or unit_changed or pose_changed or health_changed


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
    if CORPSE_POSE_FIX_MARKER not in mgr:
        raise FixupError("Dungeon Master dead-pose combatant normalization is not installed")
    if "const bool nativeDeadPose = c->getStandState() == UNIT_STAND_STATE_DEAD;" not in mgr:
        raise FixupError("Dungeon Master dead-pose capture is missing")
    if "c->SetStandState(UNIT_STAND_STATE_STAND);" not in mgr:
        raise FixupError("Dungeon Master dead-pose stand normalization is missing")
    if CORPSE_BAD_ACCESSOR in mgr:
        raise FixupError("Dungeon Master still uses invalid GetStandState accessor")
    if "if (c->getStandState() == UNIT_STAND_STATE_DEAD)\n        return false;" in mgr:
        raise FixupError("Dungeon Master still skips all dead-pose creatures")

    if HEALTH_FIX_MARKER not in mgr:
        raise FixupError("Dungeon Master native-health scaling fix is not installed")
    if "nativeHpRatio" not in mgr:
        raise FixupError("Dungeon Master native health ratio is missing")
    if "roleFloor" not in mgr:
        raise FixupError("Dungeon Master low-level role health floor is missing")


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
