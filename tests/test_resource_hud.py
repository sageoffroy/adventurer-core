from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from client import (  # noqa: E402
    DBC_NAMES,
    build_adventurer_resources_lua,
    build_archive_files,
    build_frame_xml_toc,
)


class AdventurerResourceHudTests(unittest.TestCase):
    def test_frame_xml_loads_resource_hud_after_native_runes(self) -> None:
        toc = build_frame_xml_toc().decode("utf-8")
        self.assertIn(
            "RuneFrame.xml\nAdventurerResources.lua\nEasyMenu.lua",
            toc,
        )
        self.assertEqual(toc.count("AdventurerResources.lua"), 1)

    def test_resource_hud_stacks_all_auxiliary_bars_under_native_mana(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('UnitPower("player", bar.powerId)', lua)
        self.assertIn('UnitPowerMax("player", bar.powerId)', lua)
        self.assertIn(
            'rageBar:SetPoint("TOPLEFT", PlayerFrameManaBar, "BOTTOMLEFT", 0, -1)',
            lua,
        )
        self.assertIn(
            'energyBar:SetPoint("TOPLEFT", rageBar, "BOTTOMLEFT", 0, -1)',
            lua,
        )
        self.assertIn(
            'runicBar:SetPoint("TOPLEFT", energyBar, "BOTTOMLEFT", 0, -1)',
            lua,
        )
        self.assertIn(
            'RuneFrame:SetPoint("TOPLEFT", runicBar, "BOTTOMLEFT", 2, -4)',
            lua,
        )

    def test_resource_hud_uses_class_id_and_preserves_native_combo_frame(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn("ADVENTURER_CLASS_ID = 10", lua)
        self.assertIn('classId == ADVENTURER_CLASS_ID', lua)
        self.assertIn("ComboFrame_Update()", lua)
        self.assertNotIn("GetComboPoints =", lua)
        self.assertNotIn("SpellDraft", lua)

    def test_root_mpq_contains_frame_xml_resource_payload(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            work = Path(tmp_name)
            for index, name in enumerate(DBC_NAMES):
                (work / name).write_bytes(f"dbc-{index}-{name}".encode("utf-8"))

            root_files, _ = build_archive_files(work)
            self.assertIn("Interface\\FrameXML\\FrameXML.toc", root_files)
            self.assertIn("Interface\\FrameXML\\AdventurerResources.lua", root_files)


if __name__ == "__main__":
    unittest.main()
