"""First-batch DK numeric contract; no claims of in-game validation."""

import collections
from decimal import Decimal
from pathlib import Path
import struct
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import DBC, DBCError
from dk_adaptations import (
    ABILITIES, BLOOD_STRIKE, EVISCERATE_RANKS, ICY_TOUCH_MIN,
    PLAGUE_STRIKE, blood_tap_energy, interpolate, level_values, preflight,
)


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
        ids = {a.native_id for a in ABILITIES} | set(EVISCERATE_RANKS) | {55078, 55095}
        rows = []
        for spell in sorted(ids - set(omit)) + list(extra):
            row = bytearray(936)
            struct.pack_into("<I", row, 0, spell)
            rows.append(row)
        return DBC(234, 936, rows, bytearray(b"\0"))

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
