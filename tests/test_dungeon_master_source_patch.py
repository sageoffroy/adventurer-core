from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import dungeon_master_source_patch as dm  # noqa: E402


class DungeonMasterSourcePatchTests(unittest.TestCase):
    def make_core(self, root: Path) -> dict[str, str]:
        originals = {
            dm.FILES[0]: "x\n    void PopulateDungeon(Session* session, InstanceMap* map);\ny\n",
            dm.FILES[1]: """x
// Populate dungeon with themed creatures and bosses
    const DifficultyTier* diff  = sDMConfig->GetDifficulty(session->DifficultyId);
    const Theme*          theme = sDMConfig->GetTheme(session->ThemeId);
    if (!diff || !theme) return;
float DungeonMasterMgr::GetSessionCreatureDamageScale(
    ObjectGuid playerGuid, ObjectGuid creatureGuid)
{
    OLD
}
// Scale environmental damage to party level
                    // ---- Sweep for stray creatures (script-spawned, respawned) ----
                    OLD SWEEP
                // ---- Auto-rez when out of combat ----
                                // Promote to boss creature
                                OLD PHASE
                                phaseCreatureFound = true;
    Loot& loot = creature->loot;
    loot.clear();
y
""",
            dm.FILES[2]: """x
        ScaleDamage(target, attacker, damage);
        ScaleDamage(target, attacker, udmg);
        ScaleDamage(target, attacker, damage);
    void ScaleDamage(Unit* target, Unit* attacker, uint32& damage)
            // Session creature damage — scale bosses, pass through trash
            OLD
        // Non-session attacker (environmental hazards, traps, etc.)
y
""",
            dm.FILES[3]: r'''x
        else if (action == GOSSIP_ACTION_SCALE_PARTY)
        {
            { std::lock_guard<std::mutex> lk(sSelMutex); sSelections[player->GetGUID()].ScaleToParty = true; }
            ShowThemeMenu(player, creature);
        }
        else if (action == GOSSIP_ACTION_SCALE_TIER)
        {
            { std::lock_guard<std::mutex> lk(sSelMutex); sSelections[player->GetGUID()].ScaleToParty = false; }
            ShowThemeMenu(player, creature);
        }
        snprintf(buf, sizeof(buf), "  Theme:      |cFF00FF00%s|r", theme ? theme->Name.c_str() : "?");
        ChatHandler(player->GetSession()).SendSysMessage(buf);
        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF3.|r Pick a creature theme");
        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF4.|r Select a dungeon or go random");
        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF5.|r You'll be teleported to a cleared instance");
        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF6.|r Defeat the boss to complete the challenge");
        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF7.|r Collect gold and gear rewards!");
y
''',
        }
        for rel, text in originals.items():
            path = root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
        return originals

    def test_install_verify_idempotent_and_rollback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            originals = self.make_core(core)
            self.assertEqual(len(dm.install(core)), 4)
            dm.verify(core)
            self.assertEqual(dm.install(core), [])

            mgr = (core / dm.FILES[1]).read_text(encoding="utf-8")
            self.assertIn("Aventureros normal mode", mgr)
            self.assertIn("original ability damage scale", mgr)
            self.assertIn("preserveNativeLoot", mgr)
            unit = (core / dm.FILES[2]).read_text(encoding="utf-8")
            self.assertIn("0.35f", unit)
            gossip = (core / dm.FILES[3]).read_text(encoding="utf-8")
            self.assertNotIn("ShowThemeMenu(player, creature);", gossip)

            self.assertEqual(len(dm.rollback(core)), 4)
            for rel, expected in originals.items():
                self.assertEqual((core / rel).read_text(encoding="utf-8"), expected)

    def test_refuses_partial_patch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            core = Path(td) / "core"
            self.make_core(core)
            path = core / dm.FILES[0]
            path.write_text(path.read_text(encoding="utf-8") + "\nPrepareOriginalCreature(Creature* creature\n", encoding="utf-8")
            with self.assertRaises(dm.DungeonMasterSourcePatchError):
                dm.install(core)

    def test_shell_entry_points_manage_dungeon_master(self) -> None:
        for name in ("apply.sh", "update.sh", "verify.sh", "rollback.sh"):
            text = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn('tools/dungeon_master_source_patch.py"', text)
            self.assertIn('tools/dungeon_master_runtime.py"', text)


if __name__ == "__main__":
    unittest.main()
