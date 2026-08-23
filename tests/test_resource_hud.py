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
    build_adventurer_resources_lua,
    build_archive_files,
    build_frame_xml_toc,
)


class AdventurerResourceHudTests(unittest.TestCase):
    def test_frame_xml_loads_diagnostic_files_after_player_frame(self) -> None:
        toc = build_frame_xml_toc().decode("utf-8")
        self.assertIn(
            "PlayerFrame.xml\nAdventurerPlayerFrame.xml\nAdventurerResources.lua\nPartyFrame.xml",
            toc,
        )

    def test_adventurer_xml_declares_no_runtime_widgets(self) -> None:
        xml = build_adventurer_player_frame_xml().decode("utf-8")
        self.assertIn("DIAGNOSTIC MODE", xml)
        runtime_xml = xml.split("<!--", 1)[0] + xml.rsplit("-->", 1)[-1]
        self.assertNotIn("<Frame ", runtime_xml)
        self.assertNotIn("<StatusBar ", runtime_xml)
        self.assertNotIn("<FontString ", runtime_xml)

    def test_lua_runtime_only_applies_custom_frame_art(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        self.assertIn("Adventurer Core diagnostic PlayerFrame mode", lua)
        runtime = lua.split("--[[", 1)[0]

        self.assertIn("ADVENTURER_CLASS_ID = 10", runtime)
        self.assertIn('ADVENTURER_FRAME_TEXTURE = "Interface\\\\Adventurer\\\\UI-AdventurerFrame"', runtime)
        self.assertIn("FRAME_ART_X_SHIFT = 8", runtime)
        self.assertIn("ApplyAdventurerFrameArt", runtime)
        self.assertIn("PlayerFrameTexture:SetTexture(ADVENTURER_FRAME_TEXTURE)", runtime)
        self.assertIn('hooksecurefunc("PlayerFrame_ToPlayerArt"', runtime)

        for forbidden in (
            "PlayerFrameHealthBar",
            "PlayerFrameManaBar",
            "PlayerFrameEnergyBar",
            "PlayerFrameRageBar",
            "GetComboPoints =",
            "UnitPower(",
            "SetMinMaxValues",
            "SetValue(",
            "ConfigureAuxiliaryMouse",
            "ApplyReferencePlayerFrameLayout",
        ):
            self.assertNotIn(forbidden, runtime)

    def test_custom_art_keeps_latest_eight_pixel_offset(self) -> None:
        lua = build_adventurer_resources_lua().decode("utf-8")
        runtime = lua.split("--[[", 1)[0]
        self.assertIn(
            'PlayerFrameTexture:SetPoint("TOPLEFT", PlayerFrame, "TOPLEFT", FRAME_ART_X_SHIFT, 0)',
            runtime,
        )
        self.assertIn(
            'PlayerFrameTexture:SetPoint("BOTTOMRIGHT", PlayerFrame, "BOTTOMRIGHT", FRAME_ART_X_SHIFT, 0)',
            runtime,
        )

    def test_adventurer_frame_art_is_valid_bundled_blp2(self) -> None:
        art = build_adventurer_frame_art()
        self.assertTrue(art.startswith(b"BLP2"))
        self.assertEqual(int.from_bytes(art[12:16], "little"), 256)
        self.assertEqual(int.from_bytes(art[16:20], "little"), 128)

    def test_root_mpq_keeps_only_inert_hud_files_plus_frame_art(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            work = Path(tmp_name)
            for index, name in enumerate(DBC_NAMES):
                (work / name).write_bytes(f"dbc-{index}-{name}".encode("utf-8"))

            root_files, locale_files = build_archive_files(work)
            self.assertIn("Interface\\FrameXML\\FrameXML.toc", root_files)
            self.assertIn(ADVENTURER_PLAYER_FRAME_INTERNAL, root_files)
            self.assertIn("Interface\\FrameXML\\AdventurerResources.lua", root_files)
            self.assertIn(ADVENTURER_FRAME_INTERNAL, root_files)

            xml = root_files[ADVENTURER_PLAYER_FRAME_INTERNAL].decode("utf-8")
            runtime_xml = xml.split("<!--", 1)[0] + xml.rsplit("-->", 1)[-1]
            self.assertNotIn("<StatusBar ", runtime_xml)

            lua = root_files["Interface\\FrameXML\\AdventurerResources.lua"].decode("utf-8")
            runtime_lua = lua.split("--[[", 1)[0]
            self.assertNotIn("PlayerFrameManaBar", runtime_lua)
            self.assertNotIn("PlayerFrameRageBar", runtime_lua)
            self.assertNotIn("PlayerFrameEnergyBar", runtime_lua)

            self.assertNotIn(ADVENTURER_PLAYER_FRAME_INTERNAL, locale_files)
            self.assertNotIn(ADVENTURER_FRAME_INTERNAL, locale_files)


if __name__ == "__main__":
    unittest.main()
