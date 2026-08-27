#!/usr/bin/env python3
"""Shared Adventurer subclass metadata and native spellbook DBC transforms.

The four subclasses are presentation/organisation families for the classless
Adventurer. They do not change spell mechanics or eligibility. A single JSON
spec owns the classification and iconography used by both SpellDraft talents
and the native spellbook skill-line tabs.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path

from dbc import DBC, DBCError, ADVENTURER_CLASS_MASK, LOCALE_ESES, LOCALE_ESMX, set_u32, u32

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "config" / "spelldraft" / "subclasses.json"
CARDS_PATH = ROOT / "config" / "spelldraft" / "cards.csv"

SKILLLINE_FIELDS = 56
SKILLLINE_RECORD_SIZE = SKILLLINE_FIELDS * 4
SKILLLINE_NAME_START = 3
SKILLLINE_DESCRIPTION_START = 20
SKILLLINE_SPELL_ICON = 37
SKILLLINE_ALTERNATE_VERB_START = 38

SPELLICON_FIELDS = 2
SPELLICON_RECORD_SIZE = SPELLICON_FIELDS * 4
SPELLICON_PATH_FIELD = 1

SKILLLINEABILITY_FIELDS = 14
SKILLLINEABILITY_RECORD_SIZE = SKILLLINEABILITY_FIELDS * 4
SLA_SKILL_LINE = 1
SLA_SPELL = 2
SLA_RACE_MASK = 3
SLA_CLASS_MASK = 4
SLA_EXCLUDE_RACE = 5
SLA_EXCLUDE_CLASS = 6
SLA_MIN_SKILL_LINE_RANK = 7
SLA_SUPERCEDED_BY = 8
SLA_ACQUIRE_METHOD = 9
SLA_TRIVIAL_RANK_HIGH = 10
SLA_TRIVIAL_RANK_LOW = 11
SLA_CHARACTER_POINTS_1 = 12
SLA_CHARACTER_POINTS_2 = 13

SKILLRACECLASS_FIELDS = 8
SKILLRACECLASS_RECORD_SIZE = SKILLRACECLASS_FIELDS * 4
SRC_SKILL = 1
SRC_RACE_MASK = 2
SRC_CLASS_MASK = 3

EXPECTED_KEYS = ("mercenary", "explorer", "spellcaster", "illuminated")


class SubclassError(DBCError):
    pass


def load_spec(path: Path = SPEC_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise SubclassError(f"Unsupported subclass spec schema: {data.get('schema')}")

    subclasses = data.get("subclasses")
    if not isinstance(subclasses, list) or len(subclasses) != 4:
        raise SubclassError("subclasses.json must define exactly four subclasses")

    keys = [str(item.get("key", "")) for item in subclasses]
    if tuple(keys) != EXPECTED_KEYS:
        raise SubclassError(f"subclasses must be ordered as {EXPECTED_KEYS}, got {tuple(keys)}")

    unique_fields = ("id", "skill_line_id", "order")
    for field in unique_fields:
        values = [int(item[field]) for item in subclasses]
        if len(values) != len(set(values)):
            raise SubclassError(f"duplicate subclass {field}: {values}")

    seen_cards: dict[int, str] = {}
    for item in subclasses:
        if not item.get("enUS") or not item.get("esMX"):
            raise SubclassError(f"subclass {item['key']} is missing localized names")
        if not item.get("icon"):
            raise SubclassError(f"subclass {item['key']} is missing its icon")
        for raw_card_id in item.get("card_ids", []):
            card_id = int(raw_card_id)
            previous = seen_cards.get(card_id)
            if previous:
                raise SubclassError(
                    f"card {card_id} belongs to both {previous} and {item['key']}"
                )
            seen_cards[card_id] = item["key"]

    overrides = data.get("talent_overrides", {})
    if not isinstance(overrides, dict):
        raise SubclassError("talent_overrides must be an object")
    for raw_spell, key in overrides.items():
        int(raw_spell)
        if key not in EXPECTED_KEYS:
            raise SubclassError(f"invalid talent override subclass {key!r}")
    return data


def subclass_by_key(spec: dict | None = None) -> dict[str, dict]:
    spec = spec or load_spec()
    return {item["key"]: item for item in spec["subclasses"]}


def subclass_by_id(spec: dict | None = None) -> dict[int, dict]:
    spec = spec or load_spec()
    return {int(item["id"]): item for item in spec["subclasses"]}


def card_subclass_map(spec: dict | None = None) -> dict[int, str]:
    spec = spec or load_spec()
    result: dict[int, str] = {}
    for item in spec["subclasses"]:
        for card_id in item["card_ids"]:
            result[int(card_id)] = item["key"]
    return result


def talent_override_map(spec: dict | None = None) -> dict[int, str]:
    spec = spec or load_spec()
    return {int(spell_id): str(key) for spell_id, key in spec.get("talent_overrides", {}).items()}


def validate_card_coverage(cards_text: str, spec: dict | None = None) -> dict[int, str]:
    spec = spec or load_spec()
    mapping = card_subclass_map(spec)
    rows = list(csv.DictReader(io.StringIO(cards_text), delimiter=";"))
    ids = {int(row["id"]) for row in rows}
    missing = sorted(ids - set(mapping))
    unknown = sorted(set(mapping) - ids)
    if missing or unknown:
        parts = []
        if missing:
            parts.append("unclassified cards: " + ", ".join(map(str, missing)))
        if unknown:
            parts.append("unknown classified cards: " + ", ".join(map(str, unknown)))
        raise SubclassError("; ".join(parts))
    return mapping


def choose_synthetic_talent_subclass(
    first_rank_spell: int,
    source_card_ids: list[int],
    card_classes: dict[int, str],
    overrides: dict[int, str],
) -> str:
    override = overrides.get(first_rank_spell)
    if override:
        return override

    classes = {card_classes[card_id] for card_id in source_card_ids if card_id in card_classes}
    if not classes:
        raise SubclassError(f"talent {first_rank_spell} has no classified source cards")
    if len(classes) == 1:
        return next(iter(classes))

    # Hybrid native talent rows can be referenced by more than one ability.
    # Physical identity wins for mixed hunter/feral relationships; otherwise
    # school-based magic remains in its corresponding magical family.
    for key in ("mercenary", "explorer", "illuminated", "spellcaster"):
        if key in classes:
            return key
    raise SubclassError(f"cannot classify mixed talent {first_rank_spell}: {sorted(classes)}")


def set_localized_name(dbc: DBC, row: bytearray, start: int, en_us: str, es_mx: str) -> None:
    en_offset = dbc.append_string(en_us)
    es_offset = dbc.append_string(es_mx)
    for locale in range(16):
        set_u32(row, start + locale, es_offset if locale in (LOCALE_ESES, LOCALE_ESMX) else en_offset)


def clear_localized_block(row: bytearray, start: int) -> None:
    for locale in range(16):
        set_u32(row, start + locale, 0)


def dbc_string(dbc: DBC, offset: int) -> str:
    if not offset:
        return ""
    raw = bytes(dbc.strings)
    end = raw.find(b"\0", offset)
    if end < 0:
        raise SubclassError(f"Unterminated DBC string at offset {offset}")
    return raw[offset:end].decode("utf-8", errors="strict")


def normalized_icon_name(value: str) -> str:
    name = value.replace("/", "\\").rsplit("\\", 1)[-1]
    if name.lower().endswith(".blp"):
        name = name[:-4]
    return name.lower()


def resolve_subclass_icon_ids(path: Path, spec: dict) -> dict[str, int]:
    """Resolve subclass icon names against stock SpellIcon.dbc; never create icons."""
    icons = DBC.read(path)
    if icons.fields != SPELLICON_FIELDS or icons.record_size != SPELLICON_RECORD_SIZE:
        raise SubclassError(f"{path}: unexpected SpellIcon layout {icons.fields}/{icons.record_size}")

    by_name: dict[str, int] = {}
    for row in icons.records:
        raw_path = dbc_string(icons, u32(row, SPELLICON_PATH_FIELD))
        if raw_path:
            by_name.setdefault(normalized_icon_name(raw_path), u32(row, 0))

    result: dict[str, int] = {}
    for item in spec["subclasses"]:
        authored = str(item["icon"])
        icon_id = by_name.get(normalized_icon_name(authored))
        if icon_id is None:
            raise SubclassError(
                f"SpellIcon.dbc: stock icon {authored!r} for subclass {item['key']} not found"
            )
        result[str(item["key"])] = icon_id
    return result


def patch_skill_lines(path: Path, spec: dict, icon_ids: dict[str, int]) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != SKILLLINE_FIELDS or dbc.record_size != SKILLLINE_RECORD_SIZE:
        raise SubclassError(f"{path}: unexpected SkillLine layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    custom_ids = {int(item["skill_line_id"]) for item in spec["subclasses"]}
    source_rows = {
        int(item["source_skill_line_id"]): bytearray(
            next(
                row for row in dbc.records
                if u32(row, 0) == int(item["source_skill_line_id"])
            )
        )
        for item in spec["subclasses"]
    }
    dbc.records = [row for row in dbc.records if u32(row, 0) not in custom_ids]

    for item in spec["subclasses"]:
        source_id = int(item["source_skill_line_id"])
        if source_id not in source_rows:
            raise SubclassError(f"SkillLine.dbc source row {source_id} not found")
        row = bytearray(source_rows[source_id])
        set_u32(row, 0, int(item["skill_line_id"]))
        set_localized_name(dbc, row, SKILLLINE_NAME_START, str(item["enUS"]), str(item["esMX"]))
        clear_localized_block(row, SKILLLINE_DESCRIPTION_START)
        set_u32(row, SKILLLINE_SPELL_ICON, icon_ids[str(item["key"])])
        clear_localized_block(row, SKILLLINE_ALTERNATE_VERB_START)
        dbc.records.append(row)

    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before


def patch_skill_race_class(path: Path, spec: dict) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != SKILLRACECLASS_FIELDS or dbc.record_size != SKILLRACECLASS_RECORD_SIZE:
        raise SubclassError(f"{path}: unexpected SkillRaceClassInfo layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    custom_ids = {int(item["skill_line_id"]) for item in spec["subclasses"]}
    dbc.records = [row for row in dbc.records if u32(row, SRC_SKILL) not in custom_ids]
    next_id = max((u32(row, 0) for row in dbc.records), default=0) + 1

    for item in spec["subclasses"]:
        source_id = int(item["source_skill_line_id"])
        candidates = [row for row in dbc.records if u32(row, SRC_SKILL) == source_id]
        if not candidates:
            raise SubclassError(f"SkillRaceClassInfo.dbc source skill {source_id} not found")
        template = next(
            (row for row in candidates if u32(row, SRC_CLASS_MASK) == ADVENTURER_CLASS_MASK),
            candidates[0],
        )
        row = bytearray(template)
        set_u32(row, 0, next_id)
        next_id += 1
        set_u32(row, SRC_SKILL, int(item["skill_line_id"]))
        set_u32(row, SRC_RACE_MASK, 0)
        set_u32(row, SRC_CLASS_MASK, ADVENTURER_CLASS_MASK)
        dbc.records.append(row)

    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before


def split_grant_spells(rank_grants: str) -> list[int]:
    result: list[int] = []
    for rank in rank_grants.split("/"):
        for raw in rank.split("+"):
            raw = raw.strip()
            if raw:
                result.append(int(raw))
    return result


def active_spell_seeds(cards_text: str, spec: dict) -> dict[int, str]:
    mapping = validate_card_coverage(cards_text, spec)
    seeds: dict[int, str] = {}
    for row in csv.DictReader(io.StringIO(cards_text), delimiter=";"):
        if row["type"] != "active":
            continue
        card_id = int(row["id"])
        subclass = mapping[card_id]
        for spell_id in split_grant_spells(row["rank_grants"]):
            previous = seeds.get(spell_id)
            if previous and previous != subclass:
                raise SubclassError(
                    f"spell {spell_id} is granted by cards in both {previous} and {subclass}"
                )
            seeds[spell_id] = subclass
    return seeds


def rank_chain_closure(records: list[bytearray], spell_id: int) -> set[int]:
    next_map: dict[int, set[int]] = {}
    previous_map: dict[int, set[int]] = {}
    for row in records:
        current = u32(row, SLA_SPELL)
        following = u32(row, SLA_SUPERCEDED_BY)
        if current and following:
            next_map.setdefault(current, set()).add(following)
            previous_map.setdefault(following, set()).add(current)

    result: set[int] = set()
    pending = [spell_id]
    while pending:
        current = pending.pop()
        if current in result:
            continue
        result.add(current)
        pending.extend(next_map.get(current, ()))
        pending.extend(previous_map.get(current, ()))
    return result


def normalize_custom_skill_line_ability(
    row: bytearray,
    row_id: int,
    skill_line: int,
    spell_id: int,
) -> bytearray:
    """Make an SLA row presentation-only for the Adventurer spellbook.

    AcquireMethod must remain zero: these rows categorize spells that SpellDraft
    already granted and must never teach abilities merely because the subclass
    SkillLine exists on the character.
    """
    set_u32(row, 0, row_id)
    set_u32(row, SLA_SKILL_LINE, skill_line)
    set_u32(row, SLA_SPELL, spell_id)
    set_u32(row, SLA_RACE_MASK, 0)
    set_u32(row, SLA_CLASS_MASK, ADVENTURER_CLASS_MASK)
    set_u32(row, SLA_EXCLUDE_RACE, 0)
    set_u32(row, SLA_EXCLUDE_CLASS, 0)
    set_u32(row, SLA_MIN_SKILL_LINE_RANK, 0)
    set_u32(row, SLA_ACQUIRE_METHOD, 0)
    set_u32(row, SLA_TRIVIAL_RANK_HIGH, 0)
    set_u32(row, SLA_TRIVIAL_RANK_LOW, 0)
    set_u32(row, SLA_CHARACTER_POINTS_1, 0)
    set_u32(row, SLA_CHARACTER_POINTS_2, 0)
    return row


def patch_skill_line_abilities(path: Path, cards_text: str, spec: dict) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != SKILLLINEABILITY_FIELDS or dbc.record_size != SKILLLINEABILITY_RECORD_SIZE:
        raise SubclassError(
            f"{path}: unexpected SkillLineAbility layout {dbc.fields}/{dbc.record_size}"
        )

    before = dbc.to_bytes()
    by_key = subclass_by_key(spec)
    custom_ids = {int(item["skill_line_id"]) for item in spec["subclasses"]}
    dbc.records = [row for row in dbc.records if u32(row, SLA_SKILL_LINE) not in custom_ids]

    seeds = active_spell_seeds(cards_text, spec)
    classified: dict[int, str] = {}
    for seed_spell, subclass in seeds.items():
        for spell_id in rank_chain_closure(dbc.records, seed_spell):
            previous = classified.get(spell_id)
            if previous and previous != subclass:
                raise SubclassError(
                    f"spell rank {spell_id} maps to both {previous} and {subclass}"
                )
            classified[spell_id] = subclass

    rows_by_spell: dict[int, list[bytearray]] = {}
    for row in dbc.records:
        rows_by_spell.setdefault(u32(row, SLA_SPELL), []).append(row)

    # Existing rows let us preserve stock SupercededBySpell links. A drafted
    # seed such as Curse of Recklessness (704) can legitimately have no SLA row
    # at all in 3.3.5a; for those seeds we synthesize a minimal class-10-only
    # row. Missing terminal superseded ranks still do not need artificial rows.
    visible_classified = {
        spell_id: subclass
        for spell_id, subclass in classified.items()
        if spell_id in rows_by_spell
    }
    for spell_id, subclass in seeds.items():
        if spell_id not in rows_by_spell:
            visible_classified[spell_id] = subclass

    # Generic SkillLineAbility rows (ClassMask=0) would otherwise also expose a
    # drafted spell under its stock/general skill line. Exclude only class 10;
    # stock classes remain byte-for-byte equivalent in behavior.
    for spell_id in visible_classified:
        for row in rows_by_spell.get(spell_id, ()):
            if u32(row, SLA_CLASS_MASK) == 0:
                set_u32(
                    row,
                    SLA_EXCLUDE_CLASS,
                    u32(row, SLA_EXCLUDE_CLASS) | ADVENTURER_CLASS_MASK,
                )

    next_id = max((u32(row, 0) for row in dbc.records), default=0) + 1
    for spell_id in sorted(visible_classified):
        candidates = rows_by_spell.get(spell_id, [])
        if candidates:
            template = next(
                (row for row in candidates if u32(row, SLA_CLASS_MASK) != 0),
                candidates[0],
            )
            row = bytearray(template)
        else:
            row = bytearray(SKILLLINEABILITY_RECORD_SIZE)

        normalize_custom_skill_line_ability(
            row,
            next_id,
            int(by_key[visible_classified[spell_id]]["skill_line_id"]),
            spell_id,
        )
        next_id += 1
        dbc.records.append(row)

    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before


def validate_subclass_dbcs(
    dbc_dir: Path,
    cards_text: str,
    spec: dict,
    icon_ids: dict[str, int],
) -> None:
    skill_lines = DBC.read(dbc_dir / "SkillLine.dbc")
    skill_race = DBC.read(dbc_dir / "SkillRaceClassInfo.dbc")
    abilities = DBC.read(dbc_dir / "SkillLineAbility.dbc")

    for item in spec["subclasses"]:
        skill_id = int(item["skill_line_id"])
        skill_row = next((row for row in skill_lines.records if u32(row, 0) == skill_id), None)
        if skill_row is None:
            raise SubclassError(f"missing custom SkillLine {skill_id}")
        expected_icon = icon_ids[str(item["key"])]
        if u32(skill_row, SKILLLINE_SPELL_ICON) != expected_icon:
            raise SubclassError(
                f"custom SkillLine {skill_id} has icon {u32(skill_row, SKILLLINE_SPELL_ICON)}, expected {expected_icon}"
            )
        if not any(
            u32(row, SRC_SKILL) == skill_id
            and u32(row, SRC_CLASS_MASK) == ADVENTURER_CLASS_MASK
            for row in skill_race.records
        ):
            raise SubclassError(f"missing Adventurer SkillRaceClassInfo for {skill_id}")

    by_key = subclass_by_key(spec)
    for spell_id, subclass in active_spell_seeds(cards_text, spec).items():
        skill_id = int(by_key[subclass]["skill_line_id"])
        if not any(
            u32(row, SLA_SPELL) == spell_id
            and u32(row, SLA_SKILL_LINE) == skill_id
            and u32(row, SLA_CLASS_MASK) == ADVENTURER_CLASS_MASK
            for row in abilities.records
        ):
            raise SubclassError(f"spell {spell_id} is not mapped to subclass skill {skill_id}")


def patch_subclass_directory(
    dbc_dir: Path,
    cards_text: str | None = None,
    spec: dict | None = None,
) -> dict[str, bool]:
    spec = spec or load_spec()
    cards_text = cards_text if cards_text is not None else CARDS_PATH.read_text(encoding="utf-8")
    validate_card_coverage(cards_text, spec)

    required = (
        "SkillLine.dbc",
        "SkillRaceClassInfo.dbc",
        "SkillLineAbility.dbc",
        "SpellIcon.dbc",
    )
    missing = [name for name in required if not (dbc_dir / name).is_file()]
    if missing:
        raise SubclassError("Missing subclass DBC(s): " + ", ".join(missing))

    icon_ids = resolve_subclass_icon_ids(dbc_dir / "SpellIcon.dbc", spec)
    changed = {
        "SkillLine.dbc": patch_skill_lines(dbc_dir / "SkillLine.dbc", spec, icon_ids),
        "SkillRaceClassInfo.dbc": patch_skill_race_class(
            dbc_dir / "SkillRaceClassInfo.dbc", spec
        ),
        "SkillLineAbility.dbc": patch_skill_line_abilities(
            dbc_dir / "SkillLineAbility.dbc", cards_text, spec
        ),
    }
    validate_subclass_dbcs(dbc_dir, cards_text, spec, icon_ids)
    return changed
