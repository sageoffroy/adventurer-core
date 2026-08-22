#!/usr/bin/env python3
"""Generate native Adventurer talent tabs and cloned talent spells for WotLK 3.3.5a."""

from __future__ import annotations

import json
from pathlib import Path

from dbc import DBC, DBCError, ADVENTURER_CLASS_MASK, LOCALE_ESES, LOCALE_ESMX, u32, set_u32

ROOT = Path(__file__).resolve().parent.parent
SPEC_PATH = ROOT / "talents" / "guardian.json"

TALENT_FIELDS = 23
TALENT_RECORD_SIZE = TALENT_FIELDS * 4
TALENTTAB_FIELDS = 24
TALENTTAB_RECORD_SIZE = TALENTTAB_FIELDS * 4
SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
SPELLICON_FIELDS = 2
SPELLICON_RECORD_SIZE = SPELLICON_FIELDS * 4

TALENT_RANK_FIELDS = tuple(range(4, 13))
TALENT_PREREQ_TALENT_FIELDS = (13, 14, 15)
TALENT_PREREQ_RANK_FIELDS = (16, 17, 18)
TALENT_REQUIRED_SPELL_FIELD = 20
TALENT_CATEGORY_FIELDS = (21, 22)

TALENTTAB_NAME_START = 1
TALENTTAB_CLASS_MASK_FIELD = 20
TALENTTAB_PET_MASK_FIELD = 21
TALENTTAB_ORDER_FIELD = 22

SPELL_EFFECT_FIELDS = (71, 72, 73)
SPELL_EFFECT_BASEPOINT_FIELDS = (80, 81, 82)
SPELL_EFFECT_APPLY_AURA_FIELDS = (95, 96, 97)
SPELL_EFFECT_TRIGGER_SPELL_FIELDS = (116, 117, 118)
SPELL_ICON_FIELD = 133
SPELL_NAME_START = 136
SPELL_RANK_START = 153
SPELL_DESCRIPTION_START = 170
SPELLICON_PATH_FIELD = 1


def load_spec(path: Path = SPEC_PATH) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != 1:
        raise DBCError(f"Unsupported talent spec schema: {data.get('schema')}")
    return data


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


def normalized_icon_name(value: str) -> str:
    name = value.replace("/", "\\").rsplit("\\", 1)[-1]
    if name.lower().endswith(".blp"):
        name = name[:-4]
    return name.lower()


def resolve_existing_icon_ids(path: Path, spec: dict) -> dict[int, int]:
    """Resolve authored icon names against the stock SpellIcon.dbc; never create icons."""
    icons = DBC.read(path)
    if icons.fields != SPELLICON_FIELDS or icons.record_size != SPELLICON_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected SpellIcon layout {icons.fields}/{icons.record_size}")

    by_name: dict[str, int] = {}
    for row in icons.records:
        raw_path = dbc_string(icons, u32(row, SPELLICON_PATH_FIELD))
        if not raw_path:
            continue
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


def custom_talent_id(spec: dict, talent_index: int) -> int:
    return int(spec["talent_id_base"]) + talent_index


def talent_rank_count(row: bytearray) -> int:
    return sum(1 for field in TALENT_RANK_FIELDS if u32(row, field) != 0)


def apply_authored_effect_values(spell: bytearray, definition: dict, rank_index: int) -> None:
    for raw_slot, values in definition.get("effect_values", {}).items():
        slot = int(raw_slot)
        if not 0 <= slot < len(SPELL_EFFECT_BASEPOINT_FIELDS):
            raise DBCError(f"Effect slot {slot} out of range for {definition['key']}")
        if rank_index >= len(values):
            raise DBCError(f"Missing effect value for {definition['key']} rank {rank_index + 1}")
        value = int(values[rank_index])
        if value <= 0:
            raise DBCError(f"Effect values must be positive for {definition['key']}")
        # WotLK Spell.dbc stores the displayed scalar as BasePoints + 1.
        set_u32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[slot], value - 1)


