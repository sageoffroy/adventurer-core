#!/usr/bin/env python3
"""Build/install client metadata for Adventurer Gauntlet custom items."""

from __future__ import annotations

import argparse
import csv
import struct
from pathlib import Path

from mpq import write_mpq

MAGIC = b"WDBC"
HEADER = struct.Struct("<4sIIII")
CUSTOM_ITEM_MIN = 911000
CUSTOM_ITEM_MAX = 911999


class ClientItemError(RuntimeError):
    pass


class DBC:
    def __init__(self, fields: int, record_size: int, records: list[bytearray], strings: bytes, trailing: bytes = b""):
        self.fields = fields
        self.record_size = record_size
        self.records = records
        self.strings = strings
        self.trailing = trailing

    @classmethod
    def read(cls, path: Path) -> "DBC":
        data = path.read_bytes()
        if len(data) < HEADER.size:
            raise ClientItemError(f"{path}: DBC too small")
        magic, count, fields, record_size, string_size = HEADER.unpack_from(data)
        if magic != MAGIC:
            raise ClientItemError(f"{path}: expected WDBC")
        records_start = HEADER.size
        records_end = records_start + count * record_size
        strings_end = records_end + string_size
        if strings_end > len(data):
            raise ClientItemError(f"{path}: invalid DBC sizes")
        records = [
            bytearray(data[records_start + i * record_size: records_start + (i + 1) * record_size])
            for i in range(count)
        ]
        return cls(fields, record_size, records, data[records_end:strings_end], data[strings_end:])

    def to_bytes(self) -> bytes:
        return (
            HEADER.pack(MAGIC, len(self.records), self.fields, self.record_size, len(self.strings))
            + b"".join(self.records)
            + self.strings
            + self.trailing
        )


def u32(record: bytearray, field: int) -> int:
    return struct.unpack_from("<I", record, field * 4)[0]


def set_u32(record: bytearray, field: int, value: int) -> None:
    struct.pack_into("<I", record, field * 4, value)


def enabled(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle, delimiter=";") if enabled(row.get("enabled", ""))]


def patch_item_dbc(source_path: Path, item_rows: list[dict[str, str]]) -> bytes:
    dbc = DBC.read(source_path)
    if dbc.fields != 8 or dbc.record_size != 32:
        raise ClientItemError(
            f"{source_path}: unexpected Item.dbc layout {dbc.fields}/{dbc.record_size}; expected 8/32"
        )

    stock = {u32(row, 0): row for row in dbc.records if not (CUSTOM_ITEM_MIN <= u32(row, 0) <= CUSTOM_ITEM_MAX)}
    rebuilt = list(stock.values())

    for item in item_rows:
        entry = int(item["entry"])
        source_entry = int(item["source_entry"])
        template = stock.get(source_entry)
        if template is None:
            raise ClientItemError(f"Item.dbc has no source row {source_entry} for custom item {entry}")
        row = bytearray(template)
        set_u32(row, 0, entry)
        display_id = item.get("display_id", "").strip()
        if display_id:
            set_u32(row, 5, int(display_id))
        rebuilt.append(row)

    rebuilt.sort(key=lambda row: u32(row, 0))
    dbc.records = rebuilt
    return dbc.to_bytes()


