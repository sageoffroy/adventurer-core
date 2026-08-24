#!/usr/bin/env python3
"""Generate native Adventurer talent tabs and talent spells for WotLK 3.3.5a."""

from __future__ import annotations

import json
from pathlib import Path
import struct

from dbc import DBC, DBCError, ADVENTURER_CLASS_MASK, LOCALE_ESES, LOCALE_ESMX, u32, set_u32

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "talents" / "guardian.json"
CHAMPION_SPEC_PATH = ROOT / "talents" / "champion.json"
TALENT_SPEC_PATHS = (SPEC_PATH, CHAMPION_SPEC_PATH)

TALENT_FIELDS = 23
TALENT_RECORD_SIZE = TALENT_FIELDS * 4
TALENTTAB_FIELDS = 24
TALENTTAB_RECORD_SIZE = TALENT_FIELDS * 0 + 24 * 4
SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
SPELLICON_FIELDS = 2
SPELLICON_RECORD_SIZE = SPELLICON_FIELDS * 4

# WotLK client/core only use five talent ranks. Fields 9..12 exist in the DBC
# record but are unused in 3.3.5a.
TALENT_RANK_FIELDS = tuple(range(4, 9))
TALENT_PREREQ_TALENT_FIELDS = (13, 14, 15)
TALENT_PREREQ_RANK_FIELDS = (16, 17, 18)
TALENT_ADD_TO_SPELLBOOK_FIELD = 19
TALENT_REQUIRED_SPELL_FIELD = 20
TALENT_CATEGORY_FIELDS = (21, 22)

TALENTTAB_NAME_START = 1
TALENTTAB_CLASS_MASK_FIELD = 20
TALENTTAB_PET_MASK_FIELD = 21
TALENTTAB_ORDER_FIELD = 22

SPELL_EFFECT_FIELDS = (71, 72, 73)
SPELL_EFFECT_BASEPOINT_FIELDS = (80, 81, 82)
SPELL_EFFECT_APPLY_AURA_FIELDS = (95, 96, 97)
SPELL_EFFECT_MISC_VALUE_FIELDS = (110, 111, 112)
SPELL_EFFECT_TRIGGER_SPELL_FIELDS = (116, 117, 118)
SPELL_ICON_FIELD = 133
SPELL_NAME_START = 136
SPELL_RANK_START = 153
SPELL_DESCRIPTION_START = 170
SPELL_SCHOOL_MASK_FIELD = 225
SPELLICON_PATH_FIELD = 1

# Each tree owns a separate range. Guardian keeps its original 5000/290000 IDs;
# later trees can be added without reindexing any existing Adventurer talent.
TALENT_ID_RESERVATION = 1000
SPELL_ID_RESERVATION = 10000
TRIGGER_SPELL_RANK_OFFSET = 5

FORBIDDEN_CLASS_WORDS = (
    "paladin", "paladín", "warrior", "guerrero", "rogue", "pícaro",
    "death knight", "caballero de la muerte", "priest", "sacerdote",
    "hunter", "cazador", "shaman", "chamán", "druid", "druida",
    "mage", "mago", "warlock", "brujo",
)


def spec_tab_key(spec: dict) -> str:
    return str(spec.get("tab_key", "guardian"))


def spec_point_total(spec: dict) -> int | None:
    raw = spec.get("point_total", spec.get("guardian_points"))
    return None if raw is None else int(raw)


