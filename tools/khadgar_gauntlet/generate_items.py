#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import re
import struct
from pathlib import Path

QUALITY = {
    "2": 2, "green": 2, "verde": 2, "uncommon": 2,
    "3": 3, "blue": 3, "azul": 3, "rare": 3,
    "4": 4, "purple": 4, "violet": 4, "violeta": 4, "epic": 4,
    "5": 5, "orange": 5, "legendary": 5, "legendario": 5,
}
STAT_COLUMNS = [
    ("strength", 4), ("agility", 3), ("stamina", 7), ("intellect", 5), ("spirit", 6),
    ("attack_power", 38), ("spell_power", 45), ("hit_rating", 31), ("crit_rating", 32), ("haste_rating", 36),
]
REQUIRED_COLUMNS = {
    "enabled", "entry", "source_entry", "display_id", "set_key", "name", "quality",
    "required_level", "item_level", "strength", "agility", "stamina", "intellect", "spirit",
    "attack_power", "spell_power", "hit_rating", "crit_rating", "haste_rating", "armor", "block",
    "dmg_min1", "dmg_max1", "delay", "equip_spell1", "equip_spell2",
    "proc_spell1", "proc_ppm1", "description",
}
SET_KEY_RE = re.compile(r"^[a-z0-9_]+$")
DBC_HEADER = struct.Struct("<4sIIII")
DBC_ROW = struct.Struct("<IIIiiIII")


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def parse_int(value: str, field: str, line: int, *, minimum=None, maximum=None) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise ValueError(f"line {line}: {field} must be an integer, got {value!r}") from exc
    if minimum is not None and number < minimum:
        raise ValueError(f"line {line}: {field} must be >= {minimum}")
    if maximum is not None and number > maximum:
        raise ValueError(f"line {line}: {field} must be <= {maximum}")
    return number


def optional_number(value: str, field: str, line: int, *, integer=False):
    value = value.strip()
    if not value:
        return None
    try:
        return int(value) if integer else float(value)
    except ValueError as exc:
        raise ValueError(f"line {line}: {field} must be a {'integer' if integer else 'number'}") from exc


def load_item_dbc(path: Path) -> dict[int, tuple[int, int, int, int, int, int, int]]:
    raw = path.read_bytes()
    if len(raw) < DBC_HEADER.size:
        raise ValueError(f"{path}: Item.dbc too small")
    magic, count, fields, record_size, string_size = DBC_HEADER.unpack_from(raw)
    if magic != b"WDBC" or fields != 8 or record_size != DBC_ROW.size:
        raise ValueError(f"{path}: unexpected Item.dbc layout")
    records_end = DBC_HEADER.size + count * record_size
    if records_end + string_size > len(raw):
        raise ValueError(f"{path}: invalid Item.dbc sizes")
    result = {}
    for index in range(count):
        offset = DBC_HEADER.size + index * record_size
        entry, item_class, subclass, sound, material, display, inventory, sheath = DBC_ROW.unpack_from(raw, offset)
        result[entry] = (item_class, subclass, sound, material, display, inventory, sheath)
    return result


