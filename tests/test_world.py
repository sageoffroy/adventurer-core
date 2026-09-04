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
        generated = root / world.GAUNTLET_GENERATED_ITEMS_RELATIVE
        generated.parent.mkdir(parents=True)
        generated.write_text("-- generated Gauntlet items\n", encoding="utf-8")
        return root

    def test_installs_authoritative_world_updates_idempotently(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            removed, results = world.install(core)

            self.assertEqual(removed, [])
            self.assertEqual(len(results), 6)
            self.assertTrue(all(changed for _target, changed in results))

            installed = [core / update.relative for update in world.WORLD_UPDATES]
            self.assertTrue(all(path.is_file() for path in installed))
            self.assertIn(b"Generated Gauntlet item definitions", installed[0].read_bytes())
            self.assertEqual(world.WORLD_UPDATES[1].source.name, "001_adventurer.sql")
            self.assertEqual(world.WORLD_UPDATES[2].source.name, "002_adventurer_goldshire.sql")
            self.assertEqual(world.WORLD_UPDATES[3].source.name, "001_gauntlet_core.sql")
            self.assertEqual(world.WORLD_UPDATES[4].source.name, "002_gauntlet_world.sql")
            self.assertEqual(world.WORLD_UPDATES[5].source.name, "003_gauntlet_loot.sql")

            removed_again, results_again = world.install(core)
            self.assertEqual(removed_again, [])
            self.assertEqual(len(results_again), 6)
            self.assertTrue(all(not changed for _target, changed in results_again))

            self.assertEqual(world.verify(core), installed)

            removed = world.remove(core)
            self.assertEqual(len(removed), 6)
            self.assertTrue(all(changed for _target, changed in removed))
            self.assertTrue(all(not path.exists() for path in installed))

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

    def test_refreshes_owned_update_but_refuses_to_remove_different_pending_update(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            target = core / world.WORLD_UPDATES[0].relative
            target.write_text("different\n", encoding="utf-8")

            _removed, installed = world.install(core)
            self.assertTrue(installed[0][1])

            target.write_text("different again\n", encoding="utf-8")
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


if __name__ == "__main__":
    unittest.main()