def load_spec(path: Path = SPEC_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise DBCError(f"Unsupported talent spec schema: {data.get('schema')}")
    validate_spec(data)
    return data


def load_specs(paths: tuple[Path, ...] | None = None) -> list[dict]:
    selected = paths or TALENT_SPEC_PATHS
    specs = [load_spec(path) for path in selected if path.is_file()]
    if not specs:
        raise DBCError("No Adventurer talent specs found")
    seen_tabs: set[str] = set()
    seen_talent_ranges: list[tuple[int, int]] = []
    seen_spell_ranges: list[tuple[int, int]] = []
    for spec in specs:
        tab_key = spec_tab_key(spec)
        if tab_key in seen_tabs:
            raise DBCError(f"Duplicate Adventurer talent spec for tab {tab_key!r}")
        seen_tabs.add(tab_key)
        talent_range = (int(spec["talent_id_base"]), int(spec["talent_id_base"]) + TALENT_ID_RESERVATION)
        spell_range = (int(spec["spell_id_base"]), int(spec["spell_id_base"]) + SPELL_ID_RESERVATION)
        if any(max(talent_range[0], lo) < min(talent_range[1], hi) for lo, hi in seen_talent_ranges):
            raise DBCError(f"Overlapping Adventurer talent ID range for {tab_key}")
        if any(max(spell_range[0], lo) < min(spell_range[1], hi) for lo, hi in seen_spell_ranges):
            raise DBCError(f"Overlapping Adventurer spell ID range for {tab_key}")
        seen_talent_ranges.append(talent_range)
        seen_spell_ranges.append(spell_range)
    return specs


def validate_spec(spec: dict) -> None:
    definitions = spec.get("talents", [])
    tab_key = spec_tab_key(spec)
    tabs = {str(tab["key"]): tab for tab in spec.get("tabs", [])}
    if tab_key not in tabs:
        raise DBCError(f"Talent spec tab {tab_key!r} is not declared in tabs")

    seen_keys: set[str] = set()
    seen_positions: set[tuple[int, int]] = set()
    total_points = 0

    for definition in definitions:
        key = str(definition["key"])
        if key in seen_keys:
            raise DBCError(f"Duplicate talent key {key!r} in {tab_key}")
        seen_keys.add(key)

        pos = (int(definition["row"]), int(definition["col"]))
        if pos in seen_positions:
            raise DBCError(f"Duplicate {tab_key} talent position {pos}")
        seen_positions.add(pos)

        source_ids = talent_source_spell_ids(definition)
        rank_count = len(source_ids)
        if not 1 <= rank_count <= len(TALENT_RANK_FIELDS):
            raise DBCError(f"Talent {key} must have 1..{len(TALENT_RANK_FIELDS)} ranks")
        total_points += rank_count

        for field_name in ("effect_values", "trigger_effect_values"):
            for raw_slot, values in definition.get(field_name, {}).items():
                slot = int(raw_slot)
                if not 0 <= slot < len(SPELL_EFFECT_BASEPOINT_FIELDS):
                    raise DBCError(f"Effect slot {slot} out of range for {key}")
                if len(values) != rank_count:
                    raise DBCError(
                        f"{key} {field_name} slot {slot} has {len(values)} values for {rank_count} ranks"
                    )

        trigger_ids = definition.get("trigger_spell_source_ids")
        if trigger_ids is not None:
            if len(trigger_ids) != rank_count:
                raise DBCError(f"{key} trigger spell sources must match its {rank_count} ranks")
            trigger_slot = int(definition.get("trigger_spell_slot", 0))
            if not 0 <= trigger_slot < len(SPELL_EFFECT_TRIGGER_SPELL_FIELDS):
                raise DBCError(f"Trigger spell slot {trigger_slot} out of range for {key}")

        if definition.get("reuse_native_spells"):
            clone_only = (
                "effect_values", "effect_misc_values", "disable_effects",
                "description_enUS", "description_esMX", "spell_u32_values",
                "spell_i32_values", "spell_f32_values", "icon",
                "trigger_spell_source_ids", "trigger_spell_slot",
                "trigger_effect_values", "trigger_effect_misc_values",
                "trigger_disable_effects", "trigger_spell_u32_values",
                "trigger_spell_i32_values", "trigger_spell_f32_values",
            )
            present = [field for field in clone_only if field in definition]
            if present:
                raise DBCError(
                    f"Talent {key} reuses native spell rows but also has clone-only fields: "
                    + ", ".join(present)
                )

    expected = spec_point_total(spec)
    if expected is not None and total_points != expected:
        raise DBCError(f"{tab_key} point total expected {expected}, got {total_points}")

    for definition in definitions:
        required_key = definition.get("requires")
        if required_key and required_key not in seen_keys:
            raise DBCError(f"Unknown talent prerequisite {required_key!r} in {tab_key}")


def talent_source_spell_ids(definition: dict) -> list[int]:
    raw = definition.get("spell_source_ids")
    if raw is None:
        legacy = definition.get("spell_source_id")
        ranks = definition.get("max_ranks")
        if legacy is None or ranks is None:
            raise DBCError(
                f"Talent {definition.get('key', '<unknown>')} must define spell_source_ids"
            )
        raw = [legacy] * int(ranks)
    return [int(value) for value in raw]


def trigger_source_spell_ids(definition: dict) -> list[int]:
    return [int(value) for value in definition.get("trigger_spell_source_ids", [])]


def all_source_spell_ids(spec: dict) -> set[int]:
    result: set[int] = set()
    for definition in spec["talents"]:
        result.update(talent_source_spell_ids(definition))
        result.update(trigger_source_spell_ids(definition))
    return result


def record_by_id(dbc: DBC, record_id: int, label: str) -> bytearray:
    row = next((r for r in dbc.records if u32(r, 0) == record_id), None)
    if row is None:
        raise DBCError(f"{label}: source row {record_id} not found")
    return row


def dbc_string(dbc: DBC, offset: int) -> str:
    if not offset:
        return ""
    raw = bytes(dbc.strings)
    end = raw.find(b"\0", offset)
    if end < 0:
        raise DBCError(f"Unterminated DBC string at offset {offset}")
    return raw[offset:end].decode("utf-8", errors="strict")


def i32(record: bytearray, field: int) -> int:
    return struct.unpack_from("<i", record, field * 4)[0]


def set_i32(record: bytearray, field: int, value: int) -> None:
    struct.pack_into("<i", record, field * 4, int(value))


def f32(record: bytearray, field: int) -> float:
    return struct.unpack_from("<f", record, field * 4)[0]


def set_f32(record: bytearray, field: int, value: float) -> None:
    struct.pack_into("<f", record, field * 4, float(value))


def normalized_icon_name(value: str) -> str:
    name = value.replace("/", "\\").rsplit("\\", 1)[-1]
    if name.lower().endswith(".blp"):
        name = name[:-4]
    return name.lower()


def resolve_existing_icon_ids(path: Path, spec: dict) -> dict[int, int]:
    """Resolve authored icon names against stock SpellIcon.dbc; never create icons."""
    icons = DBC.read(path)
    if icons.fields != SPELLICON_FIELDS or icons.record_size != SPELLICON_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected SpellIcon layout {icons.fields}/{icons.record_size}")

    by_name: dict[str, int] = {}
    for row in icons.records:
        raw_path = dbc_string(icons, u32(row, SPELLICON_PATH_FIELD))
        if raw_path:
            by_name.setdefault(normalized_icon_name(raw_path), u32(row, 0))

    result: dict[int, int] = {}
    for index, definition in enumerate(spec["talents"]):
        authored = definition.get("icon")
        if not authored:
            continue
        key = normalized_icon_name(str(authored))
        icon_id = by_name.get(key)
        if icon_id is None:
            raise DBCError(
                f"SpellIcon.dbc: stock icon {authored!r} for talent {definition['key']} not found"
            )
        result[index] = icon_id
    return result


def set_localized_block(dbc: DBC, row: bytearray, start: int, en_us: str, es_mx: str) -> None:
    en_offset = dbc.append_string(en_us)
    es_offset = dbc.append_string(es_mx)
    for locale in range(16):
        value = es_offset if locale in (LOCALE_ESES, LOCALE_ESMX) else en_offset
        set_u32(row, start + locale, value)


def patch_talent_tabs(path: Path, spec: dict) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != TALENTTAB_FIELDS or dbc.record_size != TALENTTAB_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected TalentTab layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    owned_ids = {int(tab["id"]) for tab in spec["tabs"]}
    dbc.records = [r for r in dbc.records if u32(r, 0) not in owned_ids]
    source_rows = {
        int(tab["source_tab_id"]): bytearray(record_by_id(dbc, int(tab["source_tab_id"]), "TalentTab.dbc"))
        for tab in spec["tabs"]
    }

    for tab in spec["tabs"]:
        row = bytearray(source_rows[int(tab["source_tab_id"])])
        set_u32(row, 0, int(tab["id"]))
        set_localized_block(dbc, row, TALENTTAB_NAME_START, tab["enUS"], tab["esMX"])
        set_u32(row, TALENTTAB_CLASS_MASK_FIELD, ADVENTURER_CLASS_MASK)
        set_u32(row, TALENTTAB_PET_MASK_FIELD, 0)
        set_u32(row, TALENTTAB_ORDER_FIELD, int(tab["order"]))
        dbc.records.append(row)

    dbc.records.sort(key=lambda r: u32(r, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before


def custom_spell_id(spec: dict, talent_index: int, rank_index: int) -> int:
    return int(spec["spell_id_base"]) + talent_index * 10 + rank_index


def custom_trigger_spell_id(spec: dict, talent_index: int, rank_index: int) -> int:
    return int(spec["spell_id_base"]) + talent_index * 10 + TRIGGER_SPELL_RANK_OFFSET + rank_index


def custom_talent_id(spec: dict, talent_index: int) -> int:
    return int(spec["talent_id_base"]) + talent_index


def ranked_value(raw, rank_index: int, definition: dict, field: int | str):
    if isinstance(raw, list):
        if rank_index >= len(raw):
            raise DBCError(
                f"Talent {definition['key']} field {field} missing rank {rank_index + 1} value"
            )
        return raw[rank_index]
    return raw


def _key(prefix: str, name: str) -> str:
    return f"{prefix}_{name}" if prefix else name


def apply_effect_values(spell: bytearray, definition: dict, rank_index: int, prefix: str = "") -> None:
    for raw_slot, values in definition.get(_key(prefix, "effect_values"), {}).items():
        slot = int(raw_slot)
        value = int(values[rank_index])
        set_i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[slot], value - 1)


def apply_effect_misc_values(spell: bytearray, definition: dict, rank_index: int, prefix: str = "") -> None:
    for raw_slot, raw_value in definition.get(_key(prefix, "effect_misc_values"), {}).items():
        slot = int(raw_slot)
        if not 0 <= slot < len(SPELL_EFFECT_MISC_VALUE_FIELDS):
            raise DBCError(f"Effect misc-value slot {slot} out of range for {definition['key']}")
        value = ranked_value(raw_value, rank_index, definition, raw_slot)
        set_i32(spell, SPELL_EFFECT_MISC_VALUE_FIELDS[slot], int(value))


def apply_disabled_effects(spell: bytearray, definition: dict, prefix: str = "") -> None:
    for raw_slot in definition.get(_key(prefix, "disable_effects"), []):
        slot = int(raw_slot)
        if not 0 <= slot < len(SPELL_EFFECT_FIELDS):
            raise DBCError(f"Disabled effect slot {slot} out of range for {definition['key']}")
        set_u32(spell, SPELL_EFFECT_FIELDS[slot], 0)
        set_i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[slot], 0)
        set_u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[slot], 0)
        set_u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[slot], 0)


