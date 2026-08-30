#!/usr/bin/env python3
"""Rebuild both owned Z client patches from the final installed server DBC bundle."""

from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from pathlib import Path

# Import first: this extends client.DBC_NAMES/ROOT_SHARED_DBCS with Item.dbc.
from adventurer_apply import ITEM_DBC  # noqa: F401
from adventurer import load_state, save_state, sha256_file, verify_state
from client import DBC_NAMES, OWNER_MANIFEST, build_archive_files
from khadgar_gauntlet.patch_item_dbc import load_mapping as load_gauntlet_item_mapping
from khadgar_gauntlet.patch_item_dbc import patch as patch_gauntlet_item_dbc
from mpq import write_mpq


class SyncItemDbcError(RuntimeError):
    pass


def sync(core_dir: Path, server_data_dir: Path, client_dir: Path) -> None:
    core = core_dir.expanduser().resolve()
    data = server_data_dir.expanduser().resolve()
    client_dir = client_dir.expanduser().resolve()
    server_dbc = data / "dbc"

    if not server_dbc.is_dir():
        raise SyncItemDbcError(f"Installed server DBC directory not found: {server_dbc}")

    missing = [name for name in DBC_NAMES if not (server_dbc / name).is_file()]
    if missing:
        raise SyncItemDbcError(
            "Installed server DBC bundle is incomplete: " + ", ".join(missing)
        )

    # Load ownership before mutating Item.dbc. If Gauntlet is installed, the
    # resulting Item.dbc is still Adventurer-owned and its authoritative hash
    # must be refreshed after the generated rows are re-applied.
    state = load_state(core)

    # When the Gauntlet module is installed, its generated catalog is authoritative
    # for entries 911100-911399. Re-apply those rows after every normal Adventurer
    # update so a refreshed server Item.dbc cannot silently discard Gauntlet items.
    gauntlet_catalog = core / "modules/mod-adventurer-gauntlet/data/items/early_items.csv"
    if gauntlet_catalog.is_file():
        mapping = load_gauntlet_item_mapping(gauntlet_catalog)
        patch_gauntlet_item_dbc(server_dbc / ITEM_DBC, mapping)

    item_payload = (server_dbc / ITEM_DBC).read_bytes()
    item_hash = sha256_file(server_dbc / ITEM_DBC)

    dbc_state = state.get("dbc")
    if dbc_state and ITEM_DBC in dbc_state.get("files", {}):
        dbc_state["files"][ITEM_DBC] = item_hash

    client_state = state.get("client") or {}
    installed = client_state.get("installed") or {}
    root_relative = installed.get("root_patch")
    locale_relative = installed.get("locale_patch")
    if not root_relative or not locale_relative:
        raise SyncItemDbcError("Adventurer client ownership state is incomplete")

    root_target = client_dir / root_relative
    locale_target = client_dir / locale_relative
    owner_path = client_dir / OWNER_MANIFEST
    for path, label in (
        (root_target, "root Z patch"),
        (locale_target, "locale Z patch"),
        (owner_path, "client ownership manifest"),
    ):
        if not path.is_file():
            raise SyncItemDbcError(f"Missing {label}: {path}")

    with tempfile.TemporaryDirectory(prefix="adventurer-final-z-") as td:
        temp = Path(td)
        work = temp / "dbc"
        work.mkdir()

        # Use the final runtime DBCs as the single source of truth. At this point
        # they contain Adventurer, SpellDraft, contraband and (when installed)
        # Gauntlet Item.dbc rows, so rebuilding Z cannot discard an earlier stage.
        for name in DBC_NAMES:
            shutil.copy2(server_dbc / name, work / name)

        root_files, locale_files = build_archive_files(work)
        built_root = temp / "patch-Z.mpq"
        built_locale = temp / "patch-locale-z.mpq"
        write_mpq(built_root, root_files)
        write_mpq(built_locale, locale_files)

        if item_payload not in built_root.read_bytes():
            raise SyncItemDbcError("Rebuilt root Z patch does not contain final Item.dbc")
        if item_payload not in built_locale.read_bytes():
            raise SyncItemDbcError("Rebuilt locale Z patch does not contain final Item.dbc")

        shutil.copy2(built_root, root_target)
        shutil.copy2(built_locale, locale_target)

    if item_payload not in root_target.read_bytes():
        raise SyncItemDbcError("Installed root Z patch lost final Item.dbc")
    if item_payload not in locale_target.read_bytes():
        raise SyncItemDbcError("Installed locale Z patch lost final Item.dbc")

    root_hash = sha256_file(root_target)
    locale_hash = sha256_file(locale_target)

    owner = json.loads(owner_path.read_text(encoding="utf-8"))
    owner["root_sha256"] = root_hash
    owner["locale_sha256"] = locale_hash
    owner_path.write_text(
        json.dumps(owner, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    installed["root_sha256"] = root_hash
    installed["locale_sha256"] = locale_hash
    client_state["installed"] = installed
    state["client"] = client_state
    save_state(core, state)

    problems = verify_state(core, state)
    if problems:
        raise SyncItemDbcError(
            "Final Z rebuild verification failed:\n  " + "\n  ".join(problems)
        )

    print(
        f"Final Z patches rebuilt from installed server DBCs; "
        f"Item.dbc preserved ({len(item_payload)} bytes)."
    )


def main() -> int:
    parser = argparse.ArgumentParser(prog="sync_item_dbc.py")
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--server-data-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    args, _unknown = parser.parse_known_args()

    try:
        sync(args.core_dir, args.server_data_dir, args.client_dir)
    except (SyncItemDbcError, OSError, ValueError, json.JSONDecodeError, RuntimeError) as exc:
        parser.error(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
