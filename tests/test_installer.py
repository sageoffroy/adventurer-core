from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import adventurer  # noqa: E402
from core_patch import PlannedFile  # noqa: E402


class InstallerSafetyTests(unittest.TestCase):
    def git(self, root: Path, *args: str):
        return subprocess.run(["git", "-C", str(root), *args], check=True, text=True,
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    def make_repo(self, root: Path):
        self.git(root, "init")
        self.git(root, "config", "user.email", "test@example.invalid")
        self.git(root, "config", "user.name", "Test")
        required = [
            "src/server/shared/SharedDefines.h",
            "src/server/game/Entities/Player/Player.cpp",
            "src/server/scripts/Custom/custom_script_loader.cpp",
        ]
        for rel in required:
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("baseline\n", encoding="utf-8")
        self.git(root, "add", ".")
        self.git(root, "commit", "-m", "baseline")

    def test_validate_accepts_linked_worktree_gitfile(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td) / "repo"
            work = Path(td) / "work"
            parent.mkdir()
            self.make_repo(parent)
            self.git(parent, "worktree", "add", "-b", "test-worktree", str(work))
            commit = adventurer.validate_core_root(work.resolve())
            self.assertEqual(commit, self.git(work, "rev-parse", "HEAD").stdout.strip())
            adventurer.exclude_state_dir(work.resolve())
            git_path = self.git(work, "rev-parse", "--git-path", "info/exclude").stdout.strip()
            exclude = Path(git_path)
            if not exclude.is_absolute():
                exclude = work / exclude
            self.assertIn("/.adventurer-core/", exclude.read_text(encoding="utf-8"))

    def test_transaction_verifies_and_rolls_back_only_owned_files(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td).resolve()
            self.make_repo(core)
            commit = adventurer.validate_core_root(core)
            owned = core / "owned.txt"
            owned.write_text("before\n", encoding="utf-8")
            created = core / "created.txt"
            planned = [
                PlannedFile("owned.txt", b"before\n", b"after\n"),
                PlannedFile("created.txt", None, b"new\n"),
            ]
            state = adventurer.write_transaction(core, planned, commit)
            self.assertEqual(adventurer.verify_state(core, state), [])
            unrelated = core / "unrelated.txt"
            unrelated.write_text("keep\n", encoding="utf-8")

            args = argparse.Namespace(core_dir=core)
            adventurer.cmd_rollback(args)
            self.assertEqual(owned.read_text(), "before\n")
            self.assertFalse(created.exists())
            self.assertEqual(unrelated.read_text(), "keep\n")
            self.assertFalse((core / adventurer.SQL_TARGET).exists())


if __name__ == "__main__":
    unittest.main()
