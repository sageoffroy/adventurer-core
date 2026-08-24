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
            "indomitable": (5, 0),
            "acclimation": (5, 1),
            "sweeping_strikes": (5, 3),
            "nerves_of_steel": (6, 0),
            "prayer": (6, 1),
            "focused_rage": (6, 3),
            "bulwark": (7, 0),
            "damage_shield": (8, 0),
            "demolition_machine": (9, 2),
            "throw_shield": (10, 0),
        }

        self.assertEqual(set(definitions), set(expected))
        for key, position in expected.items():
            definition = definitions[key]
            self.assertEqual((int(definition["row"]), int(definition["col"])), position, key)

    def test_guardian_is_26_talents_73_available_ranks_and_eleven_rows(self) -> None:
        spec = load_spec()
        definitions = spec["talents"]
        self.assertEqual(len(definitions), 26)
        self.assertEqual(
            sum(len(talent_source_spell_ids(definition)) for definition in definitions),
            73,
        )
        self.assertEqual(int(spec["point_total"]), 73)

        positions = [(int(d["row"]), int(d["col"])) for d in definitions]
        self.assertEqual(len(positions), len(set(positions)))
        self.assertEqual(min(row for row, _col in positions), 0)
        self.assertEqual(max(row for row, _col in positions), 10)

    def test_first_six_rows_hold_the_build_complete_core(self) -> None:
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
                "indomitable",
                "acclimation",
                "sweeping_strikes",
            },
        )
        self.assertEqual(
            sum(len(talent_source_spell_ids(definitions[key])) for key in first_six),
            57,
        )

    def test_paso_firme_uses_stock_spell_icon(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        self.assertEqual(definitions["steady_footing"]["esMX"], "Paso firme")
        self.assertEqual(definitions["steady_footing"]["icon"], "ability_warstomp")
        self.assertEqual(len(talent_source_spell_ids(definitions["steady_footing"])), 2)
        self.assertFalse(any(definition.get("provisional_drive_blank") for definition in definitions.values()))

    def test_guardian_prerequisites_match_approved_arrows(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}
        expected = {
            "riposte": "deflection",
            "critical_block": "shield_specialization",
            "sweeping_strikes": "one_handed_weapon_specialization",
            "damage_shield": "bulwark",
            "throw_shield": "damage_shield",
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
