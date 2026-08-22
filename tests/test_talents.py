from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import ADVENTURER_CLASS_MASK, DBC, u32, set_u32  # noqa: E402
from talents import (  # noqa: E402
    SPELL_NAME_START,
    TALENT_RANK_FIELDS,
    TALENTTAB_CLASS_MASK_FIELD,
    TALENTTAB_ORDER_FIELD,
    custom_spell_id,
    custom_talent_id,
    load_spec,
    patch_talent_directory,
)


def write_dbc(path: Path, fields: int, records: list[bytearray], strings: bytes = b"\0") -> None:
    record_size = fields * 4
    header = struct.pack("<4sIIII", b"WDBC", len(records), fields, record_size, len(strings))
    path.write_bytes(header + b"".join(records) + strings)


def row(fields: int, values: dict[int, int]) -> bytearray:
    result = bytearray(fields * 4)
    for field, value in values.items():
        set_u32(result, field, value)
    return result


def dbc_string(dbc: DBC, offset: int) -> str:
    raw = bytes(dbc.strings)
    end = raw.find(b"\0", offset)
    if end < 0:
        raise AssertionError(f"unterminated string at offset {offset}")
    return raw[offset:end].decode("utf-8")


class TalentGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dbc_dir = Path(self.tmp.name)
        self.spec = load_spec()

        # Stock source tabs referenced by the authored spec. Only the raw fields
        # that Adventurer cares about need meaningful fixture values.
        tabs = []
        for index, tab in enumerate(self.spec["tabs"]):
            source_id = int(tab["source_tab_id"])
            tabs.append(row(24, {
                0: source_id,
                18: 100 + index,
                20: 1 << index,
                22: index,
                23: 0,
            }))
        write_dbc(self.dbc_dir / "TalentTab.dbc", 24, tabs)

        # Give every source talent two ranks. The actual production transform
        # copies however many stock ranks are present; this fixture deliberately
        # exercises multi-rank cloning without embedding retail DBC data in tests.
        talent_rows = []
        spell_rows = []
        next_native_spell = 10000
        for definition in self.spec["talents"]:
            source_talent = int(definition["source_talent_id"])
            first_spell = next_native_spell
            second_spell = next_native_spell + 1
            next_native_spell += 2
            talent_rows.append(row(23, {
                0: source_talent,
                1: 999,
                2: 9,
                3: 3,
                4: first_spell,
                5: second_spell,
                13: 1234,  # prove inherited prerequisite is removed
                16: 4,
                20: 5678,  # prove inherited required spell is removed
                21: 99,
                22: 88,
            }))
            spell_rows.append(row(234, {0: first_spell, 4: 0x11, 225: 1}))
            spell_rows.append(row(234, {0: second_spell, 4: 0x22, 225: 1}))

        write_dbc(self.dbc_dir / "Talent.dbc", 23, talent_rows)
        write_dbc(self.dbc_dir / "Spell.dbc", 234, spell_rows)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_builds_three_adventurer_tabs_and_guardian_tree(self) -> None:
        result = patch_talent_directory(self.dbc_dir)
        self.assertTrue(all(result.values()))

        tabs = DBC.read(self.dbc_dir / "TalentTab.dbc")
        for tab in self.spec["tabs"]:
            generated = next(r for r in tabs.records if u32(r, 0) == int(tab["id"]))
            self.assertEqual(u32(generated, TALENTTAB_CLASS_MASK_FIELD), ADVENTURER_CLASS_MASK)
            self.assertEqual(u32(generated, TALENTTAB_ORDER_FIELD), int(tab["order"]))

        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        guardian_id = int(next(t for t in self.spec["tabs"] if t["key"] == "guardian")["id"])
        generated_rows = [r for r in talents.records if 5000 <= u32(r, 0) < 6000]
        self.assertEqual(len(generated_rows), len(self.spec["talents"]))
        self.assertTrue(all(u32(r, 1) == guardian_id for r in generated_rows))

    def test_clones_owned_spell_ids_and_localizes_names(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")

        first = self.spec["talents"][0]
        talent = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, 0))
        rank_ids = [u32(talent, f) for f in TALENT_RANK_FIELDS if u32(talent, f)]
        self.assertEqual(rank_ids, [custom_spell_id(self.spec, 0, 0), custom_spell_id(self.spec, 0, 1)])

        spell = next(r for r in spells.records if u32(r, 0) == rank_ids[0])
        self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START)), first["enUS"])
        self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START + 7)), first["esMX"])

        # Mechanical data survives the clone.
        self.assertEqual(u32(spell, 4), 0x11)
        self.assertEqual(u32(spell, 225), 1)

    def test_replaces_stock_prerequisites_with_adventurer_prerequisites(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        key_to_index = {definition["key"]: i for i, definition in enumerate(self.spec["talents"])}

        for index, definition in enumerate(self.spec["talents"]):
            generated = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, index))
            if "requires" not in definition:
                self.assertEqual(u32(generated, 13), 0)
                self.assertEqual(u32(generated, 16), 0)
            else:
                required_index = key_to_index[definition["requires"]]
                self.assertEqual(u32(generated, 13), custom_talent_id(self.spec, required_index))
                # The fixture has two ranks, so requiring a fully ranked parent is rank index 1.
                self.assertEqual(u32(generated, 16), 1)
            self.assertEqual(u32(generated, 20), 0)
            self.assertEqual(u32(generated, 21), 0)
            self.assertEqual(u32(generated, 22), 0)

    def test_generation_is_idempotent(self) -> None:
        first = patch_talent_directory(self.dbc_dir)
        self.assertTrue(all(first.values()))
        snapshots = {
            name: (self.dbc_dir / name).read_bytes()
            for name in ("TalentTab.dbc", "Talent.dbc", "Spell.dbc")
        }

        second = patch_talent_directory(self.dbc_dir)
        self.assertEqual(second, {
            "TalentTab.dbc": False,
            "Talent.dbc": False,
            "Spell.dbc": False,
        })
        for name, before in snapshots.items():
            self.assertEqual((self.dbc_dir / name).read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
