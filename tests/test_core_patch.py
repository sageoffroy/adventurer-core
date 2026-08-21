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
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
X
    if ((proto->AllowableClass & getClassMask()) == 0 || (proto->AllowableRace & getRaceMask()) == 0)
        return EQUIP_ERR_YOU_CAN_NEVER_USE_THAT_ITEM;
        case INVTYPE_RELIC:
        {
            switch (proto->SubClass)
"""

PLAYER = """    if (!(pProto->AllowableClass & getClassMask()) && pProto->Bonding == BIND_WHEN_PICKED_UP && !IsGameMaster())
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
            for item in first:
                target = core / item.relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(item.patched)

            second = plan(core, payload)
            for item in second:
                self.assertEqual(item.original, item.patched, item.relative_path)

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
