from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"


class AdventurerResourceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.source = RUNTIME.read_text(encoding="utf-8")

    def test_auxiliary_power_pool_sizes_match_wotlk_storage_scale(self) -> None:
        self.assertIn("ADVENTURER_MAX_RAGE = 1000", self.source)
        self.assertIn("ADVENTURER_MAX_ENERGY = 100", self.source)
        self.assertIn("ADVENTURER_MAX_RUNIC_POWER = 1000", self.source)
        self.assertIn("SetMaxPower(POWER_RAGE, ADVENTURER_MAX_RAGE)", self.source)
        self.assertIn("SetMaxPower(POWER_ENERGY, ADVENTURER_MAX_ENERGY)", self.source)
        self.assertIn("SetMaxPower(POWER_RUNIC_POWER, ADVENTURER_MAX_RUNIC_POWER)", self.source)

    def test_adventurer_keeps_mana_native_and_activates_auxiliary_powers(self) -> None:
        self.assertIn("PLAYERHOOK_ON_PLAYER_HAS_ACTIVE_POWER_TYPE", self.source)
        self.assertIn("OnPlayerHasActivePowerType", self.source)
        self.assertRegex(
            self.source,
            re.compile(
                r"case POWER_RAGE:\s*case POWER_ENERGY:\s*case POWER_RUNIC_POWER:\s*"
                r"return player->GetMaxPower\(power\) > 0;",
                re.MULTILINE,
            ),
        )
        # Mana is deliberately not given a fake fixed pool: class-10 DBC/stat
        # scaling remains authoritative for the primary resource.
        self.assertNotIn("ADVENTURER_MAX_MANA", self.source)

    def test_stat_recalculation_cannot_erase_auxiliary_power_pools(self) -> None:
        self.assertIn("PLAYERHOOK_ON_AFTER_UPDATE_MAX_POWER", self.source)
        self.assertIn("OnPlayerAfterUpdateMaxPower", self.source)
        for token in (
            "ADVENTURER_MAX_RAGE",
            "ADVENTURER_MAX_ENERGY",
            "ADVENTURER_MAX_RUNIC_POWER",
        ):
            self.assertIn(f"std::max(value, static_cast<float>({token}))", self.source)

    def test_runes_reuse_native_dk_ability_context_only(self) -> None:
        self.assertIn("PLAYERHOOK_ON_PLAYER_IS_CLASS", self.source)
        self.assertIn("OnPlayerIsClass", self.source)
        self.assertIn(
            "playerClass == CLASS_DEATH_KNIGHT && context == CLASS_CONTEXT_ABILITY",
            self.source,
        )
        self.assertNotIn(
            "playerClass == CLASS_DEATH_KNIGHT && context == CLASS_CONTEXT_INIT",
            self.source,
        )
        self.assertNotIn("CLASS_CONTEXT_QUEST", self.source)
        self.assertNotIn("CLASS_CONTEXT_TAXI", self.source)

    def test_rune_state_transitions_sync_the_native_client(self) -> None:
        self.assertIn("PLAYERHOOK_ON_AFTER_UPDATE", self.source)
        self.assertIn("OnPlayerAfterUpdate(Player* player", self.source)
        self.assertIn("GetRuneReadyMask(Player const* player)", self.source)
        self.assertIn("player->GetRuneCooldown(index) == 0", self.source)
        self.assertIn("previousReadyMask & ~readyMask", self.source)
        self.assertIn("readyMask & ~previousReadyMask", self.source)
        self.assertIn("if (newlySpent == 0 && newlyReady == 0)", self.source)
        self.assertIn("player->ResyncRunes(MAX_RUNES)", self.source)
        self.assertIn("if (newlyReady != 0)", self.source)
        self.assertIn("newlyReady & uint8(1u << index)", self.source)
        self.assertIn("player->AddRunePower(index)", self.source)
        self.assertIn("runeSyncStates.erase(key)", self.source)

    def test_new_adventurer_starts_energy_full_and_generated_powers_empty(self) -> None:
        self.assertIn("SetPower(POWER_RAGE, 0)", self.source)
        self.assertIn("SetPower(POWER_ENERGY, ADVENTURER_MAX_ENERGY)", self.source)
        self.assertIn("SetPower(POWER_RUNIC_POWER, 0)", self.source)

    def test_combo_points_are_mirrored_to_frame_xml_without_reimplementing_backend(self) -> None:
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
        self.assertIn("comboSyncStates.erase(key)", self.source)
        self.assertIn("runeSyncStates.erase(key)", self.source)


if __name__ == "__main__":
    unittest.main()
