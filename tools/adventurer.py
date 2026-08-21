#!/usr/bin/env python3
"""Safe installer/verification front-end for Adventurer Core."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from core_patch import PatchError, plan as plan_core

ROOT = Path(__file__).resolve().parent.parent
COMPATIBILITY = ROOT / "compatibility.json"
PAYLOAD_ROOT = ROOT / "payload" / "core"
WORLD_SQL = ROOT / "sql" / "world" / "001_adventurer.sql"
STATE_DIR_NAME = ".adventurer-core"
STATE_FILE = "state.json"
SQL_TARGET = "data/sql/updates/pending_db_world/rev_1787358000000000000.sql"


class InstallError(RuntimeError):
    pass


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(core: Path, *args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(core), *args],
        check=check,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def validate_core_root(core: Path) -> str:
    probe = git(core, "rev-parse", "--is-inside-work-tree", check=False)
    if probe.returncode != 0 or probe.stdout.strip() != "true":
        raise InstallError(f"Not a Git checkout: {core}")

    top = Path(git(core, "rev-parse", "--show-toplevel").stdout.strip()).resolve()
    if top != core:
        raise InstallError(f"--core-dir must be the repository root: expected {top}, got {core}")

    for relative in (
        "src/server/shared/SharedDefines.h",
        "src/server/game/Entities/Player/Player.cpp",
        "src/server/scripts/Custom/custom_script_loader.cpp",
    ):
        if not (core / relative).is_file():
            raise InstallError(f"Not a compatible AzerothCore source tree: missing {relative}")
    return git(core, "rev-parse", "HEAD").stdout.strip()


def load_compatibility() -> dict:
    return json.loads(COMPATIBILITY.read_text(encoding="utf-8"))


def enforce_compatibility(commit: str, allow_unverified: bool) -> None:
    data = load_compatibility()
    supported = set(data.get("supported_core_commits", []))
    if commit in supported:
        return
    if allow_unverified:
        print(f"WARNING: applying to unverified core commit {commit}")
        return
    if not supported:
        raise InstallError(
            "Adventurer Core is still in bootstrap: no Playerbots core commit has "
            "been frozen as supported yet. Nothing was changed."
        )
    raise InstallError(
        f"Unsupported core commit {commit}. Supported: {', '.join(sorted(supported))}"
    )


def ensure_target_files_clean(core: Path, relatives: list[str]) -> None:
    tracked = [r for r in relatives if (core / r).exists()]
    if not tracked:
        return
    result = git(core, "status", "--porcelain", "--", *tracked)
    dirty = result.stdout.strip()
    if dirty:
        raise InstallError(
            "Refusing to patch source files with pre-existing local changes:\n" + dirty
        )


def exclude_state_dir(core: Path) -> None:
    raw = git(core, "rev-parse", "--git-path", "info/exclude").stdout.strip()
    info_exclude = Path(raw)
    if not info_exclude.is_absolute():
        info_exclude = core / info_exclude
    info_exclude.parent.mkdir(parents=True, exist_ok=True)
    entry = f"/{STATE_DIR_NAME}/"
    text = info_exclude.read_text(encoding="utf-8") if info_exclude.exists() else ""
    if entry not in text.splitlines():
        with info_exclude.open("a", encoding="utf-8") as f:
            if text and not text.endswith("\n"):
                f.write("\n")
            f.write(entry + "\n")


def write_transaction(core: Path, planned, commit: str) -> dict:
    state_dir = core / STATE_DIR_NAME
    if state_dir.exists():
        state_path = state_dir / STATE_FILE
        if state_path.is_file():
            raise InstallError(
                f"Existing Adventurer Core state found at {state_path}. Run verify or rollback first."
            )
        raise InstallError(f"Unexpected existing state directory: {state_dir}")

    backup_root = state_dir / "backups"
    backup_root.mkdir(parents=True)
    state_files = []

    try:
        for item in planned:
            target = core / item.relative_path
            backup = backup_root / item.relative_path
            if item.original is not None:
                backup.parent.mkdir(parents=True, exist_ok=True)
                backup.write_bytes(item.original)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.patched)
            state_files.append({
                "path": item.relative_path,
                "existed_before": item.original is not None,
                "before_sha256": sha256_bytes(item.original) if item.original is not None else None,
                "after_sha256": sha256_bytes(item.patched),
            })

        sql_target = core / SQL_TARGET
        if sql_target.exists():
            raise InstallError(f"SQL target already exists and is not owned: {SQL_TARGET}")
        sql_target.parent.mkdir(parents=True, exist_ok=True)
        sql_target.write_bytes(WORLD_SQL.read_bytes())
        state_files.append({
            "path": SQL_TARGET,
            "existed_before": False,
            "before_sha256": None,
            "after_sha256": sha256_file(sql_target),
        })

        state = {
            "schema": 1,
            "package": "adventurer-core",
            "source_core_commit": commit,
            "files": state_files,
            "dbc": None,
            "client": None,
        }
        (state_dir / STATE_FILE).write_text(
            json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        exclude_state_dir(core)
        return state
    except Exception:
        # Restore only what this transaction changed. This executes before a
        # state manifest exists and never invokes a destructive Git reset.
        for item in reversed(planned):
            target = core / item.relative_path
            backup = backup_root / item.relative_path
            if item.original is None:
                if target.exists() and target.read_bytes() == item.patched:
                    target.unlink()
            elif backup.is_file():
                target.write_bytes(backup.read_bytes())
        sql_target = core / SQL_TARGET
        if sql_target.exists() and sql_target.read_bytes() == WORLD_SQL.read_bytes():
            sql_target.unlink()
        shutil.rmtree(state_dir, ignore_errors=True)
        raise


def load_state(core: Path) -> dict:
    path = core / STATE_DIR_NAME / STATE_FILE
    if not path.is_file():
        raise InstallError(f"No Adventurer Core state found at {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise InstallError(f"Invalid Adventurer Core state: {exc}") from exc


def verify_state(core: Path, state: dict) -> list[str]:
    problems: list[str] = []
    for entry in state.get("files", []):
        path = core / entry["path"]
        if not path.is_file():
            problems.append(f"missing: {entry['path']}")
            continue
        actual = sha256_file(path)
        if actual != entry["after_sha256"]:
            problems.append(
                f"modified: {entry['path']} (expected {entry['after_sha256']}, got {actual})"
            )
    return problems


def cmd_preflight(args) -> None:
    core = args.core_dir.resolve()
    commit = validate_core_root(core)
    enforce_compatibility(commit, args.allow_unverified_core)
    planned = plan_core(core, PAYLOAD_ROOT)
    ensure_target_files_clean(core, [p.relative_path for p in planned] + [SQL_TARGET])
    if (core / SQL_TARGET).exists():
        raise InstallError(f"SQL target already exists: {SQL_TARGET}")
    print("Adventurer Core preflight OK")
    print(f"  core:   {core}")
    print(f"  commit: {commit}")
    print(f"  source files planned: {len(planned)}")
    print("  no files changed")


def cmd_apply(args) -> None:
    core = args.core_dir.resolve()
    commit = validate_core_root(core)
    enforce_compatibility(commit, args.allow_unverified_core)
    planned = plan_core(core, PAYLOAD_ROOT)
    ensure_target_files_clean(core, [p.relative_path for p in planned] + [SQL_TARGET])
    state = write_transaction(core, planned, commit)
    problems = verify_state(core, state)
    if problems:
        raise InstallError("Post-apply verification failed:\n  " + "\n  ".join(problems))
    print("Adventurer Core source layer applied and verified.")
    print(f"  core: {core}")
    print(f"  source commit: {commit}")
    print(f"  owned files: {len(state['files'])}")
    print("  NOTE: DBC/client stages are not enabled in bootstrap yet.")


def cmd_verify(args) -> None:
    core = args.core_dir.resolve()
    validate_core_root(core)
    state = load_state(core)
    problems = verify_state(core, state)
    if problems:
        raise InstallError("Verification failed:\n  " + "\n  ".join(problems))
    print("Adventurer Core owned source files verify cleanly.")
    print(f"  source commit: {state['source_core_commit']}")
    if state.get("dbc") is None or state.get("client") is None:
        print("  bootstrap: DBC/client verification is not implemented yet")


def cmd_rollback(args) -> None:
    core = args.core_dir.resolve()
    validate_core_root(core)
    state = load_state(core)
    problems = verify_state(core, state)
    if problems:
        raise InstallError(
            "Refusing rollback because Adventurer-owned files changed after apply:\n  "
            + "\n  ".join(problems)
        )

    state_dir = core / STATE_DIR_NAME
    backup_root = state_dir / "backups"
    for entry in reversed(state.get("files", [])):
        path = core / entry["path"]
        if entry["existed_before"]:
            backup = backup_root / entry["path"]
            if not backup.is_file():
                raise InstallError(f"Missing rollback backup: {backup}")
            path.write_bytes(backup.read_bytes())
        elif path.exists():
            path.unlink()
    shutil.rmtree(state_dir)
    print("Adventurer Core file layer rolled back safely.")
    print("Database rows already applied by worldserver are not modified by bootstrap rollback.")


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="adventurer.py")
    sub = p.add_subparsers(dest="command", required=True)
    for name, func in (
        ("preflight", cmd_preflight),
        ("apply", cmd_apply),
        ("verify", cmd_verify),
        ("rollback", cmd_rollback),
    ):
        sp = sub.add_parser(name)
        sp.add_argument("--core-dir", required=True, type=Path)
        if name in {"preflight", "apply"}:
            sp.add_argument("--allow-unverified-core", action="store_true")
        sp.set_defaults(func=func)
    return p


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
        return 0
    except (InstallError, PatchError, OSError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
