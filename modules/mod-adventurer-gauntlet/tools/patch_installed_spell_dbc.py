#!/usr/bin/env python3
from __future__ import annotations

import struct
import sys
from pathlib import Path

MAGIC = b"WDBC"
HEADER = struct.Struct("<4sIIII")
SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
PLEDGE_SPELL_ID = 910500
LONE_WOLF_SPELL_ID = 910501
BASE_BUFF_SPELL_ID = 1126
PLEDGE_ICON_SOURCE_SPELL_ID = 48743
LONE_WOLF_ICON_ID = 910000

SPELL_EFFECT_APPLY_AURA = 6
SPELL_AURA_MOD_INCREASE_SPEED = 31
SPELL_AURA_MOD_MELEE_RANGED_HASTE = 192
SPELL_AURA_HASTE_SPELLS = 216

PLEDGE_NAME = "Juramento del Último Aliento"
PLEDGE_DESCRIPTION = "El pacto de Khadgar sigue vigente. Si mueres, este personaje no podrá volver a la vida."
LONE_WOLF_NAME = "Lobo solitario"
LONE_WOLF_DESCRIPTION = "+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento mientras afrontas solo el Desafío de Khadgar."


def u32(record: bytearray, field: int) -> int:
    return struct.unpack_from("<I", record, field * 4)[0]


def set_u32(record: bytearray, field: int, value: int) -> None:
    struct.pack_into("<I", record, field * 4, value & 0xFFFFFFFF)


def read_dbc(path: Path):
    data = path.read_bytes()
    magic, count, fields, record_size, string_size = HEADER.unpack_from(data)
    if magic != MAGIC or fields != SPELL_FIELDS or record_size != SPELL_RECORD_SIZE:
        raise RuntimeError(f"unexpected Spell.dbc layout: {magic!r} {fields}/{record_size}")
    records_start = HEADER.size
    records_end = records_start + count * record_size
    strings_end = records_end + string_size
    records = [
        bytearray(data[records_start + i * record_size: records_start + (i + 1) * record_size])
        for i in range(count)
    ]
    strings = bytearray(data[records_end:strings_end])
    trailing = data[strings_end:]
    return records, strings, trailing


def append_string(strings: bytearray, value: str) -> int:
    encoded = value.encode("utf-8") + b"\0"
    pos = bytes(strings).find(encoded)
    if pos >= 0:
        return pos
    pos = len(strings)
    strings.extend(encoded)
    return pos


def set_localized(strings: bytearray, row: bytearray, start_field: int, text: str) -> None:
    offset = append_string(strings, text) if text else 0
    for field in range(start_field, start_field + 16):
        set_u32(row, field, offset)


def set_identity(strings: bytearray, row: bytearray, spell_id: int, icon_id: int, name: str, description: str) -> None:
    set_u32(row, 0, spell_id)
    set_u32(row, 131, 0)
    set_u32(row, 132, 0)
    set_u32(row, 133, icon_id)
    set_u32(row, 134, 0)
    set_u32(row, 135, 0)
    set_localized(strings, row, 136, name)
    set_u32(row, 152, 0)
    set_localized(strings, row, 153, "")
    set_u32(row, 169, 0)
    set_localized(strings, row, 170, description)
    set_u32(row, 186, 0)
    set_localized(strings, row, 187, description)
    set_u32(row, 203, 0)


def set_aura_effect(row: bytearray, index: int, aura_type: int, amount_pct: int) -> None:
    set_u32(row, 71 + index, SPELL_EFFECT_APPLY_AURA)
    set_u32(row, 80 + index, amount_pct - 1)
    set_u32(row, 86 + index, 1)
    set_u32(row, 95 + index, aura_type)


def build_pledge(strings: bytearray, base: bytearray, icon_id: int) -> bytearray:
    row = bytearray(base)
    for field in range(1, 40):
        set_u32(row, field, 0)
    for field in range(41, 71):
        set_u32(row, field, 0)
    set_u32(row, 68, 0xFFFFFFFF)
    for field in range(71, 131):
        set_u32(row, field, 0)
    set_u32(row, 71, SPELL_EFFECT_APPLY_AURA)
    set_u32(row, 86, 1)
    set_u32(row, 95, 4)
    set_identity(strings, row, PLEDGE_SPELL_ID, icon_id, PLEDGE_NAME, PLEDGE_DESCRIPTION)
    for field in range(204, 234):
        set_u32(row, field, 0)
    set_u32(row, 225, 32)
    return row


def build_lone_wolf(strings: bytearray, pledge: bytearray) -> bytearray:
    # Clone the already-valid pledge row, then replace only the three aura
    # effects and presentation. This intentionally uses the exact same custom
    # aura structure that already works for Juramento del Último Aliento.
    row = bytearray(pledge)
    set_identity(strings, row, LONE_WOLF_SPELL_ID, LONE_WOLF_ICON_ID, LONE_WOLF_NAME, LONE_WOLF_DESCRIPTION)
    for field in range(71, 131):
        set_u32(row, field, 0)
    set_aura_effect(row, 0, SPELL_AURA_MOD_INCREASE_SPEED, 20)
    set_aura_effect(row, 1, SPELL_AURA_MOD_MELEE_RANGED_HASTE, 10)
    set_aura_effect(row, 2, SPELL_AURA_HASTE_SPELLS, 10)
    return row


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: patch_installed_spell_dbc.py /path/to/Spell.dbc")
    path = Path(sys.argv[1])
    if not path.is_file():
        raise SystemExit(f"Spell.dbc not found: {path}")

    records, strings, trailing = read_dbc(path)
    records = [r for r in records if u32(r, 0) not in {PLEDGE_SPELL_ID, LONE_WOLF_SPELL_ID}]
    lookup = {u32(r, 0): r for r in records}
    base = lookup.get(BASE_BUFF_SPELL_ID)
    icon_source = lookup.get(PLEDGE_ICON_SOURCE_SPELL_ID)
    if base is None or icon_source is None:
        raise SystemExit("required stock spell templates are missing from Spell.dbc")

    pledge = build_pledge(strings, base, u32(icon_source, 133))
    lone_wolf = build_lone_wolf(strings, pledge)
    records.extend((pledge, lone_wolf))
    records.sort(key=lambda r: u32(r, 0))

    payload = HEADER.pack(MAGIC, len(records), SPELL_FIELDS, SPELL_RECORD_SIZE, len(strings))
    payload += b"".join(records) + bytes(strings) + trailing
    path.write_bytes(payload)

    verify_records, _, _ = read_dbc(path)
    ids = {u32(r, 0) for r in verify_records}
    for spell_id in (PLEDGE_SPELL_ID, LONE_WOLF_SPELL_ID):
        if spell_id not in ids:
            raise SystemExit(f"spell {spell_id} missing after final install patch")

    print(f"Gauntlet final Spell.dbc verified: {PLEDGE_SPELL_ID}, {LONE_WOLF_SPELL_ID}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
