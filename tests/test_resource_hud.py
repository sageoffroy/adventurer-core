from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from client import (  # noqa: E402
    ADVENTURER_COLLECTIONS_INTERNAL,
    ADVENTURER_DRAFT_META_INTERNAL,
    ADVENTURER_FRAME_INTERNAL,
    ADVENTURER_PLAYER_FRAME_INTERNAL,
    DBC_NAMES,
    build_adventurer_collections_lua,
    build_adventurer_draft_meta_lua,
    build_adventurer_frame_art,
    build_adventurer_player_frame_xml,
    build_adventurer_resources_lua,
    build_archive_files,
    build_frame_xml_toc,
)


class AdventurerResourceHudTests(unittest.TestCase):
    def test_frame_xml_loads_all_adventurer_client_layers_after_player_frame(self) -> None:
        toc = build_frame_xml_toc().decode("utf-8")
        expected = (
            "PlayerFrame.xml\n"
            "AdventurerPlayerFrame.xml\n"
            "AdventurerResources.lua\n"
            "AdventurerDraftMeta.lua\n"
            "AdventurerCollections.lua\n"
            "PartyFrame.xml"
        )
        self.assertIn(expected, toc)
        for name in (
            "AdventurerPlayerFrame.xml",
            "AdventurerResources.lua",
            "AdventurerDraftMeta.lua",
            "AdventurerCollections.lua",
        ):
            self.assertEqual(toc.count(name), 1)

    def test_xml_uses_reference_energy_and_rage_geometry(self) -> None:
        xml = build_adventurer_player_frame_xml().decode("utf-8")
        for token in (
            'name="PlayerFrameEnergyBar"',
            '<AbsDimension x="92" y="11"/>',
            '<AbsDimension x="117" y="-65"/>',
            'name="PlayerFrameRageBar"',
            'orientation="VERTICAL"',
            '<AbsDimension x="12" y="38"/>',
            '<AbsDimension x="3" y="-24"/>',
            'name="PlayerFrameEnergyBarText"',
            'name="PlayerFrameRageBarText"',
            'Interface\\TargetingFrame\\UI-StatusBar',
        ):
            self.assertIn(token, xml)

        for token in (
            "TotalAbsorbBarTemplate",
            "HealAbsorbBarTemplate",
            "SetAtlas",
            "PlayerPrimaryStat",
            "AdventurerPlayerFrameRootOffset",
        ):
            self.assertNotIn(token, xml)

    def test_player_frame_layout_still_matches_reference_contract(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        for marker in (
            'ADVENTURER_FRAME_TEXTURE = "Interface\\\\Adventurer\\\\UI-AdventurerFrame"',
            'ADVENTURER_FRAME_TEX_RIGHT = 0.07421875',
            'PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)',
            'ApplyReferencePlayerFrameLayout()',
            'hooksecurefunc("PlayerFrame_ToPlayerArt"',
            'FRAME_ART_X_SHIFT = 8',
            'RESOURCE_X_SHIFT = 0',
            'PORTRAIT_X_SHIFT = 0',
            'LEVEL_X_SHIFT = 0',
            'MANA_X_SHIFT = 0',
            'ENERGY_X_SHIFT = 0',
            'BACKGROUND_X_SHIFT = 0',
            'NAME_X_SHIFT = 0',
            'FLASH_X_SHIFT = 0',
            'STATUS_X_SHIFT = 0',
            'PLAYER_FRAME_WIDTH = 232',
            'PLAYER_FRAME_HEIGHT = 100',
            'PORTRAIT_LEFT = 42',
            'PORTRAIT_TOP = 12',
            'PORTRAIT_SIZE = 64',
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
        ):
            self.assertIn(marker, lua)

        self.assertNotIn('SetFramePoint(PlayerFrame, "TOPLEFT", UIParent', lua)
        self.assertNotIn('AdventurerPlayerFrameArtOverlay', lua)
        self.assertNotIn('frameArtOverlay', lua)

    def test_auxiliary_resources_are_native_rage_energy_and_combo_points(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        for token in (
            'PlayerFrameEnergyBar',
            'PlayerFrameRageBar',
            'UnitPower("player", powerId)',
            'UnitPowerMax("player", powerId)',
            'POWER_RAGE = 1',
            'POWER_ENERGY = 3',
            '[POWER_RAGE] = "Ira"',
            '[POWER_ENERGY] = "Energía"',
            'COMBO_PREFIX = "AdventurerCP"',
            'RegisterAddonMessagePrefix(COMBO_PREFIX)',
            'RegisterEvent("CHAT_MSG_ADDON")',
            'local nativeGetComboPoints = GetComboPoints',
            'GetComboPoints = function(unit, target)',
            'unit == "player" and target == "target"',
            'ComboFrame_Update()',
        ):
            self.assertIn(token, lua)

        for token in (
            'CreateResourceBar',
            'CreateFrame("StatusBar"',
            'AdventurerEnergyBar',
            'AdventurerRageBar',
            'POWER_RUNIC_POWER',
            'RuneFrame',
            'RUNE_POWER_UPDATE',
            'GetRuneCooldown',
            'RuneButton_Update',
            'AdventurerRunicPowerBar',
            'SpellDraft',
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

    def test_root_mpq_contains_hud_draft_and_talent_collection(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            work = Path(tmp_name)
            for index, name in enumerate(DBC_NAMES):
                (work / name).write_bytes(f"dbc-{index}-{name}".encode("utf-8"))

            root_files, locale_files = build_archive_files(work)
            for internal in (
                "Interface\\FrameXML\\FrameXML.toc",
                ADVENTURER_PLAYER_FRAME_INTERNAL,
                "Interface\\FrameXML\\AdventurerResources.lua",
                ADVENTURER_DRAFT_META_INTERNAL,
                ADVENTURER_COLLECTIONS_INTERNAL,
                ADVENTURER_FRAME_INTERNAL,
            ):
                self.assertIn(internal, root_files)

            self.assertEqual(
                root_files[ADVENTURER_PLAYER_FRAME_INTERNAL],
                build_adventurer_player_frame_xml(),
            )
            self.assertEqual(
                root_files[ADVENTURER_DRAFT_META_INTERNAL],
                build_adventurer_draft_meta_lua(),
            )
            self.assertEqual(
                root_files[ADVENTURER_COLLECTIONS_INTERNAL],
                build_adventurer_collections_lua(),
            )
            self.assertEqual(
                root_files[ADVENTURER_FRAME_INTERNAL],
                build_adventurer_frame_art(),
            )

            for internal in (
                ADVENTURER_PLAYER_FRAME_INTERNAL,
                ADVENTURER_DRAFT_META_INTERNAL,
                ADVENTURER_COLLECTIONS_INTERNAL,
                ADVENTURER_FRAME_INTERNAL,
            ):
                self.assertNotIn(internal, locale_files)


if __name__ == "__main__":
    unittest.main()
