from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import load_spec  # noqa: E402


class TalentLayoutTests(unittest.TestCase):
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
            self.assertEqual(
                blockers,
                [],
                f"{child['key']} prerequisite line from {required_key} is blocked vertically by {blockers}",
            )

    def test_guardian_shield_lane_order(self) -> None:
        definitions = {definition["key"]: definition for definition in load_spec()["talents"]}

        expected = {
            "shield_discipline": (2, 3),
            "retaliating_shield": (6, 3),
            "bulwark": (7, 3),
            "perfect_block": (8, 3),
        }
        for key, position in expected.items():
            self.assertEqual((definitions[key]["row"], definitions[key]["col"]), position, key)

        self.assertEqual(definitions["retaliating_shield"]["requires"], "shield_discipline")


if __name__ == "__main__":
    unittest.main()
