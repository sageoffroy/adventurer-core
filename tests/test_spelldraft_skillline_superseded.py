from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import ADVENTURER_CLASS_MASK, DBC, set_u32, u32  # noqa: E402
from subclasses import (  # noqa: E402
    SLA_ACQUIRE_METHOD,
    SLA_CLASS_MASK,
    SLA_EXCLUDE_CLASS,
    SLA_MIN_SKILL_LINE_RANK,
    SLA_SKILL_LINE,
    SLA_SPELL,
    SLA_SUPERCEDED_BY,
    patch_skill_line_abilities,
)


CARDS = """id;key;type;source_level;rarity;weight;rank_grants;requires_all;requires_any;unlocks;replaces_previous;name
1;test_spell;active;1;common;100;100;;;;0;Test Spell
"""

SPEC = {
    "schema": 1,
    "subclasses": [
        {"key": "mercenary", "skill_line_id": 900, "card_ids": [1]},
        {"key": "explorer", "skill_line_id": 901, "card_ids": []},
        {"key": "spellcaster", "skill_line_id": 902, "card_ids": []},
        {"key": "illuminated", "skill_line_id": 903, "card_ids": []},
    ],
}


def make_row(
    row_id: int,
    skill_line: int,
    spell_id: int,
    superseded_by: int = 0,
    acquire_method: int = 0,
) -> bytearray:
    row = bytearray(14 * 4)
    set_u32(row, 0, row_id)
    set_u32(row, SLA_SKILL_LINE, skill_line)
    set_u32(row, SLA_SPELL, spell_id)
    set_u32(row, SLA_SUPERCEDED_BY, superseded_by)
    set_u32(row, SLA_ACQUIRE_METHOD, acquire_method)
    return row


class SkillLineSupersededTests(unittest.TestCase):
    def test_terminal_superseded_spell_does_not_need_its_own_row(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "SkillLineAbility.dbc"
            DBC(
                fields=14,
                record_size=56,
                records=[make_row(1, 26, 100, superseded_by=101, acquire_method=2)],
                strings=bytearray(b"\0"),
            ).write(path)

            self.assertTrue(patch_skill_line_abilities(path, CARDS, SPEC))
            dbc = DBC.read(path)

            stock = next(row for row in dbc.records if u32(row, 0) == 1)
            self.assertEqual(u32(stock, SLA_EXCLUDE_CLASS), ADVENTURER_CLASS_MASK)
            self.assertEqual(u32(stock, SLA_ACQUIRE_METHOD), 2)

            custom = [
                row
                for row in dbc.records
                if u32(row, SLA_SPELL) == 100 and u32(row, SLA_SKILL_LINE) == 900
            ]
            self.assertEqual(len(custom), 1)
            self.assertEqual(u32(custom[0], SLA_CLASS_MASK), ADVENTURER_CLASS_MASK)
            self.assertEqual(u32(custom[0], SLA_SUPERCEDED_BY), 101)
            self.assertEqual(u32(custom[0], SLA_ACQUIRE_METHOD), 0)
            self.assertEqual(u32(custom[0], SLA_MIN_SKILL_LINE_RANK), 0)

            self.assertFalse(any(u32(row, SLA_SPELL) == 101 for row in dbc.records))

    def test_actual_drafted_seed_without_source_row_gets_minimal_custom_row(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "SkillLineAbility.dbc"
            DBC(
                fields=14,
                record_size=56,
                records=[make_row(1, 26, 999, acquire_method=2)],
                strings=bytearray(b"\0"),
            ).write(path)

            self.assertTrue(patch_skill_line_abilities(path, CARDS, SPEC))
            dbc = DBC.read(path)

            custom = [
                row
                for row in dbc.records
                if u32(row, SLA_SPELL) == 100 and u32(row, SLA_SKILL_LINE) == 900
            ]
            self.assertEqual(len(custom), 1)
            self.assertEqual(u32(custom[0], SLA_CLASS_MASK), ADVENTURER_CLASS_MASK)
            self.assertEqual(u32(custom[0], SLA_ACQUIRE_METHOD), 0)
            self.assertEqual(u32(custom[0], SLA_MIN_SKILL_LINE_RANK), 0)
            self.assertEqual(u32(custom[0], SLA_SUPERCEDED_BY), 0)


if __name__ == "__main__":
    unittest.main()
