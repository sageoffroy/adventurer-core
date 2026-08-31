#!/usr/bin/env python3
"""Rebuild the Adventurer client patch with an external SpellDraft v3 icon pack.

The pack mirrors client paths under Interface/Icons. Existing Blizzard icon
paths override only the BLP texture; new paths are appended to SpellIcon.dbc
with deterministic Adventurer-owned IDs. The same pass also reapplies current
SpellDraft rank-tab/component metadata so no later client rebuild can erase the
icon layer.
"""

from __future__ import annotations

import argparse
import os
import tempfile
from pathlib import Path

import adventurer_apply  # noqa: F401
import client
from dbc import DBC, DBCError, set_u32, u32
from spell_rank_tabs import (
    patch_component_free_drafted_spells,
    patch_server_rank_tabs,
)

SPELLICON_FIELDS = 2
SPELLICON_RECORD_SIZE = 8
SPELLICON_PATH_FIELD = 1
CUSTOM_ICON_MIN = 910000
CUSTOM_ICON_MAX = 919999
LONE_WOLF_ICON_ID = 910000
LONE_WOLF_FILENAME = "spell_hunter_lonewolf.blp"
LONE_WOLF_DBC_PATH = "Interface\\Icons\\spell_hunter_lonewolf"


def dbc_string(dbc: DBC, offset: int) -> str:
    if not offset:
        return ""
    raw = bytes(dbc.strings)
    end = raw.find(b"\0", offset)
    if end < 0:
        raise DBCError(f"Unterminated SpellIcon string at offset {offset}")
    return raw[offset:end].decode("utf-8", errors="strict")


def normalized_path(value: str) -> str:
    value = value.replace("/", "\\")
    if value.lower().endswith(".blp"):
        value = value[:-4]
    return value.lower()


