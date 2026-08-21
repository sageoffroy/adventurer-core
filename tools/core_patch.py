#!/usr/bin/env python3
"""Narrow, idempotent source transformations for native Adventurer class 10.

The transformations are deliberately anchor-based instead of fuzzy patching.
Every anchor must occur exactly as expected, or the preflight aborts before any
file is written. This gives us a compatibility signal when AzerothCore changes.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class PatchError(RuntimeError):
    pass


@dataclass(frozen=True)
class PlannedFile:
    relative_path: str
    original: bytes | None
    patched: bytes


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise PatchError(f"{label}: expected exactly one clean anchor, found {count}")
    return text.replace(old, new, 1)


def replace_exact_count(text: str, old: str, new: str, count: int, label: str) -> str:
    if old not in text:
        if text.count(new) == count:
            return text
        raise PatchError(f"{label}: clean anchor not found and patched form is incomplete")
    actual = text.count(old)
    if actual != count:
        raise PatchError(f"{label}: expected {count} clean anchors, found {actual}")
    return text.replace(old, new)


def patch_shared_defines(text: str) -> str:
    text = replace_once(
        text,
        "    CLASS_WARLOCK       = 9, // TITLE Warlock\n    //CLASS_UNK           = 10,\n    CLASS_DRUID         = 11 // TITLE Druid",
        "    CLASS_WARLOCK       = 9, // TITLE Warlock\n    CLASS_ADVENTURER    = 10, // TITLE Adventurer (native classless class)\n    CLASS_DRUID         = 11 // TITLE Druid",
        "SharedDefines Classes",
    )
    return replace_once(
        text,
        "    (1<<(CLASS_MAGE-1))   |(1<<(CLASS_WARLOCK-1))|(1<<(CLASS_DRUID-1)) | \\\n    (1<<(CLASS_DEATH_KNIGHT-1)))",
        "    (1<<(CLASS_MAGE-1))   |(1<<(CLASS_WARLOCK-1))|(1<<(CLASS_ADVENTURER-1))| \\\n    (1<<(CLASS_DRUID-1))  |(1<<(CLASS_DEATH_KNIGHT-1)))",
        "SharedDefines playable class mask",
    )


def patch_enuminfo(text: str) -> str:
    text = replace_once(
        text,
        '        case CLASS_WARLOCK: return { "CLASS_WARLOCK", "Warlock", "" };\n        case CLASS_DRUID: return { "CLASS_DRUID", "Druid", "" };',
        '        case CLASS_WARLOCK: return { "CLASS_WARLOCK", "Warlock", "" };\n        case CLASS_ADVENTURER: return { "CLASS_ADVENTURER", "Adventurer", "Native classless class" };\n        case CLASS_DRUID: return { "CLASS_DRUID", "Druid", "" };',
        "EnumUtils Classes::ToString",
    )
    text = replace_once(
        text,
        "AC_API_EXPORT std::size_t EnumUtils<Classes>::Count() { return 10; }",
        "AC_API_EXPORT std::size_t EnumUtils<Classes>::Count() { return 11; }",
        "EnumUtils Classes::Count",
    )
    text = replace_once(
        text,
        "        case 8: return CLASS_WARLOCK;\n        case 9: return CLASS_DRUID;",
        "        case 8: return CLASS_WARLOCK;\n        case 9: return CLASS_ADVENTURER;\n        case 10: return CLASS_DRUID;",
        "EnumUtils Classes::FromIndex",
    )
    return replace_once(
        text,
        "        case CLASS_WARLOCK: return 8;\n        case CLASS_DRUID: return 9;",
        "        case CLASS_WARLOCK: return 8;\n        case CLASS_ADVENTURER: return 9;\n        case CLASS_DRUID: return 10;",
        "EnumUtils Classes::ToIndex",
    )


def patch_stat_system(text: str) -> str:
    text = replace_once(
        text,
        "    0.9830f,  // Warlock\n    0.0f,     // ??\n    0.9720f   // Druid",
        "    0.9830f,  // Warlock\n    0.9880f,  // Adventurer\n    0.9720f   // Druid",
        "StatSystem diminishing k",
    )
    text = replace_once(
        text,
        "        16.00f,     // Warlock //?\n        0.0f,       // ??\n        16.00f      // Druid   //?",
        "        16.00f,     // Warlock //?\n        16.00f,     // Adventurer\n        16.00f      // Druid   //?",
        "StatSystem miss cap",
    )
    text = replace_once(
        text,
        "        0.0f,           // Warlock\n        0.0f,           // ??\n        0.0f            // Druid",
        "        0.0f,           // Warlock\n        145.560408f,    // Adventurer\n        0.0f            // Druid",
        "StatSystem parry cap",
    )
    text = replace_once(
        text,
        "        150.375940f,    // Warlock\n        0.0f,           // ??\n        116.890707f     // Druid",
        "        150.375940f,    // Warlock\n        145.560408f,    // Adventurer\n        116.890707f     // Druid",
        "StatSystem dodge cap",
    )
    text = replace_once(
        text,
        "        if (IsClass(CLASS_HUNTER, CLASS_CONTEXT_STATS))\n        {\n            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;\n        }",
        "        if (IsClass(CLASS_ADVENTURER, CLASS_CONTEXT_STATS))\n        {\n            // Classless ranged baseline: Hunter-style level scaling.\n            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;\n        }\n        else if (IsClass(CLASS_HUNTER, CLASS_CONTEXT_STATS))\n        {\n            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;\n        }",
        "StatSystem Adventurer ranged attack power",
    )
    return replace_once(
        text,
        "        if (IsClass(CLASS_PALADIN, CLASS_CONTEXT_STATS) || IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_STATS) || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_STATS))\n        {\n            val2 = level * 3.0f + GetStat(STAT_STRENGTH) * 2.0f - 20.0f;\n        }",
        "        if (IsClass(CLASS_ADVENTURER, CLASS_CONTEXT_STATS))\n        {\n            // Classless melee baseline: hybrid Strength/Agility progression.\n            val2 = level * 2.0f + GetStat(STAT_STRENGTH) + GetStat(STAT_AGILITY) - 20.0f;\n        }\n        else if (IsClass(CLASS_PALADIN, CLASS_CONTEXT_STATS) || IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_STATS) || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_STATS))\n        {\n            val2 = level * 3.0f + GetStat(STAT_STRENGTH) * 2.0f - 20.0f;\n        }",
        "StatSystem Adventurer melee attack power",
    )


def patch_custom_loader(text: str) -> str:
    text = replace_once(
        text,
        "// This is where scripts' loading functions should be declared:\n// void MyExampleScript()",
        "// This is where scripts' loading functions should be declared:\n// void MyExampleScript()\nvoid AddAdventurerCoreScripts();",
        "Custom script declaration",
    )
    return replace_once(
        text,
        "void AddCustomScripts()\n{\n    // MyExampleScript()\n}",
        "void AddCustomScripts()\n{\n    // MyExampleScript()\n    AddAdventurerCoreScripts();\n}",
        "Custom script registration",
    )


def patch_player_storage(text: str) -> str:
    old = "    if ((proto->AllowableClass & getClassMask()) == 0 || (proto->AllowableRace & getRaceMask()) == 0)\n        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;"
    new = "    if (((proto->AllowableClass & getClassMask()) == 0 && getClass() != CLASS_ADVENTURER) ||\n        (proto->AllowableRace & getRaceMask()) == 0)\n        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;"
    text = replace_exact_count(text, old, new, 2, "PlayerStorage AllowableClass checks")

    old_relic = """        case INVTYPE_RELIC:
        {
            switch (proto->SubClass)"""
    new_relic = """        case INVTYPE_RELIC:
        {
            // Adventurer is classless: every relic subtype may use the ranged
            // equipment slot. Native classes keep their stock restrictions.
            if (getClass() == CLASS_ADVENTURER)
            {
                slots[0] = EQUIPMENT_SLOT_RANGED;
                break;
            }

            switch (proto->SubClass)"""
    return replace_once(text, old_relic, new_relic, "PlayerStorage Adventurer relic slot")


def patch_player_cpp(text: str) -> str:
    return replace_once(
        text,
        "    if (!(pProto->AllowableClass & getClassMask()) && pProto->Bonding == BIND_WHEN_PICKED_UP && !IsGameMaster())",
        "    if (getClass() != CLASS_ADVENTURER && !(pProto->AllowableClass & getClassMask()) && pProto->Bonding == BIND_WHEN_PICKED_UP && !IsGameMaster())",
        "Player vendor AllowableClass check",
    )


TRANSFORMS = {
    "src/server/shared/SharedDefines.h": patch_shared_defines,
    "src/server/shared/enuminfo_SharedDefines.cpp": patch_enuminfo,
    "src/server/game/Entities/Unit/StatSystem.cpp": patch_stat_system,
    "src/server/game/Entities/Player/PlayerStorage.cpp": patch_player_storage,
    "src/server/game/Entities/Player/Player.cpp": patch_player_cpp,
    "src/server/scripts/Custom/custom_script_loader.cpp": patch_custom_loader,
}


def plan(core: Path, payload_root: Path) -> list[PlannedFile]:
    planned: list[PlannedFile] = []
    for relative, transform in TRANSFORMS.items():
        path = core / relative
        if not path.is_file():
            raise PatchError(f"Required AzerothCore source file is missing: {relative}")
        original = path.read_bytes()
        try:
            source = original.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise PatchError(f"{relative}: expected UTF-8 source") from exc
        patched = transform(source).encode("utf-8")
        planned.append(PlannedFile(relative, original, patched))

    payload_rel = "src/server/scripts/Custom/adventurer_core.cpp"
    payload = payload_root / payload_rel
    if not payload.is_file():
        raise PatchError(f"Installer payload is missing: {payload}")
    destination = core / payload_rel
    original = destination.read_bytes() if destination.exists() else None
    patched = payload.read_bytes()
    if original is not None and original != patched:
        raise PatchError(
            f"{payload_rel}: target already exists with content not owned by this package"
        )
    planned.append(PlannedFile(payload_rel, original, patched))
    return planned
