#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from dbc import DBC, DBCError, set_u32, u32

SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
PLEDGE_SPELL_ID = 910500
BASE_BUFF_SPELL_ID = 1126
ICON_SOURCE_SPELL_ID = 48743

NAME = "Juramento del Último Aliento"
DESCRIPTION = "El pacto de Khadgar sigue vigente. Si mueres, este personaje no podrá volver a la vida."


def _set_localized(dbc: DBC, row: bytearray, start_field: int, text: str) -> None:
    offset = dbc.append_string(text) if text else 0
    for field in range(start_field, start_field + 16):
        set_u32(row, field, offset)


def patch(path: Path) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != SPELL_FIELDS or dbc.record_size != SPELL_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected Spell.dbc layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    base_rows = [row for row in dbc.records if u32(row, 0) != PLEDGE_SPELL_ID]
    lookup = {u32(row, 0): row for row in base_rows}
    base = lookup.get(BASE_BUFF_SPELL_ID)
    icon_source = lookup.get(ICON_SOURCE_SPELL_ID)
    if base is None:
        raise DBCError(f"{path}: base buff spell {BASE_BUFF_SPELL_ID} not found")
    if icon_source is None:
        raise DBCError(f"{path}: icon source spell {ICON_SOURCE_SPELL_ID} not found")

    row = bytearray(base)
    set_u32(row, 0, PLEDGE_SPELL_ID)

    for field in range(1, 40):
        set_u32(row, field, 0)
    for field in range(41, 71):
        set_u32(row, field, 0)
    set_u32(row, 68, 0xFFFFFFFF)  # no equipped item class requirement

    for field in range(71, 131):
        set_u32(row, field, 0)
    set_u32(row, 71, 6)   # SPELL_EFFECT_APPLY_AURA
    set_u32(row, 86, 1)   # TARGET_UNIT_CASTER
    set_u32(row, 95, 4)   # SPELL_AURA_DUMMY

    set_u32(row, 131, 0)
    set_u32(row, 132, 0)
    set_u32(row, 133, u32(icon_source, 133))
    set_u32(row, 134, 0)
    set_u32(row, 135, 0)

    _set_localized(dbc, row, 136, NAME)
    set_u32(row, 152, 0)
    _set_localized(dbc, row, 153, "")
    set_u32(row, 169, 0)
    _set_localized(dbc, row, 170, DESCRIPTION)
    set_u32(row, 186, 0)
    _set_localized(dbc, row, 187, DESCRIPTION)
    set_u32(row, 203, 0)

    for field in range(204, 234):
        set_u32(row, field, 0)
    set_u32(row, 225, 32)

    dbc.records = base_rows + [row]
    dbc.records.sort(key=lambda record: u32(record, 0))
    after = dbc.to_bytes()
    if after == before:
        return False
    path.write_bytes(after)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dbc", required=True, type=Path)
    args = parser.parse_args()
    changed = patch(args.dbc)
    print(f"Gauntlet Spell.dbc: {'patched' if changed else 'already current'} (pledge aura {PLEDGE_SPELL_ID}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