def lua_string(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'


def build_set_addon(item_rows: list[dict[str, str]], set_rows: list[dict[str, str]]) -> str:
    items_by_set: dict[str, list[dict[str, str]]] = {}
    for item in item_rows:
        key = item.get("set_key", "").strip()
        if key:
            items_by_set.setdefault(key, []).append(item)

    bonuses_by_set: dict[str, list[dict[str, str]]] = {}
    set_names: dict[str, str] = {}
    for bonus in set_rows:
        key = bonus["set_key"].strip()
        set_names[key] = bonus["name"].strip()
        bonuses_by_set.setdefault(key, []).append(bonus)

    out = [
        "-- Generated from Adventurer Gauntlet CSV catalogs. Do not edit by hand.",
        "local SETS = {}",
        "local ITEM_TO_SET = {}",
        "",
    ]

    for key in sorted(items_by_set):
        pieces = sorted(items_by_set[key], key=lambda item: int(item["entry"]))
        bonuses = sorted(bonuses_by_set.get(key, []), key=lambda row: int(row["pieces_required"]))
        name = set_names.get(key, key)
        out.append(f"SETS[{lua_string(key)}] = {{")
        out.append(f"    name = {lua_string(name)},")
        out.append("    items = {")
        for piece in pieces:
            out.append(
                f"        {{ id = {int(piece['entry'])}, name = {lua_string(piece['name'].strip())} }},"
            )
        out.append("    },")
        out.append("    bonuses = {")
        for bonus in bonuses:
            text = bonus.get("description", "").strip()
            out.append(
                f"        {{ pieces = {int(bonus['pieces_required'])}, text = {lua_string(text)} }},"
            )
        out.append("    },")
        out.append("}")
        for piece in pieces:
            out.append(f"ITEM_TO_SET[{int(piece['entry'])}] = {lua_string(key)}")
        out.append("")

    out.extend([
        "local function ItemIdFromLink(link)",
        "    if not link then return nil end",
        "    local id = string.match(link, \"item:(%d+)\")",
        "    return id and tonumber(id) or nil",
        "end",
        "",
        "local function EquippedState(set)",
        "    local count = 0",
        "    local equipped = {}",
        "    local members = {}",
        "    for _, piece in ipairs(set.items) do members[piece.id] = true end",
        "    for slot = 1, 19 do",
        "        local id = ItemIdFromLink(GetInventoryItemLink(\"player\", slot))",
        "        if id and members[id] then",
        "            count = count + 1",
        "            equipped[id] = true",
        "        end",
        "    end",
        "    return count, equipped",
        "end",
        "",
        "local function AddGauntletSet(self)",
        "    local _, link = self:GetItem()",
        "    local id = ItemIdFromLink(link)",
        "    local key = id and ITEM_TO_SET[id]",
        "    if not key then return end",
        "    if self.__AdventurerGauntletSetLink == link then return end",
        "    self.__AdventurerGauntletSetLink = link",
        "",
        "    local set = SETS[key]",
        "    local count, equipped = EquippedState(set)",
        "    self:AddLine(\" \" )",
        "    self:AddLine(set.name .. \" (\" .. count .. \"/\" .. #set.items .. \")\", 1.0, 0.82, 0.0)",
        "    for _, piece in ipairs(set.items) do",
        "        if equipped[piece.id] then",
        "            self:AddLine(piece.name, 0.10, 1.00, 0.10)",
        "        else",
        "            self:AddLine(piece.name, 0.50, 0.50, 0.50)",
        "        end",
        "    end",
        "    self:AddLine(\" \" )",
        "    for _, bonus in ipairs(set.bonuses) do",
        "        local line = \"(\" .. bonus.pieces .. \") Bonif.: \" .. bonus.text",
        "        if count >= bonus.pieces then",
        "            self:AddLine(line, 0.10, 1.00, 0.10, true)",
        "        else",
        "            self:AddLine(line, 0.50, 0.50, 0.50, true)",
        "        end",
        "    end",
        "end",
        "",
        "local function ResetGauntletSet(self)",
        "    self.__AdventurerGauntletSetLink = nil",
        "end",
        "",
        "for _, tooltip in ipairs({ GameTooltip, ItemRefTooltip, ShoppingTooltip1, ShoppingTooltip2 }) do",
        "    if tooltip then",
        "        tooltip:HookScript(\"OnTooltipSetItem\", AddGauntletSet)",
        "        tooltip:HookScript(\"OnHide\", ResetGauntletSet)",
        "    end",
        "end",
        "",
    ])
    return "\n".join(out)


def install_addon(client_dir: Path, item_rows: list[dict[str, str]], set_rows: list[dict[str, str]]) -> Path:
    addon_dir = client_dir / "Interface" / "AddOns" / "AdventurerGauntletSets"
    addon_dir.mkdir(parents=True, exist_ok=True)
    toc = """## Interface: 30300
## Title: Adventurer Gauntlet Sets
## Notes: Native-style tooltips for Adventurer Gauntlet equipment sets
## Author: Aventureros de Azeroth
AdventurerGauntletSets.lua
"""
    (addon_dir / "AdventurerGauntletSets.toc").write_text(toc, encoding="utf-8")
    (addon_dir / "AdventurerGauntletSets.lua").write_text(
        build_set_addon(item_rows, set_rows), encoding="utf-8"
    )
    return addon_dir


def clear_item_cache(client_dir: Path) -> None:
    cache_root = client_dir / "Cache" / "WDB"
    if not cache_root.exists():
        return
    for cache in cache_root.glob("*/itemcache.wdb"):
        try:
            cache.unlink()
        except OSError:
            print(f"WARNING: could not remove {cache}; close WoW and delete it before testing")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install Adventurer Gauntlet custom item client metadata")
    parser.add_argument("--items", required=True, type=Path)
    parser.add_argument("--sets", required=True, type=Path)
    parser.add_argument("--dbc-src", required=True, type=Path)
    parser.add_argument("--client-dir", required=True, type=Path)
    parser.add_argument("--locale", default="esMX")
    args = parser.parse_args()

    item_dbc = args.dbc_src / "Item.dbc"
    if not item_dbc.is_file():
        raise SystemExit(f"ERROR: Item.dbc not found: {item_dbc}")
    if not args.client_dir.is_dir():
        raise SystemExit(f"ERROR: client directory not found: {args.client_dir}")

    item_rows = read_rows(args.items)
    set_rows = read_rows(args.sets)
    patched_item = patch_item_dbc(item_dbc, item_rows)
    archive_files = {"DBFilesClient\\Item.dbc": patched_item}

    root_patch = args.client_dir / "Data" / "patch-X.MPQ"
    locale_patch = args.client_dir / "Data" / args.locale / f"patch-{args.locale}-x.MPQ"
    write_mpq(root_patch, archive_files)
    write_mpq(locale_patch, archive_files)
    addon_dir = install_addon(args.client_dir, item_rows, set_rows)
    clear_item_cache(args.client_dir)

    print(f"Gauntlet client Item.dbc rows installed: {len(item_rows)}")
    print(f"Root patch: {root_patch}")
    print(f"Locale patch: {locale_patch}")
    print(f"Set tooltip addon: {addon_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
