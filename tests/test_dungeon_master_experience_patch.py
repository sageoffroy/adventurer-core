from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dungeon_master_experience_patch as patcher  # noqa: E402


class DungeonMasterExperiencePatchTests(unittest.TestCase):
    def make_core(self, root: Path) -> tuple[Path, Path, str, str]:
        mgr = root / patcher.MGR
        gossip = root / patcher.GOSSIP
        mgr.parent.mkdir(parents=True, exist_ok=True)
        gossip.parent.mkdir(parents=True, exist_ok=True)

        mgr_text = (
            "void Teleport()\n{\n"
            "        if (p->TeleportTo(session->MapId, ent.GetPositionX(), ent.GetPositionY(),\n"
            "                          ent.GetPositionZ(), ent.GetOrientation()))\n"
            "        {\n"
            '            Send("Welcome to |cFFFFFFFF%s|r! Defeat the boss to claim your reward.");\n'
            "        }\n"
            "}\n"
        )
        gossip_text = (
            "void x()\n{\n"
            "    sSelections[player->GetGUID()].ThemeId = 1;\n"
            '    Add("Begin Challenge");\n'
            '    Add("Scale to Party Level");\n'
            '    Add("========== Challenge Summary ==========");\n'
            '    Add("Original inhabitants|r");\n'
            '    Add("The dungeon keeps its original inhabitants and mechanics");\n'
            "    // ---- Menu builders ----\n"
            "}\n"
        )
        mgr.write_text(mgr_text, encoding="utf-8")
        gossip.write_text(gossip_text, encoding="utf-8")
        return mgr, gossip, mgr_text, gossip_text

    def test_install_verify_idempotence_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            mgr, gossip, mgr_before, gossip_before = self.make_core(core)

            changed = patcher.install(core)
            self.assertEqual(changed, [str(patcher.MGR), str(patcher.GOSSIP)])
            patcher.verify(core)
            self.assertEqual(patcher.install(core), [])

            mgr_text = mgr.read_text(encoding="utf-8")
            gossip_text = gossip.read_text(encoding="utf-8")
            self.assertIn("TELE_TO_GM_MODE", mgr_text)
            self.assertIn("Comenzar desafío", gossip_text)
            self.assertIn("Escalar al nivel del grupo", gossip_text)
            self.assertIn("Resumen del desafío", gossip_text)
            self.assertIn("Habitantes originales", gossip_text)
            self.assertIn("compatibility marker: Original inhabitants|r", gossip_text)

            patcher.rollback(core)
            self.assertEqual(mgr.read_text(encoding="utf-8"), mgr_before)
            self.assertEqual(gossip.read_text(encoding="utf-8"), gossip_before)


if __name__ == "__main__":
    unittest.main()
