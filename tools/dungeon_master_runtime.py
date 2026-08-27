#!/usr/bin/env python3
"""Manage Aventureros-owned runtime values for mod-dungeon-master."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "config" / "dungeon-master" / "managed.conf"
TARGET_CANDIDATES = (
    Path("env/dist/etc/modules/mod_dungeon_master.conf"),
    Path("env/dist/etc/mod_dungeon_master.conf"),
)
BACKUP_SUFFIX = ".adventurer-core.before"


class DungeonMasterConfigError(RuntimeError):
    pass


def read_profile(path: Path | None = None) -> dict[str, str]:
    # Resolve PROFILE at call time so tests and callers can safely inject an
    # alternate profile without being defeated by Python default-argument binding.
    if path is None:
        path = PROFILE
    if not path.is_file():
        raise DungeonMasterConfigError(f"Managed Dungeon Master profile not found: {path}")
    out: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise DungeonMasterConfigError(f"Invalid managed Dungeon Master line: {raw!r}")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key.startswith("DungeonMaster."):
            raise DungeonMasterConfigError(f"Invalid managed Dungeon Master key: {key!r}")
        if key in out:
            raise DungeonMasterConfigError(f"Duplicate managed Dungeon Master key: {key}")
        out[key] = value
    if not out:
        raise DungeonMasterConfigError("Managed Dungeon Master profile is empty")
    return out


def target_path(core: Path) -> Path:
    core = core.expanduser().resolve()
    for rel in TARGET_CANDIDATES:
        path = core / rel
        if path.is_file():
            return path
    etc = core / "env/dist/etc"
    found = sorted(etc.rglob("mod_dungeon_master.conf")) if etc.is_dir() else []
    found = [p for p in found if p.is_file()]
    if len(found) == 1:
        return found[0]
    if len(found) > 1:
        raise DungeonMasterConfigError(
            "Multiple Dungeon Master runtime configs found; refusing to guess:\n  "
            + "\n  ".join(str(p) for p in found)
        )
    raise DungeonMasterConfigError(
        "Dungeon Master runtime config not found. Searched:\n  "
        + "\n  ".join(str(core / rel) for rel in TARGET_CANDIDATES)
    )


def backup_path(target: Path) -> Path:
    return target.with_name(target.name + BACKUP_SUFFIX)


def assignment_pattern(key: str) -> re.Pattern[str]:
    return re.compile(rf"^(?P<indent>\s*){re.escape(key)}\s*=.*$", re.MULTILINE)


def patch_text(text: str, profile: dict[str, str]) -> tuple[str, list[str]]:
    changed: list[str] = []
    missing: list[tuple[str, str]] = []
    for key, value in profile.items():
        pattern = assignment_pattern(key)
        matches = list(pattern.finditer(text))
        if len(matches) > 1:
            raise DungeonMasterConfigError(
                f"Expected at most one active assignment for {key}, found {len(matches)}"
            )
        replacement = f"{key} = {value}"
        if matches:
            match = matches[0]
            if match.group(0).strip() != replacement:
                text = text[:match.start()] + replacement + text[match.end():]
                changed.append(key)
        else:
            missing.append((key, value))
    if missing:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n# Adventurer Core managed Dungeon Master values\n"
        for key, value in missing:
            text += f"{key} = {value}\n"
            changed.append(key)
    return text, changed


def active_assignments(text: str, keys: set[str]) -> dict[str, list[str]]:
    found = {key: [] for key in keys}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        if key in found:
            found[key].append(value)
    return found


def install(core: Path) -> list[str]:
    target = target_path(core)
    profile = read_profile()
    before = target.read_text(encoding="utf-8")
    after, changed = patch_text(before, profile)
    backup = backup_path(target)
    if not backup.exists():
        shutil.copy2(target, backup)
    if after != before:
        target.write_text(after, encoding="utf-8")
    verify(core)
    return changed


def verify(core: Path) -> None:
    target = target_path(core)
    profile = read_profile()
    found = active_assignments(target.read_text(encoding="utf-8"), set(profile))
    problems: list[str] = []
    for key, expected in profile.items():
        values = found[key]
        if len(values) != 1:
            problems.append(f"{key}: expected one active assignment, found {len(values)}")
        elif values[0] != expected:
            problems.append(f"{key}: expected {expected!r}, found {values[0]!r}")
    if problems:
        raise DungeonMasterConfigError(
            "Dungeon Master managed profile verification failed:\n  " + "\n  ".join(problems)
        )


def rollback(core: Path) -> bool:
    target = target_path(core)
    backup = backup_path(target)
    if not backup.is_file():
        return False
    target.write_bytes(backup.read_bytes())
    backup.unlink()
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "verify", "rollback"))
    parser.add_argument("--core-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "install":
            target = target_path(args.core_dir)
            changed = install(args.core_dir)
            print(f"Dungeon Master runtime config: {target}")
            if changed:
                print(f"Dungeon Master managed profile applied: {len(changed)} value(s) changed.")
                for key in changed:
                    print(f"  {key}")
            else:
                print("Dungeon Master managed profile already current.")
        elif args.command == "verify":
            target = target_path(args.core_dir)
            verify(args.core_dir)
            print(f"Dungeon Master runtime config: {target}")
            print("Dungeon Master managed profile verifies cleanly.")
        else:
            restored = rollback(args.core_dir)
            print(
                "Dungeon Master pre-Adventurer config restored."
                if restored
                else "Dungeon Master config backup absent; nothing to restore."
            )
        return 0
    except (OSError, DungeonMasterConfigError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
