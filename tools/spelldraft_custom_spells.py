#!/usr/bin/env python3
"""Build SpellDraft-owned active spell chains from clean WotLK spell rows.

SpellDraft v4 keeps native spells untouched and owns the identities it changes.
All three combo generators reuse Sinister Strike's rank cadence and flat bonus
progression; their balance differences live in energy cost and runtime weapon
coefficients/behaviour.
"""

from __future__ import annotations

from pathlib import Path

from dbc import DBC, DBCError, set_u32, u32
from subclasses import (
    SKILLLINEABILITY_FIELDS,
    SKILLLINEABILITY_RECORD_SIZE,
    SLA_SKILL_LINE,
    SLA_SPELL,
    normalize_custom_skill_line_ability,
)

SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
MERCENARY_SKILL_LINE_ID = 900

SINISTER_SOURCE_RANKS = (
    1752, 1757, 1758, 1759, 1760, 8621,
    11293, 11294, 26861, 26862, 48637, 48638,
)

SINISTER_RANKS = tuple(range(920000, 920012))
BRUTAL_SLAM_RANKS = tuple(range(920020, 920032))
RUTHLESS_CLEAVE_RANKS = tuple(range(920040, 920052))

CUSTOM_RANK_CHAINS = {
    SINISTER_RANKS[0]: SINISTER_RANKS,
    BRUTAL_SLAM_RANKS[0]: BRUTAL_SLAM_RANKS,
    RUTHLESS_CLEAVE_RANKS[0]: RUTHLESS_CLEAVE_RANKS,
}
CUSTOM_SPELL_IDS = frozenset(spell for chain in CUSTOM_RANK_CHAINS.values() for spell in chain)

CLEAVE_SOURCE_ID = 845
SHIELD_SLAM_SOURCE_ID = 23922

BRUTAL_SLAM_ICON_PATH = "Interface\\Icons\\INV_Shield_PandaRaid_D_02"
RUTHLESS_CLEAVE_ICON_PATH = "Interface\\Icons\\Ability_DemonHunter_SoulCleave"

POWER_ENERGY = 3
SPELL_EFFECT_SCHOOL_DAMAGE = 2

EFFECT_FIELD_STARTS = (
    71, 74, 77, 80, 83, 86, 89, 92, 95,
    98, 101, 104, 107, 110, 113, 116, 119,
)


def normalized_icon_path(value: str) -> str:
    value = value.replace("/", "\\")
    if value.lower().endswith(".blp"):
        value = value[:-4]
    return value.lower()


def _set_localized(dbc: DBC, row: bytearray, start_field: int, text: str) -> None:
    offset = dbc.append_string(text) if text else 0
    for field in range(start_field, start_field + 16):
        set_u32(row, field, offset)


def _set_text(
    dbc: DBC,
    row: bytearray,
    name: str,
    rank: int,
    description: str,
) -> None:
    _set_localized(dbc, row, 136, name)
    set_u32(row, 152, 0)
    _set_localized(dbc, row, 153, f"Rango {rank}")
    set_u32(row, 169, 0)
    _set_localized(dbc, row, 170, description)
    set_u32(row, 186, 0)
    _set_localized(dbc, row, 187, description)
    set_u32(row, 203, 0)


def _clear_effect(row: bytearray, index: int) -> None:
    for start in EFFECT_FIELD_STARTS:
        set_u32(row, start + index, 0)
    # EffectSpellClassMask is three uint32 values per effect.
    for field in range(122 + index * 3, 125 + index * 3):
        set_u32(row, field, 0)


def _clear_spell_family(row: bytearray) -> None:
    set_u32(row, 208, 0)
    set_u32(row, 209, 0)
    set_u32(row, 210, 0)
    set_u32(row, 211, 0)
    for field in range(122, 131):
        set_u32(row, field, 0)


