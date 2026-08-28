from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import chassis_audit as audit  # noqa: E402


class ChassisAuditTests(unittest.TestCase):
    def make_row(
        self,
        player_class: int,
        *,
        level: int = 1,
        base_hp: int = 20,
        base_mana: int = 0,
        strength: int = 20,
        agility: int = 20,
        stamina: int = 20,
        intellect: int = 20,
        spirit: int = 20,
        melee_base: float = 0.05,
        melee_ratio: float = 0.001,
        spell_base: float = 0.02,
        spell_ratio: float = 0.001,
    ) -> audit.ChassisRow:
        return audit.ChassisRow(
            player_class=player_class,
            level=level,
            base_hp=base_hp,
            base_mana=base_mana,
            strength=strength,
            agility=agility,
            stamina=stamina,
            intellect=intellect,
            spirit=spirit,
            melee_crit_base=melee_base,
            melee_crit_ratio=melee_ratio,
            spell_crit_base=spell_base,
            spell_crit_ratio=spell_ratio,
            regen_hp=0.1,
            regen_hp_per_spirit=0.2,
            regen_mp_per_spirit=0.3,
        )

    def make_crit_row(
        self,
        player_class: int,
        *,
        level: int = 1,
        melee_base: float = 0.05,
        melee_ratio: float = 0.001,
        spell_base: float = 0.02,
        spell_ratio: float = 0.001,
    ) -> audit.CritCurveRow:
        return audit.CritCurveRow(
            player_class=player_class,
            level=level,
            melee_crit_base=melee_base,
            melee_crit_ratio=melee_ratio,
            spell_crit_base=spell_base,
            spell_crit_ratio=spell_ratio,
        )

    def test_level_parser_is_ordered_unique_and_bounded(self):
        self.assertEqual(audit.parse_levels("1,10,1,80"), (1, 10, 80))
        with self.assertRaises(audit.AuditError):
            audit.parse_levels("0")
        with self.assertRaises(audit.AuditError):
            audit.parse_levels("81")
        with self.assertRaises(audit.AuditError):
            audit.parse_levels("banana")

    def test_wotlk_health_and_mana_thresholds(self):
        self.assertEqual(audit.health_bonus_from_stamina(20), 20)
        self.assertEqual(audit.health_bonus_from_stamina(21), 30)
        self.assertEqual(audit.mana_bonus_from_intellect(21, 100), 35)
        self.assertEqual(audit.mana_bonus_from_intellect(21, 0), 0)

    def test_crit_formula_matches_core_percent_conversion(self):
        self.assertAlmostEqual(audit.crit_percent(0.05, 0.001, 20), 7.0)

    def test_adventurer_runtime_crit_uses_best_complete_native_formula_then_80_percent(self):
        natives = []
        for player_class in audit.NATIVE_CLASSES:
            natives.append(
                self.make_crit_row(
                    player_class,
                    melee_base=0.03 + player_class * 0.001,
                    melee_ratio=0.0005,
                    spell_base=0.01,
                    spell_ratio=0.0004 + player_class * 0.00001,
                )
            )

        # Make two deliberately different winners so the test would catch a
        # future return to "best base + best ratio" component mixing.
        warrior = next(row for row in natives if row.player_class == 1)
        rogue = next(row for row in natives if row.player_class == 4)
        natives[natives.index(warrior)] = self.make_crit_row(
            1, melee_base=0.08, melee_ratio=0.0001, spell_base=0.01, spell_ratio=0.0001
        )
        natives[natives.index(rogue)] = self.make_crit_row(
            4, melee_base=0.01, melee_ratio=0.0030, spell_base=0.02, spell_ratio=0.0020
        )
        adventurer = self.make_row(
            10,
            agility=21,
            intellect=21,
            melee_base=0.20,
            melee_ratio=0.01,
            spell_base=0.20,
            spell_ratio=0.01,
        )

        melee, spell = audit.adventurer_runtime_crits(adventurer, natives)
        native_melee = max(
            audit.crit_percent(row.melee_crit_base, row.melee_crit_ratio, adventurer.agility)
            for row in natives
        )
        native_spell = max(
            audit.crit_percent(row.spell_crit_base, row.spell_crit_ratio, adventurer.intellect)
            for row in natives
        )
        self.assertAlmostEqual(melee, native_melee * 0.80)
        self.assertAlmostEqual(spell, native_spell * 0.80)

        mixed_melee = (
            max(row.melee_crit_base for row in natives)
            + adventurer.agility * max(row.melee_crit_ratio for row in natives)
        ) * 100.0 * 0.80
        self.assertLess(melee, mixed_melee)

    def test_level_one_runtime_does_not_require_death_knight_player_stats(self):
        # DK legitimately has no player_class_stats row below 55. The core still
        # evaluates its level-indexed DBC crit slot, so the audit must do the same.
        level_one_stats = [
            self.make_row(player_class)
            for player_class in audit.ALL_CLASSES
            if player_class != 6
        ]
        crit_rows = [
            self.make_crit_row(player_class, melee_base=0.01 * player_class)
            for player_class in audit.NATIVE_CLASSES
        ]
        adventurer = next(row for row in level_one_stats if row.player_class == audit.ADVENTURER_CLASS)

        melee, _spell = audit.adventurer_runtime_crits(adventurer, crit_rows)
        expected = max(
            audit.crit_percent(row.melee_crit_base, row.melee_crit_ratio, adventurer.agility)
            for row in crit_rows
        ) * audit.ADVENTURER_SCALE
        self.assertAlmostEqual(melee, expected)

    def test_query_joins_class_level_dbc_slots(self):
        sql = audit.build_query((1, 10, 80))
        self.assertIn("`player_class_stats`", sql)
        self.assertIn("`gtchancetomeleecritbase_dbc`", sql)
        self.assertIn("`gtchancetomeleecrit_dbc`", sql)
        self.assertIn("`gtchancetospellcritbase_dbc`", sql)
        self.assertIn("`gtchancetospellcrit_dbc`", sql)
        self.assertIn("`gtoctregenhp_dbc`", sql)
        self.assertIn("`gtregenhpperspt_dbc`", sql)
        self.assertIn("`gtregenmpperspt_dbc`", sql)
        self.assertIn("pcs.`Level` IN (1,10,80)", sql)
        self.assertIn("(pcs.`Class` - 1) * 100 + pcs.`Level` - 1", sql)

    def test_native_crit_query_cross_joins_all_native_classes_and_requested_levels(self):
        sql = audit.build_native_crit_query((1, 60))
        self.assertIn("SELECT 6", sql)
        self.assertIn("SELECT 11", sql)
        self.assertIn("SELECT 60", sql)
        self.assertNotIn("player_class_stats", sql)
        self.assertIn("CROSS JOIN", sql)
        self.assertIn("(classes.`player_class` - 1) * 100 + levels.`level` - 1", sql)


if __name__ == "__main__":
    unittest.main()