def apply_spell_fields(spell: bytearray, definition: dict, rank_index: int, prefix: str = "") -> None:
    for raw_field, raw_value in definition.get(_key(prefix, "spell_u32_values"), {}).items():
        field = int(raw_field)
        if not 0 <= field < SPELL_FIELDS:
            raise DBCError(f"Spell u32 field {field} out of range for {definition['key']}")
        set_u32(spell, field, int(ranked_value(raw_value, rank_index, definition, field)))
    for raw_field, raw_value in definition.get(_key(prefix, "spell_i32_values"), {}).items():
        field = int(raw_field)
        if not 0 <= field < SPELL_FIELDS:
            raise DBCError(f"Spell i32 field {field} out of range for {definition['key']}")
        set_i32(spell, field, int(ranked_value(raw_value, rank_index, definition, field)))
    for raw_field, raw_value in definition.get(_key(prefix, "spell_f32_values"), {}).items():
        field = int(raw_field)
        if not 0 <= field < SPELL_FIELDS:
            raise DBCError(f"Spell f32 field {field} out of range for {definition['key']}")
        set_f32(spell, field, float(ranked_value(raw_value, rank_index, definition, field)))


# Backward-compatible wrappers used by existing tests/callers.
def apply_authored_effect_values(spell: bytearray, definition: dict, rank_index: int) -> None:
    apply_effect_values(spell, definition, rank_index)