def apply_authored_disabled_effects(spell: bytearray, definition: dict) -> None:
    for raw_slot in definition.get("disable_effects", []):
        slot = int(raw_slot)
        if not 0 <= slot < len(SPELL_EFFECT_FIELDS):
            raise DBCError(f"Disabled effect slot {slot} out of range for {definition['key']}")
        set_u32(spell, SPELL_EFFECT_FIELDS[slot], 0)
        set_u32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[slot], 0)
        set_u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[slot], 0)
        set_u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[slot], 0)


def apply_authored_description(spells: DBC, spell: bytearray, definition: dict) -> None:
    en_us = definition.get("description_enUS")
    es_mx = definition.get("description_esMX")
    if en_us is None and es_mx is None:
        return
    if en_us is None or es_mx is None:
        raise DBCError(f"Talent {definition['key']} must define both description_enUS and description_esMX")
    set_localized_block(spells, spell, SPELL_DESCRIPTION_START, str(en_us), str(es_mx))


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

    owned_talent_ids = {custom_talent_id(spec, i) for i in range(len(talent_defs))}
    owned_spell_ids: set[int] = set()
    for i, definition in enumerate(talent_defs):
        source = record_by_id(talents, int(definition["source_talent_id"]), "Talent.dbc")
        for rank_index, field in enumerate(TALENT_RANK_FIELDS):
            if u32(source, field):
                owned_spell_ids.add(custom_spell_id(spec, i, rank_index))

    talents.records = [r for r in talents.records if u32(r, 0) not in owned_talent_ids]
    spells.records = [r for r in spells.records if u32(r, 0) not in owned_spell_ids]

    source_talents = {
        int(d["source_talent_id"]): bytearray(record_by_id(talents, int(d["source_talent_id"]), "Talent.dbc"))
        for d in talent_defs
    }
    source_spells = {u32(r, 0): bytearray(r) for r in spells.records}
    key_to_index = {d["key"]: i for i, d in enumerate(talent_defs)}
    guardian_tab = next(tab for tab in spec["tabs"] if tab["key"] == "guardian")

    rebuilt: list[bytearray] = []
    for index, definition in enumerate(talent_defs):
        source = bytearray(source_talents[int(definition["source_talent_id"])])
        set_u32(source, 0, custom_talent_id(spec, index))
        set_u32(source, 1, int(guardian_tab["id"]))
        set_u32(source, 2, int(definition["row"]))
        set_u32(source, 3, int(definition["col"]))

        source_rank_ids = [u32(source, field) for field in TALENT_RANK_FIELDS]
        rank_count = sum(1 for spell_id in source_rank_ids if spell_id)
        for raw_slot, values in definition.get("effect_values", {}).items():
            if len(values) != rank_count:
                raise DBCError(
                    f"{definition['key']} effect slot {raw_slot} has {len(values)} values for {rank_count} talent ranks"
                )

        for rank_index, field in enumerate(TALENT_RANK_FIELDS):
            native_rank_spell_id = source_rank_ids[rank_index]
            if not native_rank_spell_id:
                set_u32(source, field, 0)
                continue

            mechanic_spell_id = int(definition.get("spell_source_id", native_rank_spell_id))
            native_spell = source_spells.get(mechanic_spell_id)
            if native_spell is None:
                raise DBCError(f"Spell.dbc: talent source spell {mechanic_spell_id} not found")

            new_spell_id = custom_spell_id(spec, index, rank_index)
            cloned_spell = bytearray(native_spell)
            set_u32(cloned_spell, 0, new_spell_id)
            set_localized_block(spells, cloned_spell, SPELL_NAME_START, definition["enUS"], definition["esMX"])
            set_localized_block(
                spells,
                cloned_spell,
                SPELL_RANK_START,
                f"Rank {rank_index + 1}",
                f"Rango {rank_index + 1}",
            )
            apply_authored_description(spells, cloned_spell, definition)
            if index in icon_ids:
                set_u32(cloned_spell, SPELL_ICON_FIELD, icon_ids[index])
            apply_authored_effect_values(cloned_spell, definition, rank_index)
            apply_authored_disabled_effects(cloned_spell, definition)
            spells.records.append(cloned_spell)
            set_u32(source, field, new_spell_id)

        for field in TALENT_PREREQ_TALENT_FIELDS + TALENT_PREREQ_RANK_FIELDS:
            set_u32(source, field, 0)
        set_u32(source, TALENT_REQUIRED_SPELL_FIELD, 0)
        for field in TALENT_CATEGORY_FIELDS:
            set_u32(source, field, 0)

        required_key = definition.get("requires")
        if required_key:
            if required_key not in key_to_index:
                raise DBCError(f"Unknown talent prerequisite {required_key!r}")
            required_index = key_to_index[required_key]
            required_source = source_talents[int(talent_defs[required_index]["source_talent_id"])]
            required_rank = int(definition.get("required_rank", talent_rank_count(required_source) - 1))
            set_u32(source, TALENT_PREREQ_TALENT_FIELDS[0], custom_talent_id(spec, required_index))
            set_u32(source, TALENT_PREREQ_RANK_FIELDS[0], required_rank)

        rebuilt.append(source)

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

    guardian_tab_id = int(next(tab for tab in spec["tabs"] if tab["key"] == "guardian")["id"])
    seen_positions: set[tuple[int, int]] = set()
    for index, definition in enumerate(spec["talents"]):
        row = record_by_id(talents, custom_talent_id(spec, index), "Talent.dbc")
        if u32(row, 1) != guardian_tab_id:
            raise DBCError(f"Talent {definition['key']} is not on Guardian tab")
        pos = (u32(row, 2), u32(row, 3))
        if pos in seen_positions:
            raise DBCError(f"Duplicate Guardian talent position {pos}")
        seen_positions.add(pos)

        rank_ids = [u32(row, field) for field in TALENT_RANK_FIELDS if u32(row, field)]
        if not rank_ids:
            raise DBCError(f"Talent {definition['key']} has no ranks")

        for rank_index, spell_id in enumerate(rank_ids):
            spell = record_by_id(spells, spell_id, "Spell.dbc")
            if index in icon_ids and u32(spell, SPELL_ICON_FIELD) != icon_ids[index]:
                raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} has wrong stock icon")
            for raw_slot, values in definition.get("effect_values", {}).items():
                slot = int(raw_slot)
                expected = int(values[rank_index]) - 1
                actual = u32(spell, SPELL_EFFECT_BASEPOINT_FIELDS[slot])
                if actual != expected:
                    raise DBCError(
                        f"Talent {definition['key']} rank {rank_index + 1} effect {slot} expected {expected}, got {actual}"
                    )
            for raw_slot in definition.get("disable_effects", []):
                slot = int(raw_slot)
                if u32(spell, SPELL_EFFECT_FIELDS[slot]) != 0:
                    raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} effect {slot} was not disabled")
                if u32(spell, SPELL_EFFECT_APPLY_AURA_FIELDS[slot]) != 0:
                    raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} aura {slot} was not disabled")
                if u32(spell, SPELL_EFFECT_TRIGGER_SPELL_FIELDS[slot]) != 0:
                    raise DBCError(f"Talent {definition['key']} rank {rank_index + 1} trigger {slot} was not disabled")


def patch_talent_directory(dbc_dir: Path, spec_path: Path = SPEC_PATH) -> dict[str, bool]:
    required = ("TalentTab.dbc", "Talent.dbc", "Spell.dbc", "SpellIcon.dbc")
    missing = [name for name in required if not (dbc_dir / name).is_file()]
    if missing:
        raise DBCError("Missing talent DBC(s): " + ", ".join(missing))

    spec = load_spec(spec_path)
    icon_ids = resolve_existing_icon_ids(dbc_dir / "SpellIcon.dbc", spec)
    tab_changed = patch_talent_tabs(dbc_dir / "TalentTab.dbc", spec)
    talent_changed, spell_changed = patch_talents_and_spells(
        dbc_dir / "Talent.dbc", dbc_dir / "Spell.dbc", spec, icon_ids
    )
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
    parser.add_argument("--spec", type=Path, default=SPEC_PATH)
    args = parser.parse_args()
    result = patch_talent_directory(args.dbc_dir.expanduser().resolve(), args.spec)
    for name, changed in result.items():
        print(f"{name}: {'patched' if changed else 'already valid'}")
