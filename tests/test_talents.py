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
    SPELL_NAME_START,
    SPELL_SCHOOL_MASK_FIELD,
    TALENT_ADD_TO_SPELLBOOK_FIELD,
    TALENT_PREREQ_TALENT_FIELDS,
    TALENT_RANK_FIELDS,
    TALENTTAB_CLASS_MASK_FIELD,
    TALENTTAB_ORDER_FIELD,
    all_source_spell_ids,
    custom_spell_id,
    custom_talent_id,
    custom_trigger_spell_id,
    dbc_string,
    i32,
    load_specs,
    patch_talent_directory,
    set_f32,
    set_i32,
    talent_source_spell_ids,
)


def write_dbc(path: Path, fields: int, records: list[bytearray], strings: bytes = b"\0") -> None:
    record_size = fields * 4
    header = struct.pack("<4sIIII", b"WDBC", len(records), fields, record_size, len(strings))
    path.write_bytes(header + b"".join(records) + strings)


def row(fields: int, values: dict[int, int] | None = None) -> bytearray:
    result = bytearray(fields * 4)
    for field, value in (values or {}).items():
        set_u32(result, field, value)
    return result


class TalentGeneratorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.dbc_dir = Path(self.tmp.name)
        self.specs = load_specs()
        self.spec = next(spec for spec in self.specs if spec.get("tab_key", "guardian") == "guardian")
        self.champion = next(spec for spec in self.specs if spec.get("tab_key") == "champion")

        tabs = []
        for index, tab in enumerate(self.spec["tabs"]):
            tabs.append(row(24, {
                0: int(tab["source_tab_id"]),
                18: 100 + index,
                20: 1 << index,
                22: index,
            }))
        write_dbc(self.dbc_dir / "TalentTab.dbc", 24, tabs)
        write_dbc(
            self.dbc_dir / "Talent.dbc",
            23,
            [row(23, {0: 5999, 1: 5000, 4: 299999}), row(23, {0: 6999, 1: 5001, 4: 309999})],
        )

        source_ids = sorted(set().union(*(all_source_spell_ids(spec) for spec in self.specs)))
        spell_rows: list[bytearray] = []
        for spell_id in source_ids:
            spell = row(234, {0: spell_id, 4: 0x11, 71: 6, 80: 0, 133: 1, 225: 1})

            # Guardian structural fixtures.
            if spell_id == 19584:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 8); set_u32(spell, 96, 133)
            if spell_id == 63650:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 135); set_u32(spell, 96, 118)
            if spell_id == 20060:
                set_u32(spell, 95, 47)
            if spell_id == 21156:
                set_u32(spell, 95, 10)
                set_i32(spell, 110, 127)
            if spell_id in {12298, 12724, 12725, 12726, 12727}:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 51); set_u32(spell, 96, 42)
                set_u32(spell, 117, 99999)
            if spell_id == 12764:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_i32(spell, 80, 9); set_i32(spell, 81, -31)
            if spell_id == 31382:
                set_u32(spell, 71, 6); set_u32(spell, 95, 87)
            if spell_id in {47294, 47295, 47296}:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 251); set_u32(spell, 96, 107)
            if spell_id in {33853, 33855, 33856}:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6); set_u32(spell, 73, 3)
                set_u32(spell, 95, 80); set_u32(spell, 96, 125)
            if spell_id == 20101:
                set_u32(spell, 208, 10); set_u32(spell, 209, 0x1234)
                set_u32(spell, 210, 0x5678); set_u32(spell, 211, 0x9ABC)
            if spell_id == 12328:
                set_u32(spell, 12, 0x1); set_u32(spell, 14, 0x2)
            if spell_id == 29593:
                set_u32(spell, 12, 0x2); set_u32(spell, 35, 50)
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 87); set_u32(spell, 96, 42); set_u32(spell, 117, 57516)
            if spell_id == 31935:
                set_u32(spell, 71, 2); set_u32(spell, 72, 6)
                set_i32(spell, 74, 97); set_i32(spell, 80, 439)
                set_u32(spell, 104, 3); set_u32(spell, 204, 26)
                set_u32(spell, 208, 10); set_u32(spell, 209, 0x1234); set_u32(spell, 225, 2)
                set_f32(spell, 77, 1.0); set_f32(spell, 229, 0.07)

            # Champion structural fixtures for the custom/sanitized mechanics.
            if spell_id in {30812, 16513, 16266, 20117}:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6); set_u32(spell, 73, 6)
                set_u32(spell, 95, 108); set_u32(spell, 96, 174); set_u32(spell, 97, 175)
            if spell_id == 20266:
                set_u32(spell, 95, 137)
            if spell_id == 13975:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 108); set_u32(spell, 96, 196)
            if spell_id == 14171:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 108); set_u32(spell, 96, 280)
            if spell_id == 20049:
                set_u32(spell, 71, 6); set_u32(spell, 95, 42); set_u32(spell, 116, 20050)
            if spell_id == 20050:
                set_u32(spell, 71, 6); set_u32(spell, 95, 79); set_i32(spell, 110, 3)
            if spell_id == 29836:
                set_u32(spell, 71, 6); set_u32(spell, 72, 6)
                set_u32(spell, 95, 42); set_u32(spell, 96, 138)
            if spell_id == 55050:
                set_u32(spell, 71, 31); set_u32(spell, 72, 31); set_u32(spell, 73, 3)
                set_i32(spell, 80, 49); set_i32(spell, 81, 24)
                set_u32(spell, 104, 2); set_u32(spell, 208, 15); set_u32(spell, 226, 1)
            if spell_id in {51627, 51628, 51629}:
                set_u32(spell, 71, 65); set_u32(spell, 95, 42); set_u32(spell, 116, 52915)
            if spell_id == 52915:
                set_u32(spell, 40, 21); set_u32(spell, 71, 6); set_u32(spell, 95, 108)
                set_u32(spell, 208, 8); set_u32(spell, 209, 0xFFFF)
            if spell_id == 46924:
                set_u32(spell, 12, 0x4); set_u32(spell, 208, 4)

            spell_rows.append(spell)

        spell_rows.extend([
            row(234, {0: 299999, 71: 6, 95: 10}),
            row(234, {0: 309999, 71: 6, 95: 10}),
        ])
        write_dbc(self.dbc_dir / "Spell.dbc", 234, spell_rows)

        icon_strings = bytearray(b"\0")
        icon_rows = []
        for icon_id, name in (
            (501, "ability_warrior_intensifyrage"),
            (502, "ability_warrior_secondwind"),
            (503, "Spell_deathknight_bloodboil"),
            (504, "ability_warstomp"),
            (505, "ability_backstab"),
            (506, "spell_nature_abolishmagic"),
            (507, "inv_gauntlets_19"),
            (508, "spell_shadow_lifedrain"),
            (509, "spell_misc_emotionangry"),
        ):
            path = f"Interface\\Icons\\{name}".encode() + b"\0"
            offset = len(icon_strings)
            icon_strings.extend(path)
            icon_rows.append(row(2, {0: icon_id, 1: offset}))
        write_dbc(self.dbc_dir / "SpellIcon.dbc", 2, icon_rows, bytes(icon_strings))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    @staticmethod
    def definition(spec: dict, key: str) -> tuple[int, dict]:
        index = next(i for i, definition in enumerate(spec["talents"]) if definition["key"] == key)
        return index, spec["talents"][index]

    @staticmethod
    def rank_ids(talent: bytearray) -> list[int]:
        return [u32(talent, field) for field in TALENT_RANK_FIELDS if u32(talent, field)]

    def generated_talent(self, talents: DBC, spec: dict, key: str) -> tuple[int, dict, bytearray]:
        index, definition = self.definition(spec, key)
        talent = next(r for r in talents.records if u32(r, 0) == custom_talent_id(spec, index))
        return index, definition, talent

    def test_builds_both_native_tabs_and_exact_tree_counts(self) -> None:
        result = patch_talent_directory(self.dbc_dir)
        self.assertTrue(all(result.values()))

        tabs = DBC.read(self.dbc_dir / "TalentTab.dbc")
        for tab in self.spec["tabs"]:
            generated = next(r for r in tabs.records if u32(r, 0) == int(tab["id"]))
            self.assertEqual(u32(generated, TALENTTAB_CLASS_MASK_FIELD), ADVENTURER_CLASS_MASK)
            self.assertEqual(u32(generated, TALENTTAB_ORDER_FIELD), int(tab["order"]))

        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        guardian = [r for r in talents.records if 5000 <= u32(r, 0) < 6000]
        champion = [r for r in talents.records if 6000 <= u32(r, 0) < 7000]
        self.assertEqual(len(guardian), 26)
        self.assertEqual(len(champion), 28)
        self.assertFalse(any(u32(r, 0) in {5999, 6999} for r in talents.records))

        for spec, expected_tab in ((self.spec, 5000), (self.champion, 5001)):
            for index, _definition in enumerate(spec["talents"]):
                talent = next(r for r in talents.records if u32(r, 0) == custom_talent_id(spec, index))
                self.assertEqual(u32(talent, 1), expected_tab)

    def test_guardian_redesign_generates_the_custom_mechanics(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")

        _index, _definition, vitality = self.generated_talent(talents, self.spec, "vitality")
        for spell_id, size, health in zip(self.rank_ids(vitality), (3, 6, 9, 12, 15), (2, 4, 6, 8, 10)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, SPELL_EFFECT_FIELDS[0]), 6)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[0]), 61)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), size - 1)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[1]), health - 1)

        index, definition, talent = self.generated_talent(talents, self.spec, "steady_footing")
        self.assertEqual(definition["icon"], "ability_warstomp")
        for spell_id, speed, defense in zip(self.rank_ids(talent), (15, 30), (2, 4)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual([u32(spell, f) for f in SPELL_EFFECT_APPLY_AURA_FIELDS], [33, 51, 47])
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), speed - 1)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[1]), defense - 1)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[2]), defense - 1)

        _index, _definition, consistency = self.generated_talent(talents, self.spec, "consistency")
        for spell_id in self.rank_ids(consistency):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[0]), 4)  # runtime marker
            self.assertEqual(u32(spell, SPELL_EFFECT_FIELDS[1]), 0)

        _index, _definition, prayer = self.generated_talent(talents, self.spec, "prayer")
        for spell_id, value in zip(self.rank_ids(prayer), (-5, -10)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), value - 1)
            for field in (208, 209, 210, 211):
                self.assertEqual(u32(spell, field), 0)

        _index, _definition, demolition = self.generated_talent(talents, self.spec, "demolition_machine")
        for spell_id, proc in zip(self.rank_ids(demolition), (25, 50, 75)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, 35), proc)
            self.assertEqual(u32(spell, SPELL_EFFECT_FIELDS[0]), 0)
            self.assertNotEqual(u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[1]), 0)

        index, _definition, throw = self.generated_talent(talents, self.spec, "throw_shield")
        self.assertEqual(index, 24)
        spell = next(r for r in spells.records if u32(r, 0) == custom_spell_id(self.spec, index, 0))
        self.assertEqual(u32(spell, 0), 290240)
        self.assertEqual(u32(spell, SPELL_SCHOOL_MASK_FIELD), 1)
        self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), -1)
        self.assertEqual(u32(spell, 104), 3)

        _index, impact_definition, impact = self.generated_talent(talents, self.spec, "painful_impacts")
        self.assertEqual(impact_definition["icon"], "ability_backstab")
        for spell_id, value in zip(self.rank_ids(impact), (5, 10, 15)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), value - 1)
            self.assertEqual(i32(spell, SPELL_EFFECT_MISC_VALUE_FIELDS[0]), 1)

    def test_champion_heart_strike_uses_rage_and_has_no_dk_resource(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        index, _definition, talent = self.generated_talent(talents, self.champion, "heart_strike")
        spell_id = custom_spell_id(self.champion, index, 0)
        self.assertEqual(self.rank_ids(talent), [spell_id])
        spell = next(r for r in spells.records if u32(r, 0) == spell_id)
        self.assertEqual(u32(spell, 41), 1)  # Rage.
        self.assertEqual(u32(spell, 42), 150)  # 15 Rage in Spell.dbc units.
        self.assertEqual(u32(spell, 226), 0)
        self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), 99)
        self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[1]), 74)
        self.assertEqual(u32(spell, SPELL_EFFECT_FIELDS[2]), 0)
        for field in (208, 209, 210, 211):
            self.assertEqual(u32(spell, field), 0)

    def test_champion_find_weakness_is_global_damage_percent(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        _index, _definition, talent = self.generated_talent(talents, self.champion, "find_weakness")
        for spell_id, value in zip(self.rank_ids(talent), (2, 4, 6)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[0]), 79)
            self.assertEqual(i32(spell, SPELL_EFFECT_MISC_VALUE_FIELDS[0]), 127)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), value - 1)

    def test_champion_trigger_children_are_adventurer_owned(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")

        for key, values, aura, misc in (
            ("blood_vengeance", (1, 2, 3), 79, 1),
            ("turn_the_tables", (2, 4, 6), 52, None),
        ):
            index, definition, talent = self.generated_talent(talents, self.champion, key)
            slot = int(definition.get("trigger_spell_slot", 0))
            for rank_index, (parent_id, value) in enumerate(zip(self.rank_ids(talent), values)):
                parent = next(r for r in spells.records if u32(r, 0) == parent_id)
                child_id = custom_trigger_spell_id(self.champion, index, rank_index)
                self.assertEqual(u32(parent, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[slot]), child_id)
                child = next(r for r in spells.records if u32(r, 0) == child_id)
                self.assertEqual(u32(child, SPELL_EFFECT_APPLY_AURA_FIELDS[0]), aura)
                self.assertEqual(i32(child, SPELL_EFFECT_BASEPOINT_FIELDS[0]), value - 1)
                if misc is not None:
                    self.assertEqual(i32(child, SPELL_EFFECT_MISC_VALUE_FIELDS[0]), misc)
                if key == "turn_the_tables":
                    for field in range(122, 131):
                        self.assertEqual(u32(child, field), 0)
                    for field in (208, 209, 210, 211):
                        self.assertEqual(u32(child, field), 0)

    def test_champion_prerequisites_and_active_spellbook_flags(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        expected_requires = {
            "close_quarters_combat": "dual_wield_specialization",
            "hemorrhage": "serrated_blades",
            "blood_gorged": "heart_strike",
            "bladestorm": "blood_gorged",
        }
        active = {"hemorrhage", "ancestral_rage", "heart_strike", "bladestorm"}

        for key, required in expected_requires.items():
            _index, definition, talent = self.generated_talent(talents, self.champion, key)
            required_index, _ = self.definition(self.champion, required)
            self.assertEqual(u32(talent, TALENT_PREREQ_TALENT_FIELDS[0]), custom_talent_id(self.champion, required_index))
            self.assertEqual(definition["requires"], required)

        for definition in self.champion["talents"]:
            _index, _definition, talent = self.generated_talent(talents, self.champion, definition["key"])
            self.assertEqual(
                u32(talent, TALENT_ADD_TO_SPELLBOOK_FIELD),
                1 if definition["key"] in active else 0,
                definition["key"],
            )

    def test_custom_descriptions_do_not_name_other_classes(self) -> None:
        patch_talent_directory(self.dbc_dir)
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        forbidden = (
            "palad", "guerrer", "pícar", "caballero de la muerte",
            "sacerdot", "cazador", "chamán", "druid", "mago", "brujo",
        )
        for spec in self.specs:
            for index, definition in enumerate(spec["talents"]):
                if definition.get("reuse_native_spells"):
                    continue
                for rank_index in range(len(talent_source_spell_ids(definition))):
                    spell_id = custom_spell_id(spec, index, rank_index)
                    spell = next(r for r in spells.records if u32(r, 0) == spell_id)
                    description = dbc_string(spells, u32(spell, SPELL_DESCRIPTION_START + 7)).casefold()
                    for token in forbidden:
                        self.assertNotIn(token.casefold(), description, definition["key"])

    def test_rebuild_purges_stale_rows_and_is_idempotent(self) -> None:
        first = patch_talent_directory(self.dbc_dir)
        self.assertTrue(all(first.values()))
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        self.assertFalse(any(u32(r, 0) in {5999, 6999} for r in talents.records))
        self.assertFalse(any(u32(r, 0) in {299999, 309999} for r in spells.records))

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