def generate_row(row: dict[str, str], line: int, dbc_rows) -> str:
    entry = parse_int(row["entry"].strip(), "entry", line, minimum=911000, maximum=911999)
    source = parse_int(row["source_entry"].strip(), "source_entry", line, minimum=1)
    if 911000 <= source <= 911999:
        raise ValueError(f"line {line}: source_entry must be a stock item")
    chassis = dbc_rows.get(source)
    if chassis is None:
        raise ValueError(f"line {line}: source_entry {source} is missing from Item.dbc")
    item_class, subclass, sound, material, dbc_display, inventory, sheath = chassis

    display = optional_number(row["display_id"], "display_id", line, integer=True)
    if display is None:
        display = dbc_display
    if display <= 0:
        raise ValueError(f"line {line}: display_id must be positive")

    set_key = row["set_key"].strip().lower()
    if set_key and not SET_KEY_RE.fullmatch(set_key):
        raise ValueError(f"line {line}: invalid set_key")
    name = row["name"].strip()
    if not name:
        raise ValueError(f"line {line}: name cannot be empty")
    quality_key = row["quality"].strip().lower()
    if quality_key not in QUALITY:
        raise ValueError(f"line {line}: unsupported quality {quality_key!r}")
    quality = QUALITY[quality_key]
    required_level = parse_int(row["required_level"].strip(), "required_level", line, minimum=0, maximum=80)
    item_level = parse_int(row["item_level"].strip(), "item_level", line, minimum=1, maximum=284)
    if item_level < required_level:
        raise ValueError(f"line {line}: item_level cannot be lower than required_level")

    stats = []
    for column, stat_type in STAT_COLUMNS:
        value = row[column].strip()
        if not value:
            continue
        number = parse_int(value, column, line)
        if number:
            stats.append((stat_type, number))
    if len(stats) > 10:
        raise ValueError(f"line {line}: WoW supports at most 10 item stats")

    armor = optional_number(row["armor"], "armor", line, integer=True)
    block = optional_number(row["block"], "block", line, integer=True)
    dmg_min = optional_number(row["dmg_min1"], "dmg_min1", line)
    dmg_max = optional_number(row["dmg_max1"], "dmg_max1", line)
    delay = optional_number(row["delay"], "delay", line, integer=True)

    equip_spells = [
        optional_number(row["equip_spell1"], "equip_spell1", line, integer=True),
        optional_number(row["equip_spell2"], "equip_spell2", line, integer=True),
    ]
    proc_spell = optional_number(row["proc_spell1"], "proc_spell1", line, integer=True)
    proc_ppm = optional_number(row["proc_ppm1"], "proc_ppm1", line)

    if (dmg_min is None) != (dmg_max is None):
        raise ValueError(f"line {line}: dmg_min1 and dmg_max1 must be supplied together")
    if dmg_min is not None and dmg_max < dmg_min:
        raise ValueError(f"line {line}: dmg_max1 cannot be lower than dmg_min1")
    if proc_spell is None and proc_ppm is not None:
        raise ValueError(f"line {line}: proc_ppm1 requires proc_spell1")
    if proc_spell is not None:
        if proc_spell <= 0:
            raise ValueError(f"line {line}: proc_spell1 must be positive")
        if proc_ppm is None or proc_ppm <= 0:
            raise ValueError(f"line {line}: proc_ppm1 must be positive when proc_spell1 is set")
        if any(spell is not None for spell in equip_spells):
            raise ValueError(f"line {line}: proc_spell1 currently cannot share spell slots with equip_spell1/2")

    updates = [
        f"`entry` = {entry}", f"`class` = {item_class}", f"`subclass` = {subclass}",
        f"`SoundOverrideSubclass` = {sound}", f"`Material` = {material}", f"`displayid` = {display}",
        f"`InventoryType` = {inventory}", f"`sheath` = {sheath}", f"`name` = {sql_string(name)}",
        f"`Quality` = {quality}", f"`RequiredLevel` = {required_level}", f"`ItemLevel` = {item_level}",
        "`AllowableClass` = -1", "`AllowableRace` = -1", "`itemset` = 0",
    ]
    for index in range(1, 11):
        stat_type, stat_value = stats[index - 1] if index <= len(stats) else (0, 0)
        updates += [f"`stat_type{index}` = {stat_type}", f"`stat_value{index}` = {stat_value}"]
    if armor is not None:
        updates.append(f"`armor` = {armor}")
    if block is not None:
        updates.append(f"`block` = {block}")
    if dmg_min is not None:
        updates += [f"`dmg_min1` = {dmg_min:g}", f"`dmg_max1` = {dmg_max:g}"]
    if delay is not None:
        updates.append(f"`delay` = {delay}")

    for index in range(1, 6):
        updates += [
            f"`spellid_{index}` = 0", f"`spelltrigger_{index}` = 0", f"`spellcharges_{index}` = 0",
            f"`spellppmRate_{index}` = 0", f"`spellcooldown_{index}` = -1", f"`spellcategory_{index}` = 0",
            f"`spellcategorycooldown_{index}` = -1",
        ]

    for index, spell in enumerate(equip_spells, start=1):
        if spell is not None:
            if spell <= 0:
                raise ValueError(f"line {line}: equip_spell{index} must be positive")
            updates += [f"`spellid_{index}` = {spell}", f"`spelltrigger_{index}` = 1"]

    if proc_spell is not None:
        # ITEM_SPELLTRIGGER_CHANCE_ON_HIT = 2 in the 3.3.5a item template contract.
        updates += [
            f"`spellid_1` = {proc_spell}",
            "`spelltrigger_1` = 2",
            f"`spellppmRate_1` = {proc_ppm:g}",
        ]

    updates += [f"`description` = {sql_string(row['description'].strip())}", "`VerifiedBuild` = 0"]
    temp = f"tmp_adventurer_gauntlet_item_{entry}"
    return "\n".join([
        f"-- {entry}: {name}" + (f" [set={set_key}]" if set_key else ""),
        f"DROP TEMPORARY TABLE IF EXISTS `{temp}`;",
        f"CREATE TEMPORARY TABLE `{temp}` AS SELECT * FROM `item_template` WHERE `entry` = {source};",
        f"UPDATE `{temp}` SET\n    " + ",\n    ".join(updates) + ";",
        f"INSERT INTO `item_template` SELECT * FROM `{temp}`;",
        f"DROP TEMPORARY TABLE IF EXISTS `{temp}`;",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Adventurer Gauntlet item_template SQL from CSV")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--item-dbc", required=True, type=Path)
    args = parser.parse_args()

    dbc_rows = load_item_dbc(args.item_dbc)
    blocks = []
    seen_entries: set[int] = set()
    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames is None:
            raise SystemExit("catalog has no header")
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise SystemExit("catalog is missing columns: " + ", ".join(sorted(missing)))
        for line, row in enumerate(reader, start=2):
            enabled = (row.get("enabled") or "").strip().lower()
            if enabled in {"", "0", "false", "no", "off"}:
                continue
            if enabled not in {"1", "true", "yes", "on"}:
                raise SystemExit(f"line {line}: enabled must be 0/1")
            entry = parse_int(row["entry"].strip(), "entry", line, minimum=911000, maximum=911999)
            if entry in seen_entries:
                raise SystemExit(f"line {line}: duplicate custom entry {entry}")
            seen_entries.add(entry)
            blocks.append(generate_row(row, line, dbc_rows))

    if not seen_entries:
        raise SystemExit("catalog has no enabled Gauntlet items")
    first, last = min(seen_entries), max(seen_entries)
    expected = set(range(first, last + 1))
    if seen_entries != expected:
        missing = sorted(expected - seen_entries)
        raise SystemExit(f"Gauntlet catalog must be contiguous; first missing entries: {missing[:10]}")

    header = [
        "-- GENERATED FILE. Do not edit by hand.",
        f"-- Source: {args.input.name}",
        f"-- Chassis source: {args.item_dbc}",
        f"-- Owned Gauntlet item range: {first}-{last}.",
        f"DELETE FROM `item_template` WHERE `entry` BETWEEN {first} AND {last};",
        "",
    ]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(header + blocks) + "\n", encoding="utf-8")
    print(f"Generated {len(seen_entries)} Gauntlet item_template rows ({first}-{last}) -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
