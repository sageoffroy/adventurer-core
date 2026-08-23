from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from client import (  # noqa: E402
    ADVENTURER_FRAME_INTERNAL,
    DBC_NAMES,
    build_adventurer_frame_art,
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

    def test_resource_hud_uses_custom_adventurer_player_frame_layout(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('ADVENTURER_FRAME_TEXTURE = "Interface\\\\Adventurer\\\\UI-AdventurerFrame"', lua)
        self.assertIn('PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)', lua)
        self.assertIn('ADVENTURER_FRAME_WIDTH = 248', lua)
        self.assertIn('ADVENTURER_FRAME_RIGHT_TEXCOORD = 0.03125', lua)
        self.assertIn('BAR_LEFT = 112', lua)
        self.assertIn('BAR_WIDTH = 113', lua)
        self.assertIn('RAGE_LEFT = 100', lua)
        self.assertIn('RAGE_WIDTH = 125', lua)
        self.assertIn('RAGE_TOP = 15', lua)
        self.assertIn('RAGE_HEIGHT = 5', lua)
        self.assertIn('HEALTH_TOP = 26', lua)
        self.assertIn('MANA_TOP = 45', lua)
        self.assertIn('ENERGY_TOP = 56', lua)
        self.assertIn('RUNIC_LEFT = 231', lua)
        self.assertIn('RUNIC_TOP = 16', lua)
        self.assertIn('RUNIC_WIDTH = 9', lua)
        self.assertIn('RUNIC_HEIGHT = 43', lua)
        self.assertIn('RUNES_LEFT = 128', lua)
        self.assertIn('RUNES_TOP = 82', lua)
        self.assertIn('RUNES_SCALE = 0.90', lua)
        self.assertIn('runicBar:SetOrientation("VERTICAL")', lua)
        self.assertIn('PlayerFrameHealthBar:SetPoint(', lua)
        self.assertIn('PlayerFrameManaBar:SetPoint(', lua)
        self.assertIn(
            'rageBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", RAGE_LEFT, -RAGE_TOP)',
            lua,
        )
        self.assertIn(
            'energyBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", BAR_LEFT, -ENERGY_TOP)',
            lua,
        )
        self.assertIn(
            'runicBar:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", RUNIC_LEFT, -RUNIC_TOP)',
            lua,
        )
        self.assertIn('RuneFrame:SetScale(RUNES_SCALE)', lua)
        self.assertIn(
            'RuneFrame:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", RUNES_LEFT, -RUNES_TOP)',
            lua,
        )

    def test_auxiliary_resources_still_read_native_power_pools(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('UnitPower("player", bar.powerId)', lua)
        self.assertIn('UnitPowerMax("player", bar.powerId)', lua)
        self.assertIn('AdventurerRageBar', lua)
        self.assertIn('AdventurerEnergyBar', lua)
        self.assertIn('AdventurerRunicPowerBar', lua)

    def test_resource_text_follows_repositioned_bars_and_custom_bars_show_on_hover(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('PlayerFrameHealthBarText:SetPoint("CENTER", PlayerFrameHealthBar, "CENTER", 0, 0)', lua)
        self.assertIn('PlayerFrameManaBarText:SetPoint("CENTER", PlayerFrameManaBar, "CENTER", 0, 0)', lua)
        self.assertIn('bar:EnableMouse(true)', lua)
        self.assertIn('bar.valueText:SetText(labels[bar.powerId] .. " " .. current .. " / " .. maximum)', lua)
        self.assertIn('[POWER_RAGE] = "Ira"', lua)
        self.assertIn('[POWER_ENERGY] = "Energía"', lua)
        self.assertIn('[POWER_RUNIC_POWER] = "Poder rúnico"', lua)
        self.assertIn('bar:SetScript("OnEnter"', lua)
        self.assertIn('bar:SetScript("OnLeave"', lua)
        self.assertIn('self.valueText:Show()', lua)
        self.assertIn('self.valueText:Hide()', lua)

    def test_combo_points_feed_blizzards_native_target_frame(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('COMBO_PREFIX = "AdventurerCP"', lua)
        self.assertIn('RegisterAddonMessagePrefix(COMBO_PREFIX)', lua)
        self.assertIn('RegisterEvent("CHAT_MSG_ADDON")', lua)
        self.assertIn('local nativeGetComboPoints = GetComboPoints', lua)
        self.assertIn('GetComboPoints = function(unit, target)', lua)
        self.assertIn('unit == "player" and target == "target"', lua)
        self.assertIn('ComboFrame_Update()', lua)
        self.assertNotIn("SpellDraftCP", lua)
        self.assertNotIn("SpellDraft", lua)

    def test_rune_ready_mask_refreshes_native_action_button_usability(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('RegisterEvent("RUNE_POWER_UPDATE")', lua)
        self.assertIn('GetRuneCooldown(index)', lua)
        self.assertIn('RefreshRuneActionUsability()', lua)
        self.assertIn('ActionButton_UpdateUsable(button)', lua)
        self.assertIn('lastRuneReadyMask', lua)

    def test_resource_hud_uses_native_class_id(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn("ADVENTURER_CLASS_ID = 10", lua)
        self.assertIn('classId == ADVENTURER_CLASS_ID', lua)
        self.assertIn('classToken == "ADVENTURER"', lua)

    def test_adventurer_frame_art_is_valid_bundled_blp2(self) -> None:
        art = build_adventurer_frame_art()
        self.assertTrue(art.startswith(b"BLP2"))
        self.assertEqual(int.from_bytes(art[12:16], "little"), 256)
        self.assertEqual(int.from_bytes(art[16:20], "little"), 128)

    def test_root_mpq_contains_frame_xml_hud_and_frame_art(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            work = Path(tmp_name)
            for index, name in enumerate(DBC_NAMES):
                (work / name).write_bytes(f"dbc-{index}-{name}".encode("utf-8"))

            root_files, locale_files = build_archive_files(work)
            self.assertIn("Interface\\FrameXML\\FrameXML.toc", root_files)
            self.assertIn("Interface\\FrameXML\\AdventurerResources.lua", root_files)
            self.assertIn(ADVENTURER_FRAME_INTERNAL, root_files)
            self.assertEqual(root_files[ADVENTURER_FRAME_INTERNAL], build_adventurer_frame_art())
            self.assertNotIn(ADVENTURER_FRAME_INTERNAL, locale_files)


if __name__ == "__main__":
    unittest.main()
