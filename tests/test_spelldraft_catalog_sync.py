from __future__ import annotations

import csv
import io
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "config" / "spelldraft" / "cards.csv"
META_CLIENT = ROOT / "client" / "AdventurerDraftMeta.lua"
CORE = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"


class SpellDraftCatalogSyncTests(unittest.TestCase):
    def test_debug_pool_is_server_authoritative_and_base_catalog_is_valid(self) -> None:
        cards = {
            int(row["id"]): row
            for row in csv.DictReader(io.StringIO(CARDS.read_text(encoding="utf-8")), delimiter=";")
        }

        lua = META_CLIENT.read_text(encoding="utf-8")
        core = CORE.read_text(encoding="utf-8")

        # The client must never carry a second card/talent catalog. Pool debug is
        # streamed from the same runtime cards loaded by the server.
        self.assertNotIn("local debugCatalog = {", lua)
        self.assertIn('DRAFT_DEBUG_POOL_MESSAGE = "ADRAFT_POOL"', lua)
        self.assertIn("local function RequestDebugPool()", lua)
        self.assertIn("local function ParseDebugPool(message)", lua)
        self.assertIn('DRAFT_DEBUG_POOL_MESSAGE[] = "ADRAFT_POOL"', core)
        self.assertIn("for (DraftCard const& card : GetDraftCards())", core)
        self.assertIn("IsCardDebugEligible(player, state, card)", core)
        self.assertIn("MeetsRequirements(state, card)", core)

        active_rows = [row for row in cards.values() if row["type"] == "active"]
        self.assertGreaterEqual(len(active_rows), 190)
        self.assertEqual(max(int(row["source_level"]) for row in active_rows), 20)


if __name__ == "__main__":
    unittest.main()
