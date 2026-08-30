#!/usr/bin/env python3
"""Remove legacy fixed Adventurer talent-tree DBC rows.

Adventurer talents are owned exclusively by SpellDraft.  Older development
revisions generated native Guardian/Champion/Scholar TalentTab/Talent/Spell
rows.  The client builder still runs this compatibility pass so an install or
upgrade from an old DBC source converges back to stock talent data instead of
leaving ghost fixed talents behind.
"""

from __future__ import annotations

from pathlib import Path

from dbc import DBC, DBCError, u32

TALENTTAB_FIELDS = 24
TALENTTAB_RECORD_SIZE = TALENTTAB_FIELDS * 4
TALENT_FIELDS = 23
TALENT_RECORD_SIZE = TALENT_FIELDS * 4
SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4

LEGACY_TAB_IDS = {5000, 5001, 5002}
LEGACY_TALENT_MIN = 5000
LEGACY_TALENT_MAX = 6000
LEGACY_SPELL_MIN = 290000
LEGACY_SPELL_MAX = 300000


def _purge(
    path: Path,
    fields: int,
    record_size: int,
    owned,
) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != fields or dbc.record_size != record_size:
        raise DBCError(f"{path}: unexpected DBC layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    dbc.records = [row for row in dbc.records if not owned(u32(row, 0))]
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before


def patch_talent_directory(dbc_dir: Path) -> dict[str, bool]:
    """Purge only Adventurer-owned legacy fixed-tree rows; never create talents."""
    return {
        "TalentTab.dbc": _purge(
            dbc_dir / "TalentTab.dbc",
            TALENTTAB_FIELDS,
            TALENTTAB_RECORD_SIZE,
            lambda record_id: record_id in LEGACY_TAB_IDS,
        ),
        "Talent.dbc": _purge(
            dbc_dir / "Talent.dbc",
            TALENT_FIELDS,
            TALENT_RECORD_SIZE,
            lambda record_id: LEGACY_TALENT_MIN <= record_id < LEGACY_TALENT_MAX,
        ),
        "Spell.dbc": _purge(
            dbc_dir / "Spell.dbc",
            SPELL_FIELDS,
            SPELL_RECORD_SIZE,
            lambda record_id: LEGACY_SPELL_MIN <= record_id < LEGACY_SPELL_MAX,
        ),
    }
