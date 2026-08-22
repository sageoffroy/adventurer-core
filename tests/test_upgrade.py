from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from adventurer import sha256_file  # noqa: E402
from upgrade import verify_owned_source_state  # noqa: E402


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


if __name__ == "__main__":
    unittest.main()
