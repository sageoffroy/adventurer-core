#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from mpq_writer import write_mpq


def main() -> None:
    parser = argparse.ArgumentParser(description="Package Darker Nights as patch-Y.MPQ")
    parser.add_argument(
        "--dbc",
        type=Path,
        default=Path.home() / "darker-nights-test/DBFilesClient/LightIntBand.dbc",
    )
    parser.add_argument(
        "--client-dir",
        type=Path,
        default=Path("/mnt/c/Games/World of Warcraft 3.3.5a"),
    )
    args = parser.parse_args()

    if not args.dbc.is_file():
        raise SystemExit(f"ERROR: generated DBC not found: {args.dbc}")

    data_dir = args.client_dir / "Data"
    if not data_dir.is_dir():
        raise SystemExit(f"ERROR: WoW Data directory not found: {data_dir}")

    # WoW 3.3.5a custom patch discovery uses single-letter patch names.
    # patch-Z.MPQ is owned by Adventurer / SpellDraft, so Darker Nights uses Y.
    target = data_dir / "patch-Y.MPQ"
    backup = data_dir / "patch-Y.MPQ.bak"

    # Disable the earlier experimental two-letter name, which the client may ignore.
    legacy = data_dir / "patch-ZB.MPQ"
    legacy_disabled = data_dir / "patch-ZB.MPQ.disabled"
    if legacy.exists():
        if legacy_disabled.exists():
            legacy_disabled.unlink()
        legacy.replace(legacy_disabled)
        print(f"Legacy two-letter patch disabled: {legacy_disabled}")

    if target.exists():
        shutil.copy2(target, backup)
        print(f"Existing patch backed up: {backup}")

    files = {
        r"DBFilesClient\LightIntBand.dbc": args.dbc.read_bytes(),
    }
    write_mpq(target, files)

    print("Darker Nights MPQ generated")
    print(f"DBC:   {args.dbc}")
    print(f"Patch: {target}")
    print(f"Size:  {target.stat().st_size} bytes")
    print("Internal file: DBFilesClient\\LightIntBand.dbc")


if __name__ == "__main__":
    main()
