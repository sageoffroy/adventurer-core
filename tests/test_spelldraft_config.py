from __future__ import annotations

import configparser
import csv
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "config" / "spelldraft" / "spelldraft.conf"
CARDS = ROOT / "config" / "spelldraft" / "cards.csv"


class SpellDraftExternalConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        parser = configparser.ConfigParser()
        loaded = parser.read(CONFIG, encoding="utf-8")
        if not loaded:
            raise AssertionError(f"could not load {CONFIG}")
        cls.config = parser

        with CARDS.open(newline="", encoding="utf-8") as handle:
            cls.cards = list(csv.DictReader(handle, delimiter=";"))

    def test_runtime_balance_knobs_are_external(self) -> None:
        self.assertEqual(self.config.getint("Draft", "OfferSize"), 3)
        self.assertEqual(self.config.getint("Draft", "InitialActivePicks"), 3)
        self.assertEqual(self.config.getint("Draft", "InitialActiveSourceLevelCap"), 8)

        for section in ("Reroll", "Bless", "Destroy"):
            self.assertIn(section, self.config)

        self.assertIn("StartingCharges", self.config["Reroll"])
        self.assertIn("GainEveryLevels", self.config["Reroll"])
        self.assertIn("WeightMultiplierPercent", self.config["Bless"])
        self.assertIn("StartingCharges", self.config["Destroy"])
        self.assertIn("GainEveryLevels", self.config["Destroy"])

    def test_card_catalog_has_stable_schema(self) -> None:
        expected = {
            "id",
            "key",
            "type",
            "source_level",
            "rarity",
            "weight",
            "rank_grants",
            "requires_all",
            "requires_any",
            "unlocks",
            "replaces_previous",
            "name",
        }
        self.assertTrue(self.cards)
        self.assertEqual(set(self.cards[0]), expected)

    def test_card_ids_and_keys_are_unique(self) -> None:
        ids = [int(row["id"]) for row in self.cards]
        keys = [row["key"] for row in self.cards]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(keys), len(set(keys)))
        self.assertTrue(all(card_id > 0 for card_id in ids))
        self.assertTrue(all(keys))

    def test_cards_use_known_types_and_rarities(self) -> None:
        valid_types = {"active", "talent"}
        valid_rarities = {"common", "uncommon", "rare", "epic", "legendary"}
        for row in self.cards:
            self.assertIn(row["type"], valid_types, row)
            self.assertIn(row["rarity"], valid_rarities, row)
            self.assertGreaterEqual(int(row["source_level"]), 1, row)
            self.assertGreater(int(row["weight"]), 0, row)
            self.assertIn(row["replaces_previous"], {"0", "1"}, row)

    def test_rank_grants_support_bundles_and_progressive_ranks(self) -> None:
        by_key = {row["key"]: row for row in self.cards}
        self.assertEqual(by_key["stealth_kit"]["rank_grants"], "1784+921")
        self.assertEqual(
            by_key["cruelty"]["rank_grants"],
            "12320/12852/12853/12855/12856",
        )

        for row in self.cards:
            ranks = row["rank_grants"].split("/")
            self.assertTrue(ranks, row)
            for rank in ranks:
                grants = rank.split("+")
                self.assertTrue(all(int(spell_id) > 0 for spell_id in grants), row)

    def test_requirements_only_reference_existing_cards(self) -> None:
        card_ids = {int(row["id"]) for row in self.cards}
        for row in self.cards:
            for column in ("requires_all", "requires_any"):
                raw = row[column].strip()
                if not raw:
                    continue
                for token in raw.replace("|", ",").split(","):
                    token = token.strip()
                    if not token:
                        continue
                    card_id, rank = token.split(":", 1)
                    self.assertIn(int(card_id), card_ids, row)
                    self.assertGreater(int(rank), 0, row)

    def test_current_prototype_relationships_survive_externalization(self) -> None:
        by_key = {row["key"]: row for row in self.cards}
        self.assertEqual(by_key["charge"]["requires_all"], "1:1")
        self.assertEqual(int(by_key["charge"]["weight"]), 500)
        self.assertEqual(by_key["improved_fireball"]["requires_all"], "2:1")
        self.assertEqual(by_key["improved_frostbolt"]["requires_all"], "3:1")


if __name__ == "__main__":
    unittest.main()
