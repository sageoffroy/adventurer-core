from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from client import (  # noqa: E402
    ADVENTURER_FRAME_INTERNAL,
    ADVENTURER_PLAYER_FRAME_INTERNAL,
    DBC_NAMES,
    build_adventurer_frame_art,
    build_adventurer_player_frame_xml,
    build_archive_files,
    build_frame_xml_toc,
)


class AdventurerResourceHudTests(unittest.TestCase):
    def test_frame_xml_loads_adventurer_layout_directly_after_player_frame(self) -> None:
        toc = build_frame_xml_toc().decode("utf-8")
        self.assertIn(
            "PlayerFrame.xml\nAdventurerPlayerFrame.xml\nAdventurerResources.lua\nPartyFrame.xml",
            toc,
        )
        self.assertEqual(toc.count("AdventurerPlayerFrame.xml"), 1)
        self.assertEqual(toc.count("AdventurerResources.lua"), 1)

    def test_xml_uses_reference_energy_and_rage_geometry(self) -> None:
        xml = build_adventurer_player_frame_xml().decode("utf-8")
        self.assertIn('name="PlayerFrameEnergyBar"', xml)
        self.assertIn('<AbsDimension x="92" y="11"/>', xml)
        self.assertIn('<AbsDimension x="117" y="-65"/>', xml)
        self.assertIn('name="PlayerFrameRageBar"', xml)
        self.assertIn('orientation="VERTICAL"', xml)
        self.assertIn('<AbsDimension x="12" y="38"/>', xml)
        self.assertIn('<AbsDimension x="3" y="-24"/>', xml)
        self.assertIn('name="PlayerFrameEnergyBarText"', xml)
        self.assertIn('name="PlayerFrameRageBarText"', xml)
        self.assertIn('Interface\\TargetingFrame\\UI-StatusBar', xml)

    def test_xml_remains_stock_wotlk_compatible(self) -> None:
        xml = build_adventurer_player_frame_xml().decode("utf-8")
        for token in (
            "TotalAbsorbBarTemplate",
            "HealAbsorbBarTemplate",
            "SetAtlas",
            "PlayerPrimaryStat",
        ):
            self.assertNotIn(token, xml)
        self.assertNotIn("AdventurerPlayerFrameRootOffset", xml)

    def test_lua_reuses_real_blizzard_player_frame_texture(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('ADVENTURER_FRAME_TEXTURE = "Interface\\\\Adventurer\\\\UI-AdventurerFrame"', lua)
        self.assertIn('ADVENTURER_FRAME_TEX_RIGHT = 0.07421875', lua)
        self.assertIn('PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)', lua)
        self.assertIn('ApplyReferencePlayerFrameLayout()', lua)
        self.assertIn('hooksecurefunc("PlayerFrame_ToPlayerArt"', lua)
        self.assertNotIn('SetFramePoint(PlayerFrame, "TOPLEFT", UIParent', lua)
        self.assertNotIn('AdventurerPlayerFrameArtOverlay', lua)
        self.assertNotIn('frameArtOverlay', lua)

    def test_native_player_frame_measurements_match_reference_layout(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        expected = (
            'RESOURCE_X_SHIFT = -6',
            'PORTRAIT_X_SHIFT = -6',
            'LEVEL_X_SHIFT = -6',
            'MANA_X_SHIFT = -8',
            'ENERGY_X_SHIFT = -8',
            'BACKGROUND_X_SHIFT = -8',
            'NAME_X_SHIFT = -2',
            'FLASH_X_SHIFT = -1',
            'PLAYER_FRAME_WIDTH = 232',
            'PLAYER_FRAME_HEIGHT = 100',
            'PORTRAIT_LEFT = 42',
            'PORTRAIT_TOP = 12',
            'PORTRAIT_SIZE = 64',
            'BACKGROUND_LEFT = 106',
            'BACKGROUND_TOP = 22',
            'BACKGROUND_WIDTH = 116',
            'BACKGROUND_HEIGHT = 41',
            'HEALTH_LEFT = 106',
            'HEALTH_TOP = 41',
            'HEALTH_WIDTH = 116',
            'HEALTH_HEIGHT = 12',
            'MANA_LEFT = 106',
            'MANA_TOP = 52',
            'MANA_WIDTH = 116',
            'MANA_HEIGHT = 12',
            'ENERGY_LEFT = 117',
            'ENERGY_TOP = 65',
            'ENERGY_WIDTH = 92',
            'ENERGY_HEIGHT = 11',
            'RAGE_RIGHT = 3',
            'RAGE_TOP = 24',
            'RAGE_WIDTH = 12',
            'RAGE_HEIGHT = 38',
            'FLASH_WIDTH = 238',
            'STATUS_WIDTH = 187',
        )
        for marker in expected:
            self.assertIn(marker, lua)

    def test_frame_elements_follow_custom_blp_alignment(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        expected = (
            'SetFramePoint(PlayerPortrait, "TOPLEFT", PlayerFrame, "TOPLEFT", PORTRAIT_LEFT + PORTRAIT_X_SHIFT, -PORTRAIT_TOP)',
            'SetFramePoint(PlayerFrameBackground, "TOPLEFT", PlayerFrame, "TOPLEFT", BACKGROUND_LEFT + BACKGROUND_X_SHIFT, -BACKGROUND_TOP)',
            'SetFramePoint(PlayerName, "CENTER", PlayerFrame, "CENTER", 50 + NAME_X_SHIFT, 19)',
            'SetFramePoint(PlayerFrameHealthBar, "TOPLEFT", PlayerFrame, "TOPLEFT", HEALTH_LEFT + RESOURCE_X_SHIFT, -HEALTH_TOP)',
            'SetFramePoint(PlayerFrameManaBar, "TOPLEFT", PlayerFrame, "TOPLEFT", MANA_LEFT + MANA_X_SHIFT, -MANA_TOP)',
            'SetFramePoint(PlayerFrameEnergyBar, "TOPLEFT", PlayerFrame, "TOPLEFT", ENERGY_LEFT + ENERGY_X_SHIFT, -ENERGY_TOP)',
            'SetFramePoint(PlayerFrameRageBar, "TOPRIGHT", PlayerFrame, "TOPRIGHT", RAGE_RIGHT + RESOURCE_X_SHIFT, -RAGE_TOP)',
            'SetFramePoint(PlayerLevelText, "CENTER", PlayerFrame, "CENTER", -63 + LEVEL_X_SHIFT, -16)',
            'SetFramePoint(PlayerFrameFlash, "TOPLEFT", PlayerFrame, "TOPLEFT", FLASH_LEFT + FLASH_X_SHIFT, -FLASH_TOP)',
        )
        for marker in expected:
            self.assertIn(marker, lua)

    def test_auxiliary_bars_are_frame_xml_children_not_uiparent_statusbars(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('PlayerFrameEnergyBar', lua)
        self.assertIn('PlayerFrameRageBar', lua)
        self.assertNotIn('CreateResourceBar', lua)
        self.assertNotIn('CreateFrame("StatusBar"', lua)
        self.assertNotIn('AdventurerEnergyBar', lua)
        self.assertNotIn('AdventurerRageBar', lua)

    def test_auxiliary_resources_read_only_rage_and_energy_native_pools(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('UnitPower("player", powerId)', lua)
        self.assertIn('UnitPowerMax("player", powerId)', lua)
        self.assertIn('POWER_RAGE = 1', lua)
        self.assertIn('POWER_ENERGY = 3', lua)
        self.assertNotIn('POWER_RUNIC_POWER', lua)

    def test_resource_text_follows_shifted_bars_and_hover(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('SetFramePoint(PlayerFrameHealthBarText, "CENTER", PlayerFrame, "CENTER", 50 + RESOURCE_X_SHIFT, 3)', lua)
        self.assertIn('SetFramePoint(PlayerFrameManaBarText, "CENTER", PlayerFrame, "CENTER", 50 + MANA_X_SHIFT, -8)', lua)
        self.assertIn('SetFramePoint(PlayerFrameEnergyBarText, "CENTER", PlayerFrame, "CENTER", 50 + ENERGY_X_SHIFT, -22)', lua)
        self.assertIn('SetFramePoint(PlayerFrameRageBarText, "CENTER", PlayerFrame, "TOPRIGHT", -2 + RESOURCE_X_SHIFT, -42)', lua)
        self.assertIn('[POWER_RAGE] = "Ira"', lua)
        self.assertIn('[POWER_ENERGY] = "Energía"', lua)
        self.assertIn('bar:SetScript("OnEnter"', lua)
        self.assertIn('bar:SetScript("OnLeave"', lua)

    def test_combo_points_feed_blizzards_native_target_frame(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn('COMBO_PREFIX = "AdventurerCP"', lua)
        self.assertIn('RegisterAddonMessagePrefix(COMBO_PREFIX)', lua)
        self.assertIn('RegisterEvent("CHAT_MSG_ADDON")', lua)
        self.assertIn('local nativeGetComboPoints = GetComboPoints', lua)
        self.assertIn('GetComboPoints = function(unit, target)', lua)
        self.assertIn('unit == "player" and target == "target"', lua)
        self.assertIn('ComboFrame_Update()', lua)
        self.assertNotIn("SpellDraft", lua)

    def test_death_knight_client_resources_are_absent(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        xml = build_adventurer_player_frame_xml().decode("utf-8")
        for token in (
            'RuneFrame',
            'RUNE_POWER_UPDATE',
            'GetRuneCooldown',
            'RuneButton_Update',
            'POWER_RUNIC_POWER',
            'AdventurerRunicPowerBar',
        ):
            self.assertNotIn(token, lua)
            self.assertNotIn(token, xml)

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

    def test_root_mpq_contains_player_frame_xml_hud_and_frame_art(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            work = Path(tmp_name)
            for index, name in enumerate(DBC_NAMES):
                (work / name).write_bytes(f"dbc-{index}-{name}".encode("utf-8"))

            root_files, locale_files = build_archive_files(work)
            self.assertIn("Interface\\FrameXML\\FrameXML.toc", root_files)
            self.assertIn(ADVENTURER_PLAYER_FRAME_INTERNAL, root_files)
            self.assertIn("Interface\\FrameXML\\AdventurerResources.lua", root_files)
            self.assertIn(ADVENTURER_FRAME_INTERNAL, root_files)
            self.assertEqual(
                root_files[ADVENTURER_PLAYER_FRAME_INTERNAL],
                build_adventurer_player_frame_xml(),
            )
            self.assertEqual(root_files[ADVENTURER_FRAME_INTERNAL], build_adventurer_frame_art())
            self.assertNotIn(ADVENTURER_PLAYER_FRAME_INTERNAL, locale_files)
            self.assertNotIn(ADVENTURER_FRAME_INTERNAL, locale_files)


if __name__ == "__main__":
    unittest.main()
