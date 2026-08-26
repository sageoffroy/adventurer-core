from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "payload" / "core" / "src" / "server" / "scripts" / "Custom" / "adventurer_core.cpp"
CLIENT = ROOT / "client" / "AdventurerDraftMeta.lua"


class SpellDraftAuthoritativePoolTests(unittest.TestCase):
    def test_server_exports_authoritative_debug_pool(self) -> None:
        text = CORE.read_text(encoding="utf-8")
        self.assertIn('DRAFT_DEBUG_POOL_MESSAGE[] = "ADRAFT_POOL"', text)
        self.assertIn("bool IsCardDebugEligible", text)
        self.assertIn("return MeetsRequirements(state, card);", text)
        self.assertIn("void SendDraftDebugPool", text)
        self.assertIn('payload << "D|C|"', text)
        self.assertIn("HandleDraftDebugPool(player);", text)

    def test_client_has_no_hardcoded_card_or_talent_pool(self) -> None:
        text = CLIENT.read_text(encoding="utf-8")
        self.assertNotIn("local debugCatalog = {", text)
        self.assertNotIn('id=105, type="talent"', text)
        self.assertIn('DRAFT_DEBUG_POOL_MESSAGE = "ADRAFT_POOL"', text)
        self.assertIn("local function RequestDebugPool()", text)
        self.assertIn("local function ParseDebugPool(message)", text)
        self.assertIn("state.debugCatalog", text)


if __name__ == "__main__":
    unittest.main()
