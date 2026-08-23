from __future__ import annotations

import inspect
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import diagnostic_zero_ui  # noqa: E402


class ZeroUIDiagnosticTests(unittest.TestCase):
    def test_diagnostic_packages_only_dbfilesclient_entries(self) -> None:
        source = inspect.getsource(diagnostic_zero_ui.build_zero_ui_bundle)

        self.assertIn('f"DBFilesClient\\\\{name}"', source)
        self.assertNotIn("build_frame_xml_toc", source)
        self.assertNotIn("build_adventurer_player_frame_xml", source)
        self.assertNotIn("build_adventurer_resources_lua", source)
        self.assertNotIn("build_adventurer_frame_art", source)
        self.assertNotIn("build_character_create_lua", source)
        self.assertNotIn("Interface\\\\FrameXML", source)
        self.assertNotIn("Interface\\\\GlueXML", source)
        self.assertNotIn("UI-AdventurerFrame", source)

    def test_diagnostic_does_not_modify_server_runtime(self) -> None:
        source = inspect.getsource(diagnostic_zero_ui.main)
        self.assertNotIn("install_server_dbcs", source)
        self.assertNotIn("core_dir", source)


if __name__ == "__main__":
    unittest.main()
