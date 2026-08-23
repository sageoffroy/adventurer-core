from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import diagnostic_zero_ui  # noqa: E402


class ZeroUIDiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = Path(diagnostic_zero_ui.__file__).read_text(encoding="utf-8")

    def test_diagnostic_does_not_use_production_install_patch(self) -> None:
        self.assertNotIn("install_patch,", self.source)
        self.assertIn("def install_zero_ui_patch(", self.source)

    def test_diagnostic_still_protects_unowned_z_slots(self) -> None:
        self.assertIn('old_owner.get("owner") != "adventurer-core"', self.source)
        self.assertIn("Refusing to overwrite unowned diagnostic Z slot", self.source)

    def test_bundle_remains_zero_interface(self) -> None:
        self.assertIn('name.lower().startswith("interface\\\\")', self.source)
        self.assertIn("Interface entries: 0", self.source)


if __name__ == "__main__":
    unittest.main()
