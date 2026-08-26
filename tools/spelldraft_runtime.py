#!/usr/bin/env python3
"""Install editable SpellDraft runtime data beside AzerothCore's server data.

cards.csv remains file-managed: package updates advance it while unedited and
preserve it wholesale after a real local edit.

spelldraft.conf is merged option-by-option against the previous packaged .dist.
That lets package updates add/reorder options and advance untouched defaults while
preserving values the server owner deliberately changed for runtime testing.
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


def parse_config_values(text: str) -> dict[tuple[str, str], str]:
    values: dict[tuple[str, str], str] = {}
    section = ""
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or line.startswith(";"):
            continue
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1].strip()
            continue
        if "=" not in raw or not section:
            continue
        key, value = raw.split("=", 1)
        key = key.strip()
        if key:
            values[(section, key)] = value.strip()
    return values


def merge_config_text(source_text: str, live_text: str, previous_text: str | None) -> str | None:
    """Render the new package template while preserving genuine local values.

    previous_text is the package baseline from the prior update. If a live value
    still equals that baseline, it was not locally changed and may advance to the
    new package value. If it differs, the local override wins. Missing live keys
    always adopt the new package value.

    A pre-marker/stale install can already have the current .dist beside an older
    live file. The same rule still works: existing differing values are treated as
    intentional overrides while newly introduced options are added from source.
    """
    source_values = parse_config_values(source_text)
    live_values = parse_config_values(live_text)
    if not source_values or not live_values:
        return None

    previous_values = parse_config_values(previous_text) if previous_text is not None else {}
    output: list[str] = []
    section = ""

    for raw in source_text.splitlines(keepends=True):
        stripped = raw.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1].strip()
            output.append(raw)
            continue
        if "=" not in raw or not section or stripped.startswith("#") or stripped.startswith(";"):
            output.append(raw)
            continue

        left, source_value_raw = raw.split("=", 1)
        key = left.strip()
        option = (section, key)
        if not key or option not in source_values:
            output.append(raw)
            continue

        chosen = source_values[option]
        if option in live_values:
            live_value = live_values[option]
            previous_value = previous_values.get(option)
            if previous_value is None or live_value != previous_value:
                chosen = live_value

        newline = "\n" if raw.endswith("\n") else ""
        output.append(f"{left}= {chosen}{newline}")

    return "".join(output)


def install(core: Path, server_data_dir: Path | None) -> None:
    data_dir = resolve_data_dir(core, server_data_dir)
    if not data_dir.is_dir():
        raise SpellDraftRuntimeError(f"Server data directory not found: {data_dir}")

    target = data_dir / "spelldraft"
    target.mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    updated: list[str] = []
    migrated: list[str] = []
    merged: list[str] = []
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
                package_managed = True
            elif previous_dist_hash is not None and live_hash == previous_dist_hash:
                package_managed = True
                legacy_migration = True
            elif live_hash in LEGACY_PACKAGED_SHA256.get(name, set()):
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
            elif name == "spelldraft.conf":
                source_text = source.read_text(encoding="utf-8")
                live_text = live.read_text(encoding="utf-8")
                previous_text = dist.read_text(encoding="utf-8") if dist.is_file() else None
                merged_text = merge_config_text(source_text, live_text, previous_text)
                if merged_text is None:
                    preserved.append(name)
                else:
                    if merged_text != live_text:
                        live.write_text(merged_text, encoding="utf-8")
                        merged.append(name)
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
    if merged:
        print("  merged config:    " + ", ".join(merged))
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
