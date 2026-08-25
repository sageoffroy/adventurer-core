from __future__ import annotations

import csv
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"
CLIENT = ROOT / "client" / "AdventurerResources.lua"
META_CLIENT = ROOT / "client" / "AdventurerDraftMeta.lua"
CONFIG = ROOT / "config" / "spelldraft" / "spelldraft.conf"
CARDS = ROOT / "config" / "spelldraft" / "cards.csv"


class SpellDraftV1Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.client = CLIENT.read_text(encoding="utf-8")
        cls.meta_client = META_CLIENT.read_text(encoding="utf-8")
        cls.config = CONFIG.read_text(encoding="utf-8")
        cls.cards_text = CARDS.read_text(encoding="utf-8")
        cls.cards = {
            int(row["id"]): row
            for row in csv.DictReader(io.StringIO(cls.cards_text), delimiter=";")
        }

    def test_card_is_the_unit_and_supports_bundles_requirements_and_weight(self) -> None:
        for token in (
            "struct DraftCard",
            "DraftCardType type",
            "DraftRarity rarity",
            "uint32 weight",
            "rankGrants",
            "requirementsAll",
            "requirementsAny",
            "unlocks",
        ):
            self.assertIn(token, self.runtime)

        self.assertEqual(self.cards[10]["rank_grants"], "1784+921")
        self.assertIn("ParseRankGrants", self.runtime)
        self.assertIn("ParseRequirements", self.runtime)

    def test_battle_stance_unlocks_charge_without_granting_it_for_free(self) -> None:
        battle_stance = self.cards[1]
        charge = self.cards[11]
        self.assertIn("11", battle_stance["unlocks"].split(","))
        self.assertEqual(charge["requires_all"], "1:1")
        self.assertEqual(charge["weight"], "500")
        self.assertNotIn("GrantKitSpells", self.runtime)

    def test_rarity_weight_and_blessing_are_independent_inputs_to_selection(self) -> None:
        self.assertIn("RarityWeightMultiplier", self.runtime)
        self.assertIn("EffectiveCardWeight", self.runtime)
        self.assertIn("card.weight", self.runtime)
        self.assertIn("card.rarity", self.runtime)
        self.assertIn("blessedCardId == card.id", self.runtime)
        self.assertIn("blessWeightMultiplierPercent", self.runtime)
        self.assertIn("SelectWeightedCards", self.runtime)
        self.assertIn("urand(1, totalWeight)", self.runtime)

    def test_progression_matches_configured_level_one_five_and_ten_contract(self) -> None:
        for token in (
            "InitialActivePicks = 3",
            "InitialActiveSourceLevelCap = 8",
            "ActiveDraftFirstLevel = 5",
            "ActiveDraftEveryLevels = 5",
            "TalentDraftFirstLevel = 10",
            "TalentDraftEveryLevels = 1",
        ):
            self.assertIn(token, self.config)

        self.assertIn("state.pendingActive = config.initialActivePicks", self.runtime)
        self.assertIn("ApplyLevelRewards", self.runtime)
        self.assertIn("IsScheduledLevel", self.runtime)
        active_first = self.runtime.index("if (state.pendingActive > 0)")
        talent_second = self.runtime.index("if (state.pendingTalent > 0)", active_first)
        self.assertLess(active_first, talent_second)

    def test_passive_ranks_are_separate_draft_investments(self) -> None:
        self.assertEqual(
            self.cards[101]["rank_grants"],
            "12320/12852/12853/12855/12856",
        )
        self.assertEqual(self.cards[101]["replaces_previous"], "1")
        self.assertIn("uint8 nextRank = currentRank + 1", self.runtime)
        self.assertIn("state.ownedRanks[card.id] = nextRank", self.runtime)
        self.assertIn("replacesPreviousRank", self.runtime)

    def test_active_spell_families_upgrade_automatically(self) -> None:
        self.assertIn("UpgradeActiveSpellFamily", self.runtime)
        self.assertIn("GetFirstSpellInChain", self.runtime)
        self.assertIn("GetNextSpellInChain", self.runtime)
        self.assertIn("requiredLevel <= level", self.runtime)
        self.assertIn("UpgradeDraftedActiveSpells(player, state)", self.runtime)

    def test_offer_owned_and_meta_state_survive_relogs(self) -> None:
        self.assertIn('ADVENTURER_DRAFT_SETTINGS_SOURCE[] = "adventurer_draft_v1"', self.runtime)
        self.assertIn("SerializeDraftState", self.runtime)
        self.assertIn("DeserializeDraftState", self.runtime)
        self.assertIn("character_settings", self.runtime)
        for token in (
            "offeredCards",
            "ownedRanks",
            "rerollCharges",
            "destroyCharges",
            "blessedCardId",
            "destroyedCards",
            "PersistDraftState",
            "LoadPersistedDraftState",
        ):
            self.assertIn(token, self.runtime)

    def test_server_validates_pick_against_persisted_offer_and_eligibility(self) -> None:
        self.assertIn("IsCardInCurrentOffer", self.runtime)
        self.assertIn('SendDraftError(player, "INVALID_PICK"', self.runtime)
        self.assertIn('SendDraftError(player, "INELIGIBLE_PICK"', self.runtime)
        self.assertIn("IsCardEligible(player, state, *card, state.offerType)", self.runtime)

    def test_runtime_catalog_is_external_and_reloadable_without_recompile(self) -> None:
        self.assertIn("std::ifstream", self.runtime)
        self.assertIn('"spelldraft.conf"', self.runtime)
        self.assertIn('"cards.csv"', self.runtime)
        self.assertIn("ReloadDraftRuntimeData", self.runtime)
        self.assertIn("keeping last valid catalog", self.runtime)
        self.assertIn("BuildFallbackDraftCards", self.runtime)

    def test_reroll_bless_and_destroy_have_server_and_client_protocols(self) -> None:
        for token in (
            'DRAFT_REROLL_MESSAGE[] = "ADRAFT_REROLL"',
            'DRAFT_BLESS_PREFIX[] = "ADRAFT_BLESS:"',
            'DRAFT_DESTROY_PREFIX[] = "ADRAFT_DESTROY:"',
            "HandleDraftReroll",
            "HandleDraftBless",
            "HandleDraftDestroy",
        ):
            self.assertIn(token, self.runtime)

        for token in (
            'DRAFT_REROLL_MESSAGE = "ADRAFT_REROLL"',
            'DRAFT_BLESS_PREFIX = "ADRAFT_BLESS:"',
            'DRAFT_DESTROY_PREFIX = "ADRAFT_DESTROY:"',
            "AdventurerDraftRerollButton",
            "AdventurerDraftBlessButton",
            "AdventurerDraftDestroyButton",
        ):
            self.assertIn(token, self.meta_client)

    def test_destroyed_cards_are_removed_and_bless_does_not_bypass_requirements(self) -> None:
        self.assertIn("state.destroyedCards.count(card.id)", self.runtime)
        self.assertIn("state.destroyedCards.insert(cardId)", self.runtime)
        self.assertIn("return MeetsRequirements(state, card)", self.runtime)
        self.assertIn("state.blessedCardId = cardId", self.runtime)

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

    def test_client_core_chooser_is_not_the_upstream_spelldraft_addon(self) -> None:
        self.assertNotIn("Spell" + "Draft", self.client)
        self.assertNotIn("Prestige", self.client)
        self.assertNotIn("PrestigeShop", self.client)


if __name__ == "__main__":
    unittest.main()
