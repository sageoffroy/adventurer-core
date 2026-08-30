#!/usr/bin/env python3
"""Restore the file/runtime layer to the original pre-Adventurer installation."""

from __future__ import annotations

import argparse
from pathlib import Path
import shutil
import sys

from adventurer import InstallError, STATE_DIR_NAME, load_state, verify_state
from client import ClientError, remove_client_patch


class PackageRollbackError(RuntimeError):
    pass


def restore_server_dbcs(state: dict) -> None:
    dbc_state = state.get("dbc")
    if not dbc_state:
        return

    dbc_dir = Path(dbc_state["directory"])
    for name in dbc_state.get("files", {}):
        target = dbc_dir / name
        # Initial releases used .adventurer-backup. A later canonical name was
        # briefly considered, so accept either and delete both after restore.
        backups = (
            dbc_dir / f"{name}.pre-adventurer-core.bak",
            dbc_dir / f"{name}.adventurer-backup",
        )
        source = next((path for path in backups if path.is_file()), None)
        if source is None:
            raise PackageRollbackError(
                f"Original server DBC backup is missing for {name}: "
                + " or ".join(str(path) for path in backups)
            )
        shutil.copy2(source, target)
        for backup in backups:
            if backup.exists():
                backup.unlink()


def restore_source(core: Path, state: dict) -> None:
    state_dir = core / STATE_DIR_NAME
    backup_root = state_dir / "backups"

    for entry in reversed(state.get("files", [])):
        path = core / entry["path"]
        if entry["existed_before"]:
            backup = backup_root / entry["path"]
            if not backup.is_file():
                raise PackageRollbackError(f"Missing rollback backup: {backup}")
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(backup, path)
        elif path.exists():
            path.unlink()


def rollback(core: Path) -> None:
    core = core.expanduser().resolve()
    state = load_state(core)
    problems = verify_state(core, state)
    if problems:
        raise PackageRollbackError(
            "Refusing file rollback because Adventurer-owned files changed:\n  "
            + "\n  ".join(problems)
        )

    client_state = state.get("client")
    if client_state:
        remove_client_patch(Path(client_state["directory"]))

    restore_server_dbcs(state)
    restore_source(core, state)
    shutil.rmtree(core / STATE_DIR_NAME)


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="package_rollback.py")
    result.add_argument("--core-dir", required=True, type=Path)
    return result


def main() -> int:
    args, _unknown = parser().parse_known_args()
    try:
        rollback(args.core_dir)
        print("Adventurer source, server DBC and client patch restored to pre-install state.")
        return 0
    except (PackageRollbackError, InstallError, ClientError, OSError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
