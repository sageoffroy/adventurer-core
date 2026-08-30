#!/usr/bin/env python3
"""Install, verify and roll back the Adventurer-owned Playerbots profile."""

from __future__ import annotations

import argparse
import re
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
PROFILE = ROOT / "config" / "playerbots" / "managed.conf"
# AzerothCore installs module configs under etc/modules. Older/local layouts may
# place them directly under etc, so target_path() deliberately supports both and
# finally discovers one unambiguous playerbots.conf below the install etc dir.
TARGET_RELATIVE = Path("env/dist/etc/modules/playerbots.conf")
TARGET_CANDIDATES = (
    TARGET_RELATIVE,
    Path("env/dist/etc/playerbots.conf"),
)
BACKUP_SUFFIX = ".adventurer-core.before"


class PlayerbotsConfigError(RuntimeError):
    pass


def read_profile(path: Path = PROFILE) -> dict[str, str]:
    if not path.is_file():
        raise PlayerbotsConfigError(f"Managed Playerbots profile not found: {path}")

    result: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            raise PlayerbotsConfigError(f"Invalid managed Playerbots line: {raw!r}")
        key, value = (part.strip() for part in line.split("=", 1))
        if not key.startswith("AiPlayerbot.") or not key:
            raise PlayerbotsConfigError(f"Invalid managed Playerbots key: {key!r}")
        if key in result:
            raise PlayerbotsConfigError(f"Duplicate managed Playerbots key: {key}")
        result[key] = value

    if not result:
        raise PlayerbotsConfigError("Managed Playerbots profile is empty")
    if result.get("AiPlayerbot.DeleteRandomBotAccounts") != "0":
        raise PlayerbotsConfigError(
            "AiPlayerbot.DeleteRandomBotAccounts must remain 0 in the permanent profile"
        )
    return result


def target_path(core: Path) -> Path:
    core = core.expanduser().resolve()

    # Prefer known AzerothCore layouts deterministically.
    for relative in TARGET_CANDIDATES:
        target = core / relative
        if target.is_file():
            return target

    # Be tolerant of a custom install layout, but never guess when ambiguous.
    etc_dir = core / "env" / "dist" / "etc"
    discovered = sorted(path for path in etc_dir.rglob("playerbots.conf") if path.is_file()) \
        if etc_dir.is_dir() else []
    if len(discovered) == 1:
        return discovered[0]
    if len(discovered) > 1:
        rendered = "\n  ".join(str(path) for path in discovered)
        raise PlayerbotsConfigError(
            "Multiple Playerbots runtime configs found; refusing to guess:\n  " + rendered
        )

    searched = "\n  ".join(str(core / relative) for relative in TARGET_CANDIDATES)
    raise PlayerbotsConfigError(
        "Playerbots runtime config not found. Searched:\n  " + searched
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
            raise PlayerbotsConfigError(
                f"Expected at most one active assignment for {key}, found {len(matches)}"
            )
        replacement = f"{key} = {value}"
        if matches:
            match = matches[0]
            current = match.group(0).strip()
            if current != replacement:
                text = text[:match.start()] + replacement + text[match.end():]
                changed.append(key)
        else:
            missing.append((key, value))

    if missing:
        if text and not text.endswith("\n"):
            text += "\n"
        text += "\n# Adventurer Core managed Playerbots values\n"
        for key, value in missing:
            text += f"{key} = {value}\n"
            changed.append(key)

    return text, changed


def active_assignments(text: str, keys: set[str]) -> dict[str, list[str]]:
    found = {key: [] for key in keys}
    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = (part.strip() for part in stripped.split("=", 1))
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
        raise PlayerbotsConfigError(
            "Playerbots managed profile verification failed:\n  " + "\n  ".join(problems)
        )


def rollback(core: Path) -> bool:
    target = target_path(core)
    backup = backup_path(target)
    if not backup.is_file():
        return False
    target.write_bytes(backup.read_bytes())
    backup.unlink()
    return True


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="playerbots_runtime.py")
    result.add_argument("command", choices=("install", "verify", "rollback"))
    result.add_argument("--core-dir", required=True, type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "install":
            target = target_path(args.core_dir)
            changed = install(args.core_dir)
            print(f"Playerbots runtime config: {target}")
            if changed:
                print(f"Playerbots managed profile applied: {len(changed)} value(s) changed.")
                for key in changed:
                    print(f"  {key}")
            else:
                print("Playerbots managed profile already current.")
        elif args.command == "verify":
            target = target_path(args.core_dir)
            verify(args.core_dir)
            print(f"Playerbots runtime config: {target}")
            print("Playerbots managed profile verifies cleanly.")
        else:
            restored = rollback(args.core_dir)
            print(
                "Playerbots pre-Adventurer config restored."
                if restored
                else "Playerbots config backup absent; nothing to restore."
            )
        return 0
    except (OSError, PlayerbotsConfigError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
