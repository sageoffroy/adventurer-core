#!/usr/bin/env python3
"""Adapt Rogue talent spell masks/tooltips to SpellDraft v4 combo generators.

The three Adventurer combo generators keep their own spell IDs, but reuse the
stock Rogue spell-modifier system through three Adventurer-owned family bits.
Stock masks are only extended; native WotLK spell support is never removed.
"""

from __future__ import annotations

from pathlib import Path

from dbc import DBC, DBCError, set_u32, u32
from spelldraft_custom_spells import (
    BRUTAL_SLAM_ICON_PATH,
    BRUTAL_SLAM_RANKS,
    RUTHLESS_CLEAVE_ICON_PATH,
    RUTHLESS_CLEAVE_RANKS,
    SINISTER_RANKS,
    normalized_icon_path,
)

SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
FAMILY_FIELD = 208
FAMILY_MASK_FIELDS = (209, 210, 211)
EFFECT_CLASS_MASK_BASE = 122

IMPROVED_SOURCE_RANKS = (13732, 13863)
IMPROVED_SINISTER_RANKS = (920100, 920101)
IMPROVED_BRUTAL_RANKS = (920102, 920103)
IMPROVED_RUTHLESS_RANKS = (920104, 920105)
CUSTOM_TALENT_IDS = frozenset(
    (*IMPROVED_SINISTER_RANKS, *IMPROVED_BRUTAL_RANKS, *IMPROVED_RUTHLESS_RANKS)
)

# Visible talent roots whose native rank chains are read from Talent.dbc.
TALENT_MASK_EXTENSIONS = (
    # root, effect index, affected custom generators
    (14082, 1, "all"),       # Actos reprobables: low-health special damage
    (18427, 0, "sin_tajo"),  # Agresión
    (31234, 0, "all"),       # Descubrir debilidad: direct ability damage
    (32601, 1, "sin_tajo"),  # Ataques por sorpresa: damage half only
    (14128, 0, "all"),       # Letalidad
    (14186, 0, "all"),       # Sello del destino
    (31124, 1, "sin"),       # Malabares cortantes: damage half only
    (14177, 0, "all"),       # Sangre fría
)

# Internal/trigger spells. These are mechanics, not talent cards.
TRIGGER_MASK_EXTENSIONS = (
    (14143, 0, "all"),  # Sin remordimientos rank 1 buff
    (14149, 0, "all"),  # Sin remordimientos rank 2 buff
    (52910, 0, "all"),  # Ganar ventaja 6%
    (52914, 0, "all"),  # Ganar ventaja 2%
    (52915, 0, "all"),  # Ganar ventaja 4%
    (52916, 0, "all"),  # Honor entre ladrones slave
    (51662, 0, "all"),  # Hambre de sangre visible active talent
    (63848, 0, "all"),  # Hambre de sangre damage buff
    (36563, 1, "all"),  # Paso de las Sombras damage buff
    (44373, 0, "all"),  # Paso de las Sombras threat buff
)


def _set_localized(dbc: DBC, row: bytearray, start_field: int, text: str) -> None:
    offset = dbc.append_string(text) if text else 0
    for field in range(start_field, start_field + 16):
        set_u32(row, field, offset)


def _set_description(dbc: DBC, row: bytearray, text: str) -> None:
    _set_localized(dbc, row, 170, text)
    set_u32(row, 186, 0)
    _set_localized(dbc, row, 187, text)
    set_u32(row, 203, 0)


