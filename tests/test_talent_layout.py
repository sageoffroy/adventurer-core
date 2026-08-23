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
            "steady_hand": (0, 2),
            "cicatrization": (1, 0),
            "threatening_presence": (1, 1),
            "deflection": (1, 2),
            "nerves_of_steel": (2, 0),
            "consistency": (2, 1),
            "riposte": (2, 2),
            "shield_specialization": (2, 3),
            "last_stand": (3, 0),
            "one_handed_weapon_specialization": (3, 2),
            "steady_footing": (4, 1),
            "critical_block": (4, 3),
            "bulwark": (5, 1),
            "spell_deflection": (5, 2),
            "ardent_defender": (6, 0),
            "shield_mastery": (6, 3),
            "unbreakable_will": (7, 0),
            "sweeping_strikes": (7, 2),
            "vitality": (8, 0),
            "improved_mortal_strike": (8, 1),
            "damage_shield": (8, 3),
            "acclimation": (9, 1),
            "mortal_strike": (9, 2),
            "throw_shield": (10, 3),
        }

        self.assertEqual(set(definitions), set(expected))
        for key, position in expected.items():
            definition = definitions[key]
            self.assertEqual((int(definition["row"]), int(definition["col"])), position, key)

    def test_guardian_is_exactly_25_talents_and_71_points(self) -> None:
        spec = load_spec()
        definitions = spec["talents"]
        self.assertEqual(len(definitions), 25)
        self.assertEqual(
            sum(len(talent_source_spell_ids(definition)) for definition in definitions),
            71,
        )
        self.assertEqual(int(spec["guardian_points"]), 71)

        positions = [(int(d["row"]), int(d["col"])) for d in definitions]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertEqual(min(row for row, _col in positions), 0)
        self.assertEqual(max(row for row, _col in positions), 10)

    def test_paso_firme_replaces_the_previous_blank_slot(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        self.assertNotIn("combat_instinct", definitions)
        self.assertIn("steady_footing", definitions)
        self.assertEqual(definitions["steady_footing"]["esMX"], "Paso firme")
        self.assertEqual(definitions["steady_footing"]["icon"], "inv_boots_plate_04")
        self.assertEqual(len(talent_source_spell_ids(definitions["steady_footing"])), 2)
        self.assertFalse(any(definition.get("provisional_drive_blank") for definition in definitions.values()))

    def test_guardian_prerequisites_match_reference_arrows(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        expected = {
            "cicatrization": "tenacity",
            "riposte": "deflection",
            "critical_block": "shield_specialization",
            "spell_deflection": "one_handed_weapon_specialization",
            "mortal_strike": "sweeping_strikes",
            "throw_shield": "damage_shield",
        }
        actual = {
            key: definition.get("requires")
            for key, definition in definitions.items()
            if definition.get("requires")
        }
        self.assertEqual(actual, expected)

    def test_vertical_prerequisite_lanes_are_clear(self) -> None:
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

            self.assertLess(parent_row, child_row, f"{child['key']} prerequisite must be above it")
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
