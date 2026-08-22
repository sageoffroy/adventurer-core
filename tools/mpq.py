#!/usr/bin/env python3
"""Minimal MPQ v1 writer for the Adventurer Core client patch."""

from __future__ import annotations

import struct
from pathlib import Path


def _build_crypt_table() -> list[int]:
    table = [0] * 0x500
    seed = 0x00100001
    for index1 in range(0x100):
        index2 = index1
        for _ in range(5):
            seed = (seed * 125 + 3) % 0x2AAAAB
            temp1 = (seed & 0xFFFF) << 0x10
            seed = (seed * 125 + 3) % 0x2AAAAB
            temp2 = seed & 0xFFFF
            table[index2] = temp1 | temp2
            index2 += 0x100
    return table


_CRYPT = _build_crypt_table()


def _hash_string(value: str, hash_type: int) -> int:
    seed1, seed2 = 0x7FED7FED, 0xEEEEEEEE
    for ch in value.upper():
        crypt_value = _CRYPT[(hash_type << 8) + ord(ch)]
        seed1 = (crypt_value ^ ((seed1 + seed2) & 0xFFFFFFFF)) & 0xFFFFFFFF
        seed2 = (ord(ch) + seed1 + seed2 + (seed2 << 5) + 3) & 0xFFFFFFFF
    return seed1


def _encrypt(words: list[int], key: int) -> list[int]:
    seed = 0xEEEEEEEE
    output: list[int] = []
    for word in words:
        seed = (seed + _CRYPT[0x400 + (key & 0xFF)]) & 0xFFFFFFFF
        output.append(word ^ ((key + seed) & 0xFFFFFFFF))
        key = (((~key << 0x15) + 0x11111111) | (key >> 0x0B)) & 0xFFFFFFFF
        seed = (word + seed + (seed << 5) + 3) & 0xFFFFFFFF
    return output


def build_mpq(files: dict[str, bytes]) -> bytes:
    archive_files = dict(files)
    archive_files["(listfile)"] = ("\r\n".join(archive_files) + "\r\n").encode()

    hash_size = 1
    while hash_size < len(archive_files) * 2:
        hash_size *= 2

    header_size = 32
    blobs: list[bytes] = []
    block_entries: list[tuple[int, int, int, int]] = []
    offset = header_size
    hash_entries = [[0xFFFFFFFF] * 4 for _ in range(hash_size)]

    for block_index, (name, data) in enumerate(archive_files.items()):
        blobs.append(data)
        # Raw multi-sector storage is deliberate. SINGLE_UNIT archives have
        # caused instability in the 3.3.5a async MPQ reader.
        block_entries.append((offset, len(data), len(data), 0x80000000))
        index = _hash_string(name, 0) & (hash_size - 1)
        while hash_entries[index][3] != 0xFFFFFFFF:
            index = (index + 1) & (hash_size - 1)
        hash_entries[index] = [
            _hash_string(name, 1),
            _hash_string(name, 2),
            0,
            block_index,
        ]
        offset += len(data)

    hash_words = [word for entry in hash_entries for word in entry]
    block_words = [word for entry in block_entries for word in entry]
    hash_data = struct.pack(
        f"<{len(hash_words)}I",
        *_encrypt(hash_words, _hash_string("(hash table)", 3)),
    )
    block_data = struct.pack(
        f"<{len(block_words)}I",
        *_encrypt(block_words, _hash_string("(block table)", 3)),
    )

    hash_pos = offset
    block_pos = hash_pos + len(hash_data)
    archive_size = block_pos + len(block_data)
    header = struct.pack(
        "<4sIIHHIIII",
        b"MPQ\x1a",
        header_size,
        archive_size,
        0,
        3,
        hash_pos,
        block_pos,
        hash_size,
        len(block_entries),
    )
    return header + b"".join(blobs) + hash_data + block_data


def write_mpq(path: Path, files: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(build_mpq(files))
