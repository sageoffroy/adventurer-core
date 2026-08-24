from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from talents import CHAMPION_SPEC_PATH, load_spec, talent_source_spell_ids  # noqa: E402


class ChampionLayoutTests(unittest.TestCase):
    def setUp(self) -> None:
        self.spec = load_spec(CHAMPION_SPEC_PATH)
        self.definitions = {definition["key"]: definition for definition in self.spec["talents"]}

    def test_champion_layout_matches_drive(self) -> None:
        expected = {
            "mental_quickness": (0, 0, 3),
            "trauma": (0, 1, 2),
            "dual_wield_specialization": (0, 2, 5),
            "weapon_strength": (1, 1, 2),
            "close_quarters_combat": (1, 2, 5),
            "vile_poisons": (1, 3, 3),
            "elemental_weapons": (2, 0, 3),
            "endless_rage": (2, 1, 1),
            "ruthlessness": (2, 2, 3),
            "master_of_deception": (2, 3, 2),
            "eye_for_an_eye": (3, 0, 2),
            "two_handed_weapon_specialization": (3, 1, 5),
            "serrated_blades": (3, 2, 3),
            "conviction": (4, 1, 5),
            "hack_and_slash": (4, 2, 5),
            "hemorrhage": (4, 3, 1),
            "blood_vengeance": (5, 1, 3),
            "weapon_expertise": (5, 3, 2),
            "ancestral_rage": (6, 0, 1),
            "overflowing_energy": (6, 2, 3),
            "cheat_death": (6, 3, 3),
            "mental_dexterity": (7, 0, 3),
            "find_weakness": (7, 2, 3),
            "blood_frenzy": (7, 3, 2),
            "heart_strike": (8, 1, 1),
            "turn_the_tables": (8, 2, 3),
            "blood_gorged": (9, 1, 5),
            "bladestorm": (10, 1, 1),
        }
        actual = {
            definition["key"]: (
                int(definition["row"]),
                int(definition["col"]),
                len(talent_source_spell_ids(definition)),
            )
            for definition in self.spec["talents"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 28)
        self.assertEqual(sum(ranks for _row, _col, ranks in actual.values()), 80)
        self.assertEqual(self.spec["point_total"], 80)

    def test_champion_has_separate_owned_id_ranges(self) -> None:
        self.assertEqual(self.spec["tab_key"], "champion")
        self.assertEqual(self.spec["talent_id_base"], 6000)
        self.assertEqual(self.spec["spell_id_base"], 300000)

    def test_champion_prerequisite_chain(self) -> None:
        expected = {
            "close_quarters_combat": "dual_wield_specialization",
            "hemorrhage": "serrated_blades",
            "blood_gorged": "heart_strike",
            "bladestorm": "blood_gorged",
        }
        actual = {
            key: definition.get("requires")
            for key, definition in self.definitions.items()
            if definition.get("requires")
        }
        self.assertEqual(actual, expected)

    def test_audited_customizations_are_explicit(self) -> None:
        hack = self.definitions["hack_and_slash"]
        self.assertEqual(hack["spell_source_ids"], [13960, 13961, 13962, 13963, 13964])

        elemental = self.definitions["elemental_weapons"]
        self.assertEqual(elemental["effect_values"]["0"], [10, 20, 30])
        self.assertEqual(elemental["effect_values"]["1"], [10, 20, 30])
        self.assertEqual(elemental["effect_values"]["2"], [13, 27, 40])

        weakness = self.definitions["find_weakness"]
        self.assertEqual(weakness["effect_values"]["0"], [2, 4, 6])
        self.assertEqual(weakness["effect_misc_values"]["0"], 127)

        heart = self.definitions["heart_strike"]
        self.assertEqual(heart["effect_values"], {"0": [100], "1": [75]})
        self.assertEqual(heart["spell_u32_values"]["41"], 1)
        self.assertEqual(heart["spell_u32_values"]["226"], 0)

        tables = self.definitions["turn_the_tables"]
        self.assertEqual(tables["trigger_effect_values"]["0"], [2, 4, 6])
        self.assertEqual(tables["trigger_spell_u32_values"]["95"], 52)

        energy = self.definitions["overflowing_energy"]
        self.assertEqual(energy["spell_source_ids"], [31122, 31123, 61329])
        self.assertFalse(energy.get("reuse_native_spells", False))


if __name__ == "__main__":
    unittest.main()