def apply_authored_effect_misc_values(spell: bytearray, definition: dict, rank_index: int) -> None:
    apply_effect_misc_values(spell, definition, rank_index)


def apply_authored_disabled_effects(spell: bytearray, definition: dict) -> None:
    apply_disabled_effects(spell, definition)


def apply_authored_description(spells: DBC, spell: bytearray, definition: dict) -> None:
    en_us = definition.get("description_enUS")
    es_mx = definition.get("description_esMX")
    if en_us is None and es_mx is None:
        return
    if en_us is None or es_mx is None:
        raise DBCError(f"Talent {definition['key']} must define both description locales")
    set_localized_block(spells, spell, SPELL_DESCRIPTION_START, str(en_us), str(es_mx))


def apply_authored_spell_fields(spell: bytearray, definition: dict, rank_index: int) -> None:
    apply_spell_fields(spell, definition, rank_index)


def has_forbidden_class_reference(text: str) -> bool:
    normalized = "".join(
        char if (char.isalpha() or char.isspace()) else " "
        for char in text.casefold()
    )
    words = " ".join(normalized.split())
    padded = f" {words} "
    return any(f" {class_name.casefold()} " in padded for class_name in FORBIDDEN_CLASS_WORDS)


def _clone_trigger_spell(
    spells: DBC,
    source_spells: dict[int, bytearray],
    spec: dict,
    definition: dict,
    talent_index: int,
    rank_index: int,
) -> int | None:
    trigger_ids = trigger_source_spell_ids(definition)
    if not trigger_ids:
        return None
    source_id = trigger_ids[rank_index]
    native = source_spells.get(source_id)
    if native is None:
        raise DBCError(f"Spell.dbc: trigger source spell {source_id} for {definition['key']} not found")
    spell_id = custom_trigger_spell_id(spec, talent_index, rank_index)
    child = bytearray(native)
    set_u32(child, 0, spell_id)
    set_localized_block(
        spells, child, SPELL_NAME_START,
        f"{definition['enUS']} Trigger", f"{definition['esMX']} activador",
    )
    set_localized_block(
        spells, child, SPELL_RANK_START,
        f"Rank {rank_index + 1}", f"Rango {rank_index + 1}",
    )
    apply_effect_values(child, definition, rank_index, "trigger")
    apply_effect_misc_values(child, definition, rank_index, "trigger")
    apply_disabled_effects(child, definition, "trigger")
    apply_spell_fields(child, definition, rank_index, "trigger")
    spells.records.append(child)
    return spell_id