def default_pack_dir() -> Path:
    configured = os.environ.get("ADVENTURER_ICON_PACK_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "adventurer-icons"


def collect_icons(pack_dir: Path) -> list[tuple[Path, str, str]]:
    icon_root = pack_dir / "Interface" / "Icons"
    if not icon_root.is_dir():
        raise DBCError(
            f"SpellDraft v3 icon pack must contain Interface/Icons: {icon_root}"
        )

    icons: list[tuple[Path, str, str]] = []
    for path in sorted(icon_root.rglob("*.blp"), key=lambda p: str(p).lower()):
        payload = path.read_bytes()
        if len(payload) < 4 or payload[:4] not in (b"BLP1", b"BLP2"):
            raise DBCError(f"Icon is not a valid BLP texture: {path}")
        relative = path.relative_to(pack_dir).as_posix().replace("/", "\\")
        dbc_path = relative[:-4]
        icons.append((path, relative, dbc_path))

    if not icons:
        raise DBCError(f"No .blp icons found under {icon_root}")
    return icons


def patch_spell_icon(path: Path, icons: list[tuple[Path, str, str]]) -> dict[str, int]:
    dbc = DBC.read(path)
    if dbc.fields != SPELLICON_FIELDS or dbc.record_size != SPELLICON_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected SpellIcon layout {dbc.fields}/{dbc.record_size}")

    stock_rows = [row for row in dbc.records if not (CUSTOM_ICON_MIN <= u32(row, 0) <= CUSTOM_ICON_MAX)]
    stock_by_path: dict[str, int] = {}
    used_ids = {u32(row, 0) for row in stock_rows}
    for row in stock_rows:
        raw_path = dbc_string(dbc, u32(row, SPELLICON_PATH_FIELD))
        if raw_path:
            stock_by_path.setdefault(normalized_path(raw_path), u32(row, 0))

    assigned: dict[str, int] = {}
    custom_rows: list[bytearray] = []
    next_id = CUSTOM_ICON_MIN + 1

    for _source, _internal, dbc_path in icons:
        key = normalized_path(dbc_path)
        existing = stock_by_path.get(key)
        if existing is not None:
            assigned[key] = existing
            continue

        filename = dbc_path.replace("/", "\\").rsplit("\\", 1)[-1].lower() + ".blp"
        if filename == LONE_WOLF_FILENAME and LONE_WOLF_ICON_ID not in used_ids:
            icon_id = LONE_WOLF_ICON_ID
        else:
            while next_id in used_ids:
                next_id += 1
            if next_id > CUSTOM_ICON_MAX:
                raise DBCError("SpellDraft v3 custom SpellIcon ID range exhausted")
            icon_id = next_id
            next_id += 1

        row = bytearray(SPELLICON_RECORD_SIZE)
        set_u32(row, 0, icon_id)
        set_u32(row, SPELLICON_PATH_FIELD, dbc.append_string(dbc_path))
        custom_rows.append(row)
        used_ids.add(icon_id)
        assigned[key] = icon_id

    dbc.records = stock_rows + custom_rows
    dbc.records.sort(key=lambda row: u32(row, 0))
    path.write_bytes(dbc.to_bytes())
    return assigned


def install_wrappers(
    pack_dir: Path,
    spell_ranks_path: Path | None = None,
) -> tuple[list[tuple[Path, str, str]], dict[str, int]]:
    icons = collect_icons(pack_dir)
    assigned: dict[str, int] = {}

    original_patch_dbc_copy = client.patch_dbc_copy
    original_build_archive_files = client.build_archive_files

    def patch_dbc_copy(source: Path, work: Path):
        changed = original_patch_dbc_copy(source, work)

        if spell_ranks_path is not None:
            rank_changed = patch_server_rank_tabs(
                work / "SkillLineAbility.dbc",
                spell_ranks_path,
            )
            component_changed = patch_component_free_drafted_spells(
                work / "Spell.dbc",
                spell_ranks_path,
            )
            changed["SkillLineAbility.dbc"] = rank_changed or changed.get("SkillLineAbility.dbc", False)
            changed["Spell.dbc"] = component_changed or changed.get("Spell.dbc", False)

        before = (work / "SpellIcon.dbc").read_bytes()
        assigned.clear()
        assigned.update(patch_spell_icon(work / "SpellIcon.dbc", icons))
        changed["SpellIcon.dbc"] = (work / "SpellIcon.dbc").read_bytes() != before
        return changed

    def build_archive_files(work: Path):
        root_files, locale_files = original_build_archive_files(work)
        spell_icon_payload = (work / "SpellIcon.dbc").read_bytes()
        root_files["DBFilesClient\\SpellIcon.dbc"] = spell_icon_payload
        locale_files["DBFilesClient\\SpellIcon.dbc"] = spell_icon_payload
        for source, internal, _dbc_path in icons:
            root_files[internal] = source.read_bytes()
        return root_files, locale_files

    client.patch_dbc_copy = patch_dbc_copy
    client.build_archive_files = build_archive_files
    return icons, assigned


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--dbc-src", required=True, type=Path)
    parser.add_argument("--server-data-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument("--locale", default="esMX")
    parser.add_argument("--icon-pack-dir", type=Path, default=default_pack_dir())
    args, _unknown = parser.parse_known_args()

    try:
        spell_ranks = (
            args.core_dir.expanduser().resolve()
            / "data" / "sql" / "base" / "db_world" / "spell_ranks.sql"
        )
        icons, assigned = install_wrappers(
            args.icon_pack_dir.expanduser().resolve(),
            spell_ranks,
        )
        with tempfile.TemporaryDirectory(prefix="spelldraft-v3-icons-") as tmp_name:
            build_dir = Path(tmp_name)
            client.build_patch(args.dbc_src, build_dir, args.locale)
            client.install_server_dbcs(build_dir, args.server_data_dir / "dbc")
            client.install_patch(args.client_dir, build_dir, args.locale)

        lone_key = normalized_path(LONE_WOLF_DBC_PATH)
        lone_id = assigned.get(lone_key)
        print(f"SpellDraft v3 icon pack installed: {len(icons)} BLP textures.")
        if lone_id is not None:
            print(f"Lobo solitario icon registered as SpellIcon ID {lone_id} ({LONE_WOLF_FILENAME}).")
        else:
            print(f"WARNING: {LONE_WOLF_FILENAME} not present in the icon pack yet.")
        return 0
    except (DBCError, client.ClientError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