def _set_name_rank_description(
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
    _set_description(dbc, row, description)


def _talent_aliases(path: Path) -> dict[int, tuple[int, ...]]:
    dbc = DBC.read(path)
    if dbc.fields < 9:
        raise DBCError(f"{path}: unexpected Talent.dbc layout {dbc.fields}/{dbc.record_size}")

    aliases: dict[int, tuple[int, ...]] = {}
    for row in dbc.records:
        ranks = tuple(u32(row, field) for field in range(4, 9) if u32(row, field))
        if not ranks:
            continue
        for spell_id in ranks:
            aliases[spell_id] = ranks
    return aliases


def _allocate_family_bits(rows: list[bytearray], rogue_family: int) -> tuple[int, int, int]:
    used = [0, 0, 0]
    for row in rows:
        if u32(row, FAMILY_FIELD) != rogue_family:
            continue
        for index, field in enumerate(FAMILY_MASK_FIELDS):
            used[index] |= u32(row, field)

    free: list[int] = []
    for bit in range(95, -1, -1):
        word, offset = divmod(bit, 32)
        if not (used[word] & (1 << offset)):
            free.append(bit)
        if len(free) == 3:
            break
    if len(free) != 3:
        raise DBCError("SpellDraft v4 could not reserve three unused Rogue family bits")
    return tuple(free)  # type: ignore[return-value]


def _bit_words(bit: int) -> tuple[int, int, int]:
    words = [0, 0, 0]
    word, offset = divmod(bit, 32)
    words[word] = 1 << offset
    return tuple(words)  # type: ignore[return-value]


def _or_words(*values: tuple[int, int, int]) -> tuple[int, int, int]:
    return tuple(a | b | c for a, b, c in zip(*values))  # type: ignore[return-value]


def _set_spell_family(row: bytearray, rogue_family: int, words: tuple[int, int, int]) -> None:
    set_u32(row, FAMILY_FIELD, rogue_family)
    for field, value in zip(FAMILY_MASK_FIELDS, words):
        set_u32(row, field, value)


def _effect_mask(row: bytearray, effect_index: int) -> tuple[int, int, int]:
    start = EFFECT_CLASS_MASK_BASE + effect_index * 3
    return tuple(u32(row, start + i) for i in range(3))  # type: ignore[return-value]


def _set_effect_mask(row: bytearray, effect_index: int, words: tuple[int, int, int]) -> None:
    start = EFFECT_CLASS_MASK_BASE + effect_index * 3
    for index, value in enumerate(words):
        set_u32(row, start + index, value)


def _extend_effect_mask(row: bytearray, effect_index: int, words: tuple[int, int, int]) -> None:
    current = _effect_mask(row, effect_index)
    # Zero means the stock spell does not use a SpellClassMask for this effect;
    # do not turn a global effect into a restricted one accidentally.
    if not any(current):
        return
    _set_effect_mask(row, effect_index, tuple(a | b for a, b in zip(current, words)))


def _words_for_group(
    group: str,
    sinister: tuple[int, int, int],
    brutal: tuple[int, int, int],
    ruthless: tuple[int, int, int],
) -> tuple[int, int, int]:
    if group == "all":
        return _or_words(sinister, brutal, ruthless)
    if group == "sin_tajo":
        return _or_words(sinister, ruthless)
    if group == "sin":
        return sinister
    raise DBCError(f"unknown custom talent mask group {group}")


def _patch_chain(
    lookup: dict[int, bytearray],
    aliases: dict[int, tuple[int, ...]],
    root: int,
    effect_index: int,
    words: tuple[int, int, int],
) -> None:
    ranks = aliases.get(root, (root,))
    missing = [spell_id for spell_id in ranks if spell_id not in lookup]
    if missing:
        raise DBCError(f"SpellDraft v4 talent chain {root} missing Spell.dbc rows {missing}")
    for spell_id in ranks:
        _extend_effect_mask(lookup[spell_id], effect_index, words)


def _clone_improved_talent(
    dbc: DBC,
    source: bytearray,
    spell_id: int,
    name: str,
    rank: int,
    energy_reduction: int,
    words: tuple[int, int, int],
    icon_id: int | None,
) -> bytearray:
    row = bytearray(source)
    set_u32(row, 0, spell_id)
    if icon_id is not None:
        set_u32(row, 133, icon_id)
    for effect_index in range(3):
        _set_effect_mask(row, effect_index, (0, 0, 0))
    _set_effect_mask(row, 0, words)
    _set_name_rank_description(
        dbc,
        row,
        name,
        rank,
        f"Reduce el coste de energía de {name.removesuffix(' mejorado')} en {energy_reduction} p.",
    )
    return row


def _patch_tooltips(
    dbc: DBC,
    lookup: dict[int, bytearray],
    aliases: dict[int, tuple[int, ...]],
) -> None:
    for spell_id in aliases.get(18427, (18427,)):
        if spell_id in lookup:
            _set_description(
                dbc,
                lookup[spell_id],
                "Aumenta el daño de Golpe siniestro, Tajo despiadado, Puñalada y Eviscerar.",
            )

    for spell_id in aliases.get(31234, (31234,)):
        if spell_id in lookup:
            _set_description(
                dbc,
                lookup[spell_id],
                "Daño de facultades ofensivas que cuestan energía aumentado.",
            )

    if 32601 in lookup:
        _set_description(
            dbc,
            lookup[32601],
            "Tus remates ya no se pueden esquivar, y el daño de Golpe siniestro, Tajo despiadado, "
            "Puñalada, Puyazo, Hemorragia y Gubia aumenta un 10%.",
        )

    for spell_id in aliases.get(14144, (14144,)):
        if spell_id in lookup:
            _set_description(
                dbc,
                lookup[spell_id],
                "Después de matar a un enemigo que otorgue experiencia u honor, aumenta la probabilidad "
                "de golpe crítico de tu siguiente facultad ofensiva que genere puntos de combo y no "
                "requiera sigilo. Dura 20 s.",
            )

    shadowstep = lookup.get(36554)
    if shadowstep is not None:
        _set_description(
            dbc,
            shadowstep,
            "Intenta avanzar entre las sombras y reaparecer detrás del enemigo, aumentando tu velocidad "
            "de movimiento un 70% durante 3 s. El daño de tu siguiente facultad ofensiva que requiera "
            "energía aumenta un 20% y la amenaza que causa se reduce un 50%. Dura 10 s.",
        )


def patch(spell_path: Path, talent_path: Path, icon_ids: dict[str, int]) -> bool:
    dbc = DBC.read(spell_path)
    if dbc.fields != SPELL_FIELDS or dbc.record_size != SPELL_RECORD_SIZE:
        raise DBCError(
            f"{spell_path}: unexpected Spell.dbc layout {dbc.fields}/{dbc.record_size}"
        )

    before = dbc.to_bytes()
    dbc.records = [row for row in dbc.records if u32(row, 0) not in CUSTOM_TALENT_IDS]
    lookup = {u32(row, 0): row for row in dbc.records}

    sinister_source = lookup.get(1752)
    if sinister_source is None:
        raise DBCError("SpellDraft v4 requires stock Sinister Strike 1752")
    rogue_family = u32(sinister_source, FAMILY_FIELD)
    if not rogue_family:
        raise DBCError("stock Sinister Strike has no Rogue spell family")

    bits = _allocate_family_bits(dbc.records, rogue_family)
    sinister_words, brutal_words, ruthless_words = map(_bit_words, bits)

    for spell_id in SINISTER_RANKS:
        _set_spell_family(lookup[spell_id], rogue_family, sinister_words)
    for spell_id in BRUTAL_SLAM_RANKS:
        _set_spell_family(lookup[spell_id], rogue_family, brutal_words)
    for spell_id in RUTHLESS_CLEAVE_RANKS:
        _set_spell_family(lookup[spell_id], rogue_family, ruthless_words)

    aliases = _talent_aliases(talent_path)
    for root, effect_index, group in TALENT_MASK_EXTENSIONS:
        _patch_chain(
            lookup,
            aliases,
            root,
            effect_index,
            _words_for_group(group, sinister_words, brutal_words, ruthless_words),
        )

    for spell_id, effect_index, group in TRIGGER_MASK_EXTENSIONS:
        row = lookup.get(spell_id)
        if row is not None:
            _extend_effect_mask(
                row,
                effect_index,
                _words_for_group(group, sinister_words, brutal_words, ruthless_words),
            )

    brutal_icon = icon_ids.get(normalized_icon_path(BRUTAL_SLAM_ICON_PATH))
    ruthless_icon = icon_ids.get(normalized_icon_path(RUTHLESS_CLEAVE_ICON_PATH))
    source_rows = [lookup.get(spell_id) for spell_id in IMPROVED_SOURCE_RANKS]
    if any(row is None for row in source_rows):
        raise DBCError("SpellDraft v4 missing Improved Sinister Strike source ranks")

    custom_rows: list[bytearray] = []
    specs = (
        (IMPROVED_SINISTER_RANKS, "Golpe siniestro mejorado", sinister_words, None),
        (IMPROVED_BRUTAL_RANKS, "Embate brutal mejorado", brutal_words, brutal_icon),
        (IMPROVED_RUTHLESS_RANKS, "Tajo despiadado mejorado", ruthless_words, ruthless_icon),
    )
    for rank_index, source in enumerate(source_rows):
        assert source is not None
        for ids, name, words, icon_id in specs:
            custom_rows.append(
                _clone_improved_talent(
                    dbc,
                    source,
                    ids[rank_index],
                    name,
                    rank_index + 1,
                    3 if rank_index == 0 else 5,
                    words,
                    icon_id,
                )
            )

    dbc.records.extend(custom_rows)
    lookup.update({u32(row, 0): row for row in custom_rows})
    _patch_tooltips(dbc, lookup, aliases)

    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        spell_path.write_bytes(after)

    verify = DBC.read(spell_path)
    present = {u32(row, 0) for row in verify.records}
    missing = sorted(CUSTOM_TALENT_IDS - present)
    if missing:
        raise DBCError(f"SpellDraft v4 custom talent rows missing after patch: {missing}")
    return after != before
