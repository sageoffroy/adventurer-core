#!/usr/bin/env python3
"""Adopt explicitly approved existing core files into Adventurer ownership."""

from __future__ import annotations

import argparse
from pathlib import Path

from adventurer import (
    STATE_DIR_NAME,
    InstallError,
    git,
    load_state,
    save_state,
    sha256_bytes,
    validate_core_root,
)

ADOPTABLE_FILES = {
    "src/server/game/Spells/SpellEffects.cpp",
}


def adopt(core: Path, relative: str) -> None:
    if relative not in ADOPTABLE_FILES:
        raise InstallError(f"Source file is not approved for adoption: {relative}")

    core = core.expanduser().resolve()
    state = load_state(core)
    installed_commit = state.get("source_core_commit")
    current_commit = validate_core_root(core)
    if installed_commit and current_commit != installed_commit:
        raise InstallError(
            "AzerothCore HEAD changed after Adventurer was installed; refusing ownership migration: "
            f"installed={installed_commit}, current={current_commit}"
        )

    if any(entry.get("path") == relative for entry in state.get("files", [])):
        return

    target = core / relative
    if not target.is_file():
        raise InstallError(f"Cannot adopt missing source file: {relative}")

    dirty = git(core, "status", "--porcelain", "--", relative).stdout.strip()
    if dirty:
        raise InstallError(
            f"Refusing to adopt source file with pre-existing local changes: {relative}\n{dirty}"
        )

    original = target.read_bytes()
    backup = core / STATE_DIR_NAME / "backups" / relative
    backup.parent.mkdir(parents=True, exist_ok=True)
    if backup.exists():
        if backup.read_bytes() != original:
            raise InstallError(f"Conflicting rollback backup already exists: {backup}")
    else:
        backup.write_bytes(original)

    digest = sha256_bytes(original)
    state.setdefault("files", []).append({
        "path": relative,
        "existed_before": True,
        "before_sha256": digest,
        "after_sha256": digest,
    })
    save_state(core, state)
    print(f"Adopted existing Adventurer-owned source with rollback backup: {relative}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--path", required=True)
    args = parser.parse_args()
    try:
        adopt(args.core_dir, args.path)
        return 0
    except (InstallError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
