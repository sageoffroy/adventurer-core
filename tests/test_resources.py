from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"


class AdventurerResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = RUNTIME.read_text(encoding="utf-8")

    def test_diagnostic_baseline_exposes_only_native_mana(self) -> None:
        for token in (
            "ADVENTURER_MAX_RAGE",
            "ADVENTURER_MAX_ENERGY",
            "SetMaxPower(POWER_RAGE",
            "SetMaxPower(POWER_ENERGY",
            "SetPower(POWER_RAGE",
            "SetPower(POWER_ENERGY",
            "PLAYERHOOK_ON_PLAYER_HAS_ACTIVE_POWER_TYPE",
            "OnPlayerHasActivePowerType",
            "PLAYERHOOK_ON_AFTER_UPDATE_MAX_POWER",
            "OnPlayerAfterUpdateMaxPower",
        ):
            self.assertNotIn(token, self.source)

        # Mana remains native to the class-10 DBC/stat path; the runtime does
        # not create a fake fixed mana pool either.
        self.assertNotIn("ADVENTURER_MAX_MANA", self.source)
        self.assertIn("Mana is the Adventurer's only active power pool", self.source)

    def test_death_knight_runtime_is_not_attached_to_adventurer(self) -> None:
        forbidden = (
            "PLAYERHOOK_ON_PLAYER_IS_CLASS",
            "OnPlayerIsClass",
            "CLASS_DEATH_KNIGHT",
            "POWER_RUNIC_POWER",
            "POWER_RUNE",
            "MAX_RUNES",
            "GetRuneCooldown",
            "ResyncRunes",
            "AddRunePower",
            "RuneSyncState",
            "runeSyncStates",
        )
        for token in forbidden:
            self.assertNotIn(token, self.source)

    def test_combo_points_backend_bridge_remains_server_side(self) -> None:
        self.assertIn("PLAYERHOOK_ON_UPDATE", self.source)
        self.assertIn("OnPlayerUpdate(Player* player, uint32 diff)", self.source)
        self.assertIn("ADVENTURER_COMBO_SYNC_INTERVAL_MS = 100", self.source)
        self.assertIn('ADVENTURER_COMBO_PREFIX[] = "AdventurerCP"', self.source)
        self.assertIn("player->GetComboPoints(selectedTarget)", self.source)
        self.assertIn("WorldPacket data(SMSG_MESSAGECHAT, 100)", self.source)
        self.assertIn("data << uint8(0); // CHAT_MSG_ADDON", self.source)
        self.assertIn("LANG_ADDON", self.source)
        self.assertIn('std::string(ADVENTURER_COMBO_PREFIX) + "\\t"', self.source)
        self.assertIn("player->SendDirectMessage(&data)", self.source)
        self.assertNotIn("AddComboPoints(", self.source)

    def test_runtime_sync_state_is_removed_on_logout(self) -> None:
        self.assertIn("PLAYERHOOK_ON_LOGOUT", self.source)
        self.assertIn("OnPlayerLogout(Player* player)", self.source)
        self.assertIn("comboSyncStates.erase", self.source)
        self.assertNotIn("runeSyncStates", self.source)


if __name__ == "__main__":
    unittest.main()
