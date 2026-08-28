from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import ADVENTURER_CLASS_MASK, DBC, set_u32, u32  # noqa: E402
from spell_rank_tabs import (  # noqa: E402
    SPELL_COMPONENT_FIELDS,
    load_server_rank_chains,
    patch_component_free_drafted_spells,
    patch_server_rank_tabs,
)
from subclasses import (  # noqa: E402
    SLA_CLASS_MASK,
    SLA_EXCLUDE_CLASS,
    SLA_SKILL_LINE,
    SLA_SPELL,
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

SPELL_RANKS = """CREATE TABLE `spell_ranks` (
  `first_spell_id` int unsigned NOT NULL,
  `spell_id` int unsigned NOT NULL,
  `rank` tinyint unsigned NOT NULL
);
INSERT INTO `spell_ranks` VALUES
(100,100,1),
(100,101,2),
(100,102,3);
"""


def make_row(row_id: int, skill_line: int, spell_id: int) -> bytearray:
    row = bytearray(14 * 4)
    set_u32(row, 0, row_id)
    set_u32(row, SLA_SKILL_LINE, skill_line)
    set_u32(row, SLA_SPELL, spell_id)
    return row


def make_spell(spell_id: int, component_value: int) -> bytearray:
    row = bytearray(234 * 4)
    set_u32(row, 0, spell_id)
    for field in SPELL_COMPONENT_FIELDS:
        set_u32(row, field, component_value)
    return row


class ServerRankTabTests(unittest.TestCase):
    def test_server_rank_source_expands_every_spell_in_chain(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            ranks = Path(td) / "spell_ranks.sql"
            ranks.write_text(SPELL_RANKS, encoding="utf-8")
            chains = load_server_rank_chains(ranks)
            self.assertEqual(chains[100], (100, 101, 102))
            self.assertEqual(chains[101], (100, 101, 102))
            self.assertEqual(chains[102], (100, 101, 102))

    def test_automatic_higher_ranks_receive_same_custom_skill_line(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            dbc_path = root / "SkillLineAbility.dbc"
            ranks_path = root / "spell_ranks.sql"
            ranks_path.write_text(SPELL_RANKS, encoding="utf-8")

            # Rank 1 is the drafted seed. Rank 2 has a stock row but no
            # SupercededBySpell relation, and rank 3 has no SLA row at all.
            # This reproduces the mismatch between client DBC metadata and the
            # server's SpellMgr spell_ranks chain.
            DBC(
                fields=14,
                record_size=56,
                records=[
                    make_row(1, 26, 100),
                    make_row(2, 26, 101),
                ],
                strings=bytearray(b"\0"),
            ).write(dbc_path)

            patch_skill_line_abilities(dbc_path, CARDS, SPEC)
            self.assertTrue(
                patch_server_rank_tabs(dbc_path, ranks_path, CARDS, SPEC)
            )
            dbc = DBC.read(dbc_path)

            for spell_id in (100, 101, 102):
                custom = [
                    row
                    for row in dbc.records
                    if u32(row, SLA_SPELL) == spell_id
                    and u32(row, SLA_SKILL_LINE) == 900
                ]
                self.assertEqual(len(custom), 1, spell_id)
                self.assertEqual(u32(custom[0], SLA_CLASS_MASK), ADVENTURER_CLASS_MASK)

            rank_two_stock = next(row for row in dbc.records if u32(row, 0) == 2)
            self.assertEqual(
                u32(rank_two_stock, SLA_EXCLUDE_CLASS) & ADVENTURER_CLASS_MASK,
                ADVENTURER_CLASS_MASK,
            )

    def test_all_drafted_active_ranks_are_component_free(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            spell_path = root / "Spell.dbc"
            ranks_path = root / "spell_ranks.sql"
            ranks_path.write_text(SPELL_RANKS, encoding="utf-8")

            DBC(
                fields=234,
                record_size=936,
                records=[
                    make_spell(100, 11),
                    make_spell(101, 12),
                    make_spell(102, 13),
                    make_spell(999, 99),
                ],
                strings=bytearray(b"\0"),
            ).write(spell_path)

            self.assertTrue(
                patch_component_free_drafted_spells(
                    spell_path, ranks_path, CARDS, SPEC
                )
            )
            dbc = DBC.read(spell_path)
            rows = {u32(row, 0): row for row in dbc.records}

            for spell_id in (100, 101, 102):
                for field in SPELL_COMPONENT_FIELDS:
                    self.assertEqual(u32(rows[spell_id], field), 0, (spell_id, field))

            # The rule is scoped to SpellDraft abilities: unrelated native spells
            # retain their original component/tool metadata.
            for field in SPELL_COMPONENT_FIELDS:
                self.assertEqual(u32(rows[999], field), 99, field)

            self.assertFalse(
                patch_component_free_drafted_spells(
                    spell_path, ranks_path, CARDS, SPEC
                )
            )


if __name__ == "__main__":
    unittest.main()
