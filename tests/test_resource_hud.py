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
    def test_frame_xml_loads_resource_hud_after_combo_frame(self) -> None:
        toc = build_frame_xml_toc().decode("utf-8")
        self.assertIn(
            "ComboFrame.xml\nAdventurerResources.lua\nTabardFrame.xml",
            toc,
        )
        self.assertEqual(toc.count("AdventurerResources.lua"), 1)

    def test_resource_hud_uses_custom_adventurer_player_frame_layout(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('ADVENTURER_FRAME_TEXTURE = "Interface\\\\Adventurer\\\\UI-AdventurerFrame"', lua)
        self.assertIn('ADVENTURER_FRAME_WIDTH = 248', lua)
        self.assertIn('ADVENTURER_FRAME_RIGHT_TEXCOORD = 0.03125', lua)
        self.assertIn('BAR_LEFT = 110', lua)
        self.assertIn('BAR_WIDTH = 115', lua)
        self.assertIn('RAGE_LEFT = 91', lua)
        self.assertIn('RAGE_WIDTH = 135', lua)
        self.assertIn('RAGE_TOP = 12', lua)
        self.assertIn('RAGE_HEIGHT = 10', lua)
        self.assertIn('HEALTH_TOP = 26', lua)
        self.assertIn('MANA_TOP = 45', lua)
        self.assertIn('ENERGY_TOP = 56', lua)
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

    def test_frame_art_is_rendered_above_all_resource_bars(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('AdventurerPlayerFrameArtOverlay', lua)
        self.assertIn('frameArtTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)', lua)
        self.assertIn('frameArtOverlay:EnableMouse(false)', lua)
        self.assertIn('PlayerFrameTexture:SetAlpha(0)', lua)
        self.assertIn('bar:SetFrameStrata("BACKGROUND")', lua)
        self.assertIn('frameArtOverlay:SetFrameStrata("HIGH")', lua)
        self.assertIn('frameArtOverlay:Show()', lua)
        self.assertIn('frameArtOverlay:Hide()', lua)
        self.assertIn('PlayerFrameTexture:SetAlpha(1)', lua)

    def test_player_level_is_mirrored_above_frame_art(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('AdventurerPlayerLevelText', lua)
        self.assertIn('frameArtOverlay:CreateFontString(', lua)
        self.assertIn('adventurerLevelText:SetPoint("CENTER", PlayerFrame, "CENTER", -63, -16)', lua)
        self.assertIn('adventurerLevelText:SetText(UnitLevel("player") or "")', lua)
        self.assertIn('PlayerLevelText:Hide()', lua)
        self.assertIn('PlayerLevelText:Show()', lua)

    def test_auxiliary_resources_read_only_rage_and_energy_native_pools(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('UnitPower("player", bar.powerId)', lua)
        self.assertIn('UnitPowerMax("player", bar.powerId)', lua)
        self.assertIn('AdventurerRageBar', lua)
        self.assertIn('AdventurerEnergyBar', lua)
        self.assertNotIn('AdventurerRunicPowerBar', lua)
        self.assertNotIn('POWER_RUNIC_POWER', lua)

    def test_resource_text_follows_repositioned_bars_and_custom_bars_show_on_hover(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('PlayerFrameHealthBarText:SetPoint("CENTER", PlayerFrameHealthBar, "CENTER", 0, 0)', lua)
        self.assertIn('PlayerFrameManaBarText:SetPoint("CENTER", PlayerFrameManaBar, "CENTER", 0, 0)', lua)
        self.assertIn('bar:EnableMouse(true)', lua)
        self.assertIn('bar.valueText:SetText(labels[bar.powerId] .. " " .. current .. " / " .. maximum)', lua)
        self.assertIn('[POWER_RAGE] = "Ira"', lua)
        self.assertIn('[POWER_ENERGY] = "Energía"', lua)
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

    def test_death_knight_client_resources_are_absent(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        for token in (
            'RuneFrame',
            'RUNE_POWER_UPDATE',
            'GetRuneCooldown',
            'RuneButton_Update',
            'POWER_RUNIC_POWER',
            'AdventurerRunicPowerBar',
        ):
            self.assertNotIn(token, lua)

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
