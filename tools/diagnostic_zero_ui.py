#!/usr/bin/env python3
"""Build/install a client patch containing DBC data only, with zero Interface files.

This is a temporary diagnostic tool for isolating PlayerFrame regressions. It
intentionally does not package GlueXML, FrameXML, Lua, XML, textures, or any
other Interface path. The server/core is not modified.
"""

from __future__ import annotations

import argparse
import shutil
import tempfile
from pathlib import Path

from client import (
    DBC_NAMES,
    DEFAULT_LOCALE,
    PROJECT_SUFFIX,
    ROOT_SHARED_DBCS,
    install_patch,
    patch_dbc_copy,
)
from mpq import write_mpq


def build_zero_ui_bundle(dbc_source: Path, output: Path, locale: str) -> tuple[Path, Path]:
    dbc_source = dbc_source.expanduser().resolve()
    output = output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="adventurer-zero-ui-") as tmp_name:
        work = Path(tmp_name)
        patch_dbc_copy(dbc_source, work)

        root_files = {
            f"DBFilesClient\\{name}": (work / name).read_bytes()
            for name in ROOT_SHARED_DBCS
        }
        locale_files = {
            f"DBFilesClient\\{name}": (work / name).read_bytes()
            for name in DBC_NAMES
        }

        interface_entries = [
            name for name in (*root_files.keys(), *locale_files.keys())
            if name.lower().startswith("interface\\")
        ]
        if interface_entries:
            raise RuntimeError(
                "zero-UI diagnostic unexpectedly contains Interface entries: "
                + ", ".join(interface_entries)
            )

        root_patch = output / "Data" / f"patch-{PROJECT_SUFFIX}.mpq"
        locale_patch = output / "Data" / locale / f"patch-{locale}-{PROJECT_SUFFIX.lower()}.mpq"
        write_mpq(root_patch, root_files)
        write_mpq(locale_patch, locale_files)

    return root_patch, locale_patch


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Install a DBC-only Adventurer client patch with zero Interface files"
    )
    parser.add_argument("--dbc-src", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument("--locale", default=DEFAULT_LOCALE)
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="adventurer-zero-ui-build-") as tmp_name:
        build_dir = Path(tmp_name)
        root_patch, locale_patch = build_zero_ui_bundle(
            args.dbc_src,
            build_dir,
            args.locale,
        )
        owner = install_patch(args.client_dir, build_dir, args.locale)

        print("Adventurer ZERO-UI diagnostic patch installed.")
        print("  Interface entries: 0")
        print(f"  root patch:         {owner['root_patch']}")
        print(f"  locale patch:       {owner['locale_patch']}")
        print(f"  built root:         {root_patch.name}")
        print(f"  built locale:       {locale_patch.name}")
        print("  server/core:        untouched")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
