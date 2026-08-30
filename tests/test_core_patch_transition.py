from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from core_patch import PatchError, patch_custom_loader  # noqa: E402


CLEAN_DECL = "// This is where scripts' loading functions should be declared:\n// void MyExampleScript()"
LEGACY_DECL = CLEAN_DECL + "\nvoid AddAdventurerCoreScripts();"
CURRENT_DECL = LEGACY_DECL + "\nvoid AddAdventurerCollectionScripts();"

CLEAN_BODY = "void AddCustomScripts()\n{\n    // MyExampleScript()\n}"
LEGACY_BODY = "void AddCustomScripts()\n{\n    // MyExampleScript()\n    AddAdventurerCoreScripts();\n}"
CURRENT_BODY = "void AddCustomScripts()\n{\n    // MyExampleScript()\n    AddAdventurerCoreScripts();\n    AddAdventurerCollectionScripts();\n}"


class CorePatchTransitionTests(unittest.TestCase):
    def test_loader_upgrades_previous_adventurer_state_when_stock_anchor_is_nested(self) -> None:
        legacy = LEGACY_DECL + "\n\n// The name of this function should match:\n" + LEGACY_BODY + "\n"
        patched = patch_custom_loader(legacy)
        self.assertIn(CURRENT_DECL, patched)
        self.assertIn(CURRENT_BODY, patched)
        self.assertEqual(patched.count("void AddAdventurerCoreScripts();"), 1)
        self.assertEqual(patched.count("void AddAdventurerCollectionScripts();"), 1)

    def test_loader_remains_idempotent_after_upgrade(self) -> None:
        current = CURRENT_DECL + "\n\n// The name of this function should match:\n" + CURRENT_BODY + "\n"
        self.assertEqual(patch_custom_loader(current), current)

    def test_loader_rejects_real_duplicate_stock_anchor_outside_legacy_block(self) -> None:
        ambiguous = (
            LEGACY_DECL
            + "\n\n"
            + CLEAN_DECL
            + "\n\n// The name of this function should match:\n"
            + LEGACY_BODY
            + "\n"
        )
        with self.assertRaises(PatchError):
            patch_custom_loader(ambiguous)


if __name__ == "__main__":
    unittest.main()
