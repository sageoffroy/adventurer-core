from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import (  # noqa: E402
    ADVENTURER_CLASS,
    ADVENTURER_STARTER_ITEMS,
    CHARSTART_FULL_RECORD_SIZE,
    CHR_CLASS_NAME_BLOCKS,
    DBC,
    LOCALE_ENUS,
    LOCALE_ESMX,
    PLAYABLE_RACES,
    RACE_NATIVE_SKILLS,
    patch_directory,
    read_outfit_entry,
    set_u32,
    u32,
    write_outfit_entry,
)


def write_dbc(path: Path, fields: int, record_size: int, records: list[bytearray], strings=b"\0"):
    DBC(fields, record_size, records, bytearray(strings)).write(path)


def make_u32_record(fields: int) -> bytearray:
    return bytearray(fields * 4)


def cstring(strings: bytes, offset: int) -> str:
    end = strings.index(b"\0", offset)
    return strings[offset:end].decode("utf-8")


class DBCTests(unittest.TestCase):
    def make_fixture(self, root: Path):
        root.mkdir(parents=True, exist_ok=True)

        classes = []
        for klass in (1, 2, 3, 4, 5, 6, 7, 8, 9, 11):
            row = make_u32_record(60)
            set_u32(row, 0, klass)
            set_u32(row, 2, 0)
            classes.append(row)
        write_dbc(root / "ChrClasses.dbc", 60, 240, classes)

        base = [bytearray((1, 1)), bytearray((2, 1)), bytearray((10, 2))]
        write_dbc(root / "CharBaseInfo.dbc", 2, 2, base)

        outfits = []
        row_id = 1
        inv_types = (13, 14, 15, 24)
        for race in PLAYABLE_RACES:
            for gender in (0, 1):
                row = bytearray(CHARSTART_FULL_RECORD_SIZE)
                set_u32(row, 0, row_id)
                row_id += 1
                row[4], row[5], row[6] = race, 1, gender
                for i, (item, inv) in enumerate(zip(ADVENTURER_STARTER_ITEMS, inv_types)):
                    write_outfit_entry(row, i, item, 5000 + item, inv)
                write_outfit_entry(row, 4, 100000 + race * 10 + gender, 1, 4)
                outfits.append(row)
        write_dbc(root / "CharStartOutfit.dbc", 74, CHARSTART_FULL_RECORD_SIZE, outfits)

        skills = []
        next_id = 1
        for race, race_skills in RACE_NATIVE_SKILLS.items():
            for skill in race_skills:
                row = make_u32_record(8)
                set_u32(row, 0, next_id); next_id += 1
                set_u32(row, 1, skill)
                set_u32(row, 2, 1 << (race - 1))
                set_u32(row, 3, 1)
                skills.append(row)
        for skill in (43, 163, 762, 777):
            row = make_u32_record(8)
            set_u32(row, 0, next_id); next_id += 1
            set_u32(row, 1, skill)
            set_u32(row, 2, 1)
            set_u32(row, 3, 1)
            skills.append(row)
        write_dbc(root / "SkillRaceClassInfo.dbc", 8, 32, skills)

    def test_full_patch_and_locales_are_idempotent(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_fixture(root)
            first = patch_directory(root)
            self.assertTrue(all(first.values()))

            chrclasses = DBC.read(root / "ChrClasses.dbc")
            adventurer = next(r for r in chrclasses.records if u32(r, 0) == ADVENTURER_CLASS)
            strings = bytes(chrclasses.strings)
            self.assertEqual(cstring(strings, u32(adventurer, CHR_CLASS_NAME_BLOCKS[0] + LOCALE_ENUS)), "Adventurer")
            self.assertEqual(cstring(strings, u32(adventurer, CHR_CLASS_NAME_BLOCKS[0] + LOCALE_ESMX)), "Aventurero")
            self.assertEqual(cstring(strings, u32(adventurer, CHR_CLASS_NAME_BLOCKS[1] + LOCALE_ESMX)), "Aventurera")

            base = DBC.read(root / "CharBaseInfo.dbc")
            self.assertEqual([(r[0], r[1]) for r in base.records], [(race, 10) for race in PLAYABLE_RACES])

            outfits = DBC.read(root / "CharStartOutfit.dbc")
            adventurer_rows = [r for r in outfits.records if r[5] == 10]
            self.assertEqual(len(adventurer_rows), 20)
            for row in adventurer_rows:
                ids = {read_outfit_entry(row, i)[0] for i in range(24)}
                self.assertTrue(set(ADVENTURER_STARTER_ITEMS).issubset(ids))

            skills = DBC.read(root / "SkillRaceClassInfo.dbc")
            classless_43 = [r for r in skills.records if u32(r, 1) == 43 and u32(r, 3) == 512 and u32(r, 2) == 0]
            self.assertEqual(len(classless_43), 1)

            second = patch_directory(root)
            self.assertFalse(any(second.values()))

    def test_bad_layout_aborts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.make_fixture(root)
            write_dbc(root / "ChrClasses.dbc", 59, 236, [bytearray(236)])
            with self.assertRaises(Exception):
                patch_directory(root)


if __name__ == "__main__":
    unittest.main()
