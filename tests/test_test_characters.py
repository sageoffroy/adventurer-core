from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import test_characters as probes  # noqa: E402


class TestCharacterProbeTests(unittest.TestCase):
    def test_default_probe_set_covers_all_level_one_native_classes_except_death_knight(self):
        selected = probes.select_probes(None)
        self.assertEqual(
            [probe.player_class for probe in selected],
            [1, 2, 3, 4, 5, 7, 8, 9, 11],
        )
        self.assertNotIn(6, [probe.player_class for probe in selected])
        self.assertEqual(len({probe.name for probe in selected}), len(selected))
        self.assertTrue(all(len(probe.name) <= 12 for probe in selected))

    def test_subset_selection_preserves_requested_order_and_rejects_unknowns(self):
        selected = probes.select_probes("mage,warrior,druid")
        self.assertEqual([probe.key for probe in selected], ["mage", "warrior", "druid"])
        with self.assertRaises(probes.ProbeError):
            probes.select_probes("mage,banana")
        with self.assertRaises(probes.ProbeError):
            probes.select_probes("mage,mage")

    def test_character_insert_reuses_location_but_resets_contaminating_state(self):
        columns = [
            "guid",
            "account",
            "name",
            "race",
            "class",
            "gender",
            "level",
            "xp",
            "money",
            "position_x",
            "position_y",
            "position_z",
            "map",
            "zone",
            "taximask",
            "online",
            "cinematic",
            "health",
            "power1",
            "equipmentCache",
            "exploredZones",
            "talentGroupsCount",
            "activeTalentGroup",
            "creation_date",
            "deleteInfos_Account",
            "deleteInfos_Name",
            "deleteDate",
            "innTriggerId",
        ]
        probe = probes.PROBE_BY_KEY["mage"]
        sql = probes.build_character_insert(columns, probe, 101, 7)

        self.assertIn("SELECT 101, `account`, 'Statmag', 1, 8, 0, 1", sql)
        self.assertIn("`position_x`, `position_y`, `position_z`, `map`, `zone`, `taximask`", sql)
        self.assertIn("0, 1, 1, 0, '', '', 1, 0, CURRENT_TIMESTAMP, NULL, NULL, NULL, `innTriggerId`", sql)
        self.assertIn("WHERE `guid` = 7", sql)

    def test_transaction_adds_only_homebind_and_defense_skill_beside_character_row(self):
        columns = ["guid", "account", "name", "race", "class", "gender", "level", "health", "innTriggerId"]
        selected = probes.select_probes("warrior,rogue")
        sql = probes.build_probe_transaction(columns, selected, 100, 5)

        self.assertTrue(sql.startswith("START TRANSACTION;"))
        self.assertTrue(sql.rstrip().endswith("COMMIT;"))
        self.assertEqual(sql.count("INSERT INTO `characters`"), 2)
        self.assertEqual(sql.count("INSERT INTO `character_homebind`"), 2)
        self.assertEqual(sql.count("INSERT INTO `character_skills`"), 2)
        self.assertEqual(sql.count("VALUES (100, 95, 5, 5)"), 1)
        self.assertEqual(sql.count("VALUES (101, 95, 5, 5)"), 1)
        self.assertNotIn("character_spell", sql)
        self.assertNotIn("character_talent", sql)
        self.assertNotIn("character_inventory", sql)

    def test_worldserver_process_detection_uses_proc_comm(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "123").mkdir()
            (root / "123" / "comm").write_text("worldserver\n", encoding="utf-8")
            (root / "abc").mkdir()
            self.assertTrue(probes.worldserver_running(root))

        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "456").mkdir()
            (root / "456" / "comm").write_text("authserver\n", encoding="utf-8")
            self.assertFalse(probes.worldserver_running(root))


if __name__ == "__main__":
    unittest.main()
