#!/usr/bin/env python3
import argparse
import csv
from pathlib import Path

QUALITY = {
    "2": 2,
    "green": 2,
    "verde": 2,
    "uncommon": 2,
    "3": 3,
    "blue": 3,
    "azul": 3,
    "rare": 3,
    "4": 4,
    "purple": 4,
    "violet": 4,
    "violeta": 4,
    "epic": 4,
}

STAT_COLUMNS = [
    ("strength", 4),
    ("agility", 3),
    ("stamina", 7),
    ("intellect", 5),
    ("spirit", 6),
    ("attack_power", 38),
    ("spell_power", 45),
    ("hit_rating", 31),
    ("crit_rating", 32),
    ("haste_rating", 36),
]

REQUIRED_COLUMNS = {
    "enabled", "entry", "source_entry", "name", "quality", "required_level", "item_level",
    "strength", "agility", "stamina", "intellect", "spirit", "attack_power", "spell_power",
    "hit_rating", "crit_rating", "haste_rating", "armor", "dmg_min1", "dmg_max1", "delay",
    "description",
}


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


def generate_row(row, line: int) -> str:
    entry = parse_int(row["entry"].strip(), "entry", line, minimum=911000, maximum=911999)
    source = parse_int(row["source_entry"].strip(), "source_entry", line, minimum=1)
    if 911000 <= source <= 911999:
        raise ValueError(f"line {line}: source_entry must be a stock item, not another gauntlet item")

    name = row["name"].strip()
    if not name:
        raise ValueError(f"line {line}: name cannot be empty")

    quality_key = row["quality"].strip().lower()
    if quality_key not in QUALITY:
        raise ValueError(f"line {line}: quality must be green/blue/purple (or 2/3/4)")
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
    dmg_min = parse_optional_number(row["dmg_min1"], "dmg_min1", line)
    dmg_max = parse_optional_number(row["dmg_max1"], "dmg_max1", line)
    delay = parse_optional_number(row["delay"], "delay", line, integer=True)
    if (dmg_min is None) != (dmg_max is None):
        raise ValueError(f"line {line}: dmg_min1 and dmg_max1 must be supplied together")
    if dmg_min is not None and dmg_max < dmg_min:
        raise ValueError(f"line {line}: dmg_max1 cannot be lower than dmg_min1")
    if armor is not None and armor < 0:
        raise ValueError(f"line {line}: armor cannot be negative")
    if delay is not None and delay <= 0:
        raise ValueError(f"line {line}: delay must be positive")

    updates = [
        f"`entry` = {entry}",
        f"`name` = {sql_string(name)}",
        f"`Quality` = {quality}",
        f"`RequiredLevel` = {required_level}",
        f"`ItemLevel` = {item_level}",
        f"`StatsCount` = {len(stats)}",
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
    if dmg_min is not None:
        updates.append(f"`dmg_min1` = {dmg_min:g}")
        updates.append(f"`dmg_max1` = {dmg_max:g}")
    if delay is not None:
        updates.append(f"`delay` = {delay}")

    description = row["description"].strip()
    updates.append(f"`description` = {sql_string(description)}")
    updates.append("`VerifiedBuild` = 0")

    temp = f"tmp_adventurer_gauntlet_item_{entry}"
    return "\n".join([
        f"-- {entry}: {name}",
        f"DROP TEMPORARY TABLE IF EXISTS `{temp}`;",
        f"CREATE TEMPORARY TABLE `{temp}` AS SELECT * FROM `item_template` WHERE `entry` = {source};",
        f"UPDATE `{temp}` SET\n    " + ",\n    ".join(updates) + ";",
        f"INSERT INTO `item_template` SELECT * FROM `{temp}`;",
        f"DROP TEMPORARY TABLE `{temp}`;",
    ])


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Adventurer Gauntlet item_template SQL from CSV")
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

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
                blocks.append(generate_row(row, line))
                enabled_count += 1
            except ValueError as exc:
                raise SystemExit(str(exc)) from exc

    args.output.parent.mkdir(parents=True, exist_ok=True)
    header = [
        "-- GENERATED FILE. Do not edit by hand.",
        f"-- Source: {args.input.name}",
        f"-- Enabled custom items: {enabled_count}",
        "-- The CSV is authoritative for the reserved gauntlet item range.",
        "DELETE FROM `item_template` WHERE `entry` BETWEEN 911000 AND 911999;",
        "",
    ]
    args.output.write_text("\n".join(header + blocks) + "\n", encoding="utf-8")
    print(f"Generated {enabled_count} Adventurer Gauntlet item(s): {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
