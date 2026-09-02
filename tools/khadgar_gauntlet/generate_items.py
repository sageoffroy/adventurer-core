#!/usr/bin/env python3
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
    "dmg_min1", "dmg_max1", "delay", "equip_spell1", "equip_spell2", "description",
}

SET_KEY_RE = re.compile(r"^[a-z0-9_]+$")
DBC_HEADER = struct.Struct("<4sIIII")
DBC_ROW = struct.Struct("<8I")


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


def parse_optional_number(value: str, field: str, line: int, *, integer=False):
    value = value.strip()
    if not value:
        return None
    try:
        return int(value) if integer else float(value)
    except ValueError as exc:
        kind = "integer" if integer else "number"
        raise ValueError(f"line {line}: {field} must be a {kind}, got {value!r}") from exc


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
        entry, item_class, subclass, sound_override, material, display_id, inventory_type, sheath = DBC_ROW.unpack_from(raw, offset)
        result[entry] = (item_class, subclass, sound_override, material, display_id, inventory_type, sheath)
    return result


def generate_row(row, line: int, dbc_rows: dict[int, tuple[int, int, int, int, int, int, int]]) -> str:
    entry = parse_int(row["entry"].strip(), "entry", line, minimum=911000, maximum=911999)
    source = parse_int(row["source_entry"].strip(), "source_entry", line, minimum=1)
    if 911000 <= source <= 911999:
        raise ValueError(f"line {line}: source_entry must be a stock item, not another gauntlet item")

    chassis = dbc_rows.get(source)
    if chassis is None:
        raise ValueError(f"line {line}: source_entry {source} is missing from Item.dbc")
    item_class, subclass, sound_override, material, dbc_display_id, inventory_type, sheath = chassis

    display_id = parse_optional_number(row["display_id"], "display_id", line, integer=True)
    if display_id is None:
        display_id = dbc_display_id
    if display_id <= 0:
        raise ValueError(f"line {line}: display_id must be positive")

    set_key = row["set_key"].strip().lower()
    if set_key and not SET_KEY_RE.fullmatch(set_key):
        raise ValueError(f"line {line}: set_key may contain only lowercase letters, numbers and underscores")

    name = row["name"].strip()
    if not name:
        raise ValueError(f"line {line}: name cannot be empty")

    quality_key = row["quality"].strip().lower()
    if quality_key not in QUALITY:
        raise ValueError(f"line {line}: quality must be green/blue/purple/legendary (or 2/3/4/5)")
    quality = QUALITY[quality_key]

    required_level = parse_int(row["required_level"].strip(), "required_level", line, minimum=0, maximum=80)
    item_level = parse_int(row["item_level"].strip(), "item_level", line, minimum=1, maximum=284)
    if item_level < required_level:
        raise ValueError(f"line {line}: item_level cannot be lower than required_level")

    stats = []
    for column, stat_type in STAT_COLUMNS:
        raw = row[column].strip()
        if not raw:
            continue
        value = parse_int(raw, column, line)
        if value:
            stats.append((stat_type, value))
    if len(stats) > 10:
        raise ValueError(f"line {line}: WoW 3.3.5a supports at most 10 item stats")

    armor = parse_optional_number(row["armor"], "armor", line, integer=True)
    block = parse_optional_number(row["block"], "block", line, integer=True)
    dmg_min = parse_optional_number(row["dmg_min1"], "dmg_min1", line)
    dmg_max = parse_optional_number(row["dmg_max1"], "dmg_max1", line)
    delay = parse_optional_number(row["delay"], "delay", line, integer=True)
    equip_spell1 = parse_optional_number(row["equip_spell1"], "equip_spell1", line, integer=True)
    equip_spell2 = parse_optional_number(row["equip_spell2"], "equip_spell2", line, integer=True)

    if (dmg_min is None) != (dmg_max is None):
        raise ValueError(f"line {line}: dmg_min1 and dmg_max1 must be supplied together")
    if dmg_min is not None and dmg_max < dmg_min:
        raise ValueError(f"line {line}: dmg_max1 cannot be lower than dmg_min1")
    if armor is not None and armor < 0:
        raise ValueError(f"line {line}: armor cannot be negative")
    if block is not None and block < 0:
        raise ValueError(f"line {line}: block cannot be negative")
    if delay is not None and delay <= 0:
        raise ValueError(f"line {line}: delay must be positive")
    for field, spell in (("equip_spell1", equip_spell1), ("equip_spell2", equip_spell2)):
        if spell is not None and spell <= 0:
            raise ValueError(f"line {line}: {field} must be positive")

    updates = [
        f"`entry` = {entry}",
        f"`class` = {item_class}",
        f"`subclass` = {subclass}",
        f"`SoundOverrideSubclass` = {sound_override}",
        f"`Material` = {material}",
        f"`displayid` = {display_id}",
        f"`InventoryType` = {inventory_type}",
        f"`sheath` = {sheath}",
        f"`name` = {sql_string(name)}",
        f"`Quality` = {quality}",
        f"`RequiredLevel` = {required_level}",
        f"`ItemLevel` = {item_level}",
        "`AllowableClass` = -1", "`AllowableRace` = -1", "`itemset` = 0",
    ]

    for index in range(1, 11):
        if index <= len(stats):
            stat_type, stat_value = stats[index - 1]
        else:
            stat_type, stat_value = 0, 0
        updates.append(f"`stat_type{index}` = {stat_type}")
        updates.append(f"`stat_value{index}` = {stat_value}")

    if armor is not None:
        updates.append(f"`armor` = {armor}")
    if block is not None:
        updates.append(f"`block` = {block}")
    if dmg_min is not None:
        updates.append(f"`dmg_min1` = {dmg_min:g}")
        updates.append(f"`dmg_max1` = {dmg_max:g}")
    if delay is not None:
        updates.append(f"`delay` = {delay}")

    for index in range(1, 6):
        updates.extend([
            f"`spellid_{index}` = 0", f"`spelltrigger_{index}` = 0", f"`spellcharges_{index}` = 0",
            f"`spellppmRate_{index}` = 0", f"`spellcooldown_{index}` = -1", f"`spellcategory_{index}` = 0",
            f"`spellcategorycooldown_{index}` = -1",
        ])
    for index, spell in enumerate((equip_spell1, equip_spell2), start=1):
        if spell is not None:
            updates.extend([f"`spellid_{index}` = {spell}", f"`spelltrigger_{index}` = 1"])

    updates.append(f"`description` = {sql_string(row['description'].strip())}")
    updates.append("`VerifiedBuild` = 0")

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

    try:
        dbc_rows = load_item_dbc(args.item_dbc)
    except (OSError, ValueError) as exc:
        raise SystemExit(str(exc)) from exc

    with args.input.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames is None:
            raise SystemExit("catalog has no header")
        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise SystemExit("catalog is missing columns: " + ", ".join(sorted(missing)))

        blocks = []
        enabled_count = 0
        seen_entries = set()
        for line, row in enumerate(reader, start=2):
            enabled = (row.get("enabled") or "").strip().lower()
            if enabled in {"", "0", "false", "no", "off"}:
                continue
            if enabled not in {"1", "true", "yes", "on"}:
                raise SystemExit(f"line {line}: enabled must be 0/1")
            try:
                entry = parse_int(row["entry"].strip(), "entry", line, minimum=911000, maximum=911999)
                if entry in seen_entries:
                    raise ValueError(f"line {line}: duplicate custom entry {entry}")
                seen_entries.add(entry)
                blocks.append(generate_row(row, line, dbc_rows))
                enabled_count += 1
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "-- GENERATED FILE. Do not edit by hand.",
        f"-- Source: {args.input.name}",
        f"-- Chassis source: {args.item_dbc}",
        "-- This catalog owns the complete Gauntlet item range and replaces it atomically during development.",
        "DELETE FROM `item_template` WHERE `entry` BETWEEN 911100 AND 911399;",
        "",
    ]
    args.output.write_text("\n".join(header + blocks) + "\n", encoding="utf-8")
    print(f"Generated {enabled_count} Gauntlet item_template rows -> {args.output}")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
