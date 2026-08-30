from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import playerbots_runtime  # noqa: E402


class PlayerbotsRuntimeTests(unittest.TestCase):
    def make_core(self, root: Path, text: str, relative: Path | None = None) -> tuple[Path, Path]:
        target = root / (relative or playerbots_runtime.TARGET_RELATIVE)
        target.parent.mkdir(parents=True)
        target.write_text(text, encoding="utf-8")
        return root, target

    def test_versioned_profile_is_small_world_population_and_safe(self) -> None:
        profile = playerbots_runtime.read_profile()
        self.assertEqual(profile["AiPlayerbot.Enabled"], "1")
        self.assertEqual(profile["AiPlayerbot.RandomBotAutologin"], "1")
        self.assertEqual(profile["AiPlayerbot.MinRandomBots"], "20")
        self.assertEqual(profile["AiPlayerbot.MaxRandomBots"], "30")
        self.assertEqual(profile["AiPlayerbot.DisabledWithoutRealPlayer"], "1")
        # Current Playerbots level-sync path underflows at real-player level 1
        # (playersLevel - 3 => 4294967294) and can lead to invalid urand ranges.
        self.assertEqual(profile["AiPlayerbot.SyncLevelWithPlayers"], "0")
        self.assertEqual(profile["AiPlayerbot.AddClassAccountPoolSize"], "5")
        self.assertEqual(profile["AiPlayerbot.IterationsPerTick"], "5")
        self.assertEqual(profile["AiPlayerbot.DeleteRandomBotAccounts"], "0")

    def test_prefers_standard_azerothcore_module_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core, target = self.make_core(Path(td) / "core", "AiPlayerbot.Enabled = 1\n")
            self.assertEqual(playerbots_runtime.target_path(core), target)

    def test_supports_legacy_direct_etc_config_path(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            relative = Path("env/dist/etc/playerbots.conf")
            core, target = self.make_core(Path(td) / "core", "AiPlayerbot.Enabled = 1\n", relative)
            self.assertEqual(playerbots_runtime.target_path(core), target)

    def test_discovers_one_custom_playerbots_config_below_etc(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            relative = Path("env/dist/etc/custom/modules/playerbots.conf")
            core, target = self.make_core(Path(td) / "core", "AiPlayerbot.Enabled = 1\n", relative)
            self.assertEqual(playerbots_runtime.target_path(core), target)

    def test_refuses_ambiguous_custom_playerbots_configs(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            self.make_core(core, "AiPlayerbot.Enabled = 1\n", Path("env/dist/etc/a/playerbots.conf"))
            self.make_core(core, "AiPlayerbot.Enabled = 1\n", Path("env/dist/etc/b/playerbots.conf"))
            with self.assertRaises(playerbots_runtime.PlayerbotsConfigError):
                playerbots_runtime.target_path(core)

    def test_install_overrides_only_managed_keys_and_is_idempotent(self) -> None:
        original = """# test playerbots config
AiPlayerbot.Enabled = 1
AiPlayerbot.RandomBotAutologin = 1
AiPlayerbot.MinRandomBots = 0
AiPlayerbot.MaxRandomBots = 0
AiPlayerbot.SomeUnmanagedOption = 777
"""
        with tempfile.TemporaryDirectory() as td:
            core, target = self.make_core(Path(td) / "core", original)
            changed = playerbots_runtime.install(core)
            self.assertIn("AiPlayerbot.MinRandomBots", changed)
            self.assertIn("AiPlayerbot.MaxRandomBots", changed)

            text = target.read_text(encoding="utf-8")
            self.assertIn("AiPlayerbot.MinRandomBots = 20", text)
            self.assertIn("AiPlayerbot.MaxRandomBots = 30", text)
            self.assertIn("AiPlayerbot.SomeUnmanagedOption = 777", text)
            self.assertIn("AiPlayerbot.DeleteRandomBotAccounts = 0", text)

            backup = playerbots_runtime.backup_path(target)
            self.assertEqual(backup.read_text(encoding="utf-8"), original)

            changed_again = playerbots_runtime.install(core)
            self.assertEqual(changed_again, [])
            self.assertEqual(backup.read_text(encoding="utf-8"), original)
            playerbots_runtime.verify(core)

    def test_duplicate_active_managed_assignment_is_rejected(self) -> None:
        profile = {"AiPlayerbot.MaxRandomBots": "30"}
        text = "AiPlayerbot.MaxRandomBots = 0\nAiPlayerbot.MaxRandomBots = 500\n"
        with self.assertRaises(playerbots_runtime.PlayerbotsConfigError):
            playerbots_runtime.patch_text(text, profile)

    def test_rollback_restores_exact_pre_management_config(self) -> None:
        original = "AiPlayerbot.MaxRandomBots = 0\nAiPlayerbot.Custom = keep-me\n"
        with tempfile.TemporaryDirectory() as td:
            core, target = self.make_core(Path(td) / "core", original)
            playerbots_runtime.install(core)
            self.assertNotEqual(target.read_text(encoding="utf-8"), original)
            self.assertTrue(playerbots_runtime.rollback(core))
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertFalse(playerbots_runtime.backup_path(target).exists())

    def test_shell_entry_points_manage_playerbots_profile(self) -> None:
        update = (ROOT / "update.sh").read_text(encoding="utf-8")
        apply = (ROOT / "apply.sh").read_text(encoding="utf-8")
        verify = (ROOT / "verify.sh").read_text(encoding="utf-8")
        rollback = (ROOT / "rollback.sh").read_text(encoding="utf-8")
        self.assertIn('tools/playerbots_runtime.py" install', update)
        self.assertIn('tools/playerbots_runtime.py" install', apply)
        self.assertIn('tools/playerbots_runtime.py" verify', verify)
        self.assertIn('tools/playerbots_runtime.py" rollback', rollback)


if __name__ == "__main__":
    unittest.main()
