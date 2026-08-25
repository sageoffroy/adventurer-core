from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import load_spec, talent_source_spell_ids  # noqa: E402


class TalentLayoutTests(unittest.TestCase):
    def test_guardian_layout_matches_approved_builder_shape(self) -> None:
        spec = load_spec()
        definitions = {definition["key"]: definition for definition in spec["talents"]}

        expected = {
            "vitality": (0, 1),
            "consistency": (0, 2),
            "overwhelming_strength": (0, 3),
            "shield_specialization": (1, 0),
            "cicatrization": (1, 1),
            "deflection": (1, 2),
            "painful_impacts": (2, 1),
            "riposte": (2, 2),
            "impassibility": (2, 3),
            "critical_block": (3, 0),
            "last_stand": (3, 1),
            "spell_deflection": (3, 2),
            "one_handed_weapon_specialization": (3, 3),
            "steady_footing": (4, 0),
            "survivor": (4, 1),
            "unfair_advantage": (4, 2),
            "armored_to_the_teeth": (5, 0),
            "acclimation": (5, 2),
            "sweeping_strikes": (5, 3),
            "prayer": (6, 0),
            "focused_rage": (6, 1),
            "nerves_of_steel": (6, 2),
            "bulwark": (7, 0),
            "indomitable": (7, 1),
            "concussion_blow": (7, 3),
            "damage_shield": (8, 0),
            "demolition_machine": (8, 1),
            "titans_grip": (8, 2),
            "blood_gorged": (9, 1),
            "vigilance": (9, 3),
            "throw_shield": (10, 0),
            "shockwave": (10, 2),
        }

        self.assertEqual(set(definitions), set(expected))
        for key, position in expected.items():
            definition = definitions[key]
            self.assertEqual((int(definition["row"]), int(definition["col"])), position, key)

    def test_guardian_is_32_talents_80_available_ranks_and_eleven_rows(self) -> None:
        spec = load_spec()
        definitions = spec["talents"]
        self.assertEqual(len(definitions), 32)
        self.assertEqual(
            sum(len(talent_source_spell_ids(definition)) for definition in definitions),
            80,
        )
        self.assertEqual(int(spec["point_total"]), 80)

        positions = [(int(d["row"]), int(d["col"])) for d in definitions]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertEqual(min(row for row, _col in positions), 0)
        self.assertEqual(max(row for row, _col in positions), 10)

    def test_first_six_rows_hold_the_level_sixty_build_core(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        first_six = {key for key, definition in definitions.items() if int(definition["row"]) <= 5}
        self.assertEqual(
            first_six,
            {
                "vitality",
                "consistency",
                "overwhelming_strength",
                "shield_specialization",
                "cicatrization",
                "deflection",
                "painful_impacts",
                "riposte",
                "impassibility",
                "critical_block",
                "last_stand",
                "spell_deflection",
                "one_handed_weapon_specialization",
                "steady_footing",
                "survivor",
                "unfair_advantage",
                "armored_to_the_teeth",
                "acclimation",
                "sweeping_strikes",
            },
        )
        self.assertEqual(
            sum(len(talent_source_spell_ids(definitions[key])) for key in first_six),
            53,
        )

    def test_approved_custom_icons_are_locked(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        expected = {
            "vitality": "spell_nature_abolishmagic",
            "overwhelming_strength": "inv_gauntlets_19",
            "cicatrization": "spell_shadow_lifedrain",
            "steady_footing": "ability_warstomp",
            "survivor": "spell_misc_emotionangry",
            "indomitable": "ability_warrior_intensifyrage",
            "throw_shield": "inv_jewelry_trinketpvp_02",
        }
        for key, icon in expected.items():
            self.assertEqual(definitions[key].get("icon"), icon, key)

        self.assertFalse(any(definition.get("provisional_drive_blank") for definition in definitions.values()))

    def test_guardian_prerequisites_match_approved_arrows(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        expected = {
            "riposte": "deflection",
            "critical_block": "shield_specialization",
            "sweeping_strikes": "one_handed_weapon_specialization",
            "damage_shield": "bulwark",
            "throw_shield": "damage_shield",
            "vigilance": "concussion_blow",
            "shockwave": "titans_grip",
        }
        actual = {
            key: definition.get("requires")
            for key, definition in definitions.items()
            if definition.get("requires")
        }
        self.assertEqual(actual, expected)

    def test_guardian_has_two_row_eleven_ultimates(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        row_eleven = {
            key
            for key, definition in definitions.items()
            if int(definition["row"]) == 10
        }
        self.assertEqual(row_eleven, {"throw_shield", "shockwave"})
        self.assertTrue(definitions["throw_shield"].get("add_to_spellbook"))
        self.assertTrue(definitions["shockwave"].get("add_to_spellbook"))

    def test_prerequisite_lanes_are_clear(self) -> None:
        spec = load_spec()
        definitions = {definition["key"]: definition for definition in spec["talents"]}

        for child in spec["talents"]:
            required_key = child.get("requires")
            if not required_key:
                continue

            parent = definitions[required_key]
            parent_row = int(parent["row"])
            parent_col = int(parent["col"])
            child_row = int(child["row"])
            child_col = int(child["col"])

            self.assertLessEqual(parent_row, child_row, f"{child['key']} prerequisite cannot be below it")
            if parent_row == child_row:
                self.assertNotEqual(parent_col, child_col, f"{child['key']} same-row prerequisite must be horizontal")

            if parent_col != child_col:
                continue

            blockers = [
                definition["key"]
                for definition in spec["talents"]
                if int(definition["col"]) == child_col
                and parent_row < int(definition["row"]) < child_row
            ]
            self.assertEqual(blockers, [], f"{child['key']} prerequisite lane blocked by {blockers}")


if __name__ == "__main__":
    unittest.main()
