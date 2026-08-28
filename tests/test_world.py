from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import world  # noqa: E402


class WorldUpdateTests(unittest.TestCase):
    def make_core(self, root: Path) -> Path:
        (root / "data" / "sql" / "updates" / "pending_db_world").mkdir(parents=True)
        (root / "src" / "server" / "game").mkdir(parents=True)
        return root

    def test_installs_chassis_history_and_80_percent_rebalance_idempotently(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            results = world.install(core)

            self.assertEqual(len(results), 2)
            self.assertTrue(all(changed for _target, changed in results))

            original = core / world.WORLD_UPDATES[0].relative
            rebalance = core / world.WORLD_UPDATES[1].relative
            self.assertTrue(original.is_file())
            self.assertTrue(rebalance.is_file())
            self.assertEqual(world.WORLD_UPDATES[0].source.name, "003_adventurer_chassis.sql")
            self.assertEqual(world.WORLD_UPDATES[1].source.name, "005_adventurer_chassis_80.sql")
            self.assertNotIn("guardian", world.WORLD_UPDATES[0].source.name.lower())
            self.assertNotIn("guardian", world.WORLD_UPDATES[1].source.name.lower())

            original_sql = original.read_text(encoding="utf-8")
            rebalance_sql = rebalance.read_text(encoding="utf-8")
            self.assertIn("@ADVENTURER_SCALE := 0.95", original_sql)
            self.assertIn("@ADVENTURER_SCALE := 0.80", rebalance_sql)
            self.assertIn("MAX(`BaseHP`)", rebalance_sql)
            self.assertIn("MAX(`BaseMana`)", rebalance_sql)
            self.assertIn("gtoctclasscombatratingscalar_dbc", rebalance_sql)
            self.assertIn("gtregenmpperspt_dbc", rebalance_sql)

            results_again = world.install(core)
            self.assertEqual(len(results_again), 2)
            self.assertTrue(all(not changed for _target, changed in results_again))

            self.assertEqual(world.verify(core), [original, rebalance])

            removed = world.remove(core)
            self.assertEqual(len(removed), 2)
            self.assertTrue(all(changed for _target, changed in removed))
            self.assertFalse(original.exists())
            self.assertFalse(rebalance.exists())

    def test_fixed_talent_updates_are_cleanup_only(self):
        self.assertEqual(
            world.LEGACY_FIXED_TALENT_UPDATE_NAMES,
            (
                "rev_1787446800000000000.sql",
                "rev_1787779800000000000.sql",
            ),
        )
        self.assertEqual(world.LEGACY_FIXED_TALENT_SPELL_MIN, 290000)
        self.assertEqual(world.LEGACY_FIXED_TALENT_SPELL_MAX, 299999)

        active_sources = {update.source.name for update in world.WORLD_UPDATES}
        self.assertNotIn("002_guardian_last_bastion.sql", active_sources)
        self.assertNotIn("004_guardian_script_bindings.sql", active_sources)
        self.assertTrue(all("guardian" not in name.lower() for name in active_sources))

    def test_refuses_to_overwrite_or_remove_different_pending_update(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            target = core / world.WORLD_UPDATES[0].relative
            target.write_text("different\n", encoding="utf-8")

            with self.assertRaises(world.WorldUpdateError):
                world.install(core)
            with self.assertRaises(world.WorldUpdateError):
                world.remove(core)

    def test_official_clean_apply_and_update_flows_install_world_updates(self):
        apply_text = (ROOT / "apply.sh").read_text(encoding="utf-8")
        update_text = (ROOT / "update.sh").read_text(encoding="utf-8")
        verify_text = (ROOT / "verify.sh").read_text(encoding="utf-8")
        rollback_text = (ROOT / "rollback.sh").read_text(encoding="utf-8")

        self.assertIn('tools/world.py" install', apply_text)
        self.assertIn('tools/world.py" install', update_text)
        self.assertIn('tools/world.py" verify', verify_text)
        self.assertIn('tools/world.py" cleanup-db', rollback_text)
        self.assertIn('tools/world.py" remove', rollback_text)
        self.assertIn("fresh apply never depends on remembering that extra step", apply_text)


if __name__ == "__main__":
    unittest.main()