def patch_talents_and_spells(
    talent_path: Path,
    spell_path: Path,
    spec: dict,
    icon_ids: dict[int, int],
) -> tuple[bool, bool]:
    talents = DBC.read(talent_path)
    spells = DBC.read(spell_path)
    if talents.fields != TALENT_FIELDS or talents.record_size != TALENT_RECORD_SIZE:
        raise DBCError(f"{talent_path}: unexpected Talent layout {talents.fields}/{talents.record_size}")
    if spells.fields != SPELL_FIELDS or spells.record_size != SPELL_RECORD_SIZE:
        raise DBCError(f"{spell_path}: unexpected Spell layout {spells.fields}/{spells.record_size}")

    before_talents = talents.to_bytes()
    before_spells = spells.to_bytes()
    talent_defs = spec["talents"]

    talent_min = int(spec["talent_id_base"])
    talent_max = talent_min + TALENT_ID_RESERVATION
    spell_min = int(spec["spell_id_base"])
    spell_max = spell_min + SPELL_ID_RESERVATION
    talents.records = [r for r in talents.records if not talent_min <= u32(r, 0) < talent_max]
    spells.records = [r for r in spells.records if not spell_min <= u32(r, 0) < spell_max]

    source_spells = {u32(r, 0): bytearray(r) for r in spells.records}
    key_to_index = {d["key"]: i for i, d in enumerate(talent_defs)}
    tab_key = spec_tab_key(spec)
    talent_tab = next(tab for tab in spec["tabs"] if tab["key"] == tab_key)

    rebuilt: list[bytearray] = []
    for index, definition in enumerate(talent_defs):
        source_spell_ids = talent_source_spell_ids(definition)
        reuse_native = bool(definition.get("reuse_native_spells"))

        talent = bytearray(TALENT_RECORD_SIZE)
        set_u32(talent, 0, custom_talent_id(spec, index))
        set_u32(talent, 1, int(talent_tab["id"]))
        set_u32(talent, 2, int(definition["row"]))
        set_u32(talent, 3, int(definition["col"]))
        set_u32(talent, TALENT_ADD_TO_SPELLBOOK_FIELD, 1 if definition.get("add_to_spellbook") else 0)

        for rank_index, source_spell_id in enumerate(source_spell_ids):
            native_spell = source_spells.get(source_spell_id)
            if native_spell is None:
                raise DBCError(
                    f"Spell.dbc: source spell {source_spell_id} for {definition['key']} not found"
                )

            if reuse_native:
                rank_spell_id = source_spell_id
            else:
                rank_spell_id = custom_spell_id(spec, index, rank_index)
                cloned_spell = bytearray(native_spell)
                set_u32(cloned_spell, 0, rank_spell_id)
                set_localized_block(
                    spells, cloned_spell, SPELL_NAME_START,
                    str(definition["enUS"]), str(definition["esMX"]),
                )
                set_localized_block(
                    spells, cloned_spell, SPELL_RANK_START,
                    f"Rank {rank_index + 1}", f"Rango {rank_index + 1}",
                )
                apply_authored_description(spells, cloned_spell, definition)
                if index in icon_ids:
                    set_u32(cloned_spell, SPELL_ICON_FIELD, icon_ids[index])
                apply_effect_values(cloned_spell, definition, rank_index)
                apply_effect_misc_values(cloned_spell, definition, rank_index)
                apply_disabled_effects(cloned_spell, definition)
                apply_spell_fields(cloned_spell, definition, rank_index)

                trigger_spell_id = _clone_trigger_spell(
                    spells, source_spells, spec, definition, index, rank_index
                )
                if trigger_spell_id is not None:
                    trigger_slot = int(definition.get("trigger_spell_slot", 0))
                    set_u32(cloned_spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[trigger_slot], trigger_spell_id)

                spells.records.append(cloned_spell)

            set_u32(talent, TALENT_RANK_FIELDS[rank_index], rank_spell_id)

        required_key = definition.get("requires")
        if required_key:
            required_index = key_to_index[required_key]
            required_definition = talent_defs[required_index]
            required_rank = int(
                definition.get("required_rank", len(talent_source_spell_ids(required_definition)) - 1)
            )
            set_u32(talent, TALENT_PREREQ_TALENT_FIELDS[0], custom_talent_id(spec, required_index))
            set_u32(talent, TALENT_PREREQ_RANK_FIELDS[0], required_rank)

        rebuilt.append(talent)

    talents.records.extend(rebuilt)
    talents.records.sort(key=lambda r: u32(r, 0))
    spells.records.sort(key=lambda r: u32(r, 0))

    after_talents = talents.to_bytes()
    after_spells = spells.to_bytes()
    if after_talents != before_talents:
        talent_path.write_bytes(after_talents)
    if after_spells != before_spells:
        spell_path.write_bytes(after_spells)
    return after_talents != before_talents, after_spells != before_spells


