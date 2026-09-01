#!/usr/bin/env python3
"""Rebuild both owned Z client patches from the final installed server DBC bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

from adventurer_apply import ITEM_DBC  # noqa: F401
from adventurer import load_state, save_state, sha256_file, verify_state
from client import DBC_NAMES, OWNER_MANIFEST, build_archive_files
from khadgar_gauntlet.build_catalog import build_catalog as build_gauntlet_catalog
from khadgar_gauntlet.patch_item_dbc import patch as patch_gauntlet_item_dbc
from khadgar_gauntlet.patch_spell_dbc import patch as patch_gauntlet_spell_dbc
from mpq import write_mpq
from spelldraft_v3_icons import collect_icons, default_pack_dir

ROOT = Path(__file__).resolve().parent.parent
GAUNTLET_SOURCE = ROOT / "modules/mod-adventurer-gauntlet"
SPELL_DBC = "Spell.dbc"
SPELL_ICON_DBC = "SpellIcon.dbc"


class SyncItemDbcError(RuntimeError):
    pass


def gauntlet_item_mapping() -> dict[int, int]:
    """Build the authoritative Gauntlet Item.dbc mapping from source.

    Never depend on an already-generated early_items.csv inside the installed
    AzerothCore tree. update.sh and a clean Gauntlet install must produce the
    same 300 client item rows from the source catalog generator every time.
    """
    rows, _bonuses = build_gauntlet_catalog()
    mapping = {
        int(row["entry"]): int(row["source_entry"])
        for row in rows
        if (row.get("enabled") or "").strip().lower() in {"1", "true", "yes", "on"}
    }
    if len(mapping) != 300:
        raise SyncItemDbcError(
            f"Gauntlet source catalog must generate exactly 300 enabled items, found {len(mapping)}"
        )
    expected = set(range(911100, 911400))
    actual = set(mapping)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise SyncItemDbcError(
            "Gauntlet source catalog does not own the complete 911100-911399 range"
            f"; missing={missing[:10]} extra={extra[:10]}"
        )
    return mapping


def sync(
    core_dir: Path,
    server_data_dir: Path,
    client_dir: Path,
    include_icon_textures: bool = True,
) -> None:
    core = core_dir.expanduser().resolve()
    data = server_data_dir.expanduser().resolve()
    client_dir = client_dir.expanduser().resolve()
    server_dbc = data / "dbc"

    if not server_dbc.is_dir():
        raise SyncItemDbcError(f"Installed server DBC directory not found: {server_dbc}")

    missing = [name for name in DBC_NAMES if not (server_dbc / name).is_file()]
    if missing:
        raise SyncItemDbcError("Installed server DBC bundle is incomplete: " + ", ".join(missing))

    state = load_state(core)

    # Gauntlet is a branch-owned gameplay layer. If its source module exists in
    # this Adventurer Core checkout, always rebuild the final runtime DBCs from
    # that source. This makes update.sh independent of whatever generated CSV or
    # module state happened to be present in the target AzerothCore directory.
    if GAUNTLET_SOURCE.is_dir():
        mapping = gauntlet_item_mapping()
        patch_gauntlet_item_dbc(server_dbc / ITEM_DBC, mapping)
        patch_gauntlet_spell_dbc(server_dbc / SPELL_DBC)

    item_payload = (server_dbc / ITEM_DBC).read_bytes()
    spell_payload = (server_dbc / SPELL_DBC).read_bytes()
    spell_icon_path = server_dbc / SPELL_ICON_DBC
    if not spell_icon_path.is_file():
        raise SyncItemDbcError(f"Installed final {SPELL_ICON_DBC} not found: {spell_icon_path}")
    spell_icon_payload = spell_icon_path.read_bytes()

    icons = []
    if include_icon_textures:
        icon_pack_dir = default_pack_dir().expanduser().resolve()
        icons = collect_icons(icon_pack_dir)

    # The v3 client rebuild intentionally refreshes more than Item.dbc/Spell.dbc
    # (for example SkillLineAbility.dbc for SpellDraft rank metadata). Record the
    # final installed hashes for the complete owned DBC bundle before verifying
    # state, so verification remains strict against the actual final pipeline.
    dbc_state = state.get("dbc")
    if dbc_state:
        files = dbc_state.get("files", {})
        for name in list(files):
            path = server_dbc / name
            if path.is_file():
                files[name] = sha256_file(path)

    client_state = state.get("client") or {}
    installed = client_state.get("installed") or {}
    root_relative = installed.get("root_patch")
    locale_relative = installed.get("locale_patch")
    if not root_relative or not locale_relative:
        raise SyncItemDbcError("Adventurer client ownership state is incomplete")

    root_target = client_dir / root_relative
    locale_target = client_dir / locale_relative
    owner_path = client_dir / OWNER_MANIFEST
    for path, label in ((root_target, "root Z patch"), (locale_target, "locale Z patch"), (owner_path, "client ownership manifest")):
        if not path.is_file():
            raise SyncItemDbcError(f"Missing {label}: {path}")

    with tempfile.TemporaryDirectory(prefix="adventurer-final-z-") as td:
        temp = Path(td)
        work = temp / "dbc"
        work.mkdir()
        for name in DBC_NAMES:
            shutil.copy2(server_dbc / name, work / name)

        root_files, locale_files = build_archive_files(work)

        # SpellIcon.dbc remains authoritative in both modes. For diagnosis we can
        # deliberately omit the external BLP payload while preserving every DBC
        # and the rest of the owned client patch unchanged.
        root_files[f"DBFilesClient\\{SPELL_ICON_DBC}"] = spell_icon_payload
        locale_files[f"DBFilesClient\\{SPELL_ICON_DBC}"] = spell_icon_payload
        if include_icon_textures:
            for source, internal, _dbc_path in icons:
                root_files[internal] = source.read_bytes()

        built_root = temp / "patch-Z.mpq"
        built_locale = temp / "patch-locale-z.mpq"
        write_mpq(built_root, root_files)
        write_mpq(built_locale, locale_files)

        for payload, label in (
            (item_payload, "Item.dbc"),
            (spell_payload, "Spell.dbc"),
            (spell_icon_payload, "SpellIcon.dbc"),
        ):
            if payload not in built_root.read_bytes():
                raise SyncItemDbcError(f"Rebuilt root Z patch does not contain final {label}")
            if payload not in built_locale.read_bytes():
                raise SyncItemDbcError(f"Rebuilt locale Z patch does not contain final {label}")

        shutil.copy2(built_root, root_target)
        shutil.copy2(built_locale, locale_target)

    root_hash = sha256_file(root_target)
    locale_hash = sha256_file(locale_target)

    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["root_sha256"] = root_hash
    owner["locale_sha256"] = locale_hash
    owner_path.write_text(json.dumps(owner, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    installed["root_sha256"] = root_hash
    installed["locale_sha256"] = locale_hash
    client_state["installed"] = installed
    state["client"] = client_state
    save_state(core, state)

    problems = verify_state(core, state)
    if problems:
        raise SyncItemDbcError("Final Z rebuild verification failed:\n  " + "\n  ".join(problems))

    if include_icon_textures:
        print(
            f"Final Z patches rebuilt from installed server DBCs; final DBC bundle and "
            f"SpellDraft v3 icon layer preserved ({len(icons)} BLP textures)."
        )
    else:
        print(
            "Final Z patches rebuilt from installed server DBCs WITHOUT external icon textures; "
            "SpellIcon.dbc and all other owned client data were preserved."
        )


def main() -> int:
    parser = argparse.ArgumentParser(prog="sync_item_dbc.py")
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--server-data-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument(
        "--without-icon-textures",
        action="store_true",
        help="Rebuild owned Z patches without external Interface/Icons BLP files, preserving SpellIcon.dbc.",
    )
    args, _unknown = parser.parse_known_args()

    try:
        sync(
            args.core_dir,
            args.server_data_dir,
            args.client_dir,
            include_icon_textures=not args.without_icon_textures,
        )
    except (SyncItemDbcError, OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        parser.error(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
