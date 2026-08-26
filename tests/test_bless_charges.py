from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"
CLIENT = ROOT / "client" / "AdventurerDraftMeta.lua"
CONFIG = ROOT / "config" / "spelldraft" / "spelldraft.conf"


class SpellDraftBlessChargeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.client = CLIENT.read_text(encoding="utf-8")
        cls.config = CONFIG.read_text(encoding="utf-8")

    def test_blessing_has_configurable_charge_pool(self) -> None:
        for token in (
            "[Bless]",
            "StartingCharges = 1",
            "GainEveryLevels = 10",
            "GainAmount = 1",
            "MaxCharges = 0",
            "WeightMultiplierPercent = 300",
        ):
            self.assertIn(token, self.config)

    def test_server_persists_and_consumes_bless_charges(self) -> None:
        for token in (
            "blessStartingCharges",
            "blessGainEveryLevels",
            "blessGainAmount",
            "blessMaxCharges",
            "blessCharges",
            "--state.blessCharges",
            'SendDraftError(player, "NO_BLESSES"',
            "AddCharge(state.blessCharges",
            "ADVENTURER_DRAFT_SCHEMA = 3",
        ):
            self.assertIn(token, self.runtime)

    def test_client_displays_finite_bless_charges(self) -> None:
        self.assertIn('blessings = "Bendiciones: %d"', self.client)
        self.assertIn("blesses = 0", self.client)
        self.assertIn("state.blesses > 0", self.client)
        self.assertNotIn('"∞"', self.client)


if __name__ == "__main__":
    unittest.main()
