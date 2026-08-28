"""First-batch DK numeric contract; no claims of in-game validation."""

import collections
import csv
from decimal import Decimal
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import DBC, DBCError, set_u32, u32
from dk_adaptations import (
    ABILITIES, BLOOD_STRIKE, EVISCERATE_RANKS, ICY_TOUCH_MIN,
    PLAGUE_STRIKE, blood_tap_energy, interpolate, level_values, preflight,
    TALENTS, MINIMUM_LEVEL, AUXILIARY_IDS, patch_dk_directory, world_sql,
)
from spelldraft_runtime import build_runtime_cards, build_runtime_subclasses, parse_talent_dbc
from spell_rank_tabs import load_server_rank_chains


class DKAdaptationsTests(unittest.TestCase):
    def test_scope_is_four_per_branch_with_distinct_owned_ids(self):
        self.assertEqual(collections.Counter(a.branch for a in ABILITIES),
                         {"blood": 4, "frost": 4, "unholy": 4})
        ids = [spell for ability in ABILITIES for spell in ability.spell_ids]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(spell < 290000 for spell in ids))

    def test_all_80_levels_preserve_order_and_native_additive_resolution(self):
        previous = None
        for level in range(1, 81):
            values = level_values(level)
            self.assertLessEqual(values["icy_touch_min"], values["icy_touch_max"])
            self.assertEqual(values["blood_effective_additive"],
                             values["blood_raw_additive"] * Decimal("0.4"))
            self.assertEqual(values["plague_effective_additive"],
                             values["plague_raw_additive"] * Decimal("0.5"))
            if previous:
                for key in values:
                    self.assertGreaterEqual(values[key], previous[key])
            previous = values

    def test_native_anchors_are_not_buffed(self):
        for anchors, key in ((BLOOD_STRIKE, "blood_effective_additive"),
                             (PLAGUE_STRIKE, "plague_effective_additive")):
            for level, expected in anchors:
                if level >= 55:
                    self.assertEqual(level_values(level)[key], Decimal(expected))
        self.assertEqual(level_values(78)["icy_touch_min"], level_values(80)["icy_touch_min"])
        self.assertEqual(level_values(80)["icy_touch_max"], 245)
        self.assertEqual(level_values(80)["blood_raw_additive"], 764)
        self.assertEqual(level_values(80)["plague_raw_additive"], 378)

    def test_interpolation_and_rounding(self):
        self.assertEqual(interpolate(BLOOD_STRIKE, 4), Decimal("10"))
        self.assertEqual(level_values(1)["blood_effective_additive"], Decimal("7.2"))
        self.assertEqual(level_values(8)["blood_effective_additive"], Decimal("14"))
        self.assertEqual(level_values(1)["icy_touch_min"], 8)
        for level in (0, 81):
            with self.assertRaises(ValueError):
                interpolate(ICY_TOUCH_MIN, level)

    def test_blood_tap_wastes_overflow_and_internal_rage_remainder(self):
        self.assertEqual(blood_tap_energy(1000, 0), 100)
        self.assertEqual(blood_tap_energy(1000, 90), 10)
        self.assertEqual(blood_tap_energy(250, 100), 0)
        self.assertEqual(blood_tap_energy(259, 0), 25)
        self.assertEqual(blood_tap_energy(9, 0), 0)
        with self.assertRaises(ValueError):
            blood_tap_energy(0, 0)

    def template(self, extra=(), omit=()):
        ids = {a.native_id for a in ABILITIES} | set(EVISCERATE_RANKS) | {55078, 55095, 45470, 49575, 63611, 46585}
        rows = []
        for spell in sorted(ids - set(omit)) + list(extra):
            row = bytearray(936)
            struct.pack_into("<I", row, 0, spell)
            set_u32(row, 38, 55)
            set_u32(row, 39, 55)
            set_u32(row, 208, 15)  # DK native spell family, preserved by copying
            set_u32(row, 209, spell)  # recognizable sentinel, not a real family mask
            set_u32(row, 226, 99)
            for field in range(50, 68):
                set_u32(row, field, 123)
            if spell == 46584:
                set_u32(row, 81, 46584)  # native guardian spell value = base + 1
            if spell == 46585:
                set_u32(row, 71, 28)
                set_u32(row, 110, 26125)
            if spell in EVISCERATE_RANKS:
                rank = EVISCERATE_RANKS.index(spell)
                level = (1, 8, 16, 24, 32, 40, 48, 56, 60, 60, 73, 79)[rank]
                set_u32(row, 38, level)
                set_u32(row, 39, level)
                set_u32(row, 5, 0x00100000)
                set_u32(row, 74, 5)
                set_u32(row, 80, rank * 10 + 4)
                struct.pack_into("<f", row, 119 * 4, rank * 10 + 10)
            rows.append(row)
        return DBC(234, 936, rows, bytearray(b"\0"))

    def write_fixture(self, directory):
        self.template().write(directory / "Spell.dbc")
        duration = bytearray(struct.pack("<Iiii", 3, 60000, 0, 60000))
        DBC(4, 16, [duration], bytearray(b"\0")).write(directory / "SpellDuration.dbc")
        rows = []
        for index, spell in enumerate(sorted({s for spells in TALENTS.values() for s in spells}), 1):
            row = bytearray(92)
            set_u32(row, 0, index)
            set_u32(row, 4, spell)
            rows.append(row)
        DBC(23, 92, rows, bytearray(b"\0")).write(directory / "Talent.dbc")

    def test_transform_all_twelve_preserves_native_rows_and_has_no_rune_costs(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.write_fixture(directory)
            native = {u32(r, 0): bytes(r) for r in DBC.read(directory / "Spell.dbc").records}
            patch_dk_directory(directory)
            rows = {u32(r, 0): r for r in DBC.read(directory / "Spell.dbc").records}
            for spell, before in native.items():
                self.assertEqual(bytes(rows[spell]), before)
            self.assertEqual(len(rows) - len(native), 328 + len(AUXILIARY_IDS))
            for ability in ABILITIES:
                for index, spell in enumerate(ability.spell_ids):
                    row = rows[spell]
                    self.assertEqual(u32(row, 226), 0)
                    self.assertNotIn(u32(row, 41), (5, 6))
                    self.assertEqual(u32(row, 42), ability.cost)
                    self.assertEqual(u32(row, 204), ability.base_mana_percent)
                    self.assertEqual(u32(row, 209), ability.native_id)
                    self.assertEqual(u32(row, 39), index + 1 if ability.scaled else MINIMUM_LEVEL.get(ability.key, 1))
                    self.assertTrue(all(u32(row, field) == 0 for field in range(50, 68)))
            self.assertEqual(u32(rows[280180], 80) + 1, 764)
            self.assertEqual(u32(rows[280980], 80) + 1, 378)
            self.assertEqual(u32(rows[280480], 80) + 1, 227)
            self.assertEqual(u32(rows[280480], 74), 19)
            self.assertEqual(u32(rows[280701], 29), 8000)
            self.assertEqual(u32(rows[281101], 29), 180000)
            self.assertEqual(u32(rows[282003], 40), 3)
            self.assertEqual(u32(rows[281060], 80), u32(rows[26865], 80))
            self.assertTrue(u32(rows[281060], 5) & 0x00100000)

    def test_failed_talent_or_duration_preflight_never_writes_spell_data(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            for missing in ("Talent.dbc", "SpellDuration.dbc"):
                self.write_fixture(directory)
                before = (directory / "Spell.dbc").read_bytes()
                dbc = DBC.read(directory / missing)
                dbc.records = []
                dbc.write(directory / missing)
                with self.assertRaises(DBCError):
                    patch_dk_directory(directory)
                self.assertEqual((directory / "Spell.dbc").read_bytes(), before)

    def test_migration_matches_authored_ranks_and_script_bindings(self):
        self.assertEqual((ROOT / "sql/world/006_adventurer_dk_first_batch.sql").read_text(), world_sql())
        sql = world_sql()
        for ability in ABILITIES:
            for rank, spell in enumerate(ability.spell_ids, 1):
                self.assertIn(f"({spell},'spell_adventurer_dk')", sql)
                if ability.scaled:
                    self.assertIn(f"({ability.first_id},{spell},{rank})", sql)

    def test_existing_catalog_generator_registers_cards_dependencies_and_talents(self):
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            self.write_fixture(directory)
            catalog = ROOT / "config/spelldraft"
            base = (catalog / "cards.csv").read_text()
            generated, ignored = build_runtime_cards(base, (catalog / "catalog_metadata.csv").read_text(),
                                                      parse_talent_dbc(directory / "Talent.dbc"))
            rows = {int(row["id"]): row for row in csv.DictReader(io.StringIO(generated), delimiter=";")}
            for index, ability in enumerate(ABILITIES, 211):
                self.assertEqual(rows[index]["rank_grants"], str(ability.first_id))
                self.assertNotIn("/", rows[index]["rank_grants"])
                for talent in TALENTS.get(ability.key, ()):
                    self.assertNotIn(talent, ignored)
                    self.assertIn(f"{index}:1", rows[1000000 + talent]["requires_any"].split("|"))
            for finisher in (50, 55, 221):
                self.assertIn("220:1", rows[finisher]["requires_any"].split("|"))
            self.assertEqual(rows[221]["requires_all"], "")
            # Existing subclass generation must accept every new active/talent.
            classified = build_runtime_subclasses(generated, base, json.loads((catalog / "subclasses.json").read_text()))
            self.assertIn("211", classified)

    def test_owned_chains_extend_native_rank_loader_without_changing_native_chains(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "spell_ranks.sql"
            path.write_text("INSERT INTO spell_ranks (first_spell_id, spell_id, rank) VALUES (78,78,1),(78,284,2);")
            chains = load_server_rank_chains(path)
            self.assertEqual(chains[78], (78, 284))
            for ability in ABILITIES:
                if ability.scaled:
                    self.assertEqual(chains[ability.first_id], ability.spell_ids)

    def test_preflight_is_read_only_and_rejects_collisions_missing_templates_and_duplicates(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "Spell.dbc"
            valid = self.template()
            valid.write(path)
            self.assertEqual(preflight(path).to_bytes(), valid.to_bytes())
            for dbc in (self.template(extra=(280001,)), self.template(omit=(49998,)),
                        self.template(extra=(48266,)), DBC(1, 4, [], bytearray(b"\0"))):
                dbc.write(path)
                before = path.read_bytes()
                with self.assertRaises(DBCError):
                    preflight(path)
                self.assertEqual(path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
