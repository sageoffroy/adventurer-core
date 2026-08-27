#!/usr/bin/env python3
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from mpq_writer import write_mpq


def main() -> None:
    parser = argparse.ArgumentParser(description="Package Darker Nights as patch-ZB.MPQ")
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

    target = data_dir / "patch-ZB.MPQ"
    backup = data_dir / "patch-ZB.MPQ.bak"

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
