#!/usr/bin/env python3
"""Apply Adventurer Core with client Item.dbc metadata for custom items.

The custom item rows are built from stock Item.dbc chassis and the exact final
Item.dbc installed for worldserver is then written back into both staged Z MPQs
before they are copied to the client. This keeps server/client item metadata
byte-identical and prevents custom items from degrading to '?' icons.
"""

from __future__ import annotations

import struct

import client
import core_patch
import mpq


MAGIC = b"WDBC"
HEADER = struct.Struct("<4sIIII")
MPQ_HEADER = struct.Struct("<4sIIHHIIII")
ITEM_DBC = "Item.dbc"
ITEM_INTERNAL = "DBFilesClient\\Item.dbc"

# Custom Adventurer item entry -> native Item.dbc chassis.
# This mirrors sql/world/000_adventurer_items.sql: only items that actually
# exist in the authoritative item definition file are reserved client-side.
CONTRABAND_ITEMS: dict[int, int] = {
    910202: 3220,
    910210: 18957,
    910211: 4939,
    910212: 4947,
    910214: 4763,
    910215: 1372,
    910216: 85,
    910217: 2392,
    910218: 2125,
    910219: 2397,
    910220: 2119,
    910221: 7108,
    910222: 3599,
    910223: 2122,
    910224: 2393,
    910225: 4948,
    910226: 4562,
    910227: 1406,
    910228: 29584,
    910229: 27401,
    910230: 9514,
    910231: 3446,
}

