#!/usr/bin/env python3
"""Install editable SpellDraft runtime data beside AzerothCore's server data.

The package keeps a managed copy of each runtime file. Package updates refresh a
live file automatically only while that live file still matches the last managed
version. Real local edits are preserved. Historical packaged versions from the
pre-marker installer are migrated once so old installs do not stay stuck forever.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config" / "spelldraft"
FILES = ("spelldraft.conf", "cards.csv")
MARKER_SUFFIX = ".managed.sha256"

# Exact SHA-256 values of packaged files shipped before managed markers existed.
# These let update.sh repair installations created by the old "preserve forever"
# behavior without mistaking genuinely edited local files for package defaults.
LEGACY_PACKAGED_SHA256 = {
    "spelldraft.conf": {
        "9e300249cc49ddcf4bb4c4861a9d09b569a257539230615b6e69da5a219c3005",
    },
    "cards.csv": {
        "dfb1b440e13121e86cf45a27c4dcee021c2b8ac1dc52096aa9604454834d9fcf",
    },
}


class SpellDraftRuntimeError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_data_dir(core: Path, server_data_dir: Path | None) -> Path:
    if server_data_dir:
        return server_data_dir.expanduser().resolve()
    return (core.expanduser().resolve() / "env" / "dist" / "data").resolve()


def marker_path(target: Path, name: str) -> Path:
    return target / f".{name}{MARKER_SUFFIX}"


def read_marker(path: Path) -> str | None:
    if not path.is_file():
        return None
    value = path.read_text(encoding="utf-8").strip().lower()
    if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
        return None
    return value


def write_marker(path: Path, digest: str) -> None:
    path.write_text(digest + "\n", encoding="utf-8")


def install(core: Path, server_data_dir: Path | None) -> None:
    data_dir = resolve_data_dir(core, server_data_dir)
    if not data_dir.is_dir():
        raise SpellDraftRuntimeError(f"Server data directory not found: {data_dir}")

    target = data_dir / "spelldraft"
    target.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    updated: list[str] = []
    migrated: list[str] = []
    preserved: list[str] = []

    for name in FILES:
        source = SOURCE / name
        if not source.is_file():
            raise SpellDraftRuntimeError(f"Missing packaged SpellDraft file: {source}")

        live = target / name
        dist = target / f"{name}.dist"
        marker = marker_path(target, name)

        source_hash = sha256(source)
        previous_dist_hash = sha256(dist) if dist.is_file() else None
        managed_hash = read_marker(marker)

        if live.exists() and not live.is_file():
            raise SpellDraftRuntimeError(f"Runtime path is not a file: {live}")

        if not live.exists():
            shutil.copy2(source, live)
            write_marker(marker, source_hash)
            created.append(name)
        else:
            live_hash = sha256(live)
            package_managed = False
            legacy_migration = False

            if managed_hash is not None:
                package_managed = live_hash == managed_hash
            elif live_hash == source_hash:
                # Existing install already happens to be current. Adopt it as a
                # managed file so future package updates can advance it safely.
                package_managed = True
            elif previous_dist_hash is not None and live_hash == previous_dist_hash:
                # Old installer state where live still matched the previous .dist.
                package_managed = True
                legacy_migration = True
            elif live_hash in LEGACY_PACKAGED_SHA256.get(name, set()):
                # The broken updater may already have replaced .dist with the new
                # package while leaving live on an older exact packaged version.
                package_managed = True
                legacy_migration = True

            if package_managed:
                if live_hash != source_hash:
                    shutil.copy2(source, live)
                    if legacy_migration:
                        migrated.append(name)
                    else:
                        updated.append(name)
                write_marker(marker, source_hash)
            else:
                preserved.append(name)

        # .dist always represents the package currently checked out in Git.
        shutil.copy2(source, dist)

    print("SpellDraft runtime data installed.")
    print(f"  directory: {target}")
    if created:
        print("  created editable: " + ", ".join(created))
    if updated:
        print("  updated managed:  " + ", ".join(updated))
    if migrated:
        print("  migrated stale:   " + ", ".join(migrated))
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
        marker = marker_path(target, name)
        managed_hash = read_marker(marker)

        remove_live = False
        if live.is_file():
            live_hash = sha256(live)
            if managed_hash is not None and live_hash == managed_hash:
                remove_live = True
            elif dist.is_file() and live_hash == sha256(dist):
                remove_live = True

        if remove_live:
            live.unlink()
        elif live.is_file():
            print(f"WARNING: preserving edited SpellDraft runtime file during rollback: {live}")

        if dist.is_file():
            dist.unlink()
        if marker.is_file():
            marker.unlink()

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
    # apply.sh/update.sh/rollback.sh forward their full Adventurer argument set.
    # Runtime data only needs core/data paths, so ignore unrelated client/DBC
    # switches instead of forcing the shell wrappers to maintain two arg lists.
    args, _ = parser().parse_known_args()
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
