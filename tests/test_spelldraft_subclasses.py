from __future__ import annotations

import csv
import io
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from subclasses import (  # noqa: E402
    EXPECTED_KEYS,
    card_subclass_map,
    load_spec,
    validate_card_coverage,
)
from spelldraft_runtime import build_runtime_subclasses  # noqa: E402

CARDS = ROOT / "config" / "spelldraft" / "cards.csv"
SUBCLASSES = ROOT / "config" / "spelldraft" / "subclasses.json"
CLIENT = ROOT / "client" / "AdventurerCollections.lua"
CLIENT_BUILDER = ROOT / "tools" / "client.py"
RUNTIME = ROOT / "tools" / "spelldraft_runtime.py"
DBC_PATCH = ROOT / "tools" / "subclasses.py"
COLLECTION_SERVER = (
    ROOT
    / "payload"
    / "core"
    / "src"
    / "server"
    / "scripts"
    / "Custom"
    / "adventurer_collections.cpp"
)
CORE_PATCH = ROOT / "tools" / "core_patch.py"
UPGRADE = ROOT / "tools" / "upgrade.py"


class SpellDraftSubclassTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.cards_text = CARDS.read_text(encoding="utf-8")
        cls.spec = load_spec(SUBCLASSES)
        cls.mapping = validate_card_coverage(cls.cards_text, cls.spec)
        cls.client = CLIENT.read_text(encoding="utf-8")
        cls.client_builder = CLIENT_BUILDER.read_text(encoding="utf-8")
        cls.runtime = RUNTIME.read_text(encoding="utf-8")
        cls.dbc_patch = DBC_PATCH.read_text(encoding="utf-8")
        cls.collection_server = COLLECTION_SERVER.read_text(encoding="utf-8")
        cls.core_patch = CORE_PATCH.read_text(encoding="utf-8")
        cls.upgrade = UPGRADE.read_text(encoding="utf-8")

    def test_exact_four_subclasses_and_full_catalog_coverage(self) -> None:
        keys = tuple(item["key"] for item in self.spec["subclasses"])
        self.assertEqual(keys, EXPECTED_KEYS)
        self.assertEqual(len(set(self.mapping.values())), 4)

        card_ids = {
            int(row["id"])
            for row in csv.DictReader(io.StringIO(self.cards_text), delimiter=";")
        }
        self.assertEqual(set(self.mapping), card_ids)

    def test_requested_identity_examples_are_classified_by_function(self) -> None:
        expected = {
            14: "mercenary",
            40: "mercenary",
            128: "mercenary",
            42: "explorer",
            46: "explorer",
            152: "explorer",
            2: "spellcaster",
            4: "spellcaster",
            44: "spellcaster",
            59: "spellcaster",
            184: "spellcaster",
            5: "illuminated",
            30: "illuminated",
            172: "illuminated",
        }
        for card_id, subclass in expected.items():
            self.assertEqual(self.mapping[card_id], subclass, card_id)

    def test_subclass_metadata_owns_four_unique_native_skill_lines(self) -> None:
        skill_lines = [int(item["skill_line_id"]) for item in self.spec["subclasses"]]
        self.assertEqual(skill_lines, [900, 901, 902, 903])
        self.assertEqual(len(skill_lines), len(set(skill_lines)))
        self.assertEqual(
            [item["esMX"] for item in self.spec["subclasses"]],
            ["Mercenario", "Explorador", "Hechicero", "Iluminado"],
        )

    def test_spellbook_dbc_patch_is_native_and_adventurer_only(self) -> None:
        for token in (
            '"SkillLine.dbc"',
            '"SkillLineAbility.dbc"',
            '"SkillRaceClassInfo.dbc"',
            "ADVENTURER_CLASS_MASK",
            "patch_skill_lines",
            "patch_skill_line_abilities",
            "SLA_EXCLUDE_CLASS",
            "rank_chain_closure",
        ):
            self.assertIn(token, self.dbc_patch)

        self.assertIn("changed.update(patch_subclass_directory(work))", self.client_builder)
        self.assertIn('"SkillLine.dbc"', self.client_builder)
        self.assertIn('"SkillLineAbility.dbc"', self.client_builder)

    def test_runtime_keeps_cards_csv_parser_contract_and_separate_class_map(self) -> None:
        header = self.cards_text.splitlines()[0]
        self.assertEqual(len(header.split(";")), 12)
        self.assertNotIn("subclass", header)
        self.assertIn('"card_subclasses.csv"', self.runtime)
        self.assertIn("build_runtime_subclasses", self.runtime)

        generated_map = build_runtime_subclasses(
            self.cards_text,
            self.cards_text,
            self.spec,
        )
        rows = list(csv.DictReader(io.StringIO(generated_map), delimiter=";"))
        self.assertEqual(set(rows[0]), {"card_id", "subclass"})
        self.assertEqual(len(rows), len(self.mapping))
        self.assertEqual(
            {int(row["card_id"]): row["subclass"] for row in rows},
            self.mapping,
        )

    def test_talent_collection_is_server_authoritative_and_only_returns_owned_ranks(self) -> None:
        for token in (
            'TALENT_COLLECTION_REQUEST[] = "ADRAFT_TALENTS"',
            '"cards.csv"',
            '"card_subclasses.csv"',
            'payload << "T|C|"',
            "player->HasSpell(spellId)",
            "for (size_t index = talent.rankGrants.size(); index > 0; --index)",
            "ADVENTURER_SUBCLASS_SKILLS[] = {900, 901, 902, 903}",
            "player->SetSkill(skillId, 1, 1, 1)",
        ):
            self.assertIn(token, self.collection_server)

    def test_adventurer_talent_window_mirrors_spellbook_with_vertical_subclass_tabs(self) -> None:
        for token in (
            'TALENT_COLLECTION_REQUEST = "ADRAFT_TALENTS"',
            'frame = CreateFrame("Frame", "AdventurerTalentCollectionFrame"',
            '"mercenary", "explorer", "spellcaster", "illuminated"',
            "TALENTS_PER_PAGE = 12",
            "ROWS_PER_COLUMN = 6",
            '"Interface\\\\Spellbook\\\\UI-SpellbookPanel-TopLeft"',
            '"Interface\\\\Spellbook\\\\UI-SpellbookPanel-BotRight"',
            '"Interface\\\\Spellbook\\\\UI-Spellbook-SpellBackground"',
            '"Interface\\\\Buttons\\\\UI-SpellbookIcon-PrevPage-Up"',
            '"Interface\\\\Buttons\\\\UI-SpellbookIcon-NextPage-Up"',
            '"Interface\\\\SpellBook\\\\SpellBook-SkillLineTab"',
            'local subclassIcons = {',
            'Ability_Warrior_OffensiveStance',
            'Ability_Hunter_BeastTaming',
            'Spell_Frost_FrostBolt02',
            'Spell_Holy_HolyBolt',
            'CreateFrame("CheckButton", "AdventurerTalentCollectionTab" .. index, frame)',
            'tab:SetPoint("TOPLEFT", frame, "TOPRIGHT", -32, -65 - (index - 1) * 46)',
            'entry.name:SetWidth(103)',
            'GameTooltip:SetHyperlink("spell:" .. self.spellId)',
            'GameTooltip:AddLine(string.format(text.rank',
            "local NativeToggleTalentFrame = ToggleTalentFrame",
            "local function AdventurerToggleTalentFrame()",
            "local function RebindTalentEntryPoints()",
            'TalentMicroButton:SetScript("OnClick", AdventurerToggleTalentFrame)',
            'eventFrame:RegisterEvent("ADDON_LOADED")',
            'addonName == "Blizzard_TalentUI"',
        ):
            self.assertIn(token, self.client)

        self.assertNotIn(
            'CreateFrame(\n        "Button",\n        "AdventurerTalentCollectionTab" .. index,\n        frame,\n        "SpellBookFrameTabButtonTemplate")',
            self.client,
        )

        for forbidden in (
            "SetMaxLines",
            "FauxScrollFrame",
            "BRANCH_PAGE_SIZE",
            "AdventurerTalentCollectionBranch",
            "GRID_COLUMNS",
        ):
            self.assertNotIn(forbidden, self.client)

        self.assertIn("AdventurerCollections.lua", self.client_builder)
        self.assertIn("build_adventurer_collections_lua", self.client_builder)
        self.assertIn("ADVENTURER_COLLECTIONS_INTERNAL", self.client_builder)

    def test_collection_script_is_registered_and_upgrade_can_add_owned_payload(self) -> None:
        self.assertIn("AddAdventurerCollectionScripts();", self.core_patch)
        self.assertIn('"src/server/scripts/Custom/adventurer_collections.cpp"', self.core_patch)
        self.assertIn("if item.relative_path not in owned and item.original is not None", self.upgrade)
        self.assertIn('"existed_before": False', self.upgrade)
        self.assertIn("remove_new_sources(core, planned)", self.upgrade)


if __name__ == "__main__":
    unittest.main()
