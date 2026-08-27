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
            'DungeonMaster.Cooldown.Minutes = 0\n'
            'DungeonMaster.Difficulty.1 = "Novato,1,19,0.6,0.6,1.0,0.5"\n'
            'DungeonMaster.Difficulty.2 = "Aprendiz,20,29,0.8,0.8,1.5,0.7"\n'
            'DungeonMaster.Theme.1 = "Cacería de bestias,1"\n',
            encoding="utf-8",
        )
        return path

    def make_core(self, root: Path) -> tuple[Path, str]:
        target = root / "env/dist/etc/modules/mod_dungeon_master.conf"
        target.parent.mkdir(parents=True, exist_ok=True)
        original = (
            'DungeonMaster.Enable = 1\n'
            'DungeonMaster.Difficulty.1 = "Novice,10,19,0.6,0.6,1.0,0.5"\n'
            'DungeonMaster.Difficulty.2 = "Apprentice,20,29,0.8,0.8,1.5,0.7"\n'
            'DungeonMaster.Theme.1 = "Beast Hunt,1"\n'
            'DungeonMaster.Cooldown.Minutes = 5\n'
        )
        target.write_text(original, encoding="utf-8")
        return target, original

    def test_level_one_localized_no_cooldown_profile_install_verify_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            core = root / "core"
            target, original = self.make_core(core)
            profile = self.profile(root)
            with patch.object(dm, "PROFILE", profile):
                changed = dm.install(core)
                self.assertEqual(
                    changed,
                    [
                        "DungeonMaster.Cooldown.Minutes",
                        "DungeonMaster.Difficulty.1",
                        "DungeonMaster.Difficulty.2",
                        "DungeonMaster.Theme.1",
                    ],
                )
                dm.verify(core)
                text = target.read_text(encoding="utf-8")
                self.assertIn('DungeonMaster.Cooldown.Minutes = 0', text)
                self.assertIn('DungeonMaster.Difficulty.1 = "Novato,1,19', text)
                self.assertIn('DungeonMaster.Difficulty.2 = "Aprendiz,20,29', text)
                self.assertIn('DungeonMaster.Theme.1 = "Cacería de bestias,1"', text)
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
