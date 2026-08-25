#!/usr/bin/env python3
"""Install editable SpellDraft runtime data beside AzerothCore's server data.

The package copies fresh defaults to *.dist on every update, but never overwrites
an existing editable spelldraft.conf or cards.csv. This keeps local balance work
safe while still exposing the newest packaged baseline for comparison.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config" / "spelldraft"
FILES = ("spelldraft.conf", "cards.csv")


class SpellDraftRuntimeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_data_dir(core: Path, server_data_dir: Path | None) -> Path:
    if server_data_dir:
        return server_data_dir.expanduser().resolve()
    return (core.expanduser().resolve() / "env" / "dist" / "data").resolve()


def install(core: Path, server_data_dir: Path | None) -> None:
    data_dir = resolve_data_dir(core, server_data_dir)
    if not data_dir.is_dir():
        raise SpellDraftRuntimeError(f"Server data directory not found: {data_dir}")

    target = data_dir / "spelldraft"
    target.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    preserved: list[str] = []
    for name in FILES:
        source = SOURCE / name
        if not source.is_file():
            raise SpellDraftRuntimeError(f"Missing packaged SpellDraft file: {source}")

        dist = target / f"{name}.dist"
        shutil.copy2(source, dist)

        live = target / name
        if live.exists():
            if not live.is_file():
                raise SpellDraftRuntimeError(f"Runtime path is not a file: {live}")
            preserved.append(name)
        else:
            shutil.copy2(source, live)
            created.append(name)

    print("SpellDraft runtime data installed.")
    print(f"  directory: {target}")
    if created:
        print("  created editable: " + ", ".join(created))
    if preserved:
        print("  preserved edits:  " + ", ".join(preserved))
    print("  packaged defaults: spelldraft.conf.dist, cards.csv.dist")


def remove(core: Path, server_data_dir: Path | None) -> None:
    data_dir = resolve_data_dir(core, server_data_dir)
    target = data_dir / "spelldraft"
    if not target.exists():
        return

    for name in FILES:
        live = target / name
        dist = target / f"{name}.dist"
        if live.is_file() and dist.is_file() and sha256(live) == sha256(dist):
            live.unlink()
        elif live.is_file():
            print(f"WARNING: preserving edited SpellDraft runtime file during rollback: {live}")
        if dist.is_file():
            dist.unlink()

    try:
        target.rmdir()
    except OSError:
        pass


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="spelldraft_runtime.py")
    sub = result.add_subparsers(dest="command", required=True)
    for name in ("install", "remove"):
        command = sub.add_parser(name)
        command.add_argument("--core-dir", required=True, type=Path)
        command.add_argument("--server-data-dir", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            install(args.core_dir, args.server_data_dir)
        else:
            remove(args.core_dir, args.server_data_dir)
        return 0
    except (SpellDraftRuntimeError, OSError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