def _validate_custom_fields(spell: bytearray, definition: dict, rank_index: int, prefix: str = "") -> None:
    for raw_slot, values in definition.get(_key(prefix, "effect_values"), {}).items():
        slot = int(raw_slot)
        expected = int(values[rank_index]) - 1
        actual = i32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[slot])
        if actual != expected:
            raise DBCError(
                f"Talent {definition['key']} rank {rank_index + 1} {prefix or 'main'} effect {slot} expected {expected}, got {actual}"
            )
    for raw_slot, raw_value in definition.get(_key(prefix, "effect_misc_values"), {}).items():
        slot = int(raw_slot)
        expected = int(ranked_value(raw_value, rank_index, definition, raw_slot))
        actual = i32(spell, SPELL_EFFECT_MISC_VALUE_FIELDS[slot])
        if actual != expected:
            raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} misc {slot} mismatch")
    for raw_slot in definition.get(_key(prefix, "disable_effects"), []):
        slot = int(raw_slot)
        if u32(spell, SPELL_EFFECT_FIELDS[slot]) != 0:
            raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} effect {slot} not disabled")
        if u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[slot]) != 0:
            raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} aura {slot} not disabled")
        if u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[slot]) != 0:
            raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} trigger {slot} not disabled")
    for raw_field, raw_value in definition.get(_key(prefix, "spell_u32_values"), {}).items():
        field = int(raw_field)
        expected = int(ranked_value(raw_value, rank_index, definition, field))
        if u32(spell, field) != expected:
            raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} u32 field {field} mismatch")
    for raw_field, raw_value in definition.get(_key(prefix, "spell_i32_values"), {}).items():
        field = int(raw_field)
        expected = int(ranked_value(raw_value, rank_index, definition, field))
        if i32(spell, field) != expected:
            raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} i32 field {field} mismatch")
    for raw_field, raw_value in definition.get(_key(prefix, "spell_f32_values"), {}).items():
        field = int(raw_field)
        expected = float(ranked_value(raw_value, rank_index, definition, field))
        if abs(f32(spell, field) - expected) > 1e-6:
            raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} f32 field {field} mismatch")


