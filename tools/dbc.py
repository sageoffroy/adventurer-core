#!/usr/bin/env python3
"""WotLK 3.3.5a DBC transformations for native Adventurer class ID 10.

The patcher is intentionally independent from SpellDraft. It owns only the
class/race metadata required by the server and client for a classless native
class. All transforms validate their input layout and are idempotent.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

MAGIC = b"WDBC"
HEADER = struct.Struct("<4sIIII")
ADVENTURER_CLASS = 10
ADVENTURER_CLASS_MASK = 1 << (ADVENTURER_CLASS - 1)
PLAYABLE_RACES = (1, 2, 3, 4, 5, 6, 7, 8, 10, 11)

# ChrClasses.dbc localized string positions. Each block is 16 locale offsets
# followed by one flags field. WotLK order starts enUS=0 and uses esES=6,
# esMX=7.
CHR_CLASS_NAME_BLOCKS = (4, 21, 38)
LOCALE_ENUS = 0
LOCALE_ESES = 6
LOCALE_ESMX = 7

UNIVERSAL_SKILLS = {
    43, 44, 45, 46, 54, 55, 95, 136, 160, 162, 172, 173, 176,
    226, 228, 229, 293, 413, 414, 415, 433, 473,
}

RACE_NATIVE_SKILLS: dict[int, tuple[int, ...]] = {
    1: (98, 754),
    2: (109, 125),
    3: (98, 111, 101),
    4: (98, 113, 126),
    5: (109, 673, 220),
    6: (109, 115, 124),
    7: (98, 313, 753),
    8: (109, 315, 733),
    10: (109, 137, 756),
    11: (98, 759, 760),
}
RACE_NATIVE_SKILL_IDS = {skill for skills in RACE_NATIVE_SKILLS.values() for skill in skills}
BASELINE_SKILL_SENTINELS = {163, 762, 777}

MAX_OUTFIT_ITEMS = 24
CHARSTART_ITEM_IDS_OFFSET = 8
CHARSTART_DISPLAY_IDS_OFFSET = CHARSTART_ITEM_IDS_OFFSET + MAX_OUTFIT_ITEMS * 4
CHARSTART_INVENTORY_TYPES_OFFSET = CHARSTART_DISPLAY_IDS_OFFSET + MAX_OUTFIT_ITEMS * 4
CHARSTART_FULL_RECORD_SIZE = CHARSTART_INVENTORY_TYPES_OFFSET + MAX_OUTFIT_ITEMS * 4
ADVENTURER_STARTER_ITEMS = (25, 2362, 2504, 2512)
REPLACED_COMBAT_INVENTORY_TYPES = {13, 14, 15, 17, 21, 22, 23, 24, 25, 26, 28}
STARTER_ITEM_FALLBACK_INVENTORY_TYPE = {25: 13, 2362: 14, 2504: 15, 2512: 24}


class DBCError(RuntimeError):
    pass


@dataclass
class DBC:
    fields: int
    record_size: int
    records: list[bytearray]
    strings: bytearray
    trailing: bytes = b""

    @classmethod
    def read(cls, path: Path) -> "DBC":
        data = path.read_bytes()
        if len(data) < HEADER.size:
            raise DBCError(f"{path}: file is too small")
        magic, count, fields, record_size, string_size = HEADER.unpack_from(data)
        if magic != MAGIC:
            raise DBCError(f"{path}: expected WDBC, got {magic!r}")
        records_start = HEADER.size
        records_end = records_start + count * record_size
        strings_end = records_end + string_size
        if records_end < records_start or strings_end > len(data):
            raise DBCError(f"{path}: header sizes exceed file size")
        records = [
            bytearray(data[records_start + i * record_size: records_start + (i + 1) * record_size])
            for i in range(count)
        ]
        return cls(fields, record_size, records, bytearray(data[records_end:strings_end]), data[strings_end:])

    def to_bytes(self) -> bytes:
        header = HEADER.pack(MAGIC, len(self.records), self.fields, self.record_size, len(self.strings))
        return header + b"".join(self.records) + bytes(self.strings) + self.trailing

    def write(self, path: Path) -> None:
        path.write_bytes(self.to_bytes())

    def append_string(self, value: str) -> int:
        encoded = value.encode("utf-8") + b"\0"
        pos = bytes(self.strings).find(encoded)
        if pos >= 0:
            return pos
        pos = len(self.strings)
        self.strings.extend(encoded)
        return pos


def u32(record: bytearray, field: int) -> int:
    return struct.unpack_from("<I", record, field * 4)[0]


def set_u32(record: bytearray, field: int, value: int) -> None:
    struct.pack_into("<I", record, field * 4, value)


def patch_chrclasses(path: Path) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != 60 or dbc.record_size != 240:
        raise DBCError(f"{path}: unexpected ChrClasses layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    targets = [r for r in dbc.records if u32(r, 0) == ADVENTURER_CLASS]
    if targets:
        target = targets[0]
        dbc.records = [r for r in dbc.records if u32(r, 0) != ADVENTURER_CLASS or r is target]
    else:
        warrior = next((r for r in dbc.records if u32(r, 0) == 1), None)
        if warrior is None:
            raise DBCError(f"{path}: Warrior template row (class 1) not found")
        target = bytearray(warrior)
        dbc.records.append(target)

    set_u32(target, 0, ADVENTURER_CLASS)
    set_u32(target, 2, 0)   # mana
    set_u32(target, 56, 0)  # no stock spell family
    set_u32(target, 58, 0)  # no class cinematic
    set_u32(target, 59, 0)  # Classic availability

    localized = (
        ("Adventurer", "Aventurero", "Aventurero"),
        ("Adventurer", "Aventurera", "Aventurera"),
        ("Adventurer", "Aventurero", "Aventurero"),
    )
    for block, (english, es_es, es_mx) in zip(CHR_CLASS_NAME_BLOCKS, localized):
        english_offset = dbc.append_string(english)
        spanish_offsets = {
            LOCALE_ESES: dbc.append_string(es_es),
            LOCALE_ESMX: dbc.append_string(es_mx),
        }
        # Do not inherit "Warrior" from the template in unsupported locales.
        # English is a safe fallback; Spanish gets first-class locale strings.
        for locale in range(16):
            set_u32(target, block + locale, spanish_offsets.get(locale, english_offset))

    dbc.records.sort(key=lambda r: u32(r, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
        return True
    return False


def desired_charbase_pairs() -> list[tuple[int, int]]:
    return [(race, ADVENTURER_CLASS) for race in PLAYABLE_RACES]


def patch_charbaseinfo(path: Path) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != 2 or dbc.record_size != 2:
        raise DBCError(f"{path}: unexpected CharBaseInfo layout {dbc.fields}/{dbc.record_size}")
    desired = [bytearray((race, klass)) for race, klass in desired_charbase_pairs()]
    if [bytes(r) for r in dbc.records] == [bytes(r) for r in desired]:
        return False
    dbc.records = desired
    dbc.write(path)
    return True


def validate_charbaseinfo(path: Path) -> None:
    dbc = DBC.read(path)
    actual = [(r[0], r[1]) for r in dbc.records]
    if actual != desired_charbase_pairs():
        raise DBCError(f"{path}: expected only Adventurer creation pairs, got {actual}")


def read_outfit_entry(record: bytearray, index: int) -> tuple[int, int, int]:
    item_id = struct.unpack_from("<i", record, CHARSTART_ITEM_IDS_OFFSET + index * 4)[0]
    display_id = struct.unpack_from("<i", record, CHARSTART_DISPLAY_IDS_OFFSET + index * 4)[0]
    inventory_type = struct.unpack_from("<i", record, CHARSTART_INVENTORY_TYPES_OFFSET + index * 4)[0]
    return item_id, display_id, inventory_type


def write_outfit_entry(record: bytearray, index: int, item_id: int, display_id: int, inventory_type: int) -> None:
    struct.pack_into("<i", record, CHARSTART_ITEM_IDS_OFFSET + index * 4, item_id)
    struct.pack_into("<i", record, CHARSTART_DISPLAY_IDS_OFFSET + index * 4, display_id)
    struct.pack_into("<i", record, CHARSTART_INVENTORY_TYPES_OFFSET + index * 4, inventory_type)


def collect_outfit_item_metadata(records: list[bytearray]) -> dict[int, tuple[int, int]]:
    metadata: dict[int, tuple[int, int]] = {}
    wanted = set(ADVENTURER_STARTER_ITEMS)
    for row in records:
        for index in range(MAX_OUTFIT_ITEMS):
            item_id, display_id, inventory_type = read_outfit_entry(row, index)
            if item_id in wanted and item_id not in metadata:
                metadata[item_id] = (display_id, inventory_type)
    return metadata


def apply_starter_outfit(row: bytearray, metadata: dict[int, tuple[int, int]]) -> None:
    preserved: list[tuple[int, int, int]] = []
    for index in range(MAX_OUTFIT_ITEMS):
        item_id, display_id, inventory_type = read_outfit_entry(row, index)
        if item_id <= 0 or item_id in ADVENTURER_STARTER_ITEMS:
            continue
        if inventory_type in REPLACED_COMBAT_INVENTORY_TYPES:
            continue
        preserved.append((item_id, display_id, inventory_type))

    starter = [
        (item_id, *metadata.get(item_id, (0, STARTER_ITEM_FALLBACK_INVENTORY_TYPE[item_id])))
        for item_id in ADVENTURER_STARTER_ITEMS
    ]
    entries = preserved + starter
    if len(entries) > MAX_OUTFIT_ITEMS:
        raise DBCError(f"Adventurer starter outfit exceeds {MAX_OUTFIT_ITEMS} items")
    for index in range(MAX_OUTFIT_ITEMS):
        write_outfit_entry(row, index, 0, 0, 0)
    for index, entry in enumerate(entries):
        write_outfit_entry(row, index, *entry)


def patch_charstartoutfit(path: Path) -> bool:
    dbc = DBC.read(path)
    if dbc.record_size < CHARSTART_FULL_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected CharStartOutfit record size {dbc.record_size}")
    before = dbc.to_bytes()

    def key(r: bytearray) -> tuple[int, int, int]:
        return r[4], r[5], r[6]

    vanilla = [r for r in dbc.records if r[5] != ADVENTURER_CLASS]
    existing = {key(r): r for r in dbc.records if r[5] == ADVENTURER_CLASS}
    metadata = collect_outfit_item_metadata(vanilla)
    next_id = max((u32(r, 0) for r in vanilla), default=0) + 1
    rebuilt = list(vanilla)

    for race in PLAYABLE_RACES:
        for gender in (0, 1):
            wanted = (race, ADVENTURER_CLASS, gender)
            row = existing.get(wanted)
            if row is None:
                template = next((r for r in vanilla if key(r) == (race, 1, gender)), None)
                if template is None:
                    template = next((r for r in vanilla if r[4] == race and r[6] == gender and r[5] != 6), None)
                if template is None:
                    raise DBCError(f"{path}: no outfit template for race={race}, gender={gender}")
                row = bytearray(template)
                set_u32(row, 0, next_id)
                next_id += 1
                row[5] = ADVENTURER_CLASS
            apply_starter_outfit(row, metadata)
            rebuilt.append(row)

    rebuilt.sort(key=lambda r: (r[4], r[5], r[6], u32(r, 0)))
    dbc.records = rebuilt
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
        return True
    return False


def validate_charstartoutfit(path: Path) -> None:
    dbc = DBC.read(path)
    expected = {(race, ADVENTURER_CLASS, gender) for race in PLAYABLE_RACES for gender in (0, 1)}
    seen: set[tuple[int, int, int]] = set()
    for row in dbc.records:
        if row[5] != ADVENTURER_CLASS:
            continue
        key = (row[4], row[5], row[6])
        if key in seen:
            raise DBCError(f"{path}: duplicate Adventurer outfit {key}")
        seen.add(key)
        item_ids = {read_outfit_entry(row, i)[0] for i in range(MAX_OUTFIT_ITEMS)}
        missing = set(ADVENTURER_STARTER_ITEMS) - item_ids
        if missing:
            raise DBCError(f"{path}: outfit {key} missing starter items {sorted(missing)}")
    if seen != expected:
        raise DBCError(f"{path}: expected 20 Adventurer outfits, got {sorted(seen)}")


def race_bit(race: int) -> int:
    return 1 << (race - 1)


def row_applies_to_race(row: bytearray, race: int) -> bool:
    mask = u32(row, 2)
    return mask == 0 or bool(mask & race_bit(race))


def row_applies_to_adventurer(row: bytearray) -> bool:
    mask = u32(row, 3)
    return mask == 0 or bool(mask & ADVENTURER_CLASS_MASK)


def class_bound_skill_ids(records: list[bytearray]) -> set[int]:
    return {u32(r, 1) for r in records if u32(r, 3) != 0 and u32(r, 1) not in RACE_NATIVE_SKILL_IDS}


def covers_all_adventurer_races(records: list[bytearray], skill: int) -> bool:
    return all(any(
        u32(row, 1) == skill and row_applies_to_race(row, race) and row_applies_to_adventurer(row)
        for row in records
    ) for race in PLAYABLE_RACES)


def choose_skill_template(records: list[bytearray], skill: int) -> bytearray:
    candidates = [row for row in records if u32(row, 1) == skill]
    if not candidates:
        raise DBCError(f"SkillRaceClassInfo has no template for skill {skill}")

    def score(row: bytearray) -> tuple[int, int, int]:
        class_mask, race_mask = u32(row, 3), u32(row, 2)
        class_width = 32 if class_mask == 0 else class_mask.bit_count()
        race_width = 32 if race_mask == 0 else race_mask.bit_count()
        return -class_width, u32(row, 5), -race_width

    return min(candidates, key=score)


def patch_skillraceclassinfo(path: Path) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != 8 or dbc.record_size != 32:
        raise DBCError(f"{path}: unexpected SkillRaceClassInfo layout {dbc.fields}/{dbc.record_size}")
    before = dbc.to_bytes()

    wanted = {(race, skill) for race, skills in RACE_NATIVE_SKILLS.items() for skill in skills}
    for row in dbc.records:
        skill = u32(row, 1)
        class_mask = u32(row, 3)
        if class_mask == 0 or skill not in RACE_NATIVE_SKILL_IDS:
            continue
        if any(wanted_skill == skill and row_applies_to_race(row, race) for race, wanted_skill in wanted):
            set_u32(row, 3, class_mask | ADVENTURER_CLASS_MASK)

    next_id = max((u32(row, 0) for row in dbc.records), default=0) + 1
    for skill in sorted(class_bound_skill_ids(dbc.records)):
        if covers_all_adventurer_races(dbc.records, skill):
            continue
        clone = bytearray(choose_skill_template(dbc.records, skill))
        set_u32(clone, 0, next_id)
        set_u32(clone, 2, 0)
        set_u32(clone, 3, ADVENTURER_CLASS_MASK)
        dbc.records.append(clone)
        next_id += 1

    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    validate_skillraceclassinfo(path)
    return after != before


def validate_skillraceclassinfo(path: Path) -> None:
    dbc = DBC.read(path)
    if dbc.fields != 8 or dbc.record_size != 32:
        raise DBCError(f"{path}: unexpected SkillRaceClassInfo layout")
    missing_racial = []
    for race, skills in RACE_NATIVE_SKILLS.items():
        for skill in skills:
            if not any(u32(row, 1) == skill and row_applies_to_race(row, race) and row_applies_to_adventurer(row) for row in dbc.records):
                missing_racial.append((race, skill))
    if missing_racial:
        raise DBCError(f"{path}: missing Adventurer racial/language mappings {missing_racial}")
    missing_classless = [skill for skill in sorted(class_bound_skill_ids(dbc.records)) if not covers_all_adventurer_races(dbc.records, skill)]
    if missing_classless:
        raise DBCError(f"{path}: missing Adventurer classless mappings {missing_classless}")
    missing_sentinels = [skill for skill in sorted(BASELINE_SKILL_SENTINELS) if not covers_all_adventurer_races(dbc.records, skill)]
    if missing_sentinels:
        raise DBCError(f"{path}: missing baseline mappings {missing_sentinels}")


PATCHERS = {
    "ChrClasses.dbc": patch_chrclasses,
    "CharBaseInfo.dbc": patch_charbaseinfo,
    "CharStartOutfit.dbc": patch_charstartoutfit,
    "SkillRaceClassInfo.dbc": patch_skillraceclassinfo,
}


def patch_directory(dbc_dir: Path) -> dict[str, bool]:
    missing = [name for name in PATCHERS if not (dbc_dir / name).is_file()]
    if missing:
        raise DBCError("Missing required DBC(s): " + ", ".join(missing))
    changed = {name: patcher(dbc_dir / name) for name, patcher in PATCHERS.items()}
    validate_charbaseinfo(dbc_dir / "CharBaseInfo.dbc")
    validate_charstartoutfit(dbc_dir / "CharStartOutfit.dbc")
    validate_skillraceclassinfo(dbc_dir / "SkillRaceClassInfo.dbc")
    return changed
