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
            "    const CreatureTemplate* tmpl = c->GetCreatureTemplate();\n"
            "    bool challengeBoss = false;\n"
            "    bool elite = false;\n"
            "    if (!challengeBoss)\n"
            "    {\n"
            "        bool hostile = true;\n"
            "        if (!hostile)\n"
            "            return false;\n"
            "    }\n\n"
            "    const uint8 targetLevel = session->EffectiveLevel;\n"
            "    c->SetLevel(targetLevel);\n"
            "    const uint8 unitClass = tmpl->unit_class;\n"
            "    const ClassLevelStatEntry* baseStats = GetBaseStatsForLevel(unitClass, targetLevel);\n\n"
            "    float hpMult = CalculateHealthMultiplier(session);\n"
            "    float extraHpMult = challengeBoss ? sDMConfig->GetBossHealthMult()\n"
            "        : (elite ? sDMConfig->GetEliteHealthMult() : 1.0f);\n"
            "    float finalHP = baseStats\n"
            "        ? static_cast<float>(baseStats->BaseHP) * hpMult * extraHpMult\n"
            "        : static_cast<float>(c->GetMaxHealth()) * hpMult * extraHpMult;\n"
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
            self.assertIn(fixup.CORPSE_POSE_FIX_MARKER, mgr_text)
            self.assertIn("const bool nativeDeadPose = c->getStandState() == UNIT_STAND_STATE_DEAD;", mgr_text)
            self.assertIn("c->SetStandState(UNIT_STAND_STATE_STAND);", mgr_text)
            self.assertNotIn("c->GetStandState()", mgr_text)
            self.assertNotIn(
                "if (c->getStandState() == UNIT_STAND_STATE_DEAD)\n        return false;",
                mgr_text,
            )
            self.assertIn(fixup.HEALTH_FIX_MARKER, mgr_text)
            self.assertIn("nativeHpRatio", mgr_text)
            self.assertIn("roleFloor", mgr_text)

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
            self.assertIn(fixup.CORPSE_POSE_FIX_MARKER, mgr_text)
            self.assertIn(fixup.HEALTH_FIX_MARKER, mgr_text)
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
            text = mgr.read_text(encoding="utf-8")
            self.assertIn(fixup.CORPSE_POSE_FIX_MARKER, text)
            self.assertIn(fixup.HEALTH_FIX_MARKER, text)

    def test_upgrades_bad_v4_getstandstate_accessor(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr, unit = self.make_core(core)
            mgr.write_text(
                mgr.read_text(encoding="utf-8")
                .replace(fixup.MGR_LEGACY, fixup.MGR_FIXED, 1)
                .replace(
                    fixup.CORPSE_ANCHOR,
                    fixup.CORPSE_ANCHOR + fixup.CORPSE_V4_BAD_BLOCK,
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
            self.assertIn(fixup.CORPSE_POSE_FIX_MARKER, text)
            self.assertIn(fixup.CORPSE_GOOD_ACCESSOR, text)
            self.assertIn("c->SetStandState(UNIT_STAND_STATE_STAND);", text)
            self.assertNotIn(fixup.CORPSE_BAD_ACCESSOR, text)
            self.assertIn(fixup.HEALTH_FIX_MARKER, text)
            self.assertFalse(fixup.install(core))

    def test_upgrades_v5_early_return_without_leaving_crawling_combatants(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr, unit = self.make_core(core)
            mgr.write_text(
                mgr.read_text(encoding="utf-8")
                .replace(fixup.MGR_LEGACY, fixup.MGR_FIXED, 1)
                .replace(
                    fixup.CORPSE_ANCHOR,
                    fixup.CORPSE_ANCHOR + fixup.CORPSE_V5_BLOCK,
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
            self.assertIn("const bool nativeDeadPose", text)
            self.assertIn("SetStandState(UNIT_STAND_STATE_STAND)", text)
            self.assertNotIn(
                "if (c->getStandState() == UNIT_STAND_STATE_DEAD)\n        return false;",
                text,
            )

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
