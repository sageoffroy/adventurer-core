from __future__ import annotations

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"
CLIENT = ROOT / "client" / "AdventurerResources.lua"


class SpellDraftV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.client = CLIENT.read_text(encoding="utf-8")

    def test_card_is_the_unit_and_supports_bundles_requirements_and_weight(self) -> None:
        for token in (
            "struct DraftCard",
            "DraftCardType type",
            "DraftRarity rarity",
            "uint32 weight",
            "rankGrants",
            "requirements",
            "unlocks",
        ):
            self.assertIn(token, self.runtime)

        # Stealth is deliberately one card that teaches two spells.
        self.assertRegex(
            self.runtime,
            re.compile(r"\{\s*10,\s*DraftCardType::Active.*?\{\{1784,\s*921\}\}", re.DOTALL),
        )

    def test_battle_stance_unlocks_charge_without_granting_it_for_free(self) -> None:
        # Battle Stance advertises Charge in its graph metadata.
        self.assertRegex(
            self.runtime,
            re.compile(r"\{\s*1,\s*DraftCardType::Active.*?\{\{2457\}\}.*?\{11,\s*106\}", re.DOTALL),
        )
        # Charge is a separate card, requires Battle Stance, and carries x5 base weight.
        self.assertRegex(
            self.runtime,
            re.compile(r"\{\s*11,\s*DraftCardType::Active,\s*DraftRarity::Common,\s*500,\s*\{\{100\}\},\s*\{\{1,\s*1\}\}", re.DOTALL),
        )
        self.assertNotIn("GrantKitSpells", self.runtime)

    def test_rarity_and_weight_are_independent_inputs_to_selection(self) -> None:
        self.assertIn("RarityWeightMultiplier", self.runtime)
        self.assertIn("EffectiveCardWeight", self.runtime)
        self.assertIn("card.weight", self.runtime)
        self.assertIn("card.rarity", self.runtime)
        self.assertIn("SelectWeightedCards", self.runtime)
        self.assertIn("urand(1, totalWeight)", self.runtime)

    def test_progression_matches_level_one_five_and_ten_contract(self) -> None:
        self.assertIn("state.pendingActive = 3", self.runtime)
        self.assertIn("for (uint32 level = 5; level <= currentLevel; level += 5)", self.runtime)
        self.assertIn("if ((level % 5) == 0)", self.runtime)
        self.assertIn("if (level >= 10)", self.runtime)
        self.assertIn("state.pendingTalent = currentLevel - 9", self.runtime)

        active_first = self.runtime.index("if (state.pendingActive > 0)")
        talent_second = self.runtime.index("if (state.pendingTalent > 0)", active_first)
        self.assertLess(active_first, talent_second)

    def test_passive_ranks_are_separate_draft_investments(self) -> None:
        self.assertRegex(
            self.runtime,
            re.compile(r"\{\s*101,\s*DraftCardType::Talent.*?\{\{12320\},\s*\{12852\},\s*\{12853\},\s*\{12855\},\s*\{12856\}\}", re.DOTALL),
        )
        self.assertIn("uint8 nextRank = currentRank + 1", self.runtime)
        self.assertIn("state.ownedRanks[card.id] = nextRank", self.runtime)
        self.assertIn("replacesPreviousRank", self.runtime)

    def test_active_spell_families_upgrade_automatically(self) -> None:
        self.assertIn("UpgradeActiveSpellFamily", self.runtime)
        self.assertIn("GetFirstSpellInChain", self.runtime)
        self.assertIn("GetNextSpellInChain", self.runtime)
        self.assertIn("requiredLevel <= level", self.runtime)
        self.assertIn("UpgradeDraftedActiveSpells(player, state)", self.runtime)

    def test_offer_and_owned_card_state_survive_relogs(self) -> None:
        self.assertIn('ADVENTURER_DRAFT_SETTINGS_SOURCE[] = "adventurer_draft_v1"', self.runtime)
        self.assertIn("SerializeDraftState", self.runtime)
        self.assertIn("DeserializeDraftState", self.runtime)
        self.assertIn("character_settings", self.runtime)
        self.assertIn("offeredCards", self.runtime)
        self.assertIn("ownedRanks", self.runtime)
        self.assertIn("PersistDraftState", self.runtime)
        self.assertIn("LoadPersistedDraftState", self.runtime)

    def test_server_validates_pick_against_persisted_offer_and_eligibility(self) -> None:
        self.assertIn("IsCardInCurrentOffer", self.runtime)
        self.assertIn('SendDraftError(player, "INVALID_PICK")', self.runtime)
        self.assertIn('SendDraftError(player, "INELIGIBLE_PICK")', self.runtime)
        self.assertIn("IsCardEligible(state, *card, state.offerType)", self.runtime)

    def test_normal_talent_points_are_disabled_for_spell_draft_adventurer(self) -> None:
        self.assertIn("PLAYERHOOK_ON_CALCULATE_TALENTS_POINTS", self.runtime)
        self.assertIn("talentPointsForLevel = 0", self.runtime)
        self.assertIn("player->SetFreeTalentPoints(0)", self.runtime)

    def test_client_has_minimal_three_card_choice_flow(self) -> None:
        for token in (
            'DRAFT_PREFIX = "AdventurerDraft"',
            'DRAFT_READY_MESSAGE = "ADRAFT_READY"',
            'DRAFT_PICK_PREFIX = "ADRAFT_PICK:"',
            "DRAFT_BUTTON_COUNT = 3",
            "AdventurerDraftFrame",
            "GetSpellInfo(card.spellId)",
            'GameTooltip:SetHyperlink("spell:" .. self.spellId)',
            "RegisterAddonMessagePrefix(DRAFT_PREFIX)",
            "ShowDraftOffer",
            "HandleDraftServerMessage",
        ):
            self.assertIn(token, self.client)

    def test_client_is_not_the_upstream_spelldraft_addon(self) -> None:
        # tools/client.py intentionally rejects upstream SpellDraft payloads.
        self.assertNotIn("Spell" + "Draft", self.client)
        self.assertNotIn("Prestige", self.client)
        self.assertNotIn("Reroll", self.client)
        self.assertNotIn("PrestigeShop", self.client)


if __name__ == "__main__":
    unittest.main()
