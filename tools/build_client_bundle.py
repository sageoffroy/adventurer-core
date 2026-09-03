#!/usr/bin/env python3
"""Build the final Adventurer/SpellDraft/Gauntlet client and server DBC bundle.

This helper is called only by the root apply/update pipelines. It performs one
client/server build from the clean DBC source, applying every owned transform
before the final DBCs and MPQs are installed.
"""

from __future__ import annotations

import argparse
import csv
import shutil
import tempfile
from pathlib import Path

import adventurer_apply  # noqa: F401
import client
import spelldraft_custom_spells
import spelldraft_v3_icons
import spelldraft_v4_talents
from khadgar_gauntlet.patch_item_dbc import patch as patch_gauntlet_items
from khadgar_gauntlet.patch_spell_dbc import patch as patch_gauntlet_spells


def gauntlet_mapping(core_dir: Path) -> dict[int, int]:
    catalog = (
        core_dir.expanduser().resolve()
        / "modules" / "mod-adventurer-gauntlet" / "data" / "items" / "early_items.csv"
    )
    if not catalog.is_file():
        raise RuntimeError(f"staged Gauntlet item catalog not found: {catalog}")

    mapping: dict[int, int] = {}
    with catalog.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        for row in reader:
            enabled = (row.get("enabled") or "").strip().lower()
            if enabled not in {"1", "true", "yes", "on"}:
                continue
            mapping[int(row["entry"])] = int(row["source_entry"])

    if not mapping:
        raise RuntimeError("Gauntlet item catalog has no enabled rows")
    first, last = min(mapping), max(mapping)
    if first != 911100:
        raise RuntimeError(f"Gauntlet catalog must start at 911100, found {first}")
    expected = set(range(first, last + 1))
    if set(mapping) != expected:
        missing = sorted(expected - set(mapping))
        raise RuntimeError(
            "Gauntlet catalog must be one contiguous owned range; "
            f"missing={missing[:10]}"
        )
    return mapping


def build(args) -> None:
    core = args.core_dir.expanduser().resolve()
    clean_dbc = args.dbc_src.expanduser().resolve()
    server_data = args.server_data_dir.expanduser().resolve()
    runtime_dbc = server_data.parent / "bin" / "dbc"
    stale_data_dbc = server_data / "dbc"

    if not runtime_dbc.is_dir():
        raise RuntimeError(f"worldserver runtime DBC directory not found: {runtime_dbc}")

    spell_ranks = core / "data" / "sql" / "base" / "db_world" / "spell_ranks.sql"
    icons, assigned = spelldraft_v3_icons.install_wrappers(
        args.icon_pack_dir.expanduser().resolve(),
        spell_ranks,
    )

    mapping = gauntlet_mapping(core)
    original_patch_dbc_copy = client.patch_dbc_copy

    def patch_dbc_copy(source: Path, work: Path):
        changed = original_patch_dbc_copy(source, work)

        item_path = work / adventurer_apply.ITEM_DBC
        before_item = item_path.read_bytes()
        patch_gauntlet_items(item_path, mapping)
        changed[adventurer_apply.ITEM_DBC] = (
            item_path.read_bytes() != before_item
            or changed.get(adventurer_apply.ITEM_DBC, False)
        )

        spell_path = work / "Spell.dbc"
        talent_path = work / "Talent.dbc"
        before_spell = spell_path.read_bytes()
        before_talent = talent_path.read_bytes()
        spelldraft_custom_spells.patch(spell_path, assigned)
        _spell_changed, _talent_changed = spelldraft_v4_talents.patch(
            spell_path,
            talent_path,
            assigned,
        )
        patch_gauntlet_spells(spell_path)
        changed["Spell.dbc"] = (
            spell_path.read_bytes() != before_spell
            or changed.get("Spell.dbc", False)
        )
        changed["Talent.dbc"] = (
            talent_path.read_bytes() != before_talent
            or changed.get("Talent.dbc", False)
        )

        skill_path = work / "SkillLineAbility.dbc"
        before_skill = skill_path.read_bytes()
        spelldraft_custom_spells.patch_skill_line_ability(skill_path)
        changed["SkillLineAbility.dbc"] = (
            skill_path.read_bytes() != before_skill
            or changed.get("SkillLineAbility.dbc", False)
        )
        return changed

    client.patch_dbc_copy = patch_dbc_copy

    with tempfile.TemporaryDirectory(prefix="adventurer-client-bundle-") as tmp_name:
        build_dir = Path(tmp_name)
        client.build_patch(clean_dbc, build_dir, args.locale)
        client.install_server_dbcs(build_dir, runtime_dbc)
        client.install_patch(args.client_dir.expanduser().resolve(), build_dir, args.locale)

    if stale_data_dbc != runtime_dbc and stale_data_dbc.is_dir():
        shutil.rmtree(stale_data_dbc)

    lone_key = spelldraft_v3_icons.normalized_path(spelldraft_v3_icons.LONE_WOLF_DBC_PATH)
    lone_id = assigned.get(lone_key)
    if lone_id is not None and lone_id != spelldraft_v3_icons.LONE_WOLF_ICON_ID:
        raise RuntimeError(
            f"{spelldraft_v3_icons.LONE_WOLF_FILENAME} must resolve to SpellIcon ID "
            f"{spelldraft_v3_icons.LONE_WOLF_ICON_ID}, found {lone_id}"
        )

    first, last = min(mapping), max(mapping)
    print(
        f"Final client/server bundle installed in one pass: {len(mapping)} Gauntlet items "
        f"({first}-{last}), {len(spelldraft_custom_spells.CUSTOM_SPELL_IDS)} SpellDraft v4 custom spell ranks, "
        f"6 custom talent ranks, Gauntlet spells and {len(icons)} SpellDraft icon textures. "
        f"Server DBCs: {runtime_dbc}."
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--dbc-src", required=True, type=Path)
    parser.add_argument("--server-data-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument("--locale", default="esMX")
    parser.add_argument("--icon-pack-dir", type=Path, default=spelldraft_v3_icons.default_pack_dir())
    args, _unknown = parser.parse_known_args()
    try:
        build(args)
    except Exception as exc:
        parser.error(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
