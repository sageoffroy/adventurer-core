#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

MAGIC = b"WDBC"
HEADER = struct.Struct("<4sIIII")


def u32(record: bytearray, field: int) -> int:
    return struct.unpack_from("<I", record, field * 4)[0]


def set_u32(record: bytearray, field: int, value: int) -> None:
    struct.pack_into("<I", record, field * 4, value)


def load_mapping(path: Path) -> dict[int, int]:
    mapping: dict[int, int] = {}
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            enabled = (row.get("enabled") or "").strip().lower()
            if enabled not in {"1", "true", "yes", "on"}:
                continue
            entry = int(row["entry"])
            source = int(row["source_entry"])
            if not 911000 <= entry <= 911999:
                raise RuntimeError(f"custom entry outside Gauntlet range: {entry}")
            mapping[entry] = source
    if not mapping:
        raise RuntimeError("Gauntlet item catalog has no enabled rows")
    first, last = min(mapping), max(mapping)
    expected = set(range(first, last + 1))
    if set(mapping) != expected:
        missing = sorted(expected - set(mapping))
        raise RuntimeError(f"Gauntlet item range must be contiguous; missing={missing[:10]}")
    return mapping


def patch(path: Path, mapping: dict[int, int]) -> bool:
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise RuntimeError(f"{path}: Item.dbc too small")

    magic, count, fields, record_size, string_size = HEADER.unpack_from(raw)
    if magic != MAGIC or fields != 8 or record_size != 32:
        raise RuntimeError(f"{path}: unexpected Item.dbc layout")

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

    owned = set(mapping)
    base_rows = [row for row in records if u32(row, 0) not in owned]
    lookup = {u32(row, 0): row for row in base_rows}
    rebuilt = list(base_rows)

    for entry, source_entry in sorted(mapping.items()):
        source = lookup.get(source_entry)
        if source is None:
            raise RuntimeError(f"{path}: source Item.dbc row {source_entry} missing for {entry}")
        row = bytearray(source)
        set_u32(row, 0, entry)
        rebuilt.append(row)

    rebuilt.sort(key=lambda row: u32(row, 0))
    patched = HEADER.pack(MAGIC, len(rebuilt), fields, record_size, len(strings)) + b"".join(rebuilt) + strings + trailing
    if patched == raw:
        return False
    path.write_bytes(patched)
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--dbc", required=True, type=Path)
    args = parser.parse_args()
    mapping = load_mapping(args.catalog)
    changed = patch(args.dbc, mapping)
    first, last = min(mapping), max(mapping)
    print(f"Gauntlet Item.dbc: {'patched' if changed else 'already current'} ({len(mapping)} custom rows, {first}-{last}).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
