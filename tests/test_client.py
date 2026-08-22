from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from client import build_character_create_lua  # noqa: E402
from mpq import build_mpq  # noqa: E402


class ClientPatchTests(unittest.TestCase):
    def test_character_create_resolves_only_adventurer_class(self):
        payload = build_character_create_lua().decode("utf-8")
        self.assertNotIn("TECHNICAL_CLASS_ID", payload)
        self.assertIn("ResolveOnlyValidClassForCurrentRace", payload)
        self.assertIn("ADVENTURER_CLASS_INDEX", payload)
        self.assertIn("validCount ~= 1", payload)
        self.assertIn("if ( not SelectTechnicalClassForCurrentRace() ) then", payload)
        # The 11-class enumeration must not touch a nonexistent eleventh class button.
        enumerate_start = payload.index("function CharacterCreateEnumerateClasses(...)")
        enumerate_end = payload.index("function SetCharacterRace(id)", enumerate_start)
        enumerate_body = payload[enumerate_start:enumerate_end]
        self.assertNotIn("CharacterCreateClassButton", enumerate_body)

    def test_mpq_writer_emits_v1_archive_and_listfile_block(self):
        payload = build_mpq({"Interface\\GlueXML\\Test.lua": b"print('ok')\n"})
        self.assertTrue(payload.startswith(b"MPQ\x1a"))
        self.assertIn(b"print('ok')", payload)
        # The raw listfile payload lists the authored file. Its own `(listfile)`
        # hash-table name is encrypted, so validate the archive has two blocks:
        # the authored file plus the generated listfile.
        self.assertIn(b"Interface\\GlueXML\\Test.lua\r\n", payload)
        header = struct.unpack_from("<4sIIHHIIII", payload, 0)
        self.assertEqual(header[-1], 2)


if __name__ == "__main__":
    unittest.main()
