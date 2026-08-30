#!/usr/bin/env python3
"""Transactional in-place upgrades for an already-installed Adventurer Core.

Unlike the clean installer, this command deliberately allows existing class-10
characters. It upgrades already-owned files and may add new package-owned files
when the target path did not previously exist. It preserves the original
pre-install rollback backups, stages every generated client/DBC artifact before
mutation, and restores the immediately previous installed state if any upgrade
step fails.
"""

from __future__ import annotations

import argparse
import copy
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from adventurer import (
    InstallError,
    PAYLOAD_ROOT,
    load_state,
    save_state,
    sha256_bytes,
    sha256_file,
    validate_core_root,
    validate_runtime_inputs,
    verify_state,
)
from client import (
    ClientError,
    DBC_NAMES,
    OWNER_MANIFEST,
    build_patch,
    install_patch,
    install_server_dbcs,
)
from core_patch import PatchError, plan as plan_core
from dbc import DBCError


class UpgradeError(RuntimeError):
    pass


def state_file_map(state: dict) -> dict[str, dict]:
    return {entry["path"]: entry for entry in state.get("files", [])}


def verify_owned_source_state(core: Path, state: dict) -> list[str]:
    """Verify only source/package files tracked by the original transaction.

    Runtime DBCs and client MPQs are generated Adventurer artifacts and may
    legitimately have been refreshed by tools/client.py between package
    revisions. Their own ownership manifest is validated later by
    validate_runtime_inputs(), and the upgrade replaces them transactionally.
    Source/core files remain strict because overwriting local source edits would
    make rollback ownership ambiguous.
    """
    problems: list[str] = []
    for entry in state.get("files", []):
        path = core / entry["path"]
        if not path.is_file():
            problems.append(f"missing: {entry['path']}")
            continue
        actual = sha256_file(path)
        expected = entry.get("after_sha256")
        if actual != expected:
            problems.append(
                f"modified: {entry['path']} (expected {expected}, got {actual})"
            )
    return problems


def validate_installed_state(core: Path, state: dict) -> None:
    problems = verify_owned_source_state(core, state)
    if problems:
        raise UpgradeError(
            "Refusing upgrade because Adventurer-owned source/package files changed:\n  "
            + "\n  ".join(problems)
        )

    installed_commit = state.get("source_core_commit")
    current_commit = validate_core_root(core)
    if installed_commit and current_commit != installed_commit:
        raise UpgradeError(
            "AzerothCore HEAD changed after Adventurer was installed. Refusing an in-place "
            f"upgrade over a different core revision: installed={installed_commit}, current={current_commit}"
        )


def plan_owned_upgrade(core: Path, state: dict):
    planned = plan_core(core, PAYLOAD_ROOT, allow_payload_replace=True)
    owned = state_file_map(state)

    # New files introduced by a package revision are safe only when the target
    # path does not exist. An existing unowned path is never adopted silently.
    unowned_existing = [
        item.relative_path
        for item in planned
        if item.relative_path not in owned and item.original is not None
    ]
    if unowned_existing:
        raise UpgradeError(
            "Upgrade wants to modify files that are not present in the ownership manifest: "
            + ", ".join(unowned_existing)
        )

    for item in planned:
        entry = owned.get(item.relative_path)
        if entry is None:
            continue
        expected = entry.get("after_sha256")
        actual = sha256_bytes(item.original) if item.original is not None else None
        if expected != actual:
            raise UpgradeError(
                f"Owned source changed before upgrade: {item.relative_path} "
                f"(expected {expected}, got {actual})"
            )
    return planned


def snapshot_runtime(core: Path, state: dict, directory: Path) -> dict:
    snapshot: dict = {"source": {}, "dbc": {}, "client": {}}

    for entry in state.get("files", []):
        path = core / entry["path"]
        if path.is_file():
            target = directory / "source" / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            snapshot["source"][entry["path"]] = target

    dbc_state = state.get("dbc")
    if dbc_state:
        dbc_dir = Path(dbc_state["directory"])
        for name in dbc_state.get("files", {}):
            path = dbc_dir / name
            if path.is_file():
                target = directory / "dbc" / name
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                snapshot["dbc"][str(path)] = target

    client_state = state.get("client")
    if client_state:
        client_root = Path(client_state["directory"])
        installed = client_state.get("installed", {})
        for key in ("root_patch", "locale_patch"):
            relative = installed.get(key)
            if not relative:
                continue
            path = client_root / relative
            if path.is_file():
                target = directory / "client" / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, target)
                snapshot["client"][str(path)] = target
        owner = client_root / OWNER_MANIFEST
        if owner.is_file():
            target = directory / "client" / OWNER_MANIFEST
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(owner, target)
            snapshot["client"][str(owner)] = target

    return snapshot


