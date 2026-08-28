#!/usr/bin/env python3
"""Normalize SpellDraft spell metadata against AzerothCore rank chains."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import tempfile
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
SPELL_FIELDS = 234
SPELL_RECORD_SIZE = SPELL_FIELDS * 4
SPELL_TOTEM_FIELDS = (50, 51)
SPELL_REAGENT_FIELDS = tuple(range(52, 60))
SPELL_REAGENT_COUNT_FIELDS = tuple(range(60, 68))
SPELL_TOTEM_CATEGORY_FIELDS = (222, 223)
SPELL_COMPONENT_FIELDS = (
    SPELL_TOTEM_FIELDS
    + SPELL_REAGENT_FIELDS
    + SPELL_REAGENT_COUNT_FIELDS
    + SPELL_TOTEM_CATEGORY_FIELDS
)


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
        chain = tuple(ranks[rank] for rank in ordered_ranks)
        if ordered_ranks[0] != 1 or chain[0] != first:
            raise SpellRankTabError(
                f"rank chain {first} does not start at rank 1 with its first_spell_id"
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
    """Add subclass SkillLineAbility rows for every server-learnable active rank."""
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


def patch_component_free_drafted_spells(
    path: Path,
    spell_ranks_path: Path,
    cards_text: str | None = None,
    spec: dict | None = None,
) -> bool:
    """Remove inventory component/tool requirements from all drafted active ranks.

    SpellDraft abilities are self-contained for Adventurers.  We preserve weapon
    and armor requirements because they are combat mechanics, but remove WotLK's
    Totem, Reagent/ReagentCount and TotemCategory fields.  Expansion through the
    server spell_ranks table makes the rule apply to automatically learned ranks
    too, not just the rank originally listed in cards.csv.
    """
    spec = spec or load_spec()
    cards_text = cards_text if cards_text is not None else CARDS_PATH.read_text(encoding="utf-8")
    chains = load_server_rank_chains(spell_ranks_path)
    drafted = server_rank_classification(cards_text, spec, chains)

    dbc = DBC.read(path)
    if dbc.fields != SPELL_FIELDS or dbc.record_size != SPELL_RECORD_SIZE:
        raise SpellRankTabError(f"{path}: unexpected Spell layout {dbc.fields}/{dbc.record_size}")

    rows_by_id = {u32(row, 0): row for row in dbc.records}
    missing = sorted(set(drafted) - set(rows_by_id))
    if missing:
        raise SpellRankTabError(
            "Spell.dbc is missing drafted spell ranks: " + ", ".join(map(str, missing))
        )

    before = dbc.to_bytes()
    for spell_id in sorted(drafted):
        row = rows_by_id[spell_id]
        for field in SPELL_COMPONENT_FIELDS:
            set_u32(row, field, 0)

    for spell_id in drafted:
        row = rows_by_id[spell_id]
        if any(u32(row, field) != 0 for field in SPELL_COMPONENT_FIELDS):
            raise SpellRankTabError(
                f"drafted spell {spell_id} still has a component/tool requirement"
            )

    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before


def install_rank_tabs(
    core_dir: Path,
    client_dir: Path,
    server_data_dir: Path | None,
    locale: str,
) -> bool:
    """Transactionally refresh SpellDraft rank tabs and component-free spell data."""
    from adventurer import load_state, save_state, sha256_file, verify_state
    from client import DBC_NAMES, OWNER_MANIFEST, build_archive_files
    from mpq import write_mpq

    core = core_dir.expanduser().resolve()
    client = client_dir.expanduser().resolve()
    data_dir = (
        server_data_dir.expanduser().resolve()
        if server_data_dir
        else core / "env" / "dist" / "data"
    )
    server_dbc = data_dir / "dbc"
    spell_ranks = core / "data" / "sql" / "base" / "db_world" / "spell_ranks.sql"

    if not server_dbc.is_dir():
        raise SpellRankTabError(f"Server DBC directory not found: {server_dbc}")
    missing = [name for name in DBC_NAMES if not (server_dbc / name).is_file()]
    if missing:
        raise SpellRankTabError("Installed server DBC bundle is incomplete: " + ", ".join(missing))

    state = load_state(core)
    client_state = state.get("client") or {}
    installed = client_state.get("installed") or {}
    root_relative = installed.get("root_patch")
    locale_relative = installed.get("locale_patch")
    if not root_relative or not locale_relative:
        raise SpellRankTabError("Adventurer client ownership state is incomplete")

    root_target = client / root_relative
    locale_target = client / locale_relative
    owner_path = client / OWNER_MANIFEST
    state_path = core / ".adventurer-core" / "state.json"
    for target, label in (
        (root_target, "root client patch"),
        (locale_target, "locale client patch"),
        (owner_path, "client ownership manifest"),
        (state_path, "Adventurer state"),
    ):
        if not target.is_file():
            raise SpellRankTabError(f"Missing {label}: {target}")

    with tempfile.TemporaryDirectory(prefix="adventurer-spell-metadata-") as td:
        temp = Path(td)
        work = temp / "dbc"
        work.mkdir(parents=True)
        for name in DBC_NAMES:
            shutil.copy2(server_dbc / name, work / name)

        tabs_changed = patch_server_rank_tabs(work / "SkillLineAbility.dbc", spell_ranks)
        components_changed = patch_component_free_drafted_spells(
            work / "Spell.dbc", spell_ranks
        )
        if not tabs_changed and not components_changed:
            return False

        root_files, locale_files = build_archive_files(work)
        built_root = temp / "root.mpq"
        built_locale = temp / "locale.mpq"
        write_mpq(built_root, root_files)
        write_mpq(built_locale, locale_files)

        backups = temp / "previous"
        backups.mkdir()
        previous = {
            server_dbc / "SkillLineAbility.dbc": backups / "SkillLineAbility.dbc",
            server_dbc / "Spell.dbc": backups / "Spell.dbc",
            root_target: backups / "root.mpq",
            locale_target: backups / "locale.mpq",
            owner_path: backups / "owner.json",
            state_path: backups / "state.json",
        }
        for source, backup in previous.items():
            shutil.copy2(source, backup)

        try:
            shutil.copy2(work / "SkillLineAbility.dbc", server_dbc / "SkillLineAbility.dbc")
            shutil.copy2(work / "Spell.dbc", server_dbc / "Spell.dbc")
            shutil.copy2(built_root, root_target)
            shutil.copy2(built_locale, locale_target)

            root_hash = sha256_file(root_target)
            locale_hash = sha256_file(locale_target)
            sla_hash = sha256_file(server_dbc / "SkillLineAbility.dbc")
            spell_hash = sha256_file(server_dbc / "Spell.dbc")

            owner = json.loads(owner_path.read_text(encoding="utf-8"))
            owner["root_sha256"] = root_hash
            owner["locale_sha256"] = locale_hash
            owner_path.write_text(
                json.dumps(owner, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
            )

            dbc_files = state.setdefault("dbc", {}).setdefault("files", {})
            dbc_files["SkillLineAbility.dbc"] = sla_hash
            dbc_files["Spell.dbc"] = spell_hash
            installed["root_sha256"] = root_hash
            installed["locale_sha256"] = locale_hash
            client_state["installed"] = installed
            state["client"] = client_state
            save_state(core, state)

            problems = verify_state(core, state)
            if problems:
                raise SpellRankTabError(
                    "SpellDraft metadata post-install verification failed:\n  "
                    + "\n  ".join(problems)
                )
        except Exception:
            for target, backup in previous.items():
                shutil.copy2(backup, target)
            raise

    return True


def main() -> int:
    parser = argparse.ArgumentParser(prog="spell_rank_tabs.py")
    parser.add_argument("command", choices=("install",))
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument("--server-data-dir", type=Path)
    parser.add_argument("--locale", default="esMX")
    args, _unknown = parser.parse_known_args()

    try:
        changed = install_rank_tabs(
            args.core_dir,
            args.client_dir,
            args.server_data_dir,
            args.locale,
        )
    except (SpellRankTabError, OSError, ValueError) as exc:
        parser.error(str(exc))
        return 2

    print(
        "Adventurer SpellDraft spell metadata refreshed from AzerothCore spell_ranks.sql "
        "(rank tabs + component-free casts)."
        if changed
        else "Adventurer SpellDraft spell metadata already matches rank tabs and component-free policy."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
