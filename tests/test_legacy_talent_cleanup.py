from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import DBC, set_u32, u32  # noqa: E402
from talents import (  # noqa: E402
    LEGACY_SPELL_MIN,
    LEGACY_TAB_IDS,
    LEGACY_TALENT_MIN,
    patch_talent_directory,
)


def record(fields: int, record_id: int) -> bytearray:
    row = bytearray(fields * 4)
    set_u32(row, 0, record_id)
    return row


class LegacyTalentCleanupTests(unittest.TestCase):
    def make_fixture(self, root: Path) -> None:
        root.mkdir(parents=True, exist_ok=True)
        DBC(24, 96, [record(24, 161), record(24, min(LEGACY_TAB_IDS))], bytearray(b"\0")).write(
            root / "TalentTab.dbc"
        )
        DBC(23, 92, [record(23, 153), record(23, LEGACY_TALENT_MIN)], bytearray(b"\0")).write(
            root / "Talent.dbc"
        )
        DBC(234, 936, [record(234, 133), record(234, LEGACY_SPELL_MIN)], bytearray(b"\0")).write(
            root / "Spell.dbc"
        )

    def test_purges_only_legacy_fixed_tree_rows_and_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_fixture(root)

            first = patch_talent_directory(root)
            self.assertTrue(all(first.values()))

            self.assertEqual([u32(row, 0) for row in DBC.read(root / "TalentTab.dbc").records], [161])
            self.assertEqual([u32(row, 0) for row in DBC.read(root / "Talent.dbc").records], [153])
            self.assertEqual([u32(row, 0) for row in DBC.read(root / "Spell.dbc").records], [133])

            second = patch_talent_directory(root)
            self.assertFalse(any(second.values()))


if __name__ == "__main__":
    unittest.main()
