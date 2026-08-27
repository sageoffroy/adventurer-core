from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dungeon_master_source_fixup as fixup  # noqa: E402


class DungeonMasterSourceFixupTests(unittest.TestCase):
    def make_core(self, root: Path) -> Path:
        target = root / fixup.REL
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "void x()\n{\n"
            "                    // ---- Original dungeon grid activation / roguelike stray cleanup ----\n"
            "                    if (true)\n"
            "                    {\n"
            "                    }\n"
            "                // ---- Auto-rez when out of combat ----\n"
            "}\n",
            encoding="utf-8",
        )
        return target

    def test_repairs_v1_missing_brace_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            target = self.make_core(core)
            self.assertTrue(fixup.install(core))
            fixup.verify(core)
            self.assertFalse(fixup.install(core))
            text = target.read_text(encoding="utf-8")
            self.assertIn(fixup.FIX_MARKER, text)
            self.assertIn("                    }\n                }\n\n", text)
            self.assertNotIn(fixup.LEGACY, text)

    def test_refuses_unpatched_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            target = core / fixup.REL
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("int main() { return 0; }\n", encoding="utf-8")
            with self.assertRaises(fixup.FixupError):
                fixup.install(core)


if __name__ == "__main__":
    unittest.main()
