#!/usr/bin/env python3
"""Keep Adventurer spellbook subclass tabs aligned with AzerothCore rank chains."""

from __future__ import annotations

import re
from pathlib import Path

from dbc import ADVENTURER_CLASS_MASK, DBC, set_u32, u32
from subclasses import (
    CARDS_PATH,
    SKILLLINEABILITY_FIELDS,
    SKILLLINEABILITY_RECORD_SIZE,
    SLA_CLASS_MASK,
    SLA_EXCLUDE_CLASS,
    SLA_SKILL_LINE,
    SLA_SPELL,
    SubclassError,
    active_spell_seeds,
    load_spec,
    normalize_custom_skill_line_ability,
    subclass_by_key,
)

SPELL_RANK_TUPLE = re.compile(r"\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)")


class SpellRankTabError(SubclassError):
    pass


def load_server_rank_chains(path: Path) -> dict[int, tuple[int, ...]]:
    """Return the exact rank chain for every spell listed in spell_ranks.sql."""
    if not path.is_file():
        raise SpellRankTabError(f"AzerothCore spell rank source not found: {path}")

    text = path.read_text(encoding="utf-8")
    if "spell_ranks" not in text or "first_spell_id" not in text:
        raise SpellRankTabError(f"Unexpected spell rank source: {path}")

    by_first: dict[int, dict[int, int]] = {}
    spell_owner: dict[int, int] = {}
    for raw_first, raw_spell, raw_rank in SPELL_RANK_TUPLE.findall(text):
        first = int(raw_first)
        spell = int(raw_spell)
        rank = int(raw_rank)
        if not first or not spell or not rank:
            continue

        previous_first = spell_owner.get(spell)
        if previous_first is not None and previous_first != first:
            raise SpellRankTabError(
                f"spell {spell} belongs to rank chains {previous_first} and {first}"
            )
        spell_owner[spell] = first

        ranks = by_first.setdefault(first, {})
        previous_spell = ranks.get(rank)
        if previous_spell is not None and previous_spell != spell:
            raise SpellRankTabError(
                f"rank chain {first} has two spells at rank {rank}: {previous_spell}, {spell}"
            )
        ranks[rank] = spell

    if not by_first:
        raise SpellRankTabError(f"No spell rank rows found in {path}")

    by_spell: dict[int, tuple[int, ...]] = {}
    for first, ranks in by_first.items():
        ordered_ranks = sorted(ranks)
        if ordered_ranks[0] != 1 or ordered_ranks != list(range(1, ordered_ranks[-1] + 1)):
            raise SpellRankTabError(
                f"rank chain {first} is not contiguous: {ordered_ranks}"
            )
        chain = tuple(ranks[rank] for rank in ordered_ranks)
        if chain[0] != first:
            raise SpellRankTabError(
                f"rank chain {first} starts with spell {chain[0]} instead of its first_spell_id"
            )
        for spell in chain:
            by_spell[spell] = chain
    return by_spell


def server_rank_classification(
    cards_text: str,
    spec: dict,
    chains: dict[int, tuple[int, ...]],
) -> dict[int, str]:
    """Expand every drafted active spell through AzerothCore's runtime chain."""
    classified: dict[int, str] = {}
    for seed_spell, subclass in active_spell_seeds(cards_text, spec).items():
        for spell_id in chains.get(seed_spell, (seed_spell,)):
            previous = classified.get(spell_id)
            if previous and previous != subclass:
                raise SpellRankTabError(
                    f"server rank {spell_id} maps to both {previous} and {subclass}"
                )
            classified[spell_id] = subclass
    return classified


def patch_server_rank_tabs(
    path: Path,
    spell_ranks_path: Path,
    cards_text: str | None = None,
    spec: dict | None = None,
) -> bool:
    """Add subclass SkillLineAbility rows for every server-learnable active rank.

    The server upgrades drafted active abilities through SpellMgr's spell rank
    chain. That chain comes from db_world.spell_ranks, not from the client's
    SkillLineAbility.SupercededBySpell field, so the DBC must be expanded from
    the same SQL source or higher ranks can fall out of the custom spell tabs.
    """
    spec = spec or load_spec()
    cards_text = cards_text if cards_text is not None else CARDS_PATH.read_text(encoding="utf-8")
    chains = load_server_rank_chains(spell_ranks_path)
    classified = server_rank_classification(cards_text, spec, chains)
    by_key = subclass_by_key(spec)
    custom_skill_ids = {int(item["skill_line_id"]) for item in spec["subclasses"]}

    dbc = DBC.read(path)
    if dbc.fields != SKILLLINEABILITY_FIELDS or dbc.record_size != SKILLLINEABILITY_RECORD_SIZE:
        raise SpellRankTabError(
            f"{path}: unexpected SkillLineAbility layout {dbc.fields}/{dbc.record_size}"
        )

    before = dbc.to_bytes()
    rows_by_spell: dict[int, list[bytearray]] = {}
    for row in dbc.records:
        rows_by_spell.setdefault(u32(row, SLA_SPELL), []).append(row)

    next_id = max((u32(row, 0) for row in dbc.records), default=0) + 1
    for spell_id in sorted(classified):
        skill_id = int(by_key[classified[spell_id]]["skill_line_id"])
        candidates = rows_by_spell.get(spell_id, [])

        existing_custom = [
            row for row in candidates if u32(row, SLA_SKILL_LINE) in custom_skill_ids
        ]
        wrong_custom = [
            row for row in existing_custom if u32(row, SLA_SKILL_LINE) != skill_id
        ]
        if wrong_custom:
            raise SpellRankTabError(
                f"server rank {spell_id} already maps to the wrong Adventurer subclass"
            )

        for row in candidates:
            if (
                u32(row, SLA_SKILL_LINE) not in custom_skill_ids
                and u32(row, SLA_CLASS_MASK) == 0
            ):
                set_u32(
                    row,
                    SLA_EXCLUDE_CLASS,
                    u32(row, SLA_EXCLUDE_CLASS) | ADVENTURER_CLASS_MASK,
                )

        if existing_custom:
            continue

        stock_candidates = [
            row for row in candidates if u32(row, SLA_SKILL_LINE) not in custom_skill_ids
        ]
        if stock_candidates:
            template = next(
                (row for row in stock_candidates if u32(row, SLA_CLASS_MASK) != 0),
                stock_candidates[0],
            )
            row = bytearray(template)
        else:
            row = bytearray(SKILLLINEABILITY_RECORD_SIZE)

        normalize_custom_skill_line_ability(row, next_id, skill_id, spell_id)
        next_id += 1
        dbc.records.append(row)
        rows_by_spell.setdefault(spell_id, []).append(row)

    for spell_id, subclass in classified.items():
        skill_id = int(by_key[subclass]["skill_line_id"])
        if not any(
            u32(row, SLA_SPELL) == spell_id
            and u32(row, SLA_SKILL_LINE) == skill_id
            and u32(row, SLA_CLASS_MASK) == ADVENTURER_CLASS_MASK
            for row in dbc.records
        ):
            raise SpellRankTabError(
                f"server rank {spell_id} is not mapped to subclass skill {skill_id}"
            )

    dbc.records.sort(key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before
