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

    def test_installs_all_adventurer_world_updates_idempotently(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            results = world.install(core)

            self.assertEqual(len(results), 4)
            self.assertTrue(all(changed for _target, changed in results))

            bastion = core / world.WORLD_UPDATES[0].relative
            chassis = core / world.WORLD_UPDATES[1].relative
            guardian = core / world.WORLD_UPDATES[2].relative
            survivor = core / world.WORLD_UPDATES[3].relative
            self.assertTrue(bastion.is_file())
            self.assertTrue(chassis.is_file())
            self.assertTrue(guardian.is_file())
            self.assertTrue(survivor.is_file())

            bastion_sql = bastion.read_text(encoding="utf-8")
            self.assertIn("290050", bastion_sql)
            self.assertIn("spell_warr_last_stand", bastion_sql)
            self.assertIn("spell_script_names", bastion_sql)

            chassis_sql = chassis.read_text(encoding="utf-8")
            self.assertIn("@ADVENTURER_SCALE := 0.95", chassis_sql)
            self.assertIn("MAX(`BaseHP`)", chassis_sql)
            self.assertIn("MAX(`BaseMana`)", chassis_sql)
            self.assertIn("gtoctclasscombatratingscalar_dbc", chassis_sql)
            self.assertIn("gtregenmpperspt_dbc", chassis_sql)

            guardian_sql = guardian.read_text(encoding="utf-8")
            self.assertIn("290240", guardian_sql)
            self.assertIn("spell_bonus_data", guardian_sql)
            self.assertIn("0.24", guardian_sql)
            self.assertIn("290050", guardian_sql)
            self.assertIn("spell_warr_last_stand", guardian_sql)
            self.assertNotIn("290150", guardian_sql)
            self.assertNotIn("spell_pal_ardent_defender", guardian_sql)

            survivor_sql = survivor.read_text(encoding="utf-8")
            for spell_id in (290150, 290151, 290152):
                self.assertIn(str(spell_id), survivor_sql)
            self.assertIn("spell_pal_ardent_defender", survivor_sql)

            results_again = world.install(core)
            self.assertEqual(len(results_again), 4)
            self.assertTrue(all(not changed for _target, changed in results_again))

            verified = world.verify(core)
            self.assertEqual(verified, [bastion, chassis, guardian, survivor])

            removed = world.remove(core)
            self.assertEqual(len(removed), 4)
            self.assertTrue(all(was_removed for _target, was_removed in removed))
            self.assertFalse(bastion.exists())
            self.assertFalse(chassis.exists())
            self.assertFalse(guardian.exists())
            self.assertFalse(survivor.exists())

    def test_existing_previous_guardian_update_is_accepted_and_only_new_migration_is_staged(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")

            for update in world.WORLD_UPDATES[:3]:
                target = core / update.relative
                target.write_bytes(world.source_payload(update))

            results = world.install(core)
            self.assertEqual([changed for _target, changed in results], [False, False, False, True])
            self.assertEqual(results[3][0], core / world.WORLD_UPDATES[3].relative)

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
