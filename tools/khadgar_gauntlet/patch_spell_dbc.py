#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent.parent
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))

from dbc import DBC, DBCError, set_u32, u32

SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
PLEDGE_SPELL_ID = 910500
LONE_WOLF_SPELL_ID = 910501
LONE_WOLF_ICON_ID = 910000
BASE_BUFF_SPELL_ID = 1126
PLEDGE_ICON_SOURCE_SPELL_ID = 48743

PLEDGE_NAME = "Juramento del Último Aliento"
PLEDGE_DESCRIPTION = "El pacto de Khadgar sigue vigente. Si mueres, este personaje no podrá volver a la vida."
LONE_WOLF_NAME = "Lobo solitario"
LONE_WOLF_DESCRIPTION = "Has entrado solo al Desafío de Khadgar. Esta marca permanece mientras afrontes la expedición sin compañeros."


def _set_localized(dbc: DBC, row: bytearray, start_field: int, text: str) -> None:
    offset = dbc.append_string(text) if text else 0
    for field in range(start_field, start_field + 16):
        set_u32(row, field, offset)


def _build_marker_aura(
    dbc: DBC,
    base: bytearray,
    spell_id: int,
    icon_id: int,
    name: str,
    description: str,
) -> bytearray:
    row = bytearray(base)
    set_u32(row, 0, spell_id)

    for field in range(1, 40):
        set_u32(row, field, 0)
    for field in range(41, 71):
        set_u32(row, field, 0)
    set_u32(row, 68, 0xFFFFFFFF)

    for field in range(71, 131):
        set_u32(row, field, 0)
    set_u32(row, 71, 6)
    set_u32(row, 86, 1)
    set_u32(row, 95, 4)

    set_u32(row, 131, 0)
    set_u32(row, 132, 0)
    set_u32(row, 133, icon_id)
    set_u32(row, 134, 0)
    set_u32(row, 135, 0)

    _set_localized(dbc, row, 136, name)
    set_u32(row, 152, 0)
    _set_localized(dbc, row, 153, "")
    set_u32(row, 169, 0)
    _set_localized(dbc, row, 170, description)
    set_u32(row, 186, 0)
    _set_localized(dbc, row, 187, description)
    set_u32(row, 203, 0)

    for field in range(204, 234):
        set_u32(row, field, 0)
    set_u32(row, 225, 32)
    return row


def patch(path: Path) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != SPELL_FIELDS or dbc.record_size != SPELL_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected Spell.dbc layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    owned = {PLEDGE_SPELL_ID, LONE_WOLF_SPELL_ID}
    base_rows = [row for row in dbc.records if u32(row, 0) not in owned]
    lookup = {u32(row, 0): row for row in base_rows}
    base = lookup.get(BASE_BUFF_SPELL_ID)
    pledge_icon_source = lookup.get(PLEDGE_ICON_SOURCE_SPELL_ID)
    if base is None:
        raise DBCError(f"{path}: base buff spell {BASE_BUFF_SPELL_ID} not found")
    if pledge_icon_source is None:
        raise DBCError(f"{path}: icon source spell {PLEDGE_ICON_SOURCE_SPELL_ID} not found")

    pledge = _build_marker_aura(
        dbc,
        base,
        PLEDGE_SPELL_ID,
        u32(pledge_icon_source, 133),
        PLEDGE_NAME,
        PLEDGE_DESCRIPTION,
    )
    lone_wolf = _build_marker_aura(
        dbc,
        base,
        LONE_WOLF_SPELL_ID,
        LONE_WOLF_ICON_ID,
        LONE_WOLF_NAME,
        LONE_WOLF_DESCRIPTION,
    )

    dbc.records = base_rows + [pledge, lone_wolf]
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
    state = "patched" if changed else "already current"
    print(f"Gauntlet Spell.dbc: {state} (pledge {PLEDGE_SPELL_ID}, lone wolf {LONE_WOLF_SPELL_ID}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
