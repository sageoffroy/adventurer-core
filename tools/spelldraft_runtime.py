#!/usr/bin/env python3
"""Install editable SpellDraft runtime data beside AzerothCore's server data.

The packaged cards.csv is the stable structural catalog (card IDs, bundles and
ability dependencies). catalog_metadata.csv is exported from the design sheet
and is authoritative for active-card rarity/availability and ability-to-talent
relationships. During install, Talent.dbc supplies the real WotLK talent rank
chains, so the live cards.csv can be rebuilt without hardcoding talent ranks.

subclasses.json is the single classification source for the Adventurer's four
spell/talent families. Runtime generation emits card_subclasses.csv beside the
normal 12-column cards.csv, keeping the stable SpellDraft parser contract intact.

cards.csv remains file-managed: package updates advance it while unedited and
preserve it wholesale after a real local edit. spelldraft.conf is merged
option-by-option against the previous packaged .dist.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import shutil
import struct
from pathlib import Path

from subclasses import (
    SubclassError,
    choose_synthetic_talent_subclass,
    load_spec as load_subclass_spec,
    talent_override_map,
    validate_card_coverage,
)

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "config" / "spelldraft"
FILES = (
    "spelldraft.conf",
    "cards.csv",
    "catalog_metadata.csv",
    "subclasses.json",
    "card_subclasses.csv",
)
MARKER_SUFFIX = ".managed.sha256"
SYNTHETIC_TALENT_CARD_BASE = 1_000_000
VALID_RARITIES = {"common", "uncommon", "rare", "epic", "legendary"}

# Exact SHA-256 values of packaged files shipped before managed markers existed.
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


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def resolve_data_dir(core: Path, server_data_dir: Path | None) -> Path:
    if server_data_dir:
        return server_data_dir.expanduser().resolve()
    return (core.expanduser().resolve() / "env" / "dist" / "data").resolve()


def resolve_talent_dbc(core: Path, server_data_dir: Path | None, dbc_src: Path | None) -> Path | None:
    candidates: list[Path] = []
    if dbc_src:
        candidates.append(dbc_src.expanduser().resolve() / "Talent.dbc")
    data_dir = resolve_data_dir(core, server_data_dir)
    candidates.append(data_dir / "dbc" / "Talent.dbc")
    candidates.append(core.expanduser().resolve() / "env" / "dist" / "data" / "dbc" / "Talent.dbc")
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


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
        left, _ = raw.split("=", 1)
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


def parse_talent_dbc(path: Path) -> dict[int, list[int]]:
    data = path.read_bytes()
    if len(data) < 20:
        raise SpellDraftRuntimeError(f"Talent.dbc is too small: {path}")
    magic, record_count, field_count, record_size, string_size = struct.unpack_from("<4s4I", data, 0)
    if magic != b"WDBC":
        raise SpellDraftRuntimeError(f"Unsupported Talent.dbc header {magic!r}: {path}")
    if field_count < 9 or record_size < field_count * 4:
        raise SpellDraftRuntimeError(f"Unexpected Talent.dbc layout: fields={field_count} record_size={record_size}")
    records_end = 20 + record_count * record_size
    if records_end + string_size > len(data):
        raise SpellDraftRuntimeError(f"Truncated Talent.dbc: {path}")

    result: dict[int, list[int]] = {}
    for index in range(record_count):
        offset = 20 + index * record_size
        fields = struct.unpack_from(f"<{field_count}I", data, offset)
        ranks = [spell_id for spell_id in fields[4:9] if spell_id]
        if ranks:
            # Design sheets are maintained by spell ID and may reference any
            # rank of a native WotLK talent. Make every rank an alias of the
            # canonical first-rank chain so those references are normalized
            # instead of silently discarded.
            for spell_id in ranks:
                result[spell_id] = ranks
    return result


def parse_catalog_metadata(text: str) -> dict[int, dict[str, object]]:
    rows = csv.DictReader(io.StringIO(text), delimiter=";")
    expected = {"spell_id", "rarity", "talent_spells"}
    if rows.fieldnames is None or not expected.issubset(rows.fieldnames):
        raise SpellDraftRuntimeError("catalog_metadata.csv has unexpected header")

    result: dict[int, dict[str, object]] = {}
    for row in rows:
        try:
            spell_id = int((row.get("spell_id") or "").strip())
        except ValueError as exc:
            raise SpellDraftRuntimeError("catalog_metadata.csv contains invalid spell_id") from exc
        if not spell_id or spell_id in result:
            raise SpellDraftRuntimeError(f"catalog_metadata.csv contains invalid/duplicate spell_id {spell_id}")
        rarity = (row.get("rarity") or "").strip().lower()
        if rarity and rarity != "unavailable" and rarity not in VALID_RARITIES:
            raise SpellDraftRuntimeError(f"catalog_metadata.csv has invalid rarity {rarity!r} for spell {spell_id}")
        talent_spells: list[int] = []
        for raw in (row.get("talent_spells") or "").split(","):
            raw = raw.strip()
            if not raw:
                continue
            try:
                talent_spells.append(int(raw))
            except ValueError as exc:
                raise SpellDraftRuntimeError(f"invalid talent spell {raw!r} for spell {spell_id}") from exc
        result[spell_id] = {"rarity": rarity, "talent_spells": talent_spells}
    return result


def split_grant_spells(rank_grants: str) -> list[int]:
    result: list[int] = []
    for rank in rank_grants.split("/"):
        for raw in rank.split("+"):
            raw = raw.strip()
            if raw:
                result.append(int(raw))
    return result


def render_cards(rows: list[dict[str, str]], fieldnames: list[str]) -> str:
    output = io.StringIO(newline="")
    writer = csv.DictWriter(output, fieldnames=fieldnames, delimiter=";", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def build_runtime_cards(base_text: str, metadata_text: str, talent_ranks: dict[int, list[int]]) -> tuple[str, list[int]]:
    reader = csv.DictReader(io.StringIO(base_text), delimiter=";")
    fieldnames = reader.fieldnames
    if fieldnames is None or len(fieldnames) != 12 or fieldnames[0] != "id" or "rank_grants" not in fieldnames:
        raise SpellDraftRuntimeError("cards.csv has unexpected header")
    rows = [dict(row) for row in reader]
    metadata = parse_catalog_metadata(metadata_text)

    active_rows: list[dict[str, str]] = []
    explicit_talents: list[dict[str, str]] = []
    active_by_granted_spell: dict[int, set[int]] = {}

    for row in rows:
        if row["type"] == "active":
            spells = split_grant_spells(row["rank_grants"])
            if not spells:
                raise SpellDraftRuntimeError(f"active card {row['id']} has no grants")
            primary_meta = metadata.get(spells[0])
            if primary_meta and primary_meta["rarity"] == "unavailable":
                continue
            if primary_meta and primary_meta["rarity"]:
                row["rarity"] = str(primary_meta["rarity"])
            active_rows.append(row)
            card_id = int(row["id"])
            for spell_id in spells:
                active_by_granted_spell.setdefault(spell_id, set()).add(card_id)
        elif row["type"] == "talent":
            explicit_talents.append(row)
        else:
            raise SpellDraftRuntimeError(f"unknown card type {row['type']!r}")

    talent_sources: dict[int, set[int]] = {}
    for spell_id, card_ids in active_by_granted_spell.items():
        meta = metadata.get(spell_id)
        if not meta:
            continue
        for talent_spell in meta["talent_spells"]:
            ranks = talent_ranks.get(talent_spell)
            if ranks:
                talent_sources.setdefault(ranks[0], set()).update(card_ids)

    explicit_by_first: dict[int, dict[str, str]] = {}
    for row in explicit_talents:
        grants = split_grant_spells(row["rank_grants"])
        if not grants:
            raise SpellDraftRuntimeError(f"talent card {row['id']} has no grants")
        first_spell = grants[0]
        explicit_by_first[first_spell] = row
        sources = talent_sources.get(first_spell)
        if sources:
            row["requires_all"] = ""
            row["requires_any"] = "|".join(f"{card_id}:1" for card_id in sorted(sources))

    synthetic: list[dict[str, str]] = []
    used_card_ids = {int(row["id"]) for row in rows}
    for first_spell in sorted(talent_sources):
        if first_spell in explicit_by_first:
            continue
        ranks = talent_ranks[first_spell]
        card_id = SYNTHETIC_TALENT_CARD_BASE + first_spell
        if card_id in used_card_ids:
            raise SpellDraftRuntimeError(f"synthetic talent card id collision: {card_id}")
        used_card_ids.add(card_id)
        sources = sorted(talent_sources[first_spell])
        synthetic.append({
            "id": str(card_id),
            "key": f"talent_{first_spell}",
            "type": "talent",
            "source_level": "5",
            "rarity": "common",
            "weight": "100",
            "rank_grants": "/".join(str(spell_id) for spell_id in ranks),
            "requires_all": "",
            "requires_any": "|".join(f"{source}:1" for source in sources),
            "unlocks": "",
            "replaces_previous": "1",
            "name": f"Talent {first_spell}",
        })

    output_rows = active_rows + explicit_talents + synthetic
    if not active_rows or not explicit_talents:
        raise SpellDraftRuntimeError("generated cards catalog unexpectedly empty")
    ignored = sorted({
        talent_spell
        for meta in metadata.values()
        for talent_spell in meta["talent_spells"]
        if talent_spell not in talent_ranks
    })
    return render_cards(output_rows, fieldnames), ignored


def parse_requirement_card_ids(raw: str) -> list[int]:
    result: list[int] = []
    for item in raw.split("|"):
        item = item.strip()
        if not item:
            continue
        card_id, _, _rank = item.partition(":")
        if not card_id:
            continue
        result.append(int(card_id))
    return result


def build_runtime_subclasses(
    generated_cards_text: str,
    base_cards_text: str,
    subclass_spec: dict,
) -> str:
    try:
        base_classes = validate_card_coverage(base_cards_text, subclass_spec)
    except SubclassError as exc:
        raise SpellDraftRuntimeError(str(exc)) from exc
    overrides = talent_override_map(subclass_spec)

    output = io.StringIO(newline="")
    writer = csv.DictWriter(
        output,
        fieldnames=["card_id", "subclass"],
        delimiter=";",
        lineterminator="\n",
    )
    writer.writeheader()

    seen: set[int] = set()
    for row in csv.DictReader(io.StringIO(generated_cards_text), delimiter=";"):
        card_id = int(row["id"])
        if card_id in seen:
            raise SpellDraftRuntimeError(f"duplicate generated card id {card_id}")
        seen.add(card_id)

        subclass = base_classes.get(card_id)
        if subclass is None:
            if row["type"] != "talent":
                raise SpellDraftRuntimeError(f"generated active card {card_id} has no subclass")
            grants = split_grant_spells(row["rank_grants"])
            if not grants:
                raise SpellDraftRuntimeError(f"generated talent {card_id} has no ranks")
            sources = parse_requirement_card_ids(row["requires_any"])
            try:
                subclass = choose_synthetic_talent_subclass(
                    grants[0], sources, base_classes, overrides
                )
            except SubclassError as exc:
                raise SpellDraftRuntimeError(str(exc)) from exc

        writer.writerow({"card_id": str(card_id), "subclass": subclass})
    return output.getvalue()


def build_packaged_files(core: Path, server_data_dir: Path | None, dbc_src: Path | None) -> tuple[dict[str, bytes], list[int]]:
    files = {
        "spelldraft.conf": (SOURCE / "spelldraft.conf").read_bytes(),
        "catalog_metadata.csv": (SOURCE / "catalog_metadata.csv").read_bytes(),
        "subclasses.json": (SOURCE / "subclasses.json").read_bytes(),
    }
    base_cards = (SOURCE / "cards.csv").read_text(encoding="utf-8")
    metadata_text = files["catalog_metadata.csv"].decode("utf-8")
    subclass_spec = load_subclass_spec(SOURCE / "subclasses.json")
    talent_dbc = resolve_talent_dbc(core, server_data_dir, dbc_src)
    if talent_dbc is None:
        raise SpellDraftRuntimeError("Talent.dbc not found; pass --dbc-src pointing to the WotLK DBC directory")
    generated_cards, ignored = build_runtime_cards(base_cards, metadata_text, parse_talent_dbc(talent_dbc))
    files["cards.csv"] = generated_cards.encode("utf-8")
    files["card_subclasses.csv"] = build_runtime_subclasses(
        generated_cards, base_cards, subclass_spec
    ).encode("utf-8")
    return files, ignored


def install(core: Path, server_data_dir: Path | None, dbc_src: Path | None = None) -> None:
    data_dir = resolve_data_dir(core, server_data_dir)
    if not data_dir.is_dir():
        raise SpellDraftRuntimeError(f"Server data directory not found: {data_dir}")
    target = data_dir / "spelldraft"
    target.mkdir(parents=True, exist_ok=True)

    # Unit tests and legacy helper callers can use a minimal SOURCE without the
    # design metadata. Real package installs always have catalog_metadata.csv.
    metadata_source = SOURCE / "catalog_metadata.csv"
    if metadata_source.is_file():
        packaged, ignored_talents = build_packaged_files(core, server_data_dir, dbc_src)
    else:
        packaged = {name: (SOURCE / name).read_bytes() for name in ("spelldraft.conf", "cards.csv")}
        ignored_talents = []

    created: list[str] = []
    updated: list[str] = []
    migrated: list[str] = []
    merged: list[str] = []
    preserved: list[str] = []

    for name, source_bytes in packaged.items():
        live = target / name
        dist = target / f"{name}.dist"
        marker = marker_path(target, name)
        source_hash = sha256_bytes(source_bytes)
        previous_dist_hash = sha256(dist) if dist.is_file() else None
        managed_hash = read_marker(marker)

        if live.exists() and not live.is_file():
            raise SpellDraftRuntimeError(f"Runtime path is not a file: {live}")

        if not live.exists():
            live.write_bytes(source_bytes)
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
                    live.write_bytes(source_bytes)
                    (migrated if legacy_migration else updated).append(name)
                write_marker(marker, source_hash)
            elif name == "spelldraft.conf":
                source_text = source_bytes.decode("utf-8")
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

        dist.write_bytes(source_bytes)

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
    if ignored_talents:
        print("  ignored non-talent K ids: " + ", ".join(str(value) for value in ignored_talents))
    print("  packaged defaults: " + ", ".join(f"{name}.dist" for name in packaged))


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
        command.add_argument("--dbc-src", type=Path)
    return result


def main() -> int:
    args, _ = parser().parse_known_args()
    try:
        if args.command == "install":
            install(args.core_dir, args.server_data_dir, args.dbc_src)
        else:
            remove(args.core_dir, args.server_data_dir)
        return 0
    except (SpellDraftRuntimeError, SubclassError, OSError, UnicodeError, ValueError, struct.error) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
