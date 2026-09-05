#!/usr/bin/env python3
"""Single source of truth for fixed Adventurer items."""

from __future__ import annotations

import csv
import io
import struct
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CATALOG = ROOT / "config" / "items" / "adventurer_items.csv"
MAGIC = b"WDBC"
HEADER = struct.Struct("<4sIIII")

DBC_FIELDS = {
    "displayid": 5,
    "InventoryType": 6,
    "sheath": 7,
}

STRING_FIELDS = {"name", "description", "ScriptName"}
IDENTITY_FIELDS = {"entry", "source_entry"}


def load_catalog() -> list[dict[str, str]]:
    with CATALOG.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle, delimiter=";"))
    if not rows:
        raise RuntimeError(f"Adventurer item catalog is empty: {CATALOG}")

    entries = [int(row["entry"]) for row in rows]
    if len(entries) != len(set(entries)):
        raise RuntimeError("Adventurer item catalog contains duplicate entries")
    return rows


def item_mapping() -> dict[int, int]:
    return {int(row["entry"]): int(row["source_entry"]) for row in load_catalog()}


def _sql_value(field: str, value: str) -> str:
    if field in STRING_FIELDS:
        return "'" + value.replace("'", "''") + "'"
    return value


def generate_world_sql() -> bytes:
    rows = load_catalog()
    entries = ", ".join(row["entry"] for row in rows)
    out = io.StringIO()
    out.write("-- GENERATED from config/items/adventurer_items.csv. Do not edit this SQL directly.\n")
    out.write("-- Fixed Adventurer item definitions: one catalog feeds both world SQL and Item.dbc.\n\n")
    out.write(f"DELETE FROM `item_template` WHERE `entry` IN ({entries});\n\n")
    out.write("DROP TEMPORARY TABLE IF EXISTS `_adventurer_item_clone`;\n")
    out.write("CREATE TEMPORARY TABLE `_adventurer_item_clone` LIKE `item_template`;\n\n")

    for row in rows:
        entry = row["entry"]
        source = row["source_entry"]
        out.write(f"-- {entry}: {row['name']} (source {source})\n")
        out.write(
            "INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` "
            f"WHERE `entry` = {source};\n"
        )
        assignments = [f"`entry` = {entry}"]
        for field, value in row.items():
            if field in IDENTITY_FIELDS or value == "":
                continue
            assignments.append(f"`{field}` = {_sql_value(field, value)}")
        out.write("UPDATE `_adventurer_item_clone` SET\n    ")
        out.write(",\n    ".join(assignments))
        out.write(";\n")
        out.write("INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;\n")
        out.write("TRUNCATE TABLE `_adventurer_item_clone`;\n\n")

    out.write("DROP TEMPORARY TABLE `_adventurer_item_clone`;\n")
    return out.getvalue().encode("utf-8")


def _u32(record: bytearray, field: int) -> int:
    return struct.unpack_from("<I", record, field * 4)[0]


def _set_u32(record: bytearray, field: int, value: int) -> None:
    struct.pack_into("<I", record, field * 4, value)


def patch_item_dbc(path: Path) -> bool:
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise RuntimeError(f"{path}: Item.dbc is too small")

    magic, count, fields, record_size, string_size = HEADER.unpack_from(raw)
    if magic != MAGIC or fields != 8 or record_size != 32:
        raise RuntimeError(
            f"{path}: unexpected Item.dbc layout magic={magic!r} fields={fields} size={record_size}"
        )

    records_start = HEADER.size
    records_end = records_start + count * record_size
    strings_end = records_end + string_size
    if strings_end > len(raw):
        raise RuntimeError(f"{path}: invalid Item.dbc sizes")

    records = [
        bytearray(raw[records_start + i * record_size:records_start + (i + 1) * record_size])
        for i in range(count)
    ]
    strings = raw[records_end:strings_end]
    trailing = raw[strings_end:]

    catalog = load_catalog()
    owned = {int(row["entry"]) for row in catalog}
    stock = {_u32(row, 0): row for row in records if _u32(row, 0) not in owned}
    rebuilt = list(stock.values())

    for item in catalog:
        entry = int(item["entry"])
        source_entry = int(item["source_entry"])
        source = stock.get(source_entry)
        if source is None:
            raise RuntimeError(
                f"{path}: native Item.dbc row {source_entry} required for Adventurer item {entry} is missing"
            )
        row = bytearray(source)
        _set_u32(row, 0, entry)
        for column, field in DBC_FIELDS.items():
            value = item.get(column, "")
            if value != "":
                _set_u32(row, field, int(value))
        rebuilt.append(row)

    rebuilt.sort(key=lambda row: _u32(row, 0))
    patched = (
        HEADER.pack(MAGIC, len(rebuilt), fields, record_size, len(strings))
        + b"".join(rebuilt)
        + strings
        + trailing
    )
    if patched == raw:
        return False
    path.write_bytes(patched)
    return True
