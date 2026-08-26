#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = ROOT / "tools" / "spelldraft_runtime.py"
TEST = ROOT / "tests" / "test_spelldraft_design_catalog.py"


def replace_once(text: str, old: str, new: str, label: str) -> str:
    if new in text:
        return text
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"{label}: expected one anchor, found {count}")
    return text.replace(old, new, 1)


runtime = RUNTIME.read_text(encoding="utf-8")
runtime = replace_once(
    runtime,
    """        ranks = [spell_id for spell_id in fields[4:9] if spell_id]\n        if ranks:\n            result[ranks[0]] = ranks\n""",
    """        ranks = [spell_id for spell_id in fields[4:9] if spell_id]\n        if ranks:\n            # Design sheets are maintained by spell ID and may reference any\n            # rank of a native WotLK talent. Make every rank an alias of the\n            # canonical first-rank chain so those references are normalized\n            # instead of silently discarded.\n            for spell_id in ranks:\n                result[spell_id] = ranks\n""",
    "Talent.dbc alias map",
)
runtime = replace_once(
    runtime,
    """        for talent_spell in meta[\"talent_spells\"]:\n            if talent_spell in talent_ranks:\n                talent_sources.setdefault(talent_spell, set()).update(card_ids)\n""",
    """        for talent_spell in meta[\"talent_spells\"]:\n            ranks = talent_ranks.get(talent_spell)\n            if ranks:\n                talent_sources.setdefault(ranks[0], set()).update(card_ids)\n""",
    "talent source canonicalization",
)
RUNTIME.write_text(runtime, encoding="utf-8")

test = TEST.read_text(encoding="utf-8")
test = replace_once(
    test,
    """            parsed = spelldraft_runtime.parse_talent_dbc(path)\n            self.assertEqual(parsed[11069], [11069, 12338, 12339, 12340, 12341])\n            self.assertEqual(parsed[33213], [33213, 33214])\n""",
    """            parsed = spelldraft_runtime.parse_talent_dbc(path)\n            self.assertEqual(parsed[11069], [11069, 12338, 12339, 12340, 12341])\n            self.assertEqual(parsed[12339], [11069, 12338, 12339, 12340, 12341])\n            self.assertEqual(parsed[33213], [33213, 33214])\n            self.assertEqual(parsed[33214], [33213, 33214])\n""",
    "parser alias assertions",
)
insert_at = test.find("    def test_catalog_has_hundreds_of_curated_talent_links")
if insert_at < 0:
    raise RuntimeError("test insertion anchor not found")
new_test = '''    def test_intermediate_design_rank_is_canonicalized_to_first_talent_rank(self) -> None:\n        base = \"\"\"id;key;type;source_level;rarity;weight;rank_grants;requires_all;requires_any;unlocks;replaces_previous;name\n63;mind_blast;active;10;common;100;8092;;;;0;Explosión mental\n101;cruelty;talent;10;common;120;12320/12852;;;;1;Crueldad\n\"\"\"\n        metadata = \"\"\"spell_id;rarity;talent_spells\n8092;uncommon;33214\n\"\"\"\n        chain = [33213, 33214, 33215]\n        talent_ranks = {spell_id: chain for spell_id in chain}\n\n        generated, ignored = spelldraft_runtime.build_runtime_cards(base, metadata, talent_ranks)\n        rows = {\n            int(row[\"id\"]): row\n            for row in csv.DictReader(io.StringIO(generated), delimiter=\";\")\n        }\n        card = rows[spelldraft_runtime.SYNTHETIC_TALENT_CARD_BASE + 33213]\n        self.assertEqual(card[\"rank_grants\"], \"33213/33214/33215\")\n        self.assertEqual(card[\"requires_any\"], \"63:1\")\n        self.assertNotIn(33214, ignored)\n\n'''
if "test_intermediate_design_rank_is_canonicalized_to_first_talent_rank" not in test:
    test = test[:insert_at] + new_test + test[insert_at:]
TEST.write_text(test, encoding="utf-8")
print("Talent rank aliases normalized")
