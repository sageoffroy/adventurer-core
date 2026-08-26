from __future__ import annotations

import csv
import io
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "config" / "spelldraft" / "cards.csv"
META_CLIENT = ROOT / "client" / "AdventurerDraftMeta.lua"


class SpellDraftCatalogSyncTests(unittest.TestCase):
    def test_debug_catalog_is_a_valid_subset_of_packaged_server_catalog(self) -> None:
        cards = {
            int(row["id"]): row
            for row in csv.DictReader(io.StringIO(CARDS.read_text(encoding="utf-8")), delimiter=";")
        }

        lua = META_CLIENT.read_text(encoding="utf-8")
        start = lua.index("local debugCatalog = {")
        end = lua.index("\n}\n\nlocal catalogById", start)
        catalog = lua[start:end]

        pattern = re.compile(
            r'\{ id=(\d+), type="(active|talent)", level=(\d+), '
            r'rarity="(common|uncommon|rare|epic|legendary)", spell=(\d+), maxRank=(\d+)'
        )
        debug = {
            int(card_id): {
                "type": card_type,
                "level": int(level),
                "rarity": rarity,
                "spell": int(spell),
                "max_rank": int(max_rank),
            }
            for card_id, card_type, level, rarity, spell, max_rank in pattern.findall(catalog)
        }

        self.assertTrue(debug)
        self.assertTrue(set(debug).issubset(set(cards)))
        for card_id, item in debug.items():
            row = cards[card_id]
            ranks = row["rank_grants"].split("/")
            primary_spell = int(ranks[0].split("+")[0])
            self.assertEqual(item["type"], row["type"], card_id)
            self.assertEqual(item["level"], int(row["source_level"]), card_id)
            self.assertEqual(item["rarity"], row["rarity"], card_id)
            self.assertEqual(item["spell"], primary_spell, card_id)
            self.assertEqual(item["max_rank"], len(ranks), card_id)

        active_rows = [row for row in cards.values() if row["type"] == "active"]
        self.assertGreaterEqual(len(active_rows), 190)
        self.assertEqual(max(int(row["source_level"]) for row in active_rows), 20)


if __name__ == "__main__":
    unittest.main()
