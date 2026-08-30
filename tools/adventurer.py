#!/usr/bin/env python3
"""Safe all-in-one installer/verification front-end for Adventurer Core."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from client import (
    ClientError,
    DBC_NAMES,
    OWNER_MANIFEST,
    PROJECT_SUFFIX,
    build_patch,
    existing_ownership,
    install_patch,
    install_server_dbcs,
    verify_owned_file,
)
from core_patch import PatchError, plan as plan_core
from dbc import DBCError

ROOT = Path(__file__).resolve().parent.parent
PAYLOAD_ROOT = ROOT / "payload" / "core"
WORLD_SQL = ROOT / "sql" / "world" / "001_adventurer.sql"
STATE_DIR_NAME = ".adventurer-core"
STATE_FILE = "state.json"
SQL_TARGET = "data/sql/updates/pending_db_world/rev_1787358000000000000.sql"
DEFAULT_LOCALE = "esMX"


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
        with info_exclude.open("a", encoding="utf-8") as handle:
            if text and not text.endswith("\n"):
                handle.write("\n")
            handle.write(entry + "\n")


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
    sql_target = core / SQL_TARGET

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
            "schema": 2,
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
        for item in reversed(planned):
            target = core / item.relative_path
            backup = backup_root / item.relative_path
            if item.original is None:
                if target.exists() and target.read_bytes() == item.patched:
                    target.unlink()
            elif backup.is_file():
                target.write_bytes(backup.read_bytes())
        if sql_target.exists() and sql_target.read_bytes() == WORLD_SQL.read_bytes():
            sql_target.unlink()
        shutil.rmtree(state_dir, ignore_errors=True)
        raise


def save_state(core: Path, state: dict) -> None:
    path = core / STATE_DIR_NAME / STATE_FILE
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")


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

    dbc_state = state.get("dbc")
    if dbc_state:
        dbc_dir = Path(dbc_state["directory"])
        for name, expected in dbc_state.get("files", {}).items():
            path = dbc_dir / name
            if not path.is_file():
                problems.append(f"missing server DBC: {path}")
            elif sha256_file(path) != expected:
                problems.append(f"modified server DBC: {path}")

    client_state = state.get("client")
    if client_state:
        client_root = Path(client_state["directory"])
        installed = client_state["installed"]
        for key, hash_key in (("root_patch", "root_sha256"), ("locale_patch", "locale_sha256")):
            path = client_root / installed[key]
            if not path.is_file():
                problems.append(f"missing client patch: {path}")
            elif sha256_file(path) != installed[hash_key]:
                problems.append(f"modified client patch: {path}")
        owner = client_root / OWNER_MANIFEST
        if not owner.is_file():
            problems.append(f"missing client ownership manifest: {owner}")
    return problems


def runtime_paths(core: Path, args) -> tuple[Path, Path, Path]:
    data_dir = (
        args.server_data_dir.expanduser().resolve()
        if args.server_data_dir
        else core / "env" / "dist" / "data"
    )
    server_dbc = data_dir / "dbc"
    dbc_source = (
        args.dbc_src.expanduser().resolve()
        if args.dbc_src
        else server_dbc
    )
    client_dir = args.client_dir.expanduser().resolve()
    return server_dbc, dbc_source, client_dir


def validate_client_slot(client_dir: Path, locale: str) -> None:
    wow = client_dir / "Wow.exe"
    if not wow.is_file():
        wow = client_dir / "wow.exe"
    if not wow.is_file():
        raise InstallError(f"WoW 3.3.5a client not found: {client_dir}")

    target_root = client_dir / "Data" / f"patch-{PROJECT_SUFFIX}.mpq"
    target_locale = client_dir / "Data" / locale / f"patch-{locale}-{PROJECT_SUFFIX.lower()}.mpq"
    _, owner = existing_ownership(client_dir)
    if owner:
        verify_owned_file(target_root, owner.get("root_sha256"), "root Z patch")
        old_locale_rel = owner.get("locale_patch")
        if old_locale_rel:
            old_locale = client_dir / old_locale_rel
            verify_owned_file(old_locale, owner.get("locale_sha256"), "locale Z patch")
        if target_locale.exists() and old_locale_rel and target_locale != client_dir / old_locale_rel:
            raise InstallError(f"Requested locale Z target is already occupied: {target_locale}")
    else:
        verify_owned_file(target_root, None, "root Z patch")
        verify_owned_file(target_locale, None, "locale Z patch")


def validate_runtime_inputs(core: Path, args, build_smoke_test: bool = True) -> tuple[Path, Path, Path]:
    server_dbc, dbc_source, client_dir = runtime_paths(core, args)
    missing = [name for name in DBC_NAMES if not (dbc_source / name).is_file()]
    if missing:
        raise InstallError(
            f"DBC source is incomplete: {dbc_source}\nMissing: " + ", ".join(missing)
        )
    if not server_dbc.is_dir():
        raise InstallError(f"Server DBC directory not found: {server_dbc}")
    validate_client_slot(client_dir, args.locale)

    if build_smoke_test:
        with tempfile.TemporaryDirectory(prefix="adventurer-preflight-") as tmp:
            build_patch(dbc_source, Path(tmp) / "build", args.locale)
    return server_dbc, dbc_source, client_dir


def cmd_preflight(args) -> None:
    core = args.core_dir.resolve()
    commit = validate_core_root(core)
    planned = plan_core(core, PAYLOAD_ROOT)
    ensure_target_files_clean(core, [p.relative_path for p in planned] + [SQL_TARGET])
    if (core / SQL_TARGET).exists():
        raise InstallError(f"SQL target already exists: {SQL_TARGET}")
    server_dbc, dbc_source, client_dir = validate_runtime_inputs(core, args, build_smoke_test=True)
    print("Adventurer Core full preflight OK")
    print(f"  core:       {core}")
    print(f"  commit:     {commit}")
    print(f"  source:     {len(planned)} core files")
    print(f"  DBC source: {dbc_source}")
    print(f"  server DBC: {server_dbc}")
    print(f"  client:     {client_dir}")
    print(f"  locale:     {args.locale}")
    print("  SpellDraft client/subclass bundle built successfully in temporary storage")
    print("  fixed talents: none; legacy Guardian/Champion/Scholar rows are purged if present")
    print("  no files changed")


def cmd_apply(args) -> None:
    core = args.core_dir.resolve()
    commit = validate_core_root(core)
    planned = plan_core(core, PAYLOAD_ROOT)
    ensure_target_files_clean(core, [p.relative_path for p in planned] + [SQL_TARGET])
    server_dbc, dbc_source, client_dir = validate_runtime_inputs(core, args, build_smoke_test=False)

    # Build the entire data/client bundle before mutating the core. A bad source
    # DBC, SpellDraft metadata, baseline Lua, or MPQ build therefore fails safely.
    with tempfile.TemporaryDirectory(prefix="adventurer-apply-") as tmp:
        staged = Path(tmp) / "build"
        build_patch(dbc_source, staged, args.locale)

        state = write_transaction(core, planned, commit)
        generated = core / STATE_DIR_NAME / "generated"
        shutil.copytree(staged, generated)

    try:
        dbc_hashes = install_server_dbcs(generated, server_dbc)
        installed_client = install_patch(client_dir, generated, args.locale)
        state["dbc"] = {
            "directory": str(server_dbc),
            "files": dbc_hashes,
        }
        state["client"] = {
            "directory": str(client_dir),
            "installed": installed_client,
        }
        save_state(core, state)
    except Exception as exc:
        # Keep the source transaction manifest/backups intact so rollback can be
        # run safely. Runtime installers also leave one-time backups beside their
        # owned data. Never hide a partial install behind a success message.
        raise InstallError(
            "Runtime/client installation failed after source patching. "
            "Adventurer Core state was preserved; inspect the error and run rollback before retrying. "
            f"Cause: {exc}"
        ) from exc

    problems = verify_state(core, state)
    if problems:
        raise InstallError("Post-apply verification failed:\n  " + "\n  ".join(problems))
    print("Adventurer Core applied and verified.")
    print(f"  core:          {core}")
    print(f"  source commit: {commit}")
    print(f"  owned source:  {len(state['files'])} files")
    print(f"  server DBC:    {len(dbc_hashes)} files")
    print(f"  client locale: {args.locale}")
    print("  SpellDraft:    active abilities and talents enabled")
    print("  talent UI:     Libro de talentos (SpellDraft collection)")
    print("  fixed talents: none")
    print("  NEXT: rebuild/install worldserver, start it, then create a NEW Adventurer.")


def cmd_verify(args) -> None:
    core = args.core_dir.resolve()
    validate_core_root(core)
    state = load_state(core)
    problems = verify_state(core, state)
    if problems:
        raise InstallError("Verification failed:\n  " + "\n  ".join(problems))
    print("Adventurer Core owned source/runtime/client files verify cleanly.")
    print(f"  source commit: {state['source_core_commit']}")
    if state.get("dbc"):
        print(f"  server DBC: {len(state['dbc']['files'])} verified")
    if state.get("client"):
        print(f"  client: {state['client']['directory']}")


def restore_runtime(core: Path, state: dict) -> None:
    dbc_state = state.get("dbc")
    if dbc_state:
        dbc_dir = Path(dbc_state["directory"])
        for name in dbc_state.get("files", {}):
            target = dbc_dir / name
            backup = target.with_name(target.name + ".pre-adventurer-core.bak")
            if backup.is_file():
                shutil.copy2(backup, target)
            elif target.exists():
                target.unlink()

    client_state = state.get("client")
    if client_state:
        client_root = Path(client_state["directory"])
        installed = client_state["installed"]
        backup_root = client_root / ".adventurer-core-backup"
        for key in ("root_patch", "locale_patch"):
            relative = installed[key]
            target = client_root / relative
            backup = backup_root / relative
            if backup.is_file():
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup, target)
            elif target.exists():
                target.unlink()
        owner = client_root / OWNER_MANIFEST
        if owner.exists():
            owner.unlink()


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

    restore_runtime(core, state)

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
    print("Adventurer Core source/runtime/client file layer rolled back safely.")
    print("Database rows already applied by worldserver are intentionally not modified.")


def parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="adventurer.py")
    sub = parser.add_subparsers(dest="command", required=True)
    for name, func in (
        ("preflight", cmd_preflight),
        ("apply", cmd_apply),
        ("verify", cmd_verify),
        ("rollback", cmd_rollback),
    ):
        command = sub.add_parser(name)
        command.add_argument("--core-dir", required=True, type=Path)
        if name in {"preflight", "apply"}:
            command.add_argument("--client-dir", required=True, type=Path)
            command.add_argument("--server-data-dir", type=Path)
            command.add_argument("--dbc-src", type=Path)
            command.add_argument("--locale", default=DEFAULT_LOCALE)
        command.set_defaults(func=func)
    return parser


def main() -> int:
    args = parser().parse_args()
    try:
        args.func(args)
        return 0
    except (
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
