from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dungeon_master_source_fixup as fixup  # noqa: E402


class DungeonMasterSourceFixupTests(unittest.TestCase):
    def make_core(self, root: Path) -> tuple[Path, Path]:
        mgr = root / fixup.MGR_REL
        mgr.parent.mkdir(parents=True, exist_ok=True)
        mgr.write_text(
            "// Aventureros: preserve and scale the dungeon's original inhabitants.\n"
            "bool PrepareOriginalCreature(Creature* c, Session* session)\n"
            "{\n"
            "    if (!c || !session || !c->IsInWorld() || !c->IsAlive())\n"
            "        return false;\n"
            "    return true;\n"
            "}\n"
            "void x()\n{\n"
            "                    // ---- Original dungeon grid activation / roguelike stray cleanup ----\n"
            "                    if (true)\n"
            "                    {\n"
            "                    }\n"
            "                // ---- Auto-rez when out of combat ----\n"
            "}\n",
            encoding="utf-8",
        )

        unit = root / fixup.UNIT_REL
        unit.parent.mkdir(parents=True, exist_ok=True)
        unit.write_text(
            "class x\n{\n"
            "        if (attacker)\n"
            "        {\n"
            "            // Guardrail: no single hit can remove more than 35% max HP.\n"
            "            if (true)\n"
            "            {\n"
            "                return;\n"
            "            }\n"
            "        // Non-session attacker (environmental hazards, traps, etc.)\n"
            "};\n",
            encoding="utf-8",
        )
        return mgr, unit

    def test_repairs_all_native_mode_fixups_idempotently(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr, unit = self.make_core(core)
            self.assertTrue(fixup.install(core))
            fixup.verify(core)
            self.assertFalse(fixup.install(core))

            mgr_text = mgr.read_text(encoding="utf-8")
            self.assertIn(fixup.MGR_FIX_MARKER, mgr_text)
            self.assertIn("                    }\n                }\n\n", mgr_text)
            self.assertNotIn(fixup.MGR_LEGACY, mgr_text)
            self.assertIn(fixup.CORPSE_FIX_MARKER, mgr_text)
            self.assertIn(fixup.CORPSE_ACCESSOR_FIX_MARKER, mgr_text)
            self.assertIn("c->getStandState() == UNIT_STAND_STATE_DEAD", mgr_text)
            self.assertNotIn("c->GetStandState() == UNIT_STAND_STATE_DEAD", mgr_text)

            unit_text = unit.read_text(encoding="utf-8")
            self.assertIn(fixup.UNIT_FIX_MARKER, unit_text)
            self.assertIn("            }\n        }\n\n", unit_text)
            self.assertNotIn(fixup.UNIT_LEGACY, unit_text)

    def test_upgrades_tree_with_manager_brace_already_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr, unit = self.make_core(core)
            mgr.write_text(
                mgr.read_text(encoding="utf-8").replace(fixup.MGR_LEGACY, fixup.MGR_FIXED, 1),
                encoding="utf-8",
            )
            self.assertTrue(fixup.install(core))
            fixup.verify(core)
            mgr_text = mgr.read_text(encoding="utf-8")
            self.assertIn(fixup.CORPSE_FIX_MARKER, mgr_text)
            self.assertIn(fixup.UNIT_FIX_MARKER, unit.read_text(encoding="utf-8"))

    def test_upgrades_tree_with_both_braces_already_fixed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr, unit = self.make_core(core)
            mgr.write_text(
                mgr.read_text(encoding="utf-8").replace(fixup.MGR_LEGACY, fixup.MGR_FIXED, 1),
                encoding="utf-8",
            )
            unit.write_text(
                unit.read_text(encoding="utf-8").replace(fixup.UNIT_LEGACY, fixup.UNIT_FIXED, 1),
                encoding="utf-8",
            )
            self.assertTrue(fixup.install(core))
            fixup.verify(core)
            self.assertIn(fixup.CORPSE_FIX_MARKER, mgr.read_text(encoding="utf-8"))

    def test_upgrades_bad_v4_getstandstate_accessor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr, unit = self.make_core(core)
            mgr.write_text(
                mgr.read_text(encoding="utf-8")
                .replace(fixup.MGR_LEGACY, fixup.MGR_FIXED, 1)
                .replace(
                    fixup.CORPSE_ANCHOR,
                    "    if (!c || !session || !c->IsInWorld() || !c->IsAlive())\n"
                    "        return false;\n"
                    "    // Aventureros source fixup v4: ignore decorative dead-pose creatures.\n"
                    "    // Blizzard uses alive Creature objects with UNIT_STAND_STATE_DEAD for corpse props.\n"
                    "    if (c->GetStandState() == UNIT_STAND_STATE_DEAD)\n"
                    "        return false;\n",
                    1,
                ),
                encoding="utf-8",
            )
            unit.write_text(
                unit.read_text(encoding="utf-8").replace(fixup.UNIT_LEGACY, fixup.UNIT_FIXED, 1),
                encoding="utf-8",
            )

            self.assertTrue(fixup.install(core))
            fixup.verify(core)
            text = mgr.read_text(encoding="utf-8")
            self.assertIn(fixup.CORPSE_ACCESSOR_FIX_MARKER, text)
            self.assertIn(fixup.CORPSE_GOOD_ACCESSOR, text)
            self.assertNotIn(fixup.CORPSE_BAD_ACCESSOR, text)
            self.assertFalse(fixup.install(core))

    def test_refuses_unpatched_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr = core / fixup.MGR_REL
            unit = core / fixup.UNIT_REL
            mgr.parent.mkdir(parents=True, exist_ok=True)
            unit.parent.mkdir(parents=True, exist_ok=True)
            mgr.write_text("int main() { return 0; }\n", encoding="utf-8")
            unit.write_text("int main() { return 0; }\n", encoding="utf-8")
            with self.assertRaises(fixup.FixupError):
                fixup.install(core)


if __name__ == "__main__":
    unittest.main()
