from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import load_spec, talent_source_spell_ids  # noqa: E402


class GuardianContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = load_spec()
        self.definitions = {definition["key"]: definition for definition in self.spec["talents"]}

    def test_guardian_stays_28_talents_and_80_points(self) -> None:
        self.assertEqual(len(self.definitions), 28)
        self.assertEqual(
            sum(len(talent_source_spell_ids(definition)) for definition in self.spec["talents"]),
            80,
        )
        self.assertEqual(self.spec["guardian_points"], 80)

    def test_guardian_custom_balance_values_are_preserved(self) -> None:
        self.assertEqual(self.definitions["deflection"]["effect_values"]["0"], [2, 4, 6])
        self.assertEqual(
            self.definitions["consistency"]["effect_values"],
            {"0": [2, 4, 6, 8, 10], "1": [-6, -12, -18, -24, -30]},
        )
        self.assertEqual(
            self.definitions["shield_specialization"]["effect_values"]["0"],
            [2, 4, 6, 8, 10],
        )
        self.assertEqual(self.definitions["shield_specialization"]["disable_effects"], [1])
        self.assertEqual(
            self.definitions["iron_will"]["effect_values"],
            {"0": [-7, -14, -20], "1": [-7, -14, -20]},
        )
        self.assertEqual(
            self.definitions["one_handed_weapon_specialization"]["effect_values"]["0"],
            [2, 4, 6, 8, 10],
        )

    def test_guardian_script_sensitive_native_reuse_is_preserved(self) -> None:
        expected = {
            "ardent_defender": [31850, 31851, 31852],
            "damage_shield": [58872, 58874],
            "focused_rage": [29787, 29790, 29792],
        }
        for key, spell_ids in expected.items():
            definition = self.definitions[key]
            self.assertTrue(definition["reuse_native_spells"], key)
            self.assertEqual(definition["spell_source_ids"], spell_ids, key)

    def test_guardian_active_tools_remain_spellbook_talents(self) -> None:
        expected = {"riposte", "last_stand", "sweeping_strikes", "mortal_strike", "throw_shield"}
        actual = {
            definition["key"]
            for definition in self.spec["talents"]
            if definition.get("add_to_spellbook")
        }
        self.assertEqual(actual, expected)

    def test_guardian_paso_firme_and_demolition_contracts_are_preserved(self) -> None:
        steady = self.definitions["steady_footing"]
        self.assertEqual(steady["icon"], "ability_warstomp")
        self.assertEqual(steady["effect_values"], {"0": [15, 30], "1": [2, 4], "2": [2, 4]})

        demolition = self.definitions["demolition_machine"]
        self.assertEqual(demolition["spell_u32_values"]["35"], [15, 30, 45, 60, 75])
        self.assertEqual(demolition["disable_effects"], [0])

    def test_guardian_prerequisites_are_unchanged(self) -> None:
        expected = {
            "cicatrization": "tenacity",
            "riposte": "deflection",
            "spell_deflection": "one_handed_weapon_specialization",
            "improved_mortal_strike": "mortal_strike",
            "mortal_strike": "sweeping_strikes",
            "throw_shield": "demolition_machine",
        }
        actual = {
            key: definition.get("requires")
            for key, definition in self.definitions.items()
            if definition.get("requires")
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
