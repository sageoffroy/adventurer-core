from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import has_forbidden_class_reference  # noqa: E402


class TalentTextGuardTests(unittest.TestCase):
    def test_damage_does_not_false_match_mage(self) -> None:
        text = (
            "A strike that becomes active after parrying an opponent's attack. "
            "This attack deals 150% weapon damage and slows their melee attack speed."
        )
        self.assertFalse(has_forbidden_class_reference(text))

    def test_real_class_names_are_still_rejected(self) -> None:
        self.assertTrue(has_forbidden_class_reference("Increases Mage spell damage by 5%."))
        self.assertTrue(has_forbidden_class_reference("Aumenta el daño del guerrero un 5%."))
        self.assertTrue(has_forbidden_class_reference("Only usable by a Death Knight."))


if __name__ == "__main__":
    unittest.main()
