from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import load_specs  # noqa: E402


class FourTalentTabTests(unittest.TestCase):
    def test_all_specs_publish_the_same_four_adventurer_tabs(self) -> None:
        specs = load_specs()
        expected = [
            (5000, "guardian", 383, 0, "Guardián"),
            (5001, "champion", 161, 1, "Mercenario"),
            (5002, "scholar", 382, 2, "Erudito"),
            (5003, "explorer", 362, 3, "Explorador"),
        ]
        for spec in specs:
            actual = [
                (
                    int(tab["id"]),
                    str(tab["key"]),
                    int(tab["source_tab_id"]),
                    int(tab["order"]),
                    str(tab["esMX"]),
                )
                for tab in spec["tabs"]
            ]
            self.assertEqual(actual, expected)

    def test_core_patch_expands_server_talent_tab_capacity(self) -> None:
        source = (ROOT / "tools/core_patch.py").read_text(encoding="utf-8")
        self.assertIn('"#define MAX_TALENT_TABS 4"', source)
        self.assertIn('"static uint32 sTalentTabPages[MAX_CLASSES][MAX_TALENT_TABS];"', source)
        self.assertIn('"src/server/shared/DataStores/DBCStructure.h": patch_dbc_structure', source)
        self.assertIn('"src/server/game/DataStores/DBCStores.cpp": patch_dbc_stores', source)

    def test_client_moves_glyphs_to_fifth_tab_for_adventurer(self) -> None:
        source = (ROOT / "client/AdventurerResources.lua").read_text(encoding="utf-8")
        self.assertIn("ADVENTURER_TALENT_TAB_COUNT = 4", source)
        self.assertIn("ADVENTURER_GLYPH_TAB_ID = 5", source)
        self.assertIn('CreateFrame("Button", "PlayerTalentFrameTab5"', source)
        self.assertIn("fourthTab:SetScript(\"OnClick\", PlayerTalentTab_OnClick)", source)
        self.assertIn("GLYPH_TALENT_TAB = ADVENTURER_GLYPH_TAB_ID", source)
        self.assertIn('addonName == "Blizzard_TalentUI"', source)


if __name__ == "__main__":
    unittest.main()
