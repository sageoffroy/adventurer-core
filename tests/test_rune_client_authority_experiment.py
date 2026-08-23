from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

from dbc import DBC, set_u32, u32  # noqa: E402
from rune_client_authority_experiment import (  # noqa: E402
    EXPERIMENT_SPELL_IDS,
    POWER_MANA,
    SPELL_FIELDS,
    SPELL_MANA_COST_PERCENT_FIELD,
    SPELL_POWER_TYPE_FIELD,
    SPELL_RECORD_SIZE,
    SPELL_RUNE_COST_ID_FIELD,
    patch_client_rune_validation,
    rune_signature,
)


class RuneClientAuthorityExperimentTests(unittest.TestCase):
    def make_spell_dbc(self, path: Path) -> None:
        records: list[bytearray] = []
        for index, spell_id in enumerate(EXPERIMENT_SPELL_IDS, start=1):
            row = bytearray(SPELL_RECORD_SIZE)
            set_u32(row, 0, spell_id)
            set_u32(row, SPELL_POWER_TYPE_FIELD, 5)  # POWER_RUNE
            set_u32(row, 42, 100 + index)
            set_u32(row, SPELL_MANA_COST_PERCENT_FIELD, 10 + index)
            set_u32(row, SPELL_RUNE_COST_ID_FIELD, 20 + index)
            records.append(row)
        DBC(SPELL_FIELDS, SPELL_RECORD_SIZE, records, bytearray(b"\0")).write(path)

    def test_client_variant_neutralizes_only_local_rune_validation(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_name:
            tmp = Path(tmp_name)
            server = tmp / "Spell.server.dbc"
            client = tmp / "Spell.client.dbc"
            self.make_spell_dbc(server)
            client.write_bytes(server.read_bytes())

            server_before = server.read_bytes()
            server_signatures = {
                spell_id: rune_signature(server, spell_id)
                for spell_id in EXPERIMENT_SPELL_IDS
            }

            patch_client_rune_validation(client)

            self.assertEqual(server.read_bytes(), server_before)
            self.assertNotEqual(client.read_bytes(), server.read_bytes())

            for spell_id in EXPERIMENT_SPELL_IDS:
                server_power, server_rune_cost, server_mana, server_mana_pct = server_signatures[spell_id]
                client_power, client_rune_cost, client_mana, client_mana_pct = rune_signature(client, spell_id)

                self.assertEqual(server_power, 5)
                self.assertGreater(server_rune_cost, 0)
                self.assertGreater(server_mana, 0)
                self.assertGreater(server_mana_pct, 0)

                self.assertEqual(client_power, POWER_MANA)
                self.assertEqual(client_rune_cost, 0)
                self.assertEqual(client_mana, 0)
                self.assertEqual(client_mana_pct, 0)

    def test_experiment_is_limited_to_known_regression_spells(self) -> None:
        self.assertEqual(EXPERIMENT_SPELL_IDS, (45477, 45462, 45902))


if __name__ == "__main__":
    unittest.main()
