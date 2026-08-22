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

    def test_installs_last_bastion_binding_as_pending_world_update(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            target, changed = world.install(core)

            self.assertTrue(changed)
            self.assertEqual(target, core / world.WORLD_UPDATE_RELATIVE)
            sql = target.read_text(encoding="utf-8")
            self.assertIn("290050", sql)
            self.assertIn("spell_warr_last_stand", sql)
            self.assertIn("spell_script_names", sql)

            same_target, changed_again = world.install(core)
            self.assertEqual(same_target, target)
            self.assertFalse(changed_again)
            self.assertEqual(world.verify(core), target)

            removed_target, removed = world.remove(core)
            self.assertEqual(removed_target, target)
            self.assertTrue(removed)
            self.assertFalse(target.exists())

    def test_refuses_to_overwrite_or_remove_different_pending_update(self):
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            target = core / world.WORLD_UPDATE_RELATIVE
            target.write_text("different\n", encoding="utf-8")

            with self.assertRaises(world.WorldUpdateError):
                world.install(core)
            with self.assertRaises(world.WorldUpdateError):
                world.remove(core)

    def test_official_clean_apply_installs_and_verify_checks_world_updates(self):
        apply_text = (ROOT / "apply.sh").read_text(encoding="utf-8")
        verify_text = (ROOT / "verify.sh").read_text(encoding="utf-8")

        self.assertIn('tools/world.py" install', apply_text)
        self.assertIn('tools/world.py" verify', verify_text)
        self.assertIn("fresh apply never depends on remembering that extra step", apply_text)


if __name__ == "__main__":
    unittest.main()
