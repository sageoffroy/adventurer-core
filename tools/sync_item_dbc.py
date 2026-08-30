#!/usr/bin/env python3
"""Synchronize the installed Adventurer Item.dbc into both owned Z client patches."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from adventurer import load_state, save_state, sha256_file, verify_state
from adventurer_apply import ITEM_DBC, ITEM_INTERNAL, _replace_raw_mpq_file
from client import OWNER_MANIFEST


class SyncItemDbcError(RuntimeError):
    pass


def sync(core_dir: Path, server_data_dir: Path, client_dir: Path) -> None:
    core = core_dir.expanduser().resolve()
    data = server_data_dir.expanduser().resolve()
    client = client_dir.expanduser().resolve()

    item_path = data / "dbc" / ITEM_DBC
    if not item_path.is_file():
        raise SyncItemDbcError(f"Installed server Item.dbc not found: {item_path}")
    payload = item_path.read_bytes()

    state = load_state(core)
    client_state = state.get("client") or {}
    installed = client_state.get("installed") or {}
    root_relative = installed.get("root_patch")
    locale_relative = installed.get("locale_patch")
    if not root_relative or not locale_relative:
        raise SyncItemDbcError("Adventurer client ownership state is incomplete")

    root_patch = client / root_relative
    locale_patch = client / locale_relative
    owner_path = client / OWNER_MANIFEST
    for path, label in (
        (root_patch, "root Z patch"),
        (locale_patch, "locale Z patch"),
        (owner_path, "client ownership manifest"),
    ):
        if not path.is_file():
            raise SyncItemDbcError(f"Missing {label}: {path}")

    _replace_raw_mpq_file(root_patch, ITEM_INTERNAL, payload)
    _replace_raw_mpq_file(locale_patch, ITEM_INTERNAL, payload)

    # The MPQ writer stores Adventurer payloads raw, so this is a direct final
    # readback check on the actual files WoW will mount.
    if payload not in root_patch.read_bytes() or payload not in locale_patch.read_bytes():
        raise SyncItemDbcError("Final Z patch Item.dbc readback verification failed")

    root_hash = sha256_file(root_patch)
    locale_hash = sha256_file(locale_patch)

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
        raise SyncItemDbcError(
            "Final Item.dbc synchronization verification failed:\n  " + "\n  ".join(problems)
        )

    print(f"Final Item.dbc preserved in both Z patches ({len(payload)} bytes).")


def main() -> int:
    parser = argparse.ArgumentParser(prog="sync_item_dbc.py")
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--server-data-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    args, _unknown = parser.parse_known_args()

    try:
        sync(args.core_dir, args.server_data_dir, args.client_dir)
    except (SyncItemDbcError, OSError, ValueError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
