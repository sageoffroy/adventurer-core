from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import load_spec, talent_source_spell_ids  # noqa: E402


class TalentLayoutTests(unittest.TestCase):
    def test_guardian_layout_matches_drive(self) -> None:
        spec = load_spec()
        definitions = {definition["key"]: definition for definition in spec["talents"]}

        expected = {
            "tenacity": (0, 0),
            "shield_specialization": (0, 1),
            "steady_footing": (0, 2),
            "cicatrization": (1, 0),
            "iron_will": (1, 1),
            "deflection": (1, 2),
            "threatening_presence": (2, 0),
            "riposte": (2, 2),
            "steady_hand": (2, 3),
            "nerves_of_steel": (3, 1),
            "ardent_defender": (3, 2),
            "last_stand": (4, 0),
            "consistency": (4, 1),
            "one_handed_weapon_specialization": (4, 2),
            "unbreakable_will": (4, 3),
            "shield_mastery": (5, 1),
            "spell_deflection": (5, 2),
            "vitality": (5, 3),
            "focused_rage": (6, 0),
            "prayer": (6, 1),
            "acclimation": (6, 2),
            "sweeping_strikes": (6, 3),
            "bulwark": (7, 1),
            "damage_shield": (8, 1),
            "improved_mortal_strike": (8, 2),
            "mortal_strike": (8, 3),
            "demolition_machine": (9, 1),
            "throw_shield": (10, 1),
        }

        self.assertEqual(set(definitions), set(expected))
        for key, position in expected.items():
            definition = definitions[key]
            self.assertEqual((int(definition["row"]), int(definition["col"])), position, key)

    def test_guardian_is_exactly_28_talents_and_80_points(self) -> None:
        spec = load_spec()
        definitions = spec["talents"]
        self.assertEqual(len(definitions), 28)
        self.assertEqual(
            sum(len(talent_source_spell_ids(definition)) for definition in definitions),
            80,
        )
        self.assertEqual(int(spec["guardian_points"]), 80)

        positions = [(int(d["row"]), int(d["col"])) for d in definitions]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertEqual(min(row for row, _col in positions), 0)
        self.assertEqual(max(row for row, _col in positions), 10)

    def test_paso_firme_uses_stock_spell_icon(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        self.assertIn("steady_footing", definitions)
        self.assertEqual(definitions["steady_footing"]["esMX"], "Paso firme")
        self.assertEqual(definitions["steady_footing"]["icon"], "ability_warstomp")
        self.assertEqual(len(talent_source_spell_ids(definitions["steady_footing"])), 2)
        self.assertFalse(any(definition.get("provisional_drive_blank") for definition in definitions.values()))

    def test_guardian_prerequisites_match_reference_arrows(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
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
            for key, definition in definitions.items()
            if definition.get("requires")
        }
        self.assertEqual(actual, expected)

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
