from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from adventurer import sha256_bytes, sha256_file  # noqa: E402
from core_patch import PlannedFile  # noqa: E402
from upgrade import (  # noqa: E402
    UpgradeError,
    prepare_new_source_ownership,
    validate_new_owned_sources,
    verify_owned_source_state,
)


class UpgradeStateTests(unittest.TestCase):
    def test_generated_runtime_drift_is_not_part_of_source_verification(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            owned = core / "src" / "owned.cpp"
            owned.parent.mkdir(parents=True)
            owned.write_text("owned\n", encoding="utf-8")

            # Runtime hashes may be stale after a supported tools/client.py
            # refresh. The upgrade validates those artifacts through their own
            # ownership path later instead of treating them as source edits.
            state = {
                "files": [
                    {
                        "path": "src/owned.cpp",
                        "after_sha256": sha256_file(owned),
                    }
                ],
                "dbc": {
                    "directory": str(core / "dbc"),
                    "files": {"Spell.dbc": "stale-hash"},
                },
                "client": {
                    "directory": str(core / "client"),
                    "installed": {
                        "root_patch": "Data/patch-Z.mpq",
                        "root_sha256": "stale-hash",
                    },
                },
            }

            self.assertEqual(verify_owned_source_state(core, state), [])

    def test_source_drift_still_blocks_upgrade(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            owned = core / "src" / "owned.cpp"
            owned.parent.mkdir(parents=True)
            owned.write_text("original\n", encoding="utf-8")
            expected = sha256_file(owned)
            owned.write_text("manual edit\n", encoding="utf-8")

            problems = verify_owned_source_state(
                core,
                {
                    "files": [
                        {
                            "path": "src/owned.cpp",
                            "after_sha256": expected,
                        }
                    ]
                },
            )

            self.assertEqual(len(problems), 1)
            self.assertIn("modified: src/owned.cpp", problems[0])

    def make_git_core(self, root: Path) -> Path:
        subprocess.run(["git", "init", "-q", str(root)], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.email", "tests@example.invalid"], check=True)
        subprocess.run(["git", "-C", str(root), "config", "user.name", "Adventurer Tests"], check=True)
        source = root / "src" / "newly-owned.cpp"
        source.parent.mkdir(parents=True)
        source.write_text("stock\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "src/newly-owned.cpp"], check=True)
        subprocess.run(["git", "-C", str(root), "commit", "-qm", "baseline"], check=True)
        return source

    def test_pristine_tracked_file_can_be_adopted_by_new_package_revision(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            source = self.make_git_core(core)
            original = source.read_bytes()
            planned = [
                PlannedFile(
                    "src/newly-owned.cpp",
                    original,
                    b"patched\n",
                )
            ]
            state = {"files": []}

            adopted = validate_new_owned_sources(core, state, planned)
            self.assertEqual([item.relative_path for item in adopted], ["src/newly-owned.cpp"])

            created = prepare_new_source_ownership(core, state, planned)
            self.assertEqual(len(created), 1)
            self.assertEqual(created[0].read_bytes(), original)
            self.assertEqual(state["files"][0]["before_sha256"], sha256_bytes(original))
            self.assertEqual(state["files"][0]["after_sha256"], sha256_bytes(b"patched\n"))
            self.assertTrue(state["files"][0]["existed_before"])

    def test_locally_modified_new_source_file_is_never_adopted(self):
        with tempfile.TemporaryDirectory() as td:
            core = Path(td)
            source = self.make_git_core(core)
            source.write_text("manual edit\n", encoding="utf-8")
            planned = [
                PlannedFile(
                    "src/newly-owned.cpp",
                    source.read_bytes(),
                    b"patched\n",
                )
            ]

            with self.assertRaisesRegex(UpgradeError, "local changes"):
                validate_new_owned_sources(core, {"files": []}, planned)


if __name__ == "__main__":
    unittest.main()