def _set_energy_cost(row: bytearray, cost: int) -> None:
    set_u32(row, 41, POWER_ENERGY)
    set_u32(row, 42, cost)
    set_u32(row, 43, 0)
    set_u32(row, 44, 0)
    set_u32(row, 45, 0)
    set_u32(row, 204, 0)


def _copy_primary_targeting(row: bytearray, source: bytearray) -> None:
    # Preserve Sinister Strike's damage formula/flat bonus but borrow Cleave's
    # primary + nearby-target selection metadata.
    for field in (86, 89, 92, 104):
        set_u32(row, field, u32(source, field))


def _prepare_common(row: bytearray, spell_id: int, cost: int) -> None:
    set_u32(row, 0, spell_id)
    set_u32(row, 1, 0)  # no native class category ownership
    _set_energy_cost(row, cost)
    _clear_spell_family(row)


def _build_sinister(
    dbc: DBC,
    source: bytearray,
    spell_id: int,
    rank: int,
) -> bytearray:
    row = bytearray(source)
    _prepare_common(row, spell_id, 45)
    _clear_effect(row, 2)
    _set_text(
        dbc,
        row,
        "Golpe siniestro",
        rank,
        "Un golpe cruel que inflige el 75% del daño de arma más $s1 de daño. "
        "Con una daga inflige el 100% del daño de arma más $s1. Genera 1 punto de combo.",
    )
    return row


def _build_brutal_slam(
    dbc: DBC,
    source: bytearray,
    shield_visual: bytearray,
    spell_id: int,
    rank: int,
    icon_id: int,
) -> bytearray:
    row = bytearray(source)
    _prepare_common(row, spell_id, 40)

    # Sinister Strike gives us the same rank-by-rank flat bonus and a reliable
    # combo-point effect. Replace only the primary damage effect with physical
    # spell damage; the SpellScript adds Shield Slam-style block-value damage.
    set_u32(row, 71, SPELL_EFFECT_SCHOOL_DAMAGE)
    _clear_effect(row, 2)

    # Do not use Spell.dbc's generic EquippedItemClass requirement here. The
    # Adventurer owns shield proficiency outside the stock class matrix, so the
    # authoritative requirement is checked directly against the equipped
    # off-hand item by the SpellScript.
    set_u32(row, 68, 0xFFFFFFFF)
    set_u32(row, 69, 0)
    set_u32(row, 70, 0)

    set_u32(row, 131, u32(shield_visual, 131))
    set_u32(row, 132, u32(shield_visual, 132))
    set_u32(row, 133, icon_id)
    set_u32(row, 134, 0)

    _set_text(
        dbc,
        row,
        "Embate brutal",
        rank,
        "Golpea al enemigo con tu escudo, infligiendo daño físico basado en tu valor de bloqueo "
        "más $s1 de daño adicional. Requiere escudo. Genera 1 punto de combo.",
    )
    return row


def _build_ruthless_cleave(
    dbc: DBC,
    source: bytearray,
    cleave_source: bytearray,
    spell_id: int,
    rank: int,
    icon_id: int,
) -> bytearray:
    row = bytearray(source)
    _prepare_common(row, spell_id, 50)

    # Combo is conditional and is therefore granted by the SpellScript only
    # when two different enemies are actually hit.
    _clear_effect(row, 1)
    _clear_effect(row, 2)
    _copy_primary_targeting(row, cleave_source)
    set_u32(row, 212, 2)

    set_u32(row, 131, u32(cleave_source, 131))
    set_u32(row, 132, u32(cleave_source, 132))
    set_u32(row, 133, icon_id)
    set_u32(row, 134, 0)

    _set_text(
        dbc,
        row,
        "Tajo despiadado",
        rank,
        "Ataca al objetivo y a un enemigo cercano, infligiendo el 65% del daño de arma más $s1 "
        "de daño a cada uno. Genera 1 punto de combo solo si golpea a dos enemigos.",
    )
    return row


