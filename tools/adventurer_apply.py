#!/usr/bin/env python3
"""Apply Adventurer Core with client Item.dbc metadata for contraband items.

This wrapper deliberately patches the existing client builder at runtime instead
of introducing a second MPQ ownership path.  The normal Adventurer transaction,
server DBC install, client patch ownership, verification and rollback state all
remain authoritative.
"""

from __future__ import annotations

import struct

import client


MAGIC = b"WDBC"
HEADER = struct.Struct("<4sIIII")
ITEM_DBC = "Item.dbc"

# Custom Adventurer contraband entry -> (native Item.dbc chassis, inventory override).
# None keeps the chassis inventory type.  The two dagger entries intentionally
# force main-hand/off-hand client metadata to match item_template.
CONTRABAND_ITEMS: dict[int, tuple[int, int | None]] = {
    910200: (1917, None),
    910201: (1195, None),
    910210: (25, None),
    910211: (8178, None),
    910212: (2092, 21),
    910213: (2092, 22),
    910214: (2504, None),
    910215: (1372, None),
    910216: (85, None),
    910217: (2392, None),
    910218: (2125, None),
    910219: (2397, None),
    910220: (2119, None),
    910221: (2133, None),
    910222: (3599, None),
    910223: (2122, None),
    910224: (2393, None),
}


def _u32(record: bytearray, field: int) -> int:
    return struct.unpack_from("<I", record, field * 4)[0]


def _set_u32(record: bytearray, field: int, value: int) -> None:
    struct.pack_into("<I", record, field * 4, value)


def patch_item_dbc(path) -> bool:
    raw = path.read_bytes()
    if len(raw) < HEADER.size:
        raise client.ClientError(f"{path}: Item.dbc is too small")

    magic, count, fields, record_size, string_size = HEADER.unpack_from(raw)
    if magic != MAGIC or fields != 8 or record_size != 32:
        raise client.ClientError(
            f"{path}: unexpected Item.dbc layout magic={magic!r} fields={fields} size={record_size}"
        )

    records_start = HEADER.size
    records_end = records_start + count * record_size
    strings_end = records_end + string_size
    if strings_end > len(raw):
        raise client.ClientError(f"{path}: invalid Item.dbc sizes")

    records = [
        bytearray(raw[records_start + i * record_size:records_start + (i + 1) * record_size])
        for i in range(count)
    ]
    strings = raw[records_end:strings_end]
    trailing = raw[strings_end:]

    owned = set(CONTRABAND_ITEMS)
    stock = {_u32(row, 0): row for row in records if _u32(row, 0) not in owned}
    rebuilt = list(stock.values())

    for entry, (source_entry, inventory_override) in CONTRABAND_ITEMS.items():
        source = stock.get(source_entry)
        if source is None:
            raise client.ClientError(
                f"{path}: native Item.dbc row {source_entry} required for contraband item {entry} is missing"
            )
        row = bytearray(source)
        _set_u32(row, 0, entry)
        if inventory_override is not None:
            _set_u32(row, 6, inventory_override)
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


# Extend the existing atomic Adventurer client/server DBC bundle.  Item.dbc is
# duplicated in both root and locale archives for the same reason as the native
# talent bundle: 3.3.5a patch stacks can resolve DBFilesClient files differently.
client.CLASS_DBCS = client.CLASS_DBCS + (ITEM_DBC,)
client.DBC_NAMES = client.CLASS_DBCS + client.TALENT_DBCS
client.DBC_SOURCE_NAMES = client.DBC_NAMES + client.TALENT_SOURCE_ONLY_DBCS
client.ROOT_SHARED_DBCS = client.ROOT_SHARED_DBCS + (ITEM_DBC,)

_original_patch_dbc_copy = client.patch_dbc_copy


def _patch_dbc_copy(source, work):
    changed = _original_patch_dbc_copy(source, work)
    changed[ITEM_DBC] = patch_item_dbc(work / ITEM_DBC)
    return changed


client.patch_dbc_copy = _patch_dbc_copy

# Import only after the client module contract above has been extended so the
# front-end captures the complete DBC list and uses the patched build function.
import adventurer  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(adventurer.main())
