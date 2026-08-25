#!/usr/bin/env python3
"""Transactional in-place upgrades for an already-installed Adventurer Core.

Unlike the clean installer, this command deliberately allows existing class-10
characters. It upgrades Adventurer-owned files and may adopt newly-required core
files only when they are still pristine at the originally-installed AzerothCore
HEAD. Original rollback backups are preserved/extended, every generated
client/DBC artifact is staged before mutation, and the immediately previous
installed state is restored if any upgrade step fails.
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
    STATE_DIR_NAME,
    git,
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


def validate_new_owned_sources(core: Path, state: dict, planned) -> list:
    """Return planned files newly adopted by this package revision.

    A newly-adopted path that already exists must be a tracked file and must be
    byte-for-byte/mode clean relative to the unchanged AzerothCore HEAD. This is
    the safety boundary that lets a package revision expand its source ownership
    without silently overwriting a user's unrelated local core edit.
    """
    owned = state_file_map(state)
    newly_owned = [item for item in planned if item.relative_path not in owned]

    for item in newly_owned:
        if item.original is None:
            # A package-created path is safe to adopt only because plan_core has
            # already established that the destination does not exist.
            continue

        tracked = git(
            core,
            "ls-files",
            "--error-unmatch",
            "--",
            item.relative_path,
            check=False,
        )
        if tracked.returncode != 0:
            raise UpgradeError(
                "Upgrade wants to adopt an existing source file that is not tracked "
                f"by the installed AzerothCore commit: {item.relative_path}"
            )

        clean = git(
            core,
            "diff",
            "--quiet",
            "HEAD",
            "--",
            item.relative_path,
            check=False,
        )
        if clean.returncode == 1:
            raise UpgradeError(
                "Upgrade wants to adopt a newly-owned core file, but it has local "
                f"changes and will not be overwritten: {item.relative_path}"
            )
        if clean.returncode != 0:
            raise UpgradeError(
                f"Could not verify pristine state for newly-owned core file: {item.relative_path}"
            )

    return newly_owned


def plan_owned_upgrade(core: Path, state: dict):
    planned = plan_core(core, PAYLOAD_ROOT, allow_payload_replace=True)
    owned = state_file_map(state)
    validate_new_owned_sources(core, state, planned)

    for item in planned:
        if item.relative_path not in owned:
            continue
        expected = owned[item.relative_path].get("after_sha256")
        actual = sha256_bytes(item.original) if item.original is not None else None
        if expected != actual:
            raise UpgradeError(
                f"Owned source changed before upgrade: {item.relative_path} "
                f"(expected {expected}, got {actual})"
            )
    return planned


def snapshot_runtime(core: Path, state: dict, directory: Path, planned=()) -> dict:
    snapshot: dict = {"source": {}, "dbc": {}, "client": {}}

    for entry in state.get("files", []):
        path = core / entry["path"]
        if path.is_file():
            target = directory / "source" / entry["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            snapshot["source"][entry["path"]] = target

    # Newly-owned source files are not in the previous manifest yet, but they
    # still need to be restored if this upgrade fails after source mutation.
    for item in planned:
        if item.relative_path in snapshot["source"]:
            continue
        path = core / item.relative_path
        if path.is_file():
            target = directory / "source" / item.relative_path
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            snapshot["source"][item.relative_path] = target
        else:
            snapshot["source"][item.relative_path] = None

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
        if target is not None and saved is not None:
            shutil.copy2(saved, target)


def restore_sources(core: Path, snapshot: dict) -> None:
    for relative, saved in snapshot.get("source", {}).items():
        target = core / relative
        if saved is None:
            if target.exists():
                target.unlink()
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(saved, target)


def prepare_new_source_ownership(core: Path, state: dict, planned) -> list[Path]:
    """Extend rollback ownership for newly-adopted source paths before mutation."""
    owned = state_file_map(state)
    newly_owned = [item for item in planned if item.relative_path not in owned]
    backup_root = core / STATE_DIR_NAME / "backups"

    # Check every destination before writing any persistent backup.
    for item in newly_owned:
        if item.original is None:
            continue
        backup = backup_root / item.relative_path
        if backup.exists():
            raise UpgradeError(
                "Unexpected rollback backup already exists for newly-owned source file: "
                f"{backup}"
            )

    created_backups: list[Path] = []
    for item in newly_owned:
        if item.original is not None:
            backup = backup_root / item.relative_path
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_bytes(item.original)
            created_backups.append(backup)

        state.setdefault("files", []).append(
            {
                "path": item.relative_path,
                "existed_before": item.original is not None,
                "before_sha256": (
                    sha256_bytes(item.original) if item.original is not None else None
                ),
                "after_sha256": sha256_bytes(item.patched),
            }
        )

    return created_backups


def cleanup_new_backups(core: Path, created_backups: list[Path]) -> None:
    backup_root = core / STATE_DIR_NAME / "backups"
    for backup in reversed(created_backups):
        if backup.exists():
            backup.unlink()
        parent = backup.parent
        while parent != backup_root and parent.is_dir():
            try:
                parent.rmdir()
            except OSError:
                break
            parent = parent.parent


def update_source_manifest(state: dict, planned) -> None:
    owned = state_file_map(state)
    for item in planned:
        entry = owned[item.relative_path]
        entry["after_sha256"] = sha256_bytes(item.patched)


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
        snapshot = snapshot_runtime(core, state, temp / "previous", planned)
        created_backups: list[Path] = []

        try:
            created_backups = prepare_new_source_ownership(core, state, planned)

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
            for raw, saved in snapshot.get("dbc", {}).items():
                target = Path(raw)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(saved, target)
            for raw, saved in snapshot.get("client", {}).items():
                target = Path(raw)
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(saved, target)
            cleanup_new_backups(core, created_backups)
            save_state(core, previous_state)
            raise

    changed = sum(1 for item in planned if item.original != item.patched)
    adopted = len([item for item in planned if item.relative_path not in state_file_map(previous_state)])
    print("Adventurer Core upgraded and verified.")
    print(f"  core:             {core}")
    print(f"  owned source:     {changed} changed")
    print(f"  newly adopted:    {adopted} pristine core files")
    print(f"  server DBC:       {len(DBC_NAMES)} refreshed")
    print(f"  client locale:    {args.locale}")
    print("  rollback baseline: preserved and extended from the original clean installation")
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
