#!/usr/bin/env python3
"""Stage the Gauntlet module and addon for the root apply/update pipelines."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
TOOLS = ROOT / "tools" / "khadgar_gauntlet"
MODULE_SOURCE = ROOT / "modules" / "mod-adventurer-gauntlet"


def run(*args: str) -> None:
    subprocess.run([sys.executable, *args], check=True)


def stage(core_dir: Path, server_data_dir: Path, client_dir: Path, dbc_src: Path) -> None:
    core = core_dir.expanduser().resolve()
    data = server_data_dir.expanduser().resolve()
    client = client_dir.expanduser().resolve()
    clean_dbc = dbc_src.expanduser().resolve()
    item_dbc = clean_dbc / "Item.dbc"
    module_target = core / "modules" / "mod-adventurer-gauntlet"

    if not (core / "modules").is_dir():
        raise RuntimeError(f"AzerothCore modules directory not found: {core / 'modules'}")
    if not MODULE_SOURCE.is_dir():
        raise RuntimeError(f"Gauntlet module source not found: {MODULE_SOURCE}")
    if not item_dbc.is_file():
        raise RuntimeError(f"clean Item.dbc not found: {item_dbc}")

    if module_target.exists():
        shutil.rmtree(module_target)
    shutil.copytree(MODULE_SOURCE, module_target)

    (module_target / ".server-data-dir").write_text(str(data) + "\n", encoding="utf-8")

    item_catalog = module_target / "data" / "items" / "early_items.csv"
    set_catalog = module_target / "data" / "items" / "sets.csv"
    # Generated item SQL is an intermediate artifact consumed only by tools/world.py.
    # Keep it outside data/sql/world so AzerothCore's module auto-updater cannot
    # apply the same catalog through a second update path.
    item_sql = module_target / "data" / "generated" / "gauntlet_items.sql"
    set_include = module_target / "src" / "GeneratedGauntletSets.inc"

    run(str(TOOLS / "build_catalog.py"), "--items", str(item_catalog), "--sets", str(set_catalog))
    item_sql.parent.mkdir(parents=True, exist_ok=True)
    run(
        str(TOOLS / "generate_items.py"),
        "--input", str(item_catalog),
        "--output", str(item_sql),
        "--item-dbc", str(item_dbc),
    )
    run(
        str(TOOLS / "generate_sets.py"),
        "--items", str(item_catalog),
        "--sets", str(set_catalog),
        "--output", str(set_include),
    )

    addon_dir = client / "Interface" / "AddOns" / "AdventurerGauntlet"
    addon_dir.mkdir(parents=True, exist_ok=True)
    stale = addon_dir / "AdventurerGauntletStash.lua"
    if stale.exists():
        stale.unlink()

    (addon_dir / "AdventurerGauntlet.toc").write_text(
        "## Interface: 30300\n"
        "## Title: Adventurer Gauntlet\n"
        "## Notes: Gauntlet account bank, item collection and client integration for Aventureros de Azeroth.\n"
        "AdventurerGauntletBank.lua\n"
        "AdventurerGauntletBook.lua\n"
        "AdventurerMinimapFix.lua\n",
        encoding="utf-8",
    )
    for name in (
        "AdventurerGauntletBank.lua",
        "AdventurerGauntletBook.lua",
        "AdventurerMinimapFix.lua",
    ):
        shutil.copy2(TOOLS / name, addon_dir / name)

    print(f"Gauntlet module staged into: {module_target}")
    print(f"Gauntlet addon staged into: {addon_dir}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--core-dir", required=True, type=Path)
    parser.add_argument("--server-data-dir", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument("--dbc-src", required=True, type=Path)
    args, _unknown = parser.parse_known_args()
    try:
        stage(args.core_dir, args.server_data_dir, args.client_dir, args.dbc_src)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.error(str(exc))
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
