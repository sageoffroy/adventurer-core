from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dungeon_master_dungeon_names_patch as patcher  # noqa: E402


class DungeonMasterDungeonNamesPatchTests(unittest.TestCase):
    def make_core(self, root: Path) -> tuple[Path, str]:
        target = root / patcher.REL
        target.parent.mkdir(parents=True, exist_ok=True)
        original = (
            "void DMConfig::LoadDungeons()\n{\n"
            "    static const Def kDungeons[] =\n"
            "    {\n"
            '        { 36, "Deadmines", 15, 25 },\n'
            '        { 189, "Scarlet Monastery", 30, 45 },\n'
            '        { 574, "Utgarde Keep", 68, 80 },\n'
            '        { 668, "Halls of Reflection", 79, 80 },\n'
            "    };\n"
            "}\n"
        )
        target.write_text(original, encoding="utf-8")
        return target, original

    def test_install_verify_idempotence_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            target, original = self.make_core(core)
            subset = (
                ("Deadmines", "Minas de la Muerte"),
                ("Scarlet Monastery", "Monasterio Escarlata"),
                ("Utgarde Keep", "Fortaleza de Utgarde"),
                ("Halls of Reflection", "Cámaras de Reflexión"),
            )
            previous = patcher.NAMES
            try:
                patcher.NAMES = subset
                self.assertTrue(patcher.install(core))
                patcher.verify(core)
                self.assertFalse(patcher.install(core))
                text = target.read_text(encoding="utf-8")
                self.assertIn("Minas de la Muerte", text)
                self.assertIn("Cámaras de Reflexión", text)
                self.assertTrue(patcher.rollback(core))
                self.assertEqual(target.read_text(encoding="utf-8"), original)
            finally:
                patcher.NAMES = previous


if __name__ == "__main__":
    unittest.main()