# AzerothCore's world item_template data contains a few corrected presentation
# values that differ from the stock Item.dbc row with the same entry. Our SQL
# clones those world rows, so mirror the same presentation values into the
# custom Item.dbc rows. Field indexes: 5=DisplayInfoID, 6=InventoryType,
# 7=Sheath. These values come directly from the clean worldserver validation.
ITEM_DBC_OVERRIDES: dict[int, dict[int, int]] = {
    910210: {5: 31400, 6: 13, 7: 1},
    910211: {5: 20112},
    910212: {5: 20603},
    910214: {5: 3186},
    910221: {5: 18661},
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

    for entry, source_entry in CONTRABAND_ITEMS.items():
        source = stock.get(source_entry)
        if source is None:
            raise client.ClientError(
                f"{path}: native Item.dbc row {source_entry} required for contraband item {entry} is missing"
            )
        row = bytearray(source)
        _set_u32(row, 0, entry)
        for field, value in ITEM_DBC_OVERRIDES.get(entry, {}).items():
            _set_u32(row, field, value)
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


def _decrypt(words: list[int], key: int) -> list[int]:
    seed = 0xEEEEEEEE
    output: list[int] = []
    for cipher in words:
        seed = (seed + mpq._CRYPT[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        plain = cipher ^ ((key + seed) & 0xFFFFFFFF)
        output.append(plain)
        key = (((~key << 0x15) + 0x11111111) | (key >> 0x0B)) & 0xFFFFFFFF
        seed = (plain + seed + (seed << 5) + 3) & 0xFFFFFFFF
    return output


def _replace_raw_mpq_file(path, internal_name: str, payload: bytes) -> None:
    """Replace one raw file in an MPQ produced by tools/mpq.py.

    Our writer stores files uncompressed. The generated Item.dbc has a stable
    size because custom rows replace the same reserved entries on every update,
    so replacing the block in-place is both deterministic and preserves every
    other file in patch-Z.
    """
    raw = bytearray(path.read_bytes())
    if len(raw) < MPQ_HEADER.size:
        raise client.ClientError(f"{path}: MPQ is too small")

    magic, _header_size, _archive_size, _version, _block_shift, hash_pos, block_pos, hash_size, block_count = MPQ_HEADER.unpack_from(raw)
    if magic != b"MPQ\x1a":
        raise client.ClientError(f"{path}: invalid MPQ header")

    hash_words = list(struct.unpack_from(f"<{hash_size * 4}I", raw, hash_pos))
    hash_words = _decrypt(hash_words, mpq._hash_string("(hash table)", 3))
    block_words = list(struct.unpack_from(f"<{block_count * 4}I", raw, block_pos))
    block_words = _decrypt(block_words, mpq._hash_string("(block table)", 3))

    wanted_a = mpq._hash_string(internal_name, 1)
    wanted_b = mpq._hash_string(internal_name, 2)
    index = mpq._hash_string(internal_name, 0) & (hash_size - 1)
    block_index = None
    for _ in range(hash_size):
        a, b, _locale, candidate = hash_words[index * 4:index * 4 + 4]
        if candidate == 0xFFFFFFFF:
            break
        if a == wanted_a and b == wanted_b:
            block_index = candidate
            break
        index = (index + 1) & (hash_size - 1)

    if block_index is None or block_index >= block_count:
        raise client.ClientError(f"{path}: {internal_name} is missing from staged Z patch")

    offset, stored_size, file_size, flags = block_words[block_index * 4:block_index * 4 + 4]
    if not (flags & 0x80000000):
        raise client.ClientError(f"{path}: {internal_name} block is not an active MPQ file")
    if stored_size != file_size or file_size != len(payload):
        raise client.ClientError(
            f"{path}: cannot safely replace {internal_name}: MPQ={stored_size}/{file_size}, payload={len(payload)}"
        )

    raw[offset:offset + file_size] = payload
    path.write_bytes(raw)
    if payload not in path.read_bytes():
        raise client.ClientError(f"{path}: {internal_name} readback verification failed")


# Extend the existing atomic Adventurer client/server DBC bundle. Item.dbc is
# duplicated in both root and locale Z archives.
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

# install_server_dbcs runs after build_patch but before install_patch. At this
# exact point the final server Item.dbc is known and the client Z files are still
# staged, so force both client archives to contain the identical final bytes.
_original_install_server_dbcs = client.install_server_dbcs


def _install_server_dbcs(build_dir, server_dbc_dir):
    result = _original_install_server_dbcs(build_dir, server_dbc_dir)
    final_item = (server_dbc_dir / ITEM_DBC).read_bytes()

    root_patch = build_dir / "Data" / f"patch-{client.PROJECT_SUFFIX}.mpq"
    locale_candidates = list((build_dir / "Data").glob(f"*/patch-*-{client.PROJECT_SUFFIX.lower()}.mpq"))
    if not root_patch.is_file() or len(locale_candidates) != 1:
        raise client.ClientError(
            "Staged Adventurer Z patches are incomplete while syncing Item.dbc"
        )

    _replace_raw_mpq_file(root_patch, ITEM_INTERNAL, final_item)
    _replace_raw_mpq_file(locale_candidates[0], ITEM_INTERNAL, final_item)
    print(f"Contraband Item.dbc synchronized into both Z patches ({len(final_item)} bytes).")
    return result


client.install_server_dbcs = _install_server_dbcs


# Tame Beast (1515) is a native Hunter spell, but SpellDraft can legitimately
# grant it to class 10. Keep AzerothCore's normal tame flow and relax only the
# final class gate for an Adventurer that actually knows 1515.
def _patch_adventurer_tame_beast(text: str) -> str:
    clean = """    if (!m_caster->IsClass(CLASS_HUNTER, CLASS_CONTEXT_PET))
        return;"""
    patched = """    if (!m_caster->IsClass(CLASS_HUNTER, CLASS_CONTEXT_PET))
    {
        Player* player = m_caster->ToPlayer();
        if (!player || player->getClass() != CLASS_ADVENTURER || !player->HasSpell(1515))
            return;
    }"""
    return core_patch.replace_once(
        text,
        clean,
        patched,
        "SpellEffects Adventurer Tame Beast class gate",
    )


core_patch.TRANSFORMS["src/server/game/Spells/SpellEffects.cpp"] = _patch_adventurer_tame_beast

# Keep the source-layer universal chassis at 75% while accepting an existing
# owned 75% install on future upgrades.
import chassis_75  # noqa: E402,F401

# Import only after the client/core contracts above have been extended so the
# front-end captures the complete DBC list and patched source transforms.
import adventurer  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(adventurer.main())