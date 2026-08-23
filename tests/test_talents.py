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
    SPELL_EFFECT_TRIGGER_SPELL_FIELDS,
    SPELL_NAME_START,
    SPELL_SCHOOL_MASK_FIELD,
    TALENT_ADD_TO_SPELLBOOK_FIELD,
    TALENT_RANK_FIELDS,
    TALENTTAB_CLASS_MASK_FIELD,
    TALENTTAB_ORDER_FIELD,
    custom_spell_id,
    custom_talent_id,
    dbc_string,
    f32,
    i32,
    load_spec,
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
        self.spec = load_spec()

        tabs = []
        for index, tab in enumerate(self.spec["tabs"]):
            tabs.append(row(24, {
                0: int(tab["source_tab_id"]),
                18: 100 + index,
                20: 1 << index,
                22: index,
            }))
        write_dbc(self.dbc_dir / "TalentTab.dbc", 24, tabs)

        # Talent.dbc no longer needs arbitrary Blizzard talent rows as structural
        # templates. Keep one owned stale row to prove rebuild purges old layouts.
        write_dbc(self.dbc_dir / "Talent.dbc", 23, [row(23, {0: 5999, 1: 5000, 4: 299999})])

        source_ids = sorted({
            spell_id
            for definition in self.spec["talents"]
            for spell_id in talent_source_spell_ids(definition)
        })
        spell_rows: list[bytearray] = []
        for spell_id in source_ids:
            spell = row(234, {0: spell_id, 4: 0x11, 71: 6, 80: 0, 133: 1, 225: 1})

            if spell_id == 20060:  # Deflection source: native parry aura.
                set_u32(spell, 95, 47)
            if spell_id == 21156:  # Battle Stance passive used for Physical threat.
                set_u32(spell, 95, 10)
                set_i32(spell, 110, 127)
            if spell_id in {12298, 12724, 12725, 12726, 12727}:
                set_u32(spell, 71, 6)
                set_u32(spell, 72, 6)
                set_u32(spell, 95, 51)
                set_u32(spell, 96, 42)
                set_u32(spell, 116, 0)
                set_u32(spell, 117, 99999)
            if spell_id in {47294, 47295, 47296}:
                set_u32(spell, 71, 6)
                set_u32(spell, 72, 6)
                set_u32(spell, 95, 158)
                set_u32(spell, 96, 7)
            if spell_id == 12764:
                set_u32(spell, 71, 6)
                set_u32(spell, 72, 6)
                set_i32(spell, 80, 9)
                set_i32(spell, 81, -31)
            if spell_id == 12328:
                # Native Sweeping Strikes is restricted to Warrior stances.
                set_u32(spell, 12, 0x1)
                set_u32(spell, 14, 0x2)
            if spell_id == 31935:
                set_u32(spell, 71, 2)
                set_u32(spell, 72, 6)
                set_i32(spell, 74, 97)
                set_i32(spell, 80, 439)
                set_u32(spell, 104, 3)
                set_u32(spell, 204, 26)
                set_u32(spell, 208, 10)
                set_u32(spell, 209, 0x1234)
                set_u32(spell, 225, 2)
                set_f32(spell, 77, 1.0)
                set_f32(spell, 229, 0.07)

            spell_rows.append(spell)

        spell_rows.append(row(234, {0: 299999, 71: 6, 95: 10}))
        write_dbc(self.dbc_dir / "Spell.dbc", 234, spell_rows)

        icon_strings = bytearray(b"\0")
        icon_rows = []
        for icon_id, name in (
            (501, "ability_warrior_intensifyrage"),
            (502, "ability_warrior_secondwind"),
            (503, "Spell_deathknight_bloodboil"),
            (504, "inv_boots_plate_04"),
        ):
            path = f"Interface\\Icons\\{name}".encode() + b"\0"
            offset = len(icon_strings)
            icon_strings.extend(path)
            icon_rows.append(row(2, {0: icon_id, 1: offset}))
        write_dbc(self.dbc_dir / "SpellIcon.dbc", 2, icon_rows, bytes(icon_strings))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def definition(self, key: str) -> tuple[int, dict]:
        index = next(i for i, definition in enumerate(self.spec["talents"]) if definition["key"] == key)
        return index, self.spec["talents"][index]

    def generated_talent(self, talents: DBC, key: str) -> tuple[int, dict, bytearray]:
        index, definition = self.definition(key)
        talent = next(r for r in talents.records if u32(r, 0) == custom_talent_id(self.spec, index))
        return index, definition, talent

    def rank_ids(self, talent: bytearray) -> list[int]:
        return [u32(talent, field) for field in TALENT_RANK_FIELDS if u32(talent, field)]

    def test_spec_matches_current_drive_guardian_tree(self) -> None:
        expected = {
            "tenacity": (0, 0, 5),
            "steady_hand": (0, 2, 5),
            "cicatrization": (1, 0, 3),
            "threatening_presence": (1, 1, 3),
            "deflection": (1, 2, 3),
            "nerves_of_steel": (2, 0, 2),
            "consistency": (2, 1, 5),
            "riposte": (2, 2, 1),
            "shield_specialization": (2, 3, 5),
            "last_stand": (3, 0, 1),
            "one_handed_weapon_specialization": (3, 2, 3),
            "steady_footing": (4, 1, 2),
            "critical_block": (4, 3, 3),
            "bulwark": (5, 1, 3),
            "spell_deflection": (5, 2, 3),
            "ardent_defender": (6, 0, 3),
            "shield_mastery": (6, 3, 2),
            "unbreakable_will": (7, 0, 5),
            "sweeping_strikes": (7, 2, 1),
            "vitality": (8, 0, 3),
            "improved_mortal_strike": (8, 1, 3),
            "damage_shield": (8, 3, 2),
            "acclimation": (9, 1, 3),
            "mortal_strike": (9, 2, 1),
            "throw_shield": (10, 3, 1),
        }
        actual = {
            definition["key"]: (
                int(definition["row"]),
                int(definition["col"]),
                len(talent_source_spell_ids(definition)),
            )
            for definition in self.spec["talents"]
        }
        self.assertEqual(actual, expected)
        self.assertEqual(len(actual), 25)
        self.assertEqual(sum(rank_count for _row, _col, rank_count in actual.values()), 71)
        self.assertEqual(self.spec["guardian_points"], 71)
        self.assertEqual(self.definition("steady_footing")[1]["icon"], "inv_boots_plate_04")

    def test_builds_native_tabs_and_exact_guardian_count(self) -> None:
        result = patch_talent_directory(self.dbc_dir)
        self.assertTrue(all(result.values()))

        tabs = DBC.read(self.dbc_dir / "TalentTab.dbc")
        for tab in self.spec["tabs"]:
            generated = next(r for r in tabs.records if u32(r, 0) == int(tab["id"]))
            self.assertEqual(u32(generated, TALENTTAB_CLASS_MASK_FIELD), ADVENTURER_CLASS_MASK)
            self.assertEqual(u32(generated, TALENTTAB_ORDER_FIELD), int(tab["order"]))

        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        generated = [r for r in talents.records if 5000 <= u32(r, 0) < 6000]
        self.assertEqual(len(generated), 25)
        self.assertFalse(any(u32(r, 0) == 5999 for r in talents.records))

    def test_script_sensitive_native_passives_reuse_blizzard_spell_ids(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")

        scripted = {
            "ardent_defender": [31850, 31851, 31852],
            "damage_shield": [58872, 58874],
        }
        for key, expected in scripted.items():
            _index, definition, talent = self.generated_talent(talents, key)
            self.assertTrue(definition["reuse_native_spells"])
            self.assertEqual(self.rank_ids(talent), expected)

    def test_active_adventurer_clones_localize_and_remove_class_form_restrictions(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")

        expected_names = {
            "riposte": "Contestación",
            "last_stand": "Última Carga",
            "sweeping_strikes": "Golpes de barrido",
        }
        for key, expected_name in expected_names.items():
            index, definition, talent = self.generated_talent(talents, key)
            self.assertFalse(definition.get("reuse_native_spells", False))
            self.assertEqual(self.rank_ids(talent), [custom_spell_id(self.spec, index, 0)])
            spell = next(r for r in spells.records if u32(r, 0) == custom_spell_id(self.spec, index, 0))
            self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START + 7)), expected_name)

        sweeping_index, _definition, sweeping_talent = self.generated_talent(talents, "sweeping_strikes")
        sweeping = next(
            r for r in spells.records
            if u32(r, 0) == custom_spell_id(self.spec, sweeping_index, 0)
        )
        self.assertEqual(self.rank_ids(sweeping_talent), [290180])
        for field in (12, 13, 14, 15):
            self.assertEqual(u32(sweeping, field), 0)

    def test_active_talents_are_added_to_spellbook(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        active = {"riposte", "last_stand", "sweeping_strikes", "mortal_strike", "throw_shield"}

        for definition in self.spec["talents"]:
            _index, _definition, talent = self.generated_talent(talents, definition["key"])
            expected = 1 if definition["key"] in active else 0
            self.assertEqual(u32(talent, TALENT_ADD_TO_SPELLBOOK_FIELD), expected, definition["key"])

    def test_deflection_is_three_rank_native_parry_aura_with_2_4_6_values(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        index, _definition, talent = self.generated_talent(talents, "deflection")
        ids = self.rank_ids(talent)
        self.assertEqual(ids, [custom_spell_id(self.spec, index, i) for i in range(3)])

        for spell_id, value in zip(ids, (2, 4, 6)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[0]), 47)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), value - 1)
            self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START + 7)), "Desvio")

    def test_consistency_supports_signed_slow_duration_values(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        _index, _definition, talent = self.generated_talent(talents, "consistency")

        for spell_id, armor, slow in zip(self.rank_ids(talent), (2, 4, 6, 8, 10), (-6, -12, -18, -24, -30)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), armor - 1)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[1]), slow - 1)

    def test_paso_firme_is_inverse_feral_swiftness_with_block_and_parry(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        index, definition, talent = self.generated_talent(talents, "steady_footing")
        self.assertEqual(definition["esMX"], "Paso firme")
        ids = self.rank_ids(talent)
        self.assertEqual(ids, [custom_spell_id(self.spec, index, 0), custom_spell_id(self.spec, index, 1)])

        for spell_id, speed, defense in zip(ids, (15, 30), (2, 4)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual([u32(spell, field) for field in SPELL_EFFECT_FIELDS], [6, 6, 6])
            self.assertEqual([u32(spell, field) for field in SPELL_EFFECT_APPLY_AURA_FIELDS], [33, 51, 47])
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), speed - 1)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[1]), defense - 1)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[2]), defense - 1)
            self.assertEqual(dbc_string(spells, u32(spell, SPELL_NAME_START + 7)), "Paso firme")
            for field in (12, 13, 14, 15):
                self.assertEqual(u32(spell, field), 0)

    def test_shield_specialization_is_2_to_10_block_without_rage_proc(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        _index, _definition, talent = self.generated_talent(talents, "shield_specialization")

        for spell_id, value in zip(self.rank_ids(talent), (2, 4, 6, 8, 10)):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), value - 1)
            self.assertEqual(u32(spell, SPELL_EFFECT_FIELDS[1]), 0)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[1]), 0)
            self.assertEqual(u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[1]), 0)

    def test_critical_block_removes_shield_slam_crit_component(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        _index, _definition, talent = self.generated_talent(talents, "critical_block")

        self.assertEqual(len(self.rank_ids(talent)), 3)
        for spell_id in self.rank_ids(talent):
            spell = next(r for r in spells.records if u32(r, 0) == spell_id)
            self.assertNotEqual(u32(spell, SPELL_EFFECT_FIELDS[0]), 0)
            self.assertEqual(u32(spell, SPELL_EFFECT_FIELDS[1]), 0)
            self.assertEqual(u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[1]), 0)

    def test_throw_shield_is_physical_zero_base_damage_ap_template(self) -> None:
        patch_talent_directory(self.dbc_dir)
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        index, _definition, talent = self.generated_talent(talents, "throw_shield")
        self.assertEqual(index, 24)
        self.assertEqual(self.rank_ids(talent), [290240])

        spell = next(r for r in spells.records if u32(r, 0) == 290240)
        self.assertEqual(u32(spell, SPELL_SCHOOL_MASK_FIELD), 1)
        self.assertEqual(i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[0]), -1)
        self.assertEqual(i32(spell, 74), 0)
        self.assertAlmostEqual(f32(spell, 77), 0.0)
        self.assertAlmostEqual(f32(spell, 229), 0.0)
        self.assertEqual(u32(spell, 208), 0)
        self.assertEqual(u32(spell, 209), 0)
        self.assertEqual(u32(spell, 210), 0)
        self.assertEqual(u32(spell, 211), 0)
        self.assertEqual(u32(spell, 104), 3)  # Native three-target chain retained.
        self.assertEqual(u32(spell, 204), 26)  # Native mana cost retained.
        self.assertIn("0.24 * Attack power", dbc_string(spells, u32(spell, SPELL_DESCRIPTION_START + 7)))

    def test_generated_custom_descriptions_do_not_name_other_classes(self) -> None:
        patch_talent_directory(self.dbc_dir)
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        forbidden = (
            "palad", "guerrer", "pícar", "caballero de la muerte",
            "sacerdot", "cazador", "chamán", "druid", "mago", "brujo",
        )
        for definition in self.spec["talents"]:
            if definition.get("reuse_native_spells"):
                continue
            index, _definition = self.definition(definition["key"])
            for rank_index in range(len(talent_source_spell_ids(definition))):
                spell = next(r for r in spells.records if u32(r, 0) == custom_spell_id(self.spec, index, rank_index))
                description = dbc_string(spells, u32(spell, SPELL_DESCRIPTION_START + 7)).casefold()
                for token in forbidden:
                    self.assertNotIn(token.casefold(), description, definition["key"])

    def test_rebuild_purges_retired_custom_spells_and_is_idempotent(self) -> None:
        first = patch_talent_directory(self.dbc_dir)
        self.assertTrue(all(first.values()))
        talents = DBC.read(self.dbc_dir / "Talent.dbc")
        spells = DBC.read(self.dbc_dir / "Spell.dbc")
        self.assertFalse(any(u32(r, 0) == 5999 for r in talents.records))
        self.assertFalse(any(u32(r, 0) == 299999 for r in spells.records))

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
