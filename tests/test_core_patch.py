from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from core_patch import PatchError, plan  # noqa: E402


SHARED = """enum Classes
{
    CLASS_WARLOCK       = 9, // TITLE Warlock
    //CLASS_UNK           = 10,
    CLASS_DRUID         = 11 // TITLE Druid
};
#define CLASSMASK_ALL_PLAYABLE \\
    (1<<(CLASS_MAGE-1))   |(1<<(CLASS_WARLOCK-1))|(1<<(CLASS_DRUID-1)) | \\
    (1<<(CLASS_DEATH_KNIGHT-1)))
"""

ENUMINFO = """        case CLASS_WARLOCK: return { \"CLASS_WARLOCK\", \"Warlock\", \"\" };
        case CLASS_DRUID: return { \"CLASS_DRUID\", \"Druid\", \"\" };
AC_API_EXPORT std::size_t EnumUtils<Classes>::Count() { return 10; }
        case 8: return CLASS_WARLOCK;
        case 9: return CLASS_DRUID;
        case CLASS_WARLOCK: return 8;
        case CLASS_DRUID: return 9;
"""

STAT = """    0.9830f,  // Warlock
    0.0f,     // ??
    0.9720f   // Druid
        16.00f,     // Warlock //?
        0.0f,       // ??
        16.00f      // Druid   //?
        0.0f,           // Warlock
        0.0f,           // ??
        0.0f            // Druid
        150.375940f,    // Warlock
        0.0f,           // ??
        116.890707f     // Druid
        if (IsClass(CLASS_HUNTER, CLASS_CONTEXT_STATS))
        {
            val2 = level * 2.0f + GetStat(STAT_AGILITY) - 10.0f;
        }
        if (IsClass(CLASS_PALADIN, CLASS_CONTEXT_STATS) || IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_STATS) || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_STATS))
        {
            val2 = level * 3.0f + GetStat(STAT_STRENGTH) * 2.0f - 20.0f;
        }
"""

ALLOWABLE = """    if ((proto->AllowableClass & getClassMask()) == 0 || (proto->AllowableRace & getRaceMask()) == 0)
    {
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
    }
X
    if ((proto->AllowableClass & getClassMask()) == 0 || (proto->AllowableRace & getRaceMask()) == 0)
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;

InventoryResult Player::BotCanUseItem(ItemTemplate const* proto) const
{
    if (proto->Class == ITEM_CLASS_ARMOR && proto->SubClass == ITEM_SUBCLASS_ARMOR_IDOL && !IsClass(CLASS_DRUID, CLASS_CONTEXT_EQUIP_RELIC))
    {
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
    }
    if (proto->Class == ITEM_CLASS_ARMOR && proto->SubClass == ITEM_SUBCLASS_ARMOR_TOTEM && !IsClass(CLASS_SHAMAN, CLASS_CONTEXT_EQUIP_RELIC))
    {
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
    }
    if (proto->Class == ITEM_CLASS_ARMOR && proto->SubClass == ITEM_SUBCLASS_ARMOR_LIBRAM && !IsClass(CLASS_PALADIN, CLASS_CONTEXT_EQUIP_RELIC))
    {
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
    }
    if (proto->Class == ITEM_CLASS_ARMOR && proto->SubClass == ITEM_SUBCLASS_ARMOR_SIGIL && !IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_EQUIP_RELIC))
    {
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
    }
}

    if (proto->Class == ITEM_CLASS_ARMOR)
    {
        if (proto->SubClass == ITEM_SUBCLASS_ARMOR_SHIELD && !(
            IsClass(CLASS_PALADIN, CLASS_CONTEXT_EQUIP_SHIELDS)
            || IsClass(CLASS_WARRIOR, CLASS_CONTEXT_EQUIP_SHIELDS)
            || IsClass(CLASS_SHAMAN, CLASS_CONTEXT_EQUIP_SHIELDS)))
        {
            return EQUIP_ERR_NO_REQUIRED_PROFICIENCY;
        }
        if (proto->SubClass == ITEM_SUBCLASS_ARMOR_LIBRAM && !IsClass(CLASS_PALADIN, CLASS_CONTEXT_EQUIP_RELIC))
        {
            return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
        }
        if (proto->SubClass == ITEM_SUBCLASS_ARMOR_IDOL && !IsClass(CLASS_DRUID, CLASS_CONTEXT_EQUIP_RELIC))
        {
            return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
        }
        if (proto->SubClass == ITEM_SUBCLASS_ARMOR_TOTEM && !IsClass(CLASS_SHAMAN, CLASS_CONTEXT_EQUIP_RELIC))
        {
            return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
        }
        if (proto->SubClass == ITEM_SUBCLASS_ARMOR_SIGIL && !IsClass(CLASS_DEATH_KNIGHT, CLASS_CONTEXT_EQUIP_RELIC))
        {
            return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
        }
    }

    if (proto->Class == ITEM_CLASS_ARMOR && proto->SubClass > ITEM_SUBCLASS_ARMOR_MISC && proto->SubClass < ITEM_SUBCLASS_ARMOR_BUCKLER &&
        proto->InventoryType != INVTYPE_CLOAK)
    {
    }

        case INVTYPE_RELIC:
        {
            switch (proto->SubClass)
"""

PLAYER = """    if (!(pProto->AllowableClass & getClassMask()) && pProto->Bonding == BIND_WHEN_PICKED_UP && !IsGameMaster())

float Player::GetMeleeCritFromAgility()
{
    uint8 level = GetLevel();
    uint32 pclass = getClass();

    if (level > GT_MAX_LEVEL)
        level = GT_MAX_LEVEL;
    GtChanceToMeleeCritBaseEntry const* critBase  = sGtChanceToMeleeCritBaseStore.LookupEntry(pclass - 1);
    GtChanceToMeleeCritEntry     const* critRatio = sGtChanceToMeleeCritStore.LookupEntry((pclass - 1) * GT_MAX_LEVEL + level - 1);
    if (!critBase || !critRatio)
        return 0.0f;
    return (critBase->base + GetStat(STAT_AGILITY) * critRatio->ratio) * 100.0f;
}

void Player::GetDodgeFromAgility(float& diminishing, float& nondiminishing)
{
    const float dodge_base[MAX_CLASSES] =
    {
        0.036640f, // Warrior
        0.034943f, // Paladin
        -0.040873f, // Hunter
        0.020957f, // Rogue
        0.034178f, // Priest
        0.036640f, // DK
        0.021080f, // Shaman
        0.036587f, // Mage
        0.024211f, // Warlock
        0.0f,      // ??
        0.056097f  // Druid
    };
    const float crit_to_dodge[MAX_CLASSES] =
    {
        0.85f / 1.15f,  // Warrior
        1.00f / 1.15f,  // Paladin
        1.11f / 1.15f,  // Hunter
        2.00f / 1.15f,  // Rogue
        1.00f / 1.15f,  // Priest
        0.85f / 1.15f,  // DK
        1.60f / 1.15f,  // Shaman
        1.00f / 1.15f,  // Mage
        0.97f / 1.15f,  // Warlock (?)
        0.0f,           // ??
        2.00f / 1.15f   // Druid
    };
    uint8 level = GetLevel();
    uint32 pclass = getClass();
    if (level > GT_MAX_LEVEL)
        level = GT_MAX_LEVEL;
    GtChanceToMeleeCritEntry const* dodgeRatio = sGtChanceToMeleeCritStore.LookupEntry((pclass - 1) * GT_MAX_LEVEL + level - 1);
    if (!dodgeRatio || pclass > MAX_CLASSES)
        return;
    float base_agility = GetCreateStat(STAT_AGILITY) * GetPctModifierValue(UnitMods(UNIT_MOD_STAT_START + AsUnderlyingType(STAT_AGILITY)), BASE_PCT);
    float bonus_agility = GetStat(STAT_AGILITY) - base_agility;
    // calculate diminishing (green in char screen) and non-diminishing (white) contribution
    diminishing = 100.0f * bonus_agility * dodgeRatio->ratio * crit_to_dodge[pclass - 1];
    nondiminishing = 100.0f * (dodge_base[pclass - 1] + base_agility * dodgeRatio->ratio * crit_to_dodge[pclass - 1]);
}

float Player::GetSpellCritFromIntellect()
{
    uint8 level = GetLevel();
    uint32 pclass = getClass();

    if (level > GT_MAX_LEVEL)
        level = GT_MAX_LEVEL;
    GtChanceToSpellCritBaseEntry const* critBase  = sGtChanceToSpellCritBaseStore.LookupEntry(pclass - 1);
    GtChanceToSpellCritEntry     const* critRatio = sGtChanceToSpellCritStore.LookupEntry((pclass - 1) * GT_MAX_LEVEL + level - 1);
    if (!critBase || !critRatio)
        return 0.0f;
    return (critBase->base + GetStat(STAT_INTELLECT) * critRatio->ratio) * 100.0f;
}
"""

LOADER = """// This is where scripts' loading functions should be declared:
// void MyExampleScript()

// The name of this function should match:
void AddCustomScripts()
{
    // MyExampleScript()
}
"""

FILES = {
    "src/server/shared/SharedDefines.h": SHARED,
    "src/server/shared/enuminfo_SharedDefines.cpp": ENUMINFO,
    "src/server/game/Entities/Unit/StatSystem.cpp": STAT,
    "src/server/game/Entities/Player/PlayerStorage.cpp": ALLOWABLE,
    "src/server/game/Entities/Player/Player.cpp": PLAYER,
    "src/server/scripts/Custom/custom_script_loader.cpp": LOADER,
}


