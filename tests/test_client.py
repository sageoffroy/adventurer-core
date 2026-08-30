from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from client import (  # noqa: E402
    DBC_NAMES,
    DBC_SOURCE_NAMES,
    ROOT_SHARED_DBCS,
    build_archive_files,
    build_character_create_lua,
)
from mpq import build_mpq  # noqa: E402


class ClientPatchTests(unittest.TestCase):
    def test_character_create_resolves_only_adventurer_class(self):
        payload = build_character_create_lua().decode("utf-8")
        self.assertNotIn("TECHNICAL_CLASS_ID", payload)
        self.assertIn("ResolveOnlyValidClassForCurrentRace", payload)
        self.assertIn("ADVENTURER_CLASS_INDEX", payload)
        self.assertIn("validCount ~= 1", payload)
        self.assertIn("if ( not SelectTechnicalClassForCurrentRace() ) then", payload)
        enumerate_start = payload.index("function CharacterCreateEnumerateClasses(...)")
        enumerate_end = payload.index("function SetCharacterRace(id)", enumerate_start)
        enumerate_body = payload[enumerate_start:enumerate_end]
        self.assertNotIn("CharacterCreateClassButton", enumerate_body)

    def test_native_talent_bundle_is_identical_in_root_and_locale_archives(self):
        with tempfile.TemporaryDirectory() as tmp_name:
            work = Path(tmp_name)
            for index, name in enumerate(DBC_NAMES):
                (work / name).write_bytes(f"dbc-{index}-{name}".encode("utf-8"))

            root_files, locale_files = build_archive_files(work)
            shared = set(root_files) & set(locale_files)
            expected = {
                f"DBFilesClient\\{name}" for name in ROOT_SHARED_DBCS
            }

            self.assertEqual(shared, expected)
            self.assertEqual(
                ROOT_SHARED_DBCS,
                ("TalentTab.dbc", "Talent.dbc", "Spell.dbc"),
            )
            for internal_name in expected:
                self.assertEqual(root_files[internal_name], locale_files[internal_name])

    def test_spell_icon_is_source_only(self):
        self.assertIn("SpellIcon.dbc", DBC_SOURCE_NAMES)
        self.assertNotIn("SpellIcon.dbc", DBC_NAMES)
        self.assertNotIn("SpellIcon.dbc", ROOT_SHARED_DBCS)

    def test_mpq_writer_emits_v1_archive_and_listfile_block(self):
        payload = build_mpq({"Interface\\GlueXML\\Test.lua": b"print('ok')\n"})
        self.assertTrue(payload.startswith(b"MPQ\x1a"))
        self.assertIn(b"print('ok')", payload)
        self.assertIn(b"Interface\\GlueXML\\Test.lua\r\n", payload)
        header = struct.unpack_from("<4sIIHHIIII", payload, 0)
        self.assertEqual(header[-1], 2)


if __name__ == "__main__":
    unittest.main()
