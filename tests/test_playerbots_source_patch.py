from __future__ import annotations

import sys
import tempfile
import unittest
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import playerbots_source_patch  # noqa: E402


class PlayerbotsSourcePatchTests(unittest.TestCase):
    def make_core(self, root: Path) -> Path:
        grouped: OrderedDict[str, list[str]] = OrderedDict()
        for spec in playerbots_source_patch.PATCHES:
            grouped.setdefault(spec.relative_path, []).append(spec.clean)

        for relative_path, anchors in grouped.items():
            target = root / relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(
                "prefix\n" + "\nseparator\n".join(anchors) + "suffix\n",
                encoding="utf-8",
            )
        return root

    def test_install_excludes_adventurer_guards_talents_and_avoids_flush(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            changed = playerbots_source_patch.install(core)
            # Three exact patches currently touch two Playerbots source files.
            self.assertEqual(len(changed), 2)

            random_factory = (
                core
                / "modules/mod-playerbots/src/Bot/Factory/RandomPlayerbotFactory.cpp"
            ).read_text(encoding="utf-8")
            self.assertIn("if (cls == CLASS_ADVENTURER)", random_factory)
            self.assertIn("ten native WotLK classes", random_factory)
            self.assertNotIn('Execute("FLUSH TABLES")', random_factory)
            self.assertIn("RELOAD/FLUSH_TABLES", random_factory)

            talent_factory = (
                core / "modules/mod-playerbots/src/Bot/Factory/PlayerbotFactory.cpp"
            ).read_text(encoding="utf-8")
            self.assertIn("if (cls == CLASS_ADVENTURER)", talent_factory)
            self.assertIn("urand(1, 0)", talent_factory)
            playerbots_source_patch.verify(core)

            # Idempotent: a second install must not touch already-owned source.
            self.assertEqual(playerbots_source_patch.install(core), [])

    def test_rollback_restores_exact_clean_anchors(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            playerbots_source_patch.install(core)
            changed = playerbots_source_patch.rollback(core)
            self.assertEqual(len(changed), 2)
            for spec in playerbots_source_patch.PATCHES:
                text = (core / spec.relative_path).read_text(encoding="utf-8")
                self.assertEqual(text.count(spec.clean), 1)
                self.assertEqual(text.count(spec.patched), 0)

    def test_refuses_partial_or_unknown_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = self.make_core(Path(td) / "core")
            first = core / playerbots_source_patch.PATCHES[0].relative_path
            first.write_text("unexpected upstream source\n", encoding="utf-8")
            with self.assertRaises(playerbots_source_patch.PlayerbotsSourcePatchError):
                playerbots_source_patch.install(core)

    def test_shell_entry_points_manage_playerbots_source_patch(self) -> None:
        update = (ROOT / "update.sh").read_text(encoding="utf-8")
        apply = (ROOT / "apply.sh").read_text(encoding="utf-8")
        verify = (ROOT / "verify.sh").read_text(encoding="utf-8")
        rollback = (ROOT / "rollback.sh").read_text(encoding="utf-8")
        needle = 'tools/playerbots_source_patch.py"'
        self.assertIn(needle, update)
        self.assertIn(needle, apply)
        self.assertIn(needle, verify)
        self.assertIn(needle, rollback)


if __name__ == "__main__":
    unittest.main()