def restore_previous(snapshot: dict) -> None:
    for raw, saved in snapshot.get("client", {}).items():
        target = Path(raw)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(saved, target)
    for raw, saved in snapshot.get("dbc", {}).items():
        target = Path(raw)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(saved, target)
    for raw, saved in snapshot.get("source", {}).items():
        target = Path(raw) if Path(raw).is_absolute() else None
        # Source snapshots are keyed by repository-relative path. They are
        # restored separately by restore_sources(), which knows the core root.
        if target is not None:
            shutil.copy2(saved, target)


def restore_sources(core: Path, snapshot: dict) -> None:
    for relative, saved in snapshot.get("source", {}).items():
        target = core / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(saved, target)


def update_source_manifest(state: dict, planned) -> None:
    owned = state_file_map(state)
    for item in planned:
        entry = owned.get(item.relative_path)
        if entry is None:
            entry = {
                "path": item.relative_path,
                "existed_before": False,
                "before_sha256": None,
                "after_sha256": sha256_bytes(item.patched),
            }
            state.setdefault("files", []).append(entry)
            owned[item.relative_path] = entry
        else:
            entry["after_sha256"] = sha256_bytes(item.patched)


def remove_new_sources(core: Path, planned) -> None:
    for item in planned:
        if item.original is not None:
            continue
        target = core / item.relative_path
        if target.is_file() and target.read_bytes() == item.patched:
            target.unlink()


def apply_upgrade(args) -> None:
    core = args.core_dir.expanduser().resolve()
    state = load_state(core)
    validate_installed_state(core, state)
    planned = plan_owned_upgrade(core, state)

    # This validates the current generated client artifacts against their own
    # Adventurer ownership manifest. It intentionally does not compare them to
    # the older package-state hashes, because tools/client.py may have refreshed
    # them during normal talent development.
    server_dbc, dbc_source, client_dir = validate_runtime_inputs(
        core, args, build_smoke_test=False
    )

    with tempfile.TemporaryDirectory(prefix="adventurer-upgrade-") as td:
        temp = Path(td)
        staged = temp / "build"

        # Generate the entire client/server data bundle before touching the
        # installed source tree.
        build_patch(dbc_source, staged, args.locale)
        previous_state = copy.deepcopy(state)
        snapshot = snapshot_runtime(core, state, temp / "previous")

        try:
            for item in planned:
                if item.original == item.patched:
                    continue
                target = core / item.relative_path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(item.patched)

            dbc_hashes = install_server_dbcs(staged, server_dbc)
            installed_client = install_patch(client_dir, staged, args.locale)

            update_source_manifest(state, planned)
            state["dbc"] = {
                "directory": str(server_dbc),
                "files": dbc_hashes,
            }
            state["client"] = {
                "directory": str(client_dir),
                "installed": installed_client,
            }
            state["package_revision"] = "universal-chassis-v1"
            save_state(core, state)

            problems = verify_state(core, state)
            if problems:
                raise UpgradeError(
                    "Post-upgrade ownership verification failed:\n  "
                    + "\n  ".join(problems)
                )
        except Exception:
            restore_sources(core, snapshot)
            remove_new_sources(core, planned)
            for raw, saved in snapshot.get("dbc", {}).items():
                target = Path(raw)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(saved, target)
            for raw, saved in snapshot.get("client", {}).items():
                target = Path(raw)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(saved, target)
            save_state(core, previous_state)
            raise

    changed = sum(1 for item in planned if item.original != item.patched)
    print("Adventurer Core upgraded and verified.")
    print(f"  core:             {core}")
    print(f"  owned source:     {changed} changed")
    print(f"  server DBC:       {len(DBC_NAMES)} refreshed")
    print(f"  client locale:    {args.locale}")
    print("  rollback baseline: preserved from the original clean installation")
    print("  NEXT: install pending world updates, rebuild worldserver, restart.")


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="upgrade.py")
    result.add_argument("--core-dir", required=True, type=Path)
    result.add_argument("--client-dir", required=True, type=Path)
    result.add_argument("--server-data-dir", type=Path)
    result.add_argument("--dbc-src", type=Path)
    result.add_argument("--locale", default="esMX")
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        apply_upgrade(args)
        return 0
    except (
        UpgradeError,
        InstallError,
        ClientError,
        DBCError,
        PatchError,
        OSError,
        subprocess.CalledProcessError,
    ) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
