#!/usr/bin/env python3
"""Gauntlet-owned custom Spell.dbc rows layered on SpellDraft v3."""

from __future__ import annotations

from pathlib import Path

from dbc import DBC, DBCError, set_u32, u32
import icon_pack

SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
BASE_BUFF_SPELL_ID = 1126
PLEDGE_SPELL_ID = 910500
LONE_WOLF_SPELL_ID = 910501
PLEDGE_ICON_SOURCE_SPELL_ID = 48743
LONE_WOLF_ICON_SOURCE_SPELL_ID = 2645
LONE_WOLF_ICON_FILENAME = "lobo_solitario.blp"


def _set_localized(dbc: DBC, row: bytearray, start_field: int, text: str) -> None:
    offset = dbc.append_string(text) if text else 0
    for field in range(start_field, start_field + 16):
        set_u32(row, field, offset)


def _custom_icon_id(filename: str) -> int | None:
    wanted = filename.casefold()
    for path, icon_id in icon_pack.load_catalog().items():
        if Path(path).name.casefold() == wanted:
            return icon_id
    return None


def _build_marker(
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
    lone_wolf_icon_source = lookup.get(LONE_WOLF_ICON_SOURCE_SPELL_ID)
    if base is None:
        raise DBCError(f"{path}: base buff spell {BASE_BUFF_SPELL_ID} not found")
    if pledge_icon_source is None:
        raise DBCError(f"{path}: pledge icon source spell {PLEDGE_ICON_SOURCE_SPELL_ID} not found")
    if lone_wolf_icon_source is None:
        raise DBCError(f"{path}: Lone Wolf icon source spell {LONE_WOLF_ICON_SOURCE_SPELL_ID} not found")

    pledge = _build_marker(
        dbc,
        base,
        PLEDGE_SPELL_ID,
        u32(pledge_icon_source, 133),
        "Juramento del Último Aliento",
        "El pacto de Khadgar sigue vigente. Si mueres, este personaje no podrá volver a la vida.",
    )

    lone_wolf_icon = _custom_icon_id(LONE_WOLF_ICON_FILENAME)
    if lone_wolf_icon is None:
        lone_wolf_icon = u32(lone_wolf_icon_source, 133)

    lone_wolf = _build_marker(
        dbc,
        base,
        LONE_WOLF_SPELL_ID,
        lone_wolf_icon,
        "Lobo solitario",
        "Khadgar reconoce a los aventureros que se internan solos en una expedición.",
    )

    dbc.records = base_rows + [pledge, lone_wolf]
    dbc.records.sort(key=lambda record: u32(record, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before
