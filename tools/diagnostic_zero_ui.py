#!/usr/bin/env python3
"""Build/install a client patch containing DBC data only, with zero Interface files.

This is a temporary diagnostic tool for isolating PlayerFrame regressions. It
intentionally does not package GlueXML, FrameXML, Lua, XML, textures, or any
other Interface path. The server/core is not modified.

Unlike the production installer, this diagnostic may replace a stale Z patch
whose ownership manifest already says it belongs to Adventurer Core. It still
refuses to overwrite an unowned Z slot.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

from client import (
    DBC_NAMES,
    DEFAULT_LOCALE,
    LEGACY_OWNER_MANIFEST,
    OWNER_MANIFEST,
    PROJECT_SUFFIX,
    ROOT_SHARED_DBCS,
    existing_ownership,
    patch_dbc_copy,
)
from mpq import write_mpq


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def install_zero_ui_patch(client_dir: Path, build_dir: Path, locale: str) -> dict:
    """Install the diagnostic Z patch without trusting stale Adventurer hashes.

    The normal installer treats any hash mismatch as possible external
    modification and aborts. For this disposable diagnostic workflow we need to
    alternate normal and zero-UI Z archives repeatedly. We therefore allow a
    mismatch only when the ownership manifest already belongs to Adventurer
    Core. An occupied, unowned Z slot remains protected.
    """
    client_dir = client_dir.expanduser().resolve()
    build_dir = build_dir.expanduser().resolve()

    wow = client_dir / "Wow.exe"
    if not wow.is_file():
        wow = client_dir / "wow.exe"
    if not wow.is_file():
        raise RuntimeError(f"WoW 3.3.5a client not found: {client_dir}")

    source_root = build_dir / "Data" / f"patch-{PROJECT_SUFFIX}.mpq"
    source_locale = build_dir / "Data" / locale / f"patch-{locale}-{PROJECT_SUFFIX.lower()}.mpq"
    if not source_root.is_file() or not source_locale.is_file():
        raise RuntimeError(f"Built diagnostic patch files missing under {build_dir}")

    data_dir = client_dir / "Data"
    locale_dir = data_dir / locale
    locale_dir.mkdir(parents=True, exist_ok=True)
    target_root = data_dir / source_root.name
    target_locale = locale_dir / source_locale.name

    _, old_owner = existing_ownership(client_dir)
    if old_owner:
        if old_owner.get("owner") != "adventurer-core":
            raise RuntimeError("Existing Z patch manifest is not owned by Adventurer Core")

        old_locale_rel = old_owner.get("locale_patch")
        if old_locale_rel:
            old_locale = client_dir / old_locale_rel
            if old_locale != target_locale and old_locale.exists():
                old_locale.unlink()
    else:
        occupied = [path for path in (target_root, target_locale) if path.exists()]
        if occupied:
            raise RuntimeError(
                "Refusing to overwrite unowned diagnostic Z slot: "
                + ", ".join(str(path) for path in occupied)
            )

    shutil.copy2(source_root, target_root)
    shutil.copy2(source_locale, target_locale)

    owner = {
        "schema": 1,
        "owner": "adventurer-core",
        "root_patch": str(target_root.relative_to(client_dir)),
        "root_sha256": file_sha256(target_root),
        "locale_patch": str(target_locale.relative_to(client_dir)),
        "locale_sha256": file_sha256(target_locale),
    }

    modern_owner = client_dir / OWNER_MANIFEST
    modern_owner.write_text(
        json.dumps(owner, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    legacy_owner = client_dir / LEGACY_OWNER_MANIFEST
    if legacy_owner.exists() and legacy_owner != modern_owner:
        legacy_owner.unlink()

    return owner


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
        owner = install_zero_ui_patch(args.client_dir, build_dir, args.locale)

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
