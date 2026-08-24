from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import custom_spell_id, load_spec, talent_source_spell_ids  # noqa: E402


class GuardianContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = load_spec()
        self.definitions = {definition["key"]: definition for definition in self.spec["talents"]}

    def test_guardian_uses_build_depth_design_instead_of_eighty_point_padding(self) -> None:
        self.assertEqual(len(self.definitions), 26)
        self.assertEqual(
            sum(len(talent_source_spell_ids(definition)) for definition in self.spec["talents"]),
            73,
        )
        self.assertEqual(self.spec["point_total"], 73)
        self.assertNotIn("guardian_points", self.spec)

    def test_guardian_first_rows_are_generic_foundations(self) -> None:
        vitality = self.definitions["vitality"]
        self.assertEqual(vitality["effect_values"]["1"], [2, 4, 6, 8, 10])
        self.assertEqual(vitality["disable_effects"], [0])

        strength = self.definitions["overwhelming_strength"]
        self.assertEqual(strength["effect_values"]["0"], [3, 6, 9, 12, 15])

        cicatrization = self.definitions["cicatrization"]
        self.assertEqual(cicatrization["effect_values"]["1"], [3, 6])
        self.assertEqual(cicatrization["disable_effects"], [0])

        self.assertEqual(self.definitions["deflection"]["effect_values"]["0"], [2, 4, 6])
        self.assertEqual(self.definitions["impassibility"]["effect_values"]["0"], [-2, -4])

    def test_consistency_is_runtime_marker_not_a_generic_armor_aura(self) -> None:
        definition = self.definitions["consistency"]
        self.assertEqual(definition["effect_values"]["0"], [1, 2, 3, 4, 5])
        self.assertEqual(definition["disable_effects"], [1])
        self.assertEqual(definition["spell_u32_values"]["95"], 4)  # SPELL_AURA_DUMMY
        self.assertIn("tela y cuero", definition["description_esMX"])
        self.assertIn("malla", definition["description_esMX"])
        self.assertIn("placas", definition["description_esMX"])

        index = next(i for i, item in enumerate(self.spec["talents"]) if item["key"] == "consistency")
        self.assertEqual(index, 6)
        self.assertEqual(custom_spell_id(self.spec, index, 0), 290060)
        self.assertEqual(custom_spell_id(self.spec, index, 4), 290064)

    def test_painful_impacts_is_physical_threat_and_uses_backstab_icon(self) -> None:
        definition = self.definitions["painful_impacts"]
        self.assertEqual(definition["effect_values"]["0"], [5, 10, 15])
        self.assertEqual(definition["effect_misc_values"]["0"], 1)
        self.assertEqual(definition["icon"], "ability_backstab")
        self.assertEqual(definition["esMX"], "Impactos dolorosos")

    def test_native_proc_sensitive_talents_keep_native_rank_spells(self) -> None:
        expected = {
            "shield_specialization": [12298, 12724, 12725, 12726, 12727],
            "survivor": [31850, 31851, 31852],
            "unfair_advantage": [51672, 51674],
            "acclimation": [49200, 50151, 50152],
            "bulwark": [20127, 20130, 20135],
            "damage_shield": [58872, 58874],
            "focused_rage": [29787, 29790, 29792],
            "nerves_of_steel": [31130, 31131],
        }
        for key, spell_ids in expected.items():
            definition = self.definitions[key]
            self.assertTrue(definition["reuse_native_spells"], key)
            self.assertEqual(definition["spell_source_ids"], spell_ids, key)

    def test_customized_native_talents_remove_class_specific_baggage(self) -> None:
        critical = self.definitions["critical_block"]
        self.assertEqual(critical["spell_source_ids"], [47294, 47295, 47296])
        self.assertEqual(critical["disable_effects"], [1])  # no Shield Slam crit rider

        indomitable = self.definitions["indomitable"]
        self.assertEqual(indomitable["spell_source_ids"], [33853, 33855, 33856])
        self.assertEqual(indomitable["disable_effects"], [2])  # no Bear-only armor rider

    def test_guardian_active_tools_are_only_the_selected_classless_actives(self) -> None:
        expected = {"riposte", "last_stand", "sweeping_strikes", "throw_shield"}
        actual = {
            definition["key"]
            for definition in self.spec["talents"]
            if definition.get("add_to_spellbook")
        }
        self.assertEqual(actual, expected)

    def test_paso_firme_demolition_and_throw_shield_contracts_are_preserved(self) -> None:
        steady = self.definitions["steady_footing"]
        self.assertEqual(steady["icon"], "ability_warstomp")
        self.assertEqual(steady["effect_values"], {"0": [15, 30], "1": [2, 4], "2": [2, 4]})

        demolition = self.definitions["demolition_machine"]
        self.assertEqual(demolition["spell_u32_values"]["35"], [25, 50, 75])
        self.assertEqual(demolition["disable_effects"], [0])

        throw_index = next(i for i, item in enumerate(self.spec["talents"]) if item["key"] == "throw_shield")
        self.assertEqual(throw_index, 24)
        self.assertEqual(custom_spell_id(self.spec, throw_index, 0), 290240)

    def test_guardian_prerequisites_are_short_and_mechanical(self) -> None:
        expected = {
            "riposte": "deflection",
            "critical_block": "shield_specialization",
            "sweeping_strikes": "one_handed_weapon_specialization",
            "damage_shield": "bulwark",
            "throw_shield": "damage_shield",
        }
        actual = {
            key: definition.get("requires")
            for key, definition in self.definitions.items()
            if definition.get("requires")
        }
        self.assertEqual(actual, expected)


if __name__ == "__main__":
    unittest.main()
