#!/usr/bin/env python3
import argparse
import csv
import re
from collections import Counter
from pathlib import Path

SET_KEY_RE = re.compile(r"^[a-z0-9_]+$")

ITEM_REQUIRED_COLUMNS = {"enabled", "entry", "set_key"}
SET_REQUIRED_COLUMNS = {
    "enabled", "set_key", "name", "pieces_required", "bonus_type", "value", "spell_id", "description"
}

BONUS_TYPES = {
    "armor": "GAUNTLET_SET_BONUS_ARMOR",
    "strength": "GAUNTLET_SET_BONUS_STRENGTH",
    "agility": "GAUNTLET_SET_BONUS_AGILITY",
    "stamina": "GAUNTLET_SET_BONUS_STAMINA",
    "intellect": "GAUNTLET_SET_BONUS_INTELLECT",
    "spirit": "GAUNTLET_SET_BONUS_SPIRIT",
    "defense_skill": "GAUNTLET_SET_BONUS_DEFENSE_SKILL",
    "expertise_rating": "GAUNTLET_SET_BONUS_EXPERTISE_RATING",
    "spell": "GAUNTLET_SET_BONUS_SPELL",
}


def cpp_string(value: str) -> str:
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


def is_enabled(raw: str, line: int) -> bool:
    value = (raw or "").strip().lower()
    if value in {"", "0", "false", "no", "off"}:
        return False
    if value in {"1", "true", "yes", "on"}:
        return True
    raise SystemExit(f"line {line}: enabled must be 0/1")


def parse_positive_int(raw: str, field: str, line: int) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise SystemExit(f"line {line}: {field} must be an integer") from exc
    if value <= 0:
        raise SystemExit(f"line {line}: {field} must be positive")
    return value


def parse_optional_positive_int(raw: str, field: str, line: int) -> int:
    value = (raw or "").strip()
    if not value:
        return 0
    return parse_positive_int(value, field, line)


def validate_key(key: str, line: int) -> str:
    key = key.strip().lower()
    if not key or not SET_KEY_RE.fullmatch(key):
        raise SystemExit(f"line {line}: invalid set_key {key!r}")
    return key


def read_items(path: Path):
    pieces = []
    counts = Counter()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames is None:
            raise SystemExit("item catalog has no header")
        missing = ITEM_REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise SystemExit("item catalog is missing columns: " + ", ".join(sorted(missing)))

        for line, row in enumerate(reader, start=2):
            if not is_enabled(row.get("enabled"), line):
                continue
            key = (row.get("set_key") or "").strip().lower()
            if not key:
                continue
            key = validate_key(key, line)
            entry = parse_positive_int((row.get("entry") or "").strip(), "entry", line)
            pieces.append((entry, key))
            counts[key] += 1
    return pieces, counts


def read_bonuses(path: Path, piece_counts):
    bonuses = []
    names = {}
    seen = set()
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames is None:
            raise SystemExit("set catalog has no header")
        missing = SET_REQUIRED_COLUMNS.difference(reader.fieldnames)
        if missing:
            raise SystemExit("set catalog is missing columns: " + ", ".join(sorted(missing)))

        for line, row in enumerate(reader, start=2):
            if not is_enabled(row.get("enabled"), line):
                continue

            key = validate_key(row.get("set_key") or "", line)
            name = (row.get("name") or "").strip()
            if not name:
                raise SystemExit(f"line {line}: set name cannot be empty")

            pieces_required = parse_positive_int(
                (row.get("pieces_required") or "").strip(), "pieces_required", line
            )
            bonus_type = (row.get("bonus_type") or "").strip().lower()
            if bonus_type not in BONUS_TYPES:
                raise SystemExit(
                    f"line {line}: bonus_type must be one of {', '.join(sorted(BONUS_TYPES))}"
                )

            value = parse_optional_positive_int(row.get("value"), "value", line)
            spell_id = parse_optional_positive_int(row.get("spell_id"), "spell_id", line)
            if bonus_type == "spell":
                if not spell_id:
                    raise SystemExit(f"line {line}: spell bonus requires spell_id")
                if value:
                    raise SystemExit(f"line {line}: spell bonus must leave value empty")
            else:
                if not value:
                    raise SystemExit(f"line {line}: {bonus_type} bonus requires value")
                if spell_id:
                    raise SystemExit(f"line {line}: {bonus_type} bonus must leave spell_id empty")

            description = (row.get("description") or "").strip()

            if key not in piece_counts:
                raise SystemExit(f"line {line}: set_key {key!r} has no enabled item pieces")
            if pieces_required > piece_counts[key]:
                raise SystemExit(
                    f"line {line}: {key} asks for {pieces_required} pieces but only {piece_counts[key]} are enabled"
                )
            if (key, pieces_required) in seen:
                raise SystemExit(f"line {line}: duplicate {key} bonus for {pieces_required} pieces")
            if key in names and names[key] != name:
                raise SystemExit(f"line {line}: set_key {key!r} uses multiple names")

            names[key] = name
            seen.add((key, pieces_required))
            bonuses.append(
                (
                    key,
                    name,
                    pieces_required,
                    BONUS_TYPES[bonus_type],
                    value,
                    spell_id,
                    description,
                )
            )

    return bonuses


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Adventurer Gauntlet server-side set bonus definitions")
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--sets", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()

    pieces, piece_counts = read_items(args.items)
    bonuses = read_bonuses(args.sets, piece_counts)

    piece_lines = [f"    GauntletSetPiece{{{entry}, {cpp_string(key)}}}," for entry, key in pieces]
    bonus_lines = [
        "    GauntletSetBonus{" + ", ".join([
            cpp_string(key),
            cpp_string(name),
            str(required),
            bonus_type,
            str(value),
            str(spell_id),
            cpp_string(description),
        ]) + "},"
        for key, name, required, bonus_type, value, spell_id, description in bonuses
    ]

    output = [
        "// GENERATED FILE. Do not edit by hand.",
        f"// Items source: {args.items.name}",
        f"// Sets source: {args.sets.name}",
        "",
        f"static constexpr std::array<GauntletSetPiece, {len(pieces)}> GauntletSetPieces = {{{{",
        *piece_lines,
        "}};",
        "",
        f"static constexpr std::array<GauntletSetBonus, {len(bonuses)}> GauntletSetBonuses = {{{{",
        *bonus_lines,
        "}};",
        "",
    ]

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(output), encoding="utf-8")
    print(f"Generated {len(pieces)} set piece(s) and {len(bonuses)} set bonus(es): {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