def validate_talents(dbc_dir: Path, spec: dict | None = None) -> None:
    spec = spec or load_spec()
    tabs = DBC.read(dbc_dir / "TalentTab.dbc")
    talents = DBC.read(dbc_dir / "Talent.dbc")
    spells = DBC.read(dbc_dir / "Spell.dbc")
    icon_ids = resolve_existing_icon_ids(dbc_dir / "SpellIcon.dbc", spec)

    for tab in spec["tabs"]:
        row = record_by_id(tabs, int(tab["id"]), "TalentTab.dbc")
        if u32(row, TALENTTAB_CLASS_MASK_FIELD) != ADVENTURER_CLASS_MASK:
            raise DBCError(f"Talent tab {tab['key']} has wrong class mask")
        if u32(row, TALENTTAB_ORDER_FIELD) != int(tab["order"]):
            raise DBCError(f"Talent tab {tab['key']} has wrong order")

    tab_key = spec_tab_key(spec)
    tab_id = int(next(tab for tab in spec["tabs"] if tab["key"] == tab_key)["id"])
    seen_positions: set[tuple[int, int]] = set()
    total_points = 0

    for index, definition in enumerate(spec["talents"]):
        talent = record_by_id(talents, custom_talent_id(spec, index), "Talent.dbc")
        if u32(talent, 1) != tab_id:
            raise DBCError(f"Talent {definition['key']} is not on {tab_key} tab")

        pos = (u32(talent, 2), u32(talent, 3))
        if pos in seen_positions:
            raise DBCError(f"Duplicate {tab_key} talent position {pos}")
        seen_positions.add(pos)

        source_ids = talent_source_spell_ids(definition)
        reuse_native = bool(definition.get("reuse_native_spells"))
        expected_rank_ids = [
            source_id if reuse_native else custom_spell_id(spec, index, rank_index)
            for rank_index, source_id in enumerate(source_ids)
        ]
        actual_rank_ids = [u32(talent, field) for field in TALENT_RANK_FIELDS if u32(talent, field)]
        if actual_rank_ids != expected_rank_ids:
            raise DBCError(
                f"Talent {definition['key']} rank IDs expected {expected_rank_ids}, got {actual_rank_ids}"
            )
        total_points += len(actual_rank_ids)

        expected_book = 1 if definition.get("add_to_spellbook") else 0
        if u32(talent, TALENT_ADD_TO_SPELLBOOK_FIELD) != expected_book:
            raise DBCError(f"Talent {definition['key']} has wrong addToSpellBook flag")

        for rank_index, spell_id in enumerate(actual_rank_ids):
            spell = record_by_id(spells, spell_id, "Spell.dbc")

            if not reuse_native:
                if dbc_string(spells, u32(spell, SPELL_NAME_START)) != str(definition["enUS"]):
                    raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} has wrong enUS name")
                if dbc_string(spells, u32(spell, SPELL_NAME_START + LOCALE_ESMX)) != str(definition["esMX"]):
                    raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} has wrong esMX name")
                if index in icon_ids and u32(spell, SPELL_ICON_FIELD) != icon_ids[index]:
                    raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} has wrong icon")
                _validate_custom_fields(spell, definition, rank_index)

                trigger_ids = trigger_source_spell_ids(definition)
                if trigger_ids:
                    slot = int(definition.get("trigger_spell_slot", 0))
                    child_id = custom_trigger_spell_id(spec, index, rank_index)
                    if u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[slot]) != child_id:
                        raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} has wrong trigger spell")
                    child = record_by_id(spells, child_id, "Spell.dbc")
                    _validate_custom_fields(child, definition, rank_index, "trigger")

            for locale in (0, LOCALE_ESMX):
                description = dbc_string(spells, u32(spell, SPELL_DESCRIPTION_START + locale))
                if description and not reuse_native and has_forbidden_class_reference(description):
                    raise DBCError(
                        f"Talent {definition['key']} rank {rank_index + 1} description references another class: {description!r}"
                    )

    expected_points = spec_point_total(spec)
    if expected_points is not None and total_points != expected_points:
        raise DBCError(f"{tab_key} point total expected {expected_points}, got {total_points}")