def patch(path: Path, icon_ids: dict[str, int]) -> bool:
    dbc = DBC.read(path)
    if dbc.fields != SPELL_FIELDS or dbc.record_size != SPELL_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected Spell.dbc layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    base_rows = [row for row in dbc.records if u32(row, 0) not in CUSTOM_SPELL_IDS]
    lookup = {u32(row, 0): row for row in base_rows}

    missing_sources = [spell for spell in (*SINISTER_SOURCE_RANKS, CLEAVE_SOURCE_ID, SHIELD_SLAM_SOURCE_ID) if spell not in lookup]
    if missing_sources:
        raise DBCError(f"{path}: missing stock spell source rows: {missing_sources}")

    brutal_icon = icon_ids.get(normalized_icon_path(BRUTAL_SLAM_ICON_PATH))
    ruthless_icon = icon_ids.get(normalized_icon_path(RUTHLESS_CLEAVE_ICON_PATH))
    missing_icons = []
    if brutal_icon is None:
        missing_icons.append(BRUTAL_SLAM_ICON_PATH)
    if ruthless_icon is None:
        missing_icons.append(RUTHLESS_CLEAVE_ICON_PATH)
    if missing_icons:
        raise DBCError(
            "SpellDraft v4 custom spell icons are missing from the external icon pack: "
            + ", ".join(missing_icons)
        )

    cleave_source = lookup[CLEAVE_SOURCE_ID]
    shield_source = lookup[SHIELD_SLAM_SOURCE_ID]
    custom_rows: list[bytearray] = []

    for index, source_id in enumerate(SINISTER_SOURCE_RANKS):
        rank = index + 1
        source = lookup[source_id]
        custom_rows.append(_build_sinister(dbc, source, SINISTER_RANKS[index], rank))
        custom_rows.append(
            _build_brutal_slam(
                dbc,
                source,
                shield_source,
                BRUTAL_SLAM_RANKS[index],
                rank,
                brutal_icon,
            )
        )
        custom_rows.append(
            _build_ruthless_cleave(
                dbc,
                source,
                cleave_source,
                RUTHLESS_CLEAVE_RANKS[index],
                rank,
                ruthless_icon,
            )
        )

    dbc.records = base_rows + custom_rows
    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)

    verify = DBC.read(path)
    present = {u32(row, 0) for row in verify.records}
    missing = sorted(CUSTOM_SPELL_IDS - present)
    if missing:
        raise DBCError(f"{path}: custom SpellDraft spell rows missing after patch: {missing}")
    return after != before


def patch_skill_line_ability(path: Path) -> bool:
    """Expose every custom rank in the Mercenary spellbook tab."""
    dbc = DBC.read(path)
    if dbc.fields != SKILLLINEABILITY_FIELDS or dbc.record_size != SKILLLINEABILITY_RECORD_SIZE:
        raise DBCError(
            f"{path}: unexpected SkillLineAbility layout {dbc.fields}/{dbc.record_size}"
        )

    before = dbc.to_bytes()
    dbc.records = [
        row for row in dbc.records
        if u32(row, SLA_SPELL) not in CUSTOM_SPELL_IDS
    ]
    next_id = max((u32(row, 0) for row in dbc.records), default=0) + 1

    for spell_id in sorted(CUSTOM_SPELL_IDS):
        row = bytearray(SKILLLINEABILITY_RECORD_SIZE)
        normalize_custom_skill_line_ability(
            row,
            next_id,
            MERCENARY_SKILL_LINE_ID,
            spell_id,
        )
        next_id += 1
        dbc.records.append(row)

    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)

    verify = DBC.read(path)
    present = {
        u32(row, SLA_SPELL)
        for row in verify.records
        if u32(row, SLA_SKILL_LINE) == MERCENARY_SKILL_LINE_ID
    }
    missing = sorted(CUSTOM_SPELL_IDS - present)
    if missing:
        raise DBCError(
            f"{path}: custom SpellDraft ranks missing from Mercenary skill line: {missing}"
        )
    return after != before
