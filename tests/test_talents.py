from __future__ import annotations

import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import ADVENTURER_CLASS_MASK, DBC, u32, set_u32  # noqa: E402
from talents import (  # noqa: E402
    SPELL_DESCRIPTION_START,
    SPELL_EFFECT_APPLY_AURA_FIELDS,
    SPELL_EFFECT_BASEPOINT_FIELDS,
    SPELL_EFFECT_FIELDS,
    SPELL_EFFECT_MISC_VALUE_FIELDS,
    SPELL_EFFECT_TRIGGER_SPELL_FIELDS,
    SPELL_ICON_FIELD,
    SPELL_NAME_START,
    TALENT_RANK_FIELDS,
    TALENTTAB_CLASS_MASK_FIELD,
    TALENTTAB_ORDER_FIELD,
    custom_spell_id,
    custom_talent_id,
    load_spec,
    patch_talent_directory,
    resolve_existing_icon_ids,
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

        talent_rows = []
        spell_rows = []
        next_native_spell = 10000
        seen_source_talents: set[int] = set()
        for definition in self.spec["talents"]:
            source_talent = int(definition["source_talent_id"])
            if source_talent in seen_source_talents:
                continue
            seen_source_talents.add(source_talent)

            effect_lengths = [len(values) for values in definition.get("effect_values", {}).values()]
            rank_count = max(effect_lengths) if effect_lengths else (3 if definition.get("spell_source_id") else 2)
            rank_ids = list(range(next_native_spell, next_native_spell + rank_count))
            next_native_spell += rank_count
            values = {
                0: source_talent,
                1: 999,
                2: 9,
                3: 3,
                13: 1234,
                16: 4,
                20: 5678,
                21: 99,
                22: 88,
            }
            for rank_index, spell_id in enumerate(rank_ids):
                values[4 + rank_index] = spell_id
                spell_values = {0: spell_id, 4: 0x11 + rank_index, 133: 1, 225: 1}
                if definition["key"] == "shield_discipline":
                    spell_values.update({
                        71: 6,
                        72: 6,
                        80: rank_index,
                        81: 4,
                        95: 51,
                        96: 42,
                        116: 20000 + rank_index,
                    })
                spell_rows.append(row(234, spell_values))
            talent_rows.append(row(23, values))

        # Troll Regeneration source mechanic used by Cicatrization.
        spell_rows.append(row(234, {
            0: 20555,
            4: 0x33,
            71: 6,
            72: 6,
            80: 9,
            81: 9,
            95: 88,
            96: 89,
            133: 1,
            225: 1,
        }))

        # Battle Stance Passive gives us a stock passive SPELL_AURA_MOD_THREAT
        # mechanic. Guardian rewrites its scalar and school mask.
        spell_rows.append(row(234, {
            0: 21156,
            4: 0x44,
            71: 6,
            80: 0,
            95: 10,
            110: 127,
            133: 1,
            225: 1,
        }))

        write_dbc(self.dbc_dir / "Talent.dbc", 23, talent_rows)
        write_dbc(self.dbc_dir / "Spell.dbc", 234, spell_rows)

        # Stock SpellIcon rows. Adventurer resolves these by existing Blizzard names.
        icon_strings = bytearray(b"\0")
        icon_rows = []
        for icon_id, name in (
            (501, "ability_warrior_intensifyrage"),
            (502, "ability_warrior_secondwind"),
            (503, "Spell_deathknight_bloodboil"),
            (504, "inv_misc_bone_03"),
        ):
            path = f"Interface\\Icons\\{name}".encode() + b"\0"
            offset = len(icon_strings)
            icon_strings.extend(path)
            icon_rows.append(row(2, {0: icon_id, 1: offset}))
        write_dbc(self.dbc_dir / "SpellIcon.dbc", 2, icon_rows, bytes(icon_strings))

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

    def test_guardian_columns_and_early_rows_have_clear_identity(self) -> None:
        definitions = {definition["key"]: definition for definition in self.spec["talents"]}

        self.assertEqual(definitions["guardian_strength"]["icon"], "ability_warrior_secondwind")
        self.assertEqual((definitions["shield_discipline"]["row"], definitions["shield_discipline"]["col"]), (2, 3))
        self.assertEqual((definitions["threatening_presence"]["row"], definitions["threatening_presence"]["col"]), (3, 2))
        self.assertNotIn("shield_mastery", definitions)
        self.assertNotIn("arcane_deflection", definitions)
        self.assertNotIn("disarming_mastery", definitions)

        for key in ("shield_discipline", "bulwark", "retaliating_shield", "perfect_block"):
            self.assertEqual(definitions[key]["col"], 3, key)
        self.assertEqual(definitions["retaliating_shield"]["requires"], "shield_discipline")

    def test_clones_owned_spell_ids_and_localizes_names(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")

        talent = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, 0))
        rank_ids = [u32(talent, f) for f in TALENT_RANK_FIELDS if u32(talent, f)]
        self.assertEqual(rank_ids, [custom_spell_id(self.spec, 0, 0), custom_spell_id(self.spec, 0, 1)])

        spell = next(r for r in spells.records if u32(r, 0) == rank_ids[0])
        self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START)), "Tenacity")
        self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START + 7)), "Tenacidad")
        self.assertEqual(u32(spell, 4), 0x11)
        self.assertEqual(u32(spell, 225), 1)

    def test_uses_existing_stock_icons_and_cicatrization_mechanics(self) -> None:
        original_spell_icon = (self.dbc_dir / "SpellIcon.dbc").read_bytes()
        expected_icon_ids = resolve_existing_icon_ids(self.dbc_dir / "SpellIcon.dbc", self.spec)
        self.assertEqual(
            {k: expected_icon_ids[k] for k in (0, 1, 2, 6)},
            {0: 501, 1: 502, 2: 503, 6: 504},
        )

        patch_talent_directory(self.dbc_dir)
        self.assertEqual((self.dbc_dir / "SpellIcon.dbc").read_bytes(), original_spell_icon)

        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")

        for index, icon_id in ((0, 501), (1, 502), (2, 503), (6, 504)):
            talent = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, index))
            rank_ids = [u32(talent, f) for f in TALENT_RANK_FIELDS if u32(talent, f)]
            for spell_id in rank_ids:
                spell = next(r for r in spells.records if u32(r, 0) == spell_id)
                self.assertEqual(u32(spell, SPELL_ICON_FIELD), icon_id)

        cicatrization = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, 2))
        rank_ids = [u32(cicatrization, f) for f in TALENT_RANK_FIELDS if u32(cicatrization, f)]
        self.assertEqual(rank_ids, [290020, 290021, 290022])
        for spell_id, displayed_value in zip(rank_ids, (5, 10, 15)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, 4), 0x33)
            self.assertEqual(u32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), displayed_value - 1)
            self.assertEqual(u32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[1]), displayed_value - 1)
            self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START + 7)), "Cicatrización")

    def test_shield_discipline_doubles_block_and_removes_rage_proc(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")

        index = next(i for i, definition in enumerate(self.spec["talents"]) if definition["key"] == "shield_discipline")
        shield_discipline = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, index))
        rank_ids = [u32(shield_discipline, f) for f in TALENT_RANK_FIELDS if u32(shield_discipline, f)]
        self.assertEqual(rank_ids, [custom_spell_id(self.spec, index, i) for i in range(5)])

        for spell_id, displayed_value in zip(rank_ids, (2, 4, 6, 8, 10)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), displayed_value - 1)
            self.assertEqual(u32(spell, SPELL_EFFECT_FIELDS[1]), 0)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[1]), 0)
            self.assertEqual(u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[1]), 0)
            self.assertEqual(
                dbc_string(spells, u32(spell, SPELL_DESCRIPTION_START + 7)),
                "Aumenta un $s1% tu probabilidad de bloquear ataques con un escudo.",
            )

    def test_threatening_presence_is_physical_threat_only(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        index = next(i for i, definition in enumerate(self.spec["talents"]) if definition["key"] == "threatening_presence")
        threatening = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, index))
        rank_ids = [u32(threatening, f) for f in TALENT_RANK_FIELDS if u32(threatening, f)]
        self.assertEqual(rank_ids, [custom_spell_id(self.spec, index, i) for i in range(3)])

        for spell_id, displayed_value in zip(rank_ids, (5, 10, 15)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[0]), 10)
            self.assertEqual(u32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), displayed_value - 1)
            self.assertEqual(u32(spell, SPELL_EFFECT_MISC_VALUE_FIELDS[0]), 1)
            self.assertEqual(
                dbc_string(spells, u32(spell, SPELL_DESCRIPTION_START + 7)),
                "Aumenta un $s1% la amenaza generada por tus ataques y facultades físicas.",
            )

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
                required_talent = next(
                    r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, required_index)
                )
                required_rank_count = sum(1 for field in TALENT_RANK_FIELDS if u32(required_talent, field))
                self.assertEqual(u32(generated, 13), custom_talent_id(self.spec, required_index))
                self.assertEqual(u32(generated, 16), required_rank_count - 1)
            self.assertEqual(u32(generated, 20), 0)
            self.assertEqual(u32(generated, 21), 0)
            self.assertEqual(u32(generated, 22), 0)

    def test_rebuild_purges_retired_adventurer_ids(self) -> None:
        patch_talent_directory(self.dbc_dir)

        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        talents.records.append(row(23, {0: 5999, 1: 5000, 2: 3, 3: 0, 4: 299999}))
        (self.dbc_dir / "Talent.dbc").write_bytes(talents.to_bytes())

        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        spells.records.append(row(234, {0: 299999, 71: 6, 95: 10}))
        (self.dbc_dir / "Spell.dbc").write_bytes(spells.to_bytes())

        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        self.assertFalse(any(u32(r, 0) == 5999 for r in talents.records))
        self.assertFalse(any(u32(r, 0) == 299999 for r in spells.records))

    def test_generation_is_idempotent(self) -> None:
        first = patch_talent_directory(self.dbc_dir)
        self.assertTrue(all(first.values()))
        snapshots = {
            name: (self.dbc_dir / name).read_bytes()
            for name in ("TalentTab.dbc", "Talent.dbc", "Spell.dbc", "SpellIcon.dbc")
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