def patch_talent_directory(dbc_dir: Path, spec_path: Path | None = None) -> dict[str, bool]:
    required = ("TalentTab.dbc", "Talent.dbc", "Spell.dbc", "SpellIcon.dbc")
    missing = [name for name in required if not (dbc_dir / name).is_file()]
    if missing:
        raise DBCError("Missing talent DBC(s): " + ", ".join(missing))

    specs = [load_spec(spec_path)] if spec_path is not None else load_specs()
    tab_changed = patch_talent_tabs(dbc_dir / "TalentTab.dbc", specs[0])
    talent_changed = False
    spell_changed = False
    for spec in specs:
        icon_ids = resolve_existing_icon_ids(dbc_dir / "SpellIcon.dbc", spec)
        changed_talent, changed_spell = patch_talents_and_spells(
            dbc_dir / "Talent.dbc", dbc_dir / "Spell.dbc", spec, icon_ids
        )
        talent_changed = talent_changed or changed_talent
        spell_changed = spell_changed or changed_spell

    for spec in specs:
        validate_talents(dbc_dir, spec)

    return {
        "TalentTab.dbc": tab_changed,
        "Talent.dbc": talent_changed,
        "Spell.dbc": spell_changed,
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("dbc_dir", type=Path)
    parser.add_argument("--spec", type=Path)
    args = parser.parse_args()
    result = patch_talent_directory(args.dbc_dir.expanduser().resolve(), args.spec)
    for name, changed in result.items():
        print(f"{name}: {'patched' if changed else 'already valid'}")
