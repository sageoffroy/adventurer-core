#!/usr/bin/env python3
"""SpellDraft v3 custom icon pack catalog and SpellIcon.dbc integration."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

from dbc import DBC, DBCError, set_u32, u32

ROOT = Path(__file__).resolve().parent.parent
ICON_DIR = ROOT / "client" / "icons"
CATALOG = ICON_DIR / "catalog.csv"
ICON_ID_MIN = 910000
ICON_ID_MAX = 999999
SPELLICON_FIELDS = 2
SPELLICON_RECORD_SIZE = 8


def _icon_files() -> list[Path]:
    if not ICON_DIR.is_dir():
        return []
    return sorted(
        path for path in ICON_DIR.rglob("*.blp")
        if path.is_file()
    )


def _relative_icon(path: Path) -> str:
    return path.relative_to(ICON_DIR).as_posix()


def load_catalog() -> dict[str, int]:
    if not CATALOG.is_file():
        return {}
    result: dict[str, int] = {}
    with CATALOG.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=";")
        if reader.fieldnames != ["id", "file"]:
            raise DBCError(f"{CATALOG}: expected columns id;file")
        for row in reader:
            icon_id = int(row["id"])
            filename = row["file"].strip()
            if not (ICON_ID_MIN <= icon_id <= ICON_ID_MAX):
                raise DBCError(f"{CATALOG}: icon id {icon_id} outside reserved range")
            if filename in result:
                raise DBCError(f"{CATALOG}: duplicate icon file {filename}")
            result[filename] = icon_id
    return result


def write_catalog() -> None:
    existing = load_catalog()
    files = [_relative_icon(path) for path in _icon_files()]
    used = set(existing.values())
    next_id = ICON_ID_MIN
    rows: list[tuple[int, str]] = []

    for filename in files:
        icon_id = existing.get(filename)
        if icon_id is None:
            while next_id in used:
                next_id += 1
            if next_id > ICON_ID_MAX:
                raise DBCError("custom icon reserved ID range exhausted")
            icon_id = next_id
            used.add(icon_id)
            next_id += 1
        rows.append((icon_id, filename))

    ICON_DIR.mkdir(parents=True, exist_ok=True)
    with CATALOG.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle, delimiter=";", lineterminator="\n")
        writer.writerow(["id", "file"])
        for icon_id, filename in sorted(rows):
            writer.writerow([icon_id, filename])
    print(f"SpellDraft v3 icon catalog: {len(rows)} icons -> {CATALOG}")


def icon_archive_files() -> dict[str, bytes]:
    catalog = load_catalog()
    result: dict[str, bytes] = {}
    for filename in catalog:
        path = ICON_DIR / Path(filename)
        if not path.is_file():
            raise DBCError(f"missing icon declared by catalog: {path}")
        payload = path.read_bytes()
        if len(payload) < 4 or payload[:3] != b"BLP":
            raise DBCError(f"{path}: expected BLP texture")
        internal = "Interface\\Icons\\" + filename.replace("/", "\\")
        result[internal] = payload
    return result


def patch_spell_icon(path: Path) -> bool:
    catalog = load_catalog()
    if not catalog:
        return False

    dbc = DBC.read(path)
    if dbc.fields != SPELLICON_FIELDS or dbc.record_size != SPELLICON_RECORD_SIZE:
        raise DBCError(f"{path}: unexpected SpellIcon.dbc layout {dbc.fields}/{dbc.record_size}")

    before = dbc.to_bytes()
    owned_ids = set(catalog.values())
    base_rows = [row for row in dbc.records if u32(row, 0) not in owned_ids]

    for filename, icon_id in catalog.items():
        row = bytearray(SPELLICON_RECORD_SIZE)
        set_u32(row, 0, icon_id)
        without_ext = filename[:-4] if filename.lower().endswith(".blp") else filename
        icon_path = "Interface\\Icons\\" + without_ext.replace("/", "\\")
        set_u32(row, 1, dbc.append_string(icon_path))
        base_rows.append(row)

    dbc.records = sorted(base_rows, key=lambda row: u32(row, 0))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return after != before


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["catalog"])
    args = parser.parse_args()
    try:
        if args.command == "catalog":
            write_catalog()
        return 0
    except (DBCError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
