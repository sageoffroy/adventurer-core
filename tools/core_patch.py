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


def replace_transition(text: str, clean: str, legacy: str, new: str, label: str) -> str:
    """Accept a stock core or the previous Adventurer-owned form, never fuzz."""
    if new in text:
        return text
    clean_count = text.count(clean)
    legacy_count = text.count(legacy)
    if clean_count == 1 and legacy_count == 0:
        return text.replace(clean, new, 1)
    if clean_count == 0 and legacy_count == 1:
        return text.replace(legacy, new, 1)
    raise PatchError(
        f"{label}: expected exactly one stock or legacy anchor, "
        f"found stock={clean_count}, legacy={legacy_count}"
    )


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

    clean_ranged = """        if (IsClass(CLASS_HUNTER, CLASS_CONTEXT_STATS))
        {
            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;
        }"""
    legacy_ranged = """        if (IsClass(CLASS_ADVENTURER, CLASS_CONTEXT_STATS))
        {
            // Classless ranged baseline: Hunter-style level scaling.
            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;
        }
        else if (IsClass(CLASS_HUNTER, CLASS_CONTEXT_STATS))
        {
            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;
        }"""
    universal_ranged = """        if (IsClass(CLASS_ADVENTURER, CLASS_CONTEXT_STATS))
        {
            // Universal ranged baseline: 95% of Hunter's native formula.
            val2 = (level * 2.0f + GetStat(STAT_AGILITY) - 10.0f) * 0.95f;
        }
        else if (IsClass(CLASS_HUNTER, CLASS_CONTEXT_STATS))
        {
            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;
        }"""
    text = replace_transition(
        text,
        clean_ranged,
        legacy_ranged,
        universal_ranged,
        "StatSystem Adventurer ranged attack power",
    )

    clean_melee = """        if (IsClass(CLASS_PALADIN, CLASS_CONTEXT_STATS) || IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_STATS) || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_STATS))
        {
            val2 = level * 3.0f + GetStat(STAT_STRENGTH) * 2.0f - 20.0f;
        }"""
    legacy_melee = """        if (IsClass(CLASS_ADVENTURER, CLASS_CONTEXT_STATS))
        {
            // Classless melee baseline: hybrid Strength/Agility progression.
            val2 = level * 2.0f + GetStat(STAT_STRENGTH) + GetStat(STAT_AGILITY) - 20.0f;
        }
        else if (IsClass(CLASS_PALADIN, CLASS_CONTEXT_STATS) || IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_STATS) || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_STATS))
        {
            val2 = level * 3.0f + GetStat(STAT_STRENGTH) * 2.0f - 20.0f;
        }"""
    universal_melee = """        if (IsClass(CLASS_ADVENTURER, CLASS_CONTEXT_STATS))
        {
            // Universal melee baseline: compare the two strongest native
            // archetypes and keep 95% of whichever the current gear favours.
            float strengthBaseline = level * 3.0f + GetStat(STAT_STRENGTH) * 2.0f - 20.0f;
            float hybridBaseline = level * 2.0f + GetStat(STAT_STRENGTH) + GetStat(STAT_AGILITY) - 20.0f;
            val2 = (strengthBaseline > hybridBaseline ? strengthBaseline : hybridBaseline) * 0.95f;
        }
        else if (IsClass(CLASS_PALADIN, CLASS_CONTEXT_STATS) || IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_STATS) || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_STATS))
        {
            val2 = level * 3.0f + GetStat(STAT_STRENGTH) * 2.0f - 20.0f;
        }"""
    return replace_transition(
        text,
        clean_melee,
        legacy_melee,
        universal_melee,
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
    old_braced = """    if ((proto->AllowableClass & getClassMask()) == 0 || (proto->AllowableRace & getRaceMask()) == 0)
    {
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
    }"""
    new_braced = """    if (((proto->AllowableClass & getClassMask()) == 0 && getClass() != CLASS_ADVENTURER) ||
        (proto->AllowableRace & getRaceMask()) == 0)
    {
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
    }"""
    old_unbraced = """    if ((proto->AllowableClass & getClassMask()) == 0 || (proto->AllowableRace & getRaceMask()) == 0)
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;"""
    new_unbraced = """    if (((proto->AllowableClass & getClassMask()) == 0 && getClass() != CLASS_ADVENTURER) ||
        (proto->AllowableRace & getRaceMask()) == 0)
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;"""

    clean_counts = (text.count(old_braced), text.count(old_unbraced))
    patched_counts = (text.count(new_braced), text.count(new_unbraced))
    if clean_counts == (1, 1) and patched_counts == (0, 0):
        text = text.replace(old_braced, new_braced, 1)
        text = text.replace(old_unbraced, new_unbraced, 1)
    elif clean_counts == (0, 0) and patched_counts == (1, 1):
        pass
    else:
        raise PatchError(
            "PlayerStorage AllowableClass checks: expected one braced and one "
            f"unbraced anchor in the same state, found clean={clean_counts}, patched={patched_counts}"
        )

    # Playerbots has hard class gates in addition to AllowableClass. Without
    # these exceptions an Adventurer can know the proficiency and still be
    # rejected before CanUseItem reaches the generic skill checks.
    bot_relics = (
        ("ITEM_SUBCLASS_ARMOR_IDOL", "CLASS_DRUID"),
        ("ITEM_SUBCLASS_ARMOR_TOTEM", "CLASS_SHAMAN"),
        ("ITEM_SUBCLASS_ARMOR_LIBRAM", "CLASS_PALADIN"),
        ("ITEM_SUBCLASS_ARMOR_SIGIL", "CLASS_DEATH_KNIGHT"),
    )
    for subclass, native_class in bot_relics:
        old_bot = (
            f"    if (proto->Class == ITEM_CLASS_ARMOR && proto->SubClass == {subclass} && "
            f"!IsClass({native_class}, CLASS_CONTEXT_EQUIP_RELIC))"
        )
        new_bot = (
            f"    if (getClass() != CLASS_ADVENTURER && proto->Class == ITEM_CLASS_ARMOR && "
            f"proto->SubClass == {subclass} && !IsClass({native_class}, CLASS_CONTEXT_EQUIP_RELIC))"
        )
        text = replace_once(text, old_bot, new_bot, f"PlayerStorage bot relic gate {subclass}")

    old_shield = """        if (proto->SubClass == ITEM_SUBCLASS_ARMOR_SHIELD && !(
            IsClass(CLASS_PALADIN, CLASS_CONTEXT_EQUIP_SHIELDS)
            || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_EQUIP_SHIELDS)
            || IsClass(CLASS_SHAMAN, CLASS_CONTEXT_EQUIP_SHIELDS)))"""
    new_shield = """        if (getClass() != CLASS_ADVENTURER && proto->SubClass == ITEM_SUBCLASS_ARMOR_SHIELD && !(
            IsClass(CLASS_PALADIN, CLASS_CONTEXT_EQUIP_SHIELDS)
            || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_EQUIP_SHIELDS)
            || IsClass(CLASS_SHAMAN, CLASS_CONTEXT_EQUIP_SHIELDS)))"""
    text = replace_once(text, old_shield, new_shield, "PlayerStorage Adventurer shield gate")

    direct_relics = (
        ("ITEM_SUBCLASS_ARMOR_LIBRAM", "CLASS_PALADIN"),
        ("ITEM_SUBCLASS_ARMOR_IDOL", "CLASS_DRUID"),
        ("ITEM_SUBCLASS_ARMOR_TOTEM", "CLASS_SHAMAN"),
        ("ITEM_SUBCLASS_ARMOR_SIGIL", "CLASS_DEATH_KNIGHT"),
    )
    for subclass, native_class in direct_relics:
        old_direct = (
            f"        if (proto->SubClass == {subclass} && "
            f"!IsClass({native_class}, CLASS_CONTEXT_EQUIP_RELIC))"
        )
        new_direct = (
            f"        if (getClass() != CLASS_ADVENTURER && proto->SubClass == {subclass} && "
            f"!IsClass({native_class}, CLASS_CONTEXT_EQUIP_RELIC))"
        )
        text = replace_once(text, old_direct, new_direct, f"PlayerStorage relic gate {subclass}")

    old_armor_rank = """    if (proto->Class == ITEM_CLASS_ARMOR && proto->SubClass > ITEM_SUBCLASS_ARMOR_MISC && proto->SubClass < ITEM_SUBCLASS_ARMOR_BUCKLER &&
        proto->InventoryType != INVTYPE_CLOAK)"""
    new_armor_rank = """    if (getClass() != CLASS_ADVENTURER && proto->Class == ITEM_CLASS_ARMOR &&
        proto->SubClass > ITEM_SUBCLASS_ARMOR_MISC && proto->SubClass < ITEM_SUBCLASS_ARMOR_BUCKLER &&
        proto->InventoryType != INVTYPE_CLOAK)"""
    text = replace_once(text, old_armor_rank, new_armor_rank, "PlayerStorage Adventurer armor hierarchy")

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
    text = replace_once(
        text,
        "    if (!(pProto->AllowableClass & getClassMask()) && pProto->Bonding == BIND_WHEN_PICKED_UP && !IsGameMaster())",
        "    if (getClass() != CLASS_ADVENTURER && !(pProto->AllowableClass & getClassMask()) && pProto->Bonding == BIND_WHEN_PICKED_UP && !IsGameMaster())",
        "Player vendor AllowableClass check",
    )

    clean_base_dodge = """        0.024211f, // Warlock
        0.0f,      // ??
        0.056097f  // Druid"""
    legacy_base_dodge = """        0.024211f, // Warlock
        0.053292f, // Adventurer: 95% of Druid's strongest native base dodge
        0.056097f  // Druid"""
    universal_base_dodge = """        0.024211f, // Warlock
        0.053292f, // Adventurer fallback; runtime compares complete native formulas
        0.056097f  // Druid"""
    text = replace_transition(
        text,
        clean_base_dodge,
        legacy_base_dodge,
        universal_base_dodge,
        "Player Adventurer base dodge",
    )

    clean_dodge_coefficient = """        0.97f / 1.15f,  // Warlock (?)
        0.0f,           // ??
        2.00f / 1.15f   // Druid"""
    legacy_dodge_coefficient = """        0.97f / 1.15f,  // Warlock (?)
        2.00f / 1.15f,  // Adventurer; its class-10 crit curve already carries the 95% scale
        2.00f / 1.15f   // Druid"""
    universal_dodge_coefficient = """        0.97f / 1.15f,  // Warlock (?)
        2.00f / 1.15f,  // Adventurer fallback; runtime branch keeps native formulas intact
        2.00f / 1.15f   // Druid"""
    text = replace_transition(
        text,
        clean_dodge_coefficient,
        legacy_dodge_coefficient,
        universal_dodge_coefficient,
        "Player Adventurer agility-to-dodge coefficient",
    )

    melee_anchor = """    if (level > GT_MAX_LEVEL)
        level = GT_MAX_LEVEL;
    GtChanceToMeleeCritBaseEntry const* critBase  = sGtChanceToMeleeCritBaseStore.LookupEntry(pclass - 1);
    GtChanceToMeleeCritEntry     const* critRatio = sGtChanceToMeleeCritStore.LookupEntry((pclass - 1) * GT_MAX_LEVEL + level - 1);"""
    melee_runtime = """    if (level > GT_MAX_LEVEL)
        level = GT_MAX_LEVEL;

    if (pclass == CLASS_ADVENTURER)
    {
        // Compare every native class as a complete formula; never mix a base
        // from one class with the Agility coefficient from another.
        float bestCrit = 0.0f;
        bool found = false;
        for (uint32 nativeClass = CLASS_WARRIOR; nativeClass < MAX_CLASSES; ++nativeClass)
        {
            if (nativeClass == CLASS_ADVENTURER)
                continue;

            GtChanceToMeleeCritBaseEntry const* nativeBase = sGtChanceToMeleeCritBaseStore.LookupEntry(nativeClass - 1);
            GtChanceToMeleeCritEntry const* nativeRatio = sGtChanceToMeleeCritStore.LookupEntry((nativeClass - 1) * GT_MAX_LEVEL + level - 1);
            if (!nativeBase || !nativeRatio)
                continue;

            float candidate = nativeBase->base + GetStat(STAT_AGILITY) * nativeRatio->ratio;
            if (!found || candidate > bestCrit)
            {
                bestCrit = candidate;
                found = true;
            }
        }
        return (found ? bestCrit * 0.95f : 0.0f) * 100.0f;
    }

    GtChanceToMeleeCritBaseEntry const* critBase  = sGtChanceToMeleeCritBaseStore.LookupEntry(pclass - 1);
    GtChanceToMeleeCritEntry     const* critRatio = sGtChanceToMeleeCritStore.LookupEntry((pclass - 1) * GT_MAX_LEVEL + level - 1);"""
    text = replace_once(
        text,
        melee_anchor,
        melee_runtime,
        "Player Adventurer complete melee crit formula",
    )

    dodge_anchor = """    float base_agility = GetCreateStat(STAT_AGILITY) * GetPctModifierValue(UnitMods(UNIT_MOD_STAT_START + AsUnderlyingType(STAT_AGILITY)), BASE_PCT);
    float bonus_agility = GetStat(STAT_AGILITY) - base_agility;
    // calculate diminishing (green in char screen) and non-diminishing (white) contribution
    diminishing = 100.0f * bonus_agility * dodgeRatio->ratio * crit_to_dodge[pclass - 1];
    nondiminishing = 100.0f * (dodge_base[pclass - 1] + base_agility * dodgeRatio->ratio * crit_to_dodge[pclass - 1]);"""
    dodge_runtime = """    float base_agility = GetCreateStat(STAT_AGILITY) * GetPctModifierValue(UnitMods(UNIT_MOD_STAT_START + AsUnderlyingType(STAT_AGILITY)), BASE_PCT);
    float bonus_agility = GetStat(STAT_AGILITY) - base_agility;

    if (pclass == CLASS_ADVENTURER)
    {
        // Keep each native dodge model intact (base dodge plus that class's own
        // Agility conversion), choose the best total, then apply the 5% penalty.
        float bestDiminishing = 0.0f;
        float bestNondiminishing = 0.0f;
        float bestTotal = 0.0f;
        bool found = false;
        for (uint32 nativeClass = CLASS_WARRIOR; nativeClass < MAX_CLASSES; ++nativeClass)
        {
            if (nativeClass == CLASS_ADVENTURER)
                continue;

            GtChanceToMeleeCritEntry const* nativeRatio = sGtChanceToMeleeCritStore.LookupEntry((nativeClass - 1) * GT_MAX_LEVEL + level - 1);
            if (!nativeRatio)
                continue;

            float candidateDiminishing = 100.0f * bonus_agility * nativeRatio->ratio * crit_to_dodge[nativeClass - 1];
            float candidateNondiminishing = 100.0f * (dodge_base[nativeClass - 1] + base_agility * nativeRatio->ratio * crit_to_dodge[nativeClass - 1]);
            float candidateTotal = candidateDiminishing + candidateNondiminishing;
            if (!found || candidateTotal > bestTotal)
            {
                bestDiminishing = candidateDiminishing;
                bestNondiminishing = candidateNondiminishing;
                bestTotal = candidateTotal;
                found = true;
            }
        }

        diminishing = found ? bestDiminishing * 0.95f : 0.0f;
        nondiminishing = found ? bestNondiminishing * 0.95f : 0.0f;
        return;
    }

    // calculate diminishing (green in char screen) and non-diminishing (white) contribution
    diminishing = 100.0f * bonus_agility * dodgeRatio->ratio * crit_to_dodge[pclass - 1];
    nondiminishing = 100.0f * (dodge_base[pclass - 1] + base_agility * dodgeRatio->ratio * crit_to_dodge[pclass - 1]);"""
    text = replace_once(
        text,
        dodge_anchor,
        dodge_runtime,
        "Player Adventurer complete dodge formula",
    )

    spell_anchor = """    if (level > GT_MAX_LEVEL)
        level = GT_MAX_LEVEL;
    GtChanceToSpellCritBaseEntry const* critBase  = sGtChanceToSpellCritBaseStore.LookupEntry(pclass - 1);
    GtChanceToSpellCritEntry     const* critRatio = sGtChanceToSpellCritStore.LookupEntry((pclass - 1) * GT_MAX_LEVEL + level - 1);"""
    spell_runtime = """    if (level > GT_MAX_LEVEL)
        level = GT_MAX_LEVEL;

    if (pclass == CLASS_ADVENTURER)
    {
        // Compare complete native spell-crit formulas against current Intellect.
        float bestCrit = 0.0f;
        bool found = false;
        for (uint32 nativeClass = CLASS_WARRIOR; nativeClass < MAX_CLASSES; ++nativeClass)
        {
            if (nativeClass == CLASS_ADVENTURER)
                continue;

            GtChanceToSpellCritBaseEntry const* nativeBase = sGtChanceToSpellCritBaseStore.LookupEntry(nativeClass - 1);
            GtChanceToSpellCritEntry const* nativeRatio = sGtChanceToSpellCritStore.LookupEntry((nativeClass - 1) * GT_MAX_LEVEL + level - 1);
            if (!nativeBase || !nativeRatio)
                continue;

            float candidate = nativeBase->base + GetStat(STAT_INTELLECT) * nativeRatio->ratio;
            if (!found || candidate > bestCrit)
            {
                bestCrit = candidate;
                found = true;
            }
        }
        return (found ? bestCrit * 0.95f : 0.0f) * 100.0f;
    }

    GtChanceToSpellCritBaseEntry const* critBase  = sGtChanceToSpellCritBaseStore.LookupEntry(pclass - 1);
    GtChanceToSpellCritEntry     const* critRatio = sGtChanceToSpellCritStore.LookupEntry((pclass - 1) * GT_MAX_LEVEL + level - 1);"""
    return replace_once(
        text,
        spell_anchor,
        spell_runtime,
        "Player Adventurer complete spell crit formula",
    )


TRANSFORMS = {
    "src/server/shared/SharedDefines.h": patch_shared_defines,
    "src/server/shared/enuminfo_SharedDefines.cpp": patch_enuminfo,
    "src/server/game/Entities/Unit/StatSystem.cpp": patch_stat_system,
    "src/server/game/Entities/Player/PlayerStorage.cpp": patch_player_storage,
    "src/server/game/Entities/Player/Player.cpp": patch_player_cpp,
    "src/server/scripts/Custom/custom_script_loader.cpp": patch_custom_loader,
}


def plan(core: Path, payload_root: Path, *, allow_payload_replace: bool = False) -> list[PlannedFile]:
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
    if original is not None and original != patched and not allow_payload_replace:
        raise PatchError(
            f"{payload_rel}: target already exists with content not owned by this package"
        )
    planned.append(PlannedFile(payload_rel, original, patched))
    return planned