class CorePatchTests(unittest.TestCase):
    def make_tree(self, root: Path) -> Path:
        for rel, text in FILES.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        payload = root / "payload" / "src/server/scripts/Custom/adventurer_core.cpp"
        payload.parent.mkdir(parents=True, exist_ok=True)
        payload.write_text("void AddAdventurerCoreScripts() {}\n", encoding="utf-8")
        return root / "payload"

    def test_plan_is_idempotent_after_first_application(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            payload = self.make_tree(core)
            first = plan(core, payload)
            self.assertEqual(len(first), 7)
            storage = next(item.patched.decode("utf-8") for item in first if item.relative_path.endswith("PlayerStorage.cpp"))
            self.assertEqual(storage.count("getClass() != CLASS_ADVENTURER) ||"), 2)
            self.assertIn("getClass() != CLASS_ADVENTURER && proto->SubClass == ITEM_SUBCLASS_ARMOR_SHIELD", storage)
            self.assertIn("getClass() != CLASS_ADVENTURER && proto->Class == ITEM_CLASS_ARMOR", storage)
            self.assertIn("if (getClass() == CLASS_ADVENTURER)", storage)

            player = next(item.patched.decode("utf-8") for item in first if item.relative_path.endswith("Player.cpp"))
            self.assertIn("runtime compares complete native formulas", player)
            self.assertIn("for (uint32 nativeClass = CLASS_WARRIOR; nativeClass < MAX_CLASSES; ++nativeClass)", player)
            self.assertIn("nativeBase->base + GetStat(STAT_AGILITY) * nativeRatio->ratio", player)
            self.assertIn("nativeBase->base + GetStat(STAT_INTELLECT) * nativeRatio->ratio", player)
            self.assertIn("candidateTotal = candidateDiminishing + candidateNondiminishing", player)
            self.assertGreaterEqual(player.count("bestCrit * 0.95f"), 2)
            self.assertIn("bestDiminishing * 0.95f", player)
            self.assertIn("bestNondiminishing * 0.95f", player)

            stat = next(item.patched.decode("utf-8") for item in first if item.relative_path.endswith("StatSystem.cpp"))
            self.assertIn("Universal ranged baseline: 95% of Hunter's native formula", stat)
            self.assertIn("Universal melee baseline", stat)
            self.assertIn("145.560408f,    // Adventurer", stat)

            for item in first:
                target = core / item.relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(item.patched)

            second = plan(core, payload)
            for item in second:
                self.assertEqual(item.original, item.patched, item.relative_path)

    def test_accepts_previous_adventurer_dodge_table_state(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            payload = self.make_tree(core)
            path = core / "src/server/game/Entities/Player/Player.cpp"
            text = path.read_text(encoding="utf-8")
            text = text.replace(
                "        0.024211f, // Warlock\n        0.0f,      // ??\n        0.056097f  // Druid",
                "        0.024211f, // Warlock\n        0.053292f, // Adventurer: 95% of Druid's strongest native base dodge\n        0.056097f  // Druid",
            )
            text = text.replace(
                "        0.97f / 1.15f,  // Warlock (?)\n        0.0f,           // ??\n        2.00f / 1.15f   // Druid",
                "        0.97f / 1.15f,  // Warlock (?)\n        2.00f / 1.15f,  // Adventurer; its class-10 crit curve already carries the 95% scale\n        2.00f / 1.15f   // Druid",
            )
            path.write_text(text, encoding="utf-8")

            planned = plan(core, payload)
            player = next(item.patched.decode("utf-8") for item in planned if item.relative_path.endswith("Player.cpp"))
            self.assertIn("runtime compares complete native formulas", player)
            self.assertIn("runtime branch keeps native formulas intact", player)

    def test_partial_allowable_class_patch_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            payload = self.make_tree(core)
            path = core / "src/server/game/Entities/Player/PlayerStorage.cpp"
            clean = "    if ((proto->AllowableClass & getClassMask()) == 0 || (proto->AllowableRace & getRaceMask()) == 0)\n        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;"
            patched = "    if (((proto->AllowableClass & getClassMask()) == 0 && getClass() != CLASS_ADVENTURER) ||\n        (proto->AllowableRace & getRaceMask()) == 0)\n        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;"
            path.write_text(path.read_text().replace(clean, patched, 1), encoding="utf-8")
            with self.assertRaises(PatchError):
                plan(core, payload)

    def test_unknown_anchor_is_rejected_before_writes(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            payload = self.make_tree(core)
            path = core / "src/server/shared/SharedDefines.h"
            original = path.read_bytes()
            path.write_text(path.read_text().replace("//CLASS_UNK", "//SOMETHING_ELSE"), encoding="utf-8")
            before = path.read_bytes()
            with self.assertRaises(PatchError):
                plan(core, payload)
            self.assertEqual(path.read_bytes(), before)
            self.assertNotEqual(original, before)


if __name__ == "__main__":
    unittest.main()
