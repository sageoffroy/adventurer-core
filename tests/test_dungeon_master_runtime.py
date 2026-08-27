from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dungeon_master_runtime as dm  # noqa: E402


class DungeonMasterRuntimeTests(unittest.TestCase):
    def profile(self, root: Path) -> Path:
        path = root / "managed.conf"
        path.write_text(
            'DungeonMaster.Enable = 1\n'
            'DungeonMaster.Difficulty.1 = "Novice,1,19,0.6,0.6,1.0,0.5"\n',
            encoding="utf-8",
        )
        return path

    def make_core(self, root: Path) -> tuple[Path, str]:
        target = root / "env/dist/etc/modules/mod_dungeon_master.conf"
        target.parent.mkdir(parents=True, exist_ok=True)
        original = (
            'DungeonMaster.Enable = 1\n'
            'DungeonMaster.Difficulty.1 = "Novice,10,19,0.6,0.6,1.0,0.5"\n'
            'DungeonMaster.Cooldown.Minutes = 5\n'
        )
        target.write_text(original, encoding="utf-8")
        return target, original

    def test_level_one_profile_install_verify_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            core = root / "core"
            target, original = self.make_core(core)
            profile = self.profile(root)
            with patch.object(dm, "PROFILE", profile):
                changed = dm.install(core)
                self.assertEqual(changed, ["DungeonMaster.Difficulty.1"])
                dm.verify(core)
                self.assertIn('Novice,1,19', target.read_text(encoding="utf-8"))
                self.assertIn('DungeonMaster.Cooldown.Minutes = 5', target.read_text(encoding="utf-8"))
                self.assertEqual(dm.install(core), [])
                self.assertTrue(dm.rollback(core))
                self.assertEqual(target.read_text(encoding="utf-8"), original)

    def test_discovers_unique_nested_config(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            target = core / "env/dist/etc/custom/modules/mod_dungeon_master.conf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("DungeonMaster.Enable = 1\n", encoding="utf-8")
            self.assertEqual(dm.target_path(core), target.resolve())


if __name__ == "__main__":
    unittest.main()
