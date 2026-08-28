from __future__ import annotations

import csv
import io
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import spelldraft_runtime  # noqa: E402

METADATA = ROOT / "config" / "spelldraft" / "catalog_metadata.csv"


class SpellDraftDesignCatalogTests(unittest.TestCase):
    def test_design_snapshot_contains_level_20_rarities_and_associations(self) -> None:
        metadata = spelldraft_runtime.parse_catalog_metadata(METADATA.read_text(encoding="utf-8"))
        self.assertEqual(len(metadata), 212)
        self.assertEqual(metadata[8092]["rarity"], "uncommon")  # Explosión mental
        self.assertEqual(metadata[122]["rarity"], "epic")       # Nova de Escarcha
        self.assertEqual(metadata[5277]["rarity"], "epic")      # Evasión
        self.assertEqual(metadata[18960]["rarity"], "unavailable")
        self.assertEqual(metadata[5697]["rarity"], "unavailable")
        self.assertIn(33213, metadata[8092]["talent_spells"])
        self.assertIn(16934, metadata[6807]["talent_spells"])

    def test_talent_dbc_parser_reads_real_wotlk_rank_columns(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "Talent.dbc"
            records = []
            for talent_id, ranks in (
                (1, [11069, 12338, 12339, 12340, 12341]),
                (2, [33213, 33214, 0, 0, 0]),
            ):
                fields = [0] * 23
                fields[0] = talent_id
                fields[4:9] = ranks
                records.append(struct.pack("<23I", *fields))
            payload = b"".join(records)
            path.write_bytes(struct.pack("<4s4I", b"WDBC", 2, 23, 92, 1) + payload + b"\0")

            parsed = spelldraft_runtime.parse_talent_dbc(path)
            self.assertEqual(parsed[11069], [11069, 12338, 12339, 12340, 12341])
            self.assertEqual(parsed[12339], [11069, 12338, 12339, 12340, 12341])
            self.assertEqual(parsed[33213], [33213, 33214])
            self.assertEqual(parsed[33214], [33213, 33214])

    def test_runtime_catalog_overlays_rarity_and_builds_talents_from_owned_abilities(self) -> None:
        base = """id;key;type;source_level;rarity;weight;rank_grants;requires_all;requires_any;unlocks;replaces_previous;name
2;fireball;active;1;common;100;133;;;104;0;Bola de Fuego
21;bear_form;active;10;rare;100;5487+6807+6795+99;;;;0;Forma de oso
22;unavailable;active;10;common;100;18960;;;;0;Moonglade
63;mind_blast;active;10;common;100;8092;;;;0;Explosión mental
101;cruelty;talent;10;common;120;12320/12852;;;;1;Crueldad
104;improved_fireball;talent;10;uncommon;180;11069/12338/12339/12340/12341;2:1;;;1;Bola de Fuego mejorada
"""
        metadata = """spell_id;rarity;talent_spells
133;common;11069
5487;rare;16833
6807;common;16934,467
6795;common;
99;common;16858
18960;unavailable;
8092;uncommon;33213
"""
        talent_ranks = {
            11069: [11069, 12338, 12339, 12340, 12341],
            16833: [16833, 16834, 16835],
            16934: [16934, 16935, 16936, 16937, 16938],
            16858: [16858, 16859, 16860, 16861, 16862],
            33213: [33213, 33214],
        }

        generated, ignored = spelldraft_runtime.build_runtime_cards(base, metadata, talent_ranks)
        rows = {
            int(row["id"]): row
            for row in csv.DictReader(io.StringIO(generated), delimiter=";")
        }

        self.assertNotIn(22, rows)
        self.assertEqual(rows[63]["rarity"], "uncommon")
        self.assertEqual(rows[104]["requires_all"], "")
        self.assertEqual(rows[104]["requires_any"], "2:1")
        self.assertEqual(rows[101]["requires_any"], "")  # global prototype remains global

        mind_talent = rows[spelldraft_runtime.SYNTHETIC_TALENT_CARD_BASE + 33213]
        self.assertEqual(mind_talent["rank_grants"], "33213/33214")
        self.assertEqual(mind_talent["requires_any"], "63:1")
        self.assertEqual(mind_talent["replaces_previous"], "1")

        maul_talent = rows[spelldraft_runtime.SYNTHETIC_TALENT_CARD_BASE + 16934]
        self.assertEqual(maul_talent["requires_any"], "21:1")
        self.assertIn(467, ignored)  # spell itself, not a Talent.dbc first-rank entry

    def test_intermediate_design_rank_is_canonicalized_to_first_talent_rank(self) -> None:
        base = """id;key;type;source_level;rarity;weight;rank_grants;requires_all;requires_any;unlocks;replaces_previous;name
63;mind_blast;active;10;common;100;8092;;;;0;Explosión mental
101;cruelty;talent;10;common;120;12320/12852;;;;1;Crueldad
"""
        metadata = """spell_id;rarity;talent_spells
8092;uncommon;33214
"""
        chain = [33213, 33214, 33215]
        talent_ranks = {spell_id: chain for spell_id in chain}

        generated, ignored = spelldraft_runtime.build_runtime_cards(base, metadata, talent_ranks)
        rows = {
            int(row["id"]): row
            for row in csv.DictReader(io.StringIO(generated), delimiter=";")
        }
        card = rows[spelldraft_runtime.SYNTHETIC_TALENT_CARD_BASE + 33213]
        self.assertEqual(card["rank_grants"], "33213/33214/33215")
        self.assertEqual(card["requires_any"], "63:1")
        self.assertNotIn(33214, ignored)

    def test_catalog_has_hundreds_of_curated_talent_links(self) -> None:
        metadata = spelldraft_runtime.parse_catalog_metadata(METADATA.read_text(encoding="utf-8"))
        unique = {talent for item in metadata.values() for talent in item["talent_spells"]}
        self.assertGreaterEqual(len(unique), 300)


if __name__ == "__main__":
    unittest.main()
