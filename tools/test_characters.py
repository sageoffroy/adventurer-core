#!/usr/bin/env python3
"""Create disposable native-class stat probes in an existing Adventurer account.

These are deliberately minimal level-1 characters for paper-doll stat auditing,
not fully initialized playable characters.  They reuse the template character's
account/location/home bind, contain no cloned Adventurer gear/spells/talents, and
only receive Defense 5/5 so dodge is not distorted by a missing defense skill.

Run with worldserver stopped.  After probes have been logged into, remove them
through the normal character-delete flow (or AzerothCore's character erase
command), because a login may create additional character-owned rows.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import re
import subprocess
import sys

from database import (
    DatabaseError,
    _run_mysql,
    query_scalar,
    read_database_info,
    resolve_conf,
    validate_connection,
)


class ProbeError(RuntimeError):
    pass


MAX_CHARACTERS_PER_ACCOUNT = 10
DEFENSE_SKILL_ID = 95


@dataclass(frozen=True)
class Probe:
    key: str
    name: str
    race: int
    player_class: int
    label: str


# Alliance race/class pairs keep every probe on the same faction as the Human
# Adventurer template.  Death Knight is intentionally omitted: its native class
# baseline starts at level 55 and is not a valid level-1 comparison.
PROBES: tuple[Probe, ...] = (
    Probe("warrior", "Statwar", 1, 1, "Human Warrior"),
    Probe("paladin", "Statpal", 1, 2, "Human Paladin"),
    Probe("hunter", "Stathunt", 3, 3, "Dwarf Hunter"),
    Probe("rogue", "Statrog", 1, 4, "Human Rogue"),
    Probe("priest", "Statpri", 1, 5, "Human Priest"),
    Probe("shaman", "Statsha", 11, 7, "Draenei Shaman"),
    Probe("mage", "Statmag", 1, 8, "Human Mage"),
    Probe("warlock", "Statlock", 1, 9, "Human Warlock"),
    Probe("druid", "Statdru", 4, 11, "Night Elf Druid"),
)

PROBE_BY_KEY = {probe.key: probe for probe in PROBES}
PROBE_NAMES = tuple(probe.name for probe in PROBES)


RESET_ZERO = {
    "xp",
    "money",
    "skin",
    "face",
    "hairStyle",
    "hairColor",
    "facialStyle",
    "bankSlots",
    "restState",
    "playerFlags",
    "instance_id",
    "instance_mode_mask",
    "online",
    "totaltime",
    "leveltime",
    "logout_time",
    "is_logout_resting",
    "rest_bonus",
    "resettalents_cost",
    "resettalents_time",
    "trans_x",
    "trans_y",
    "trans_z",
    "trans_o",
    "transguid",
    "extra_flags",
    "stable_slots",
    "at_login",
    "death_expire_time",
    "arenaPoints",
    "totalHonorPoints",
    "todayHonorPoints",
    "yesterdayHonorPoints",
    "totalKills",
    "todayKills",
    "yesterdayKills",
    "chosenTitle",
    "knownCurrencies",
    "watchedFaction",
    "drunk",
    "power1",
    "power2",
    "power3",
    "power4",
    "power5",
    "power6",
    "power7",
    "latency",
    "activeTalentGroup",
    "ammoId",
    "actionBars",
    "grantableLevels",
    "extraBonusTalentCount",
}

RESET_EMPTY = {"exploredZones", "equipmentCache", "knownTitles"}
RESET_NULL = {"taxi_path", "order", "deleteInfos_Account", "deleteInfos_Name", "deleteDate"}


def sql_string(value: str) -> str:
    return "'" + value.replace("\\", "\\\\").replace("'", "''") + "'"


def query_rows(info, sql: str) -> list[list[str]]:
    try:
        result = _run_mysql(info, (sql.rstrip(";") + ";\n").encode(), capture=True)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        raise DatabaseError(f"Database query failed: {detail or exc}") from exc
    text = result.stdout.decode("utf-8", errors="strict")
    if not text:
        return []
    return [line.split("\t") for line in text.splitlines()]


def worldserver_running(proc_root: Path = Path("/proc")) -> bool:
    try:
        candidates = proc_root.iterdir()
    except OSError:
        return False
    for entry in candidates:
        if not entry.name.isdigit():
            continue
        comm = entry / "comm"
        try:
            if comm.read_text(encoding="utf-8").strip() == "worldserver":
                return True
        except (OSError, UnicodeDecodeError):
            continue
    return False


def select_probes(raw: str | None) -> tuple[Probe, ...]:
    if raw is None or not raw.strip():
        return PROBES
    keys = [part.strip().lower() for part in raw.split(",") if part.strip()]
    if not keys:
        raise ProbeError("--classes did not contain any class names")
    unknown = [key for key in keys if key not in PROBE_BY_KEY]
    if unknown:
        raise ProbeError(
            "Unknown probe class(es): "
            + ", ".join(unknown)
            + ". Valid: "
            + ", ".join(PROBE_BY_KEY)
        )
    if len(set(keys)) != len(keys):
        raise ProbeError("--classes contains duplicate class names")
    return tuple(PROBE_BY_KEY[key] for key in keys)


def character_columns(info) -> list[str]:
    rows = query_rows(info, "SHOW COLUMNS FROM `characters`")
    columns = [row[0] for row in rows if row]
    required = {"guid", "account", "name", "race", "class", "gender", "level", "health"}
    missing = required.difference(columns)
    if missing:
        raise ProbeError("characters table is missing required columns: " + ", ".join(sorted(missing)))
    return columns


def probe_expression(column: str, probe: Probe, guid: int) -> str:
    overrides = {
        "guid": str(guid),
        "name": sql_string(probe.name),
        "race": str(probe.race),
        "class": str(probe.player_class),
        "gender": "0",
        "level": "1",
        "health": "1",
        "cinematic": "1",
        "talentGroupsCount": "1",
        "creation_date": "CURRENT_TIMESTAMP",
    }
    if column in overrides:
        return overrides[column]
    if column in RESET_ZERO:
        return "0"
    if column in RESET_EMPTY:
        return "''"
    if column in RESET_NULL:
        return "NULL"
    return f"`{column}`"


def build_character_insert(columns: list[str], probe: Probe, guid: int, template_guid: int) -> str:
    names = ", ".join(f"`{column}`" for column in columns)
    values = ", ".join(probe_expression(column, probe, guid) for column in columns)
    return (
        f"INSERT INTO `characters` ({names})\n"
        f"SELECT {values}\n"
        f"FROM `characters` WHERE `guid` = {template_guid};"
    )


def build_probe_transaction(
    columns: list[str], probes: tuple[Probe, ...], first_guid: int, template_guid: int
) -> str:
    statements = ["START TRANSACTION;"]
    for offset, probe in enumerate(probes):
        guid = first_guid + offset
        statements.append(build_character_insert(columns, probe, guid, template_guid))
        statements.append(
            "INSERT INTO `character_homebind` (`guid`, `mapId`, `zoneId`, `posX`, `posY`, `posZ`)\n"
            f"SELECT {guid}, `mapId`, `zoneId`, `posX`, `posY`, `posZ`\n"
            f"FROM `character_homebind` WHERE `guid` = {template_guid};"
        )
        statements.append(
            "INSERT INTO `character_skills` (`guid`, `skill`, `value`, `max`) "
            f"VALUES ({guid}, {DEFENSE_SKILL_ID}, 5, 5);"
        )
    statements.append("COMMIT;")
    return "\n\n".join(statements) + "\n"


def resolve_character_db(core: Path, explicit_conf: Path | None):
    conf = resolve_conf(core, explicit_conf)
    return conf, read_database_info(conf, "CharacterDatabaseInfo")


def find_template(info, name: str) -> tuple[int, int, int]:
    if not re.fullmatch(r"[A-Za-z]{2,12}", name):
        raise ProbeError("Template name must be 2-12 ASCII letters")
    rows = query_rows(
        info,
        "SELECT `guid`, `account`, `level` FROM `characters` "
        f"WHERE BINARY `name` = {sql_string(name)} AND `deleteDate` IS NULL",
    )
    if len(rows) != 1:
        raise ProbeError(f"Expected exactly one active template named {name!r}, found {len(rows)}")
    return int(rows[0][0]), int(rows[0][1]), int(rows[0][2])


def ensure_probe_names_free(info, probes: tuple[Probe, ...]) -> None:
    quoted = ", ".join(sql_string(probe.name) for probe in probes)
    rows = query_rows(
        info,
        f"SELECT `name`, `guid` FROM `characters` WHERE `name` IN ({quoted}) AND `deleteDate` IS NULL",
    )
    if rows:
        detail = ", ".join(f"{row[0]}(guid={row[1]})" for row in rows)
        raise ProbeError(f"Probe character name(s) already exist: {detail}")


def cmd_create(args) -> None:
    if worldserver_running():
        raise ProbeError("worldserver is running. Stop it before creating DB stat probes")

    core = args.core_dir.expanduser().resolve()
    probes = select_probes(args.classes)
    conf, characters = resolve_character_db(core, args.worldserver_conf)
    validate_connection(characters)

    template_guid, account_id, template_level = find_template(characters, args.template)
    if template_level != 1:
        raise ProbeError(
            f"Template {args.template!r} is level {template_level}; use a level-1 template for this audit"
        )

    homebind_count = int(
        query_scalar(characters, f"SELECT COUNT(*) FROM `character_homebind` WHERE `guid` = {template_guid}")
    )
    if homebind_count != 1:
        raise ProbeError(
            f"Template {args.template!r} must have exactly one home bind, found {homebind_count}"
        )

    ensure_probe_names_free(characters, probes)
    active_count = int(
        query_scalar(
            characters,
            f"SELECT COUNT(*) FROM `characters` WHERE `account` = {account_id} AND `deleteDate` IS NULL",
        )
    )
    if active_count + len(probes) > MAX_CHARACTERS_PER_ACCOUNT:
        available = MAX_CHARACTERS_PER_ACCOUNT - active_count
        raise ProbeError(
            f"Account {account_id} has {active_count} active characters; only {available} probe slot(s) remain. "
            "Use --classes with a smaller comma-separated subset."
        )

    columns = character_columns(characters)
    first_guid = int(query_scalar(characters, "SELECT COALESCE(MAX(`guid`), 0) + 1 FROM `characters`"))
    sql = build_probe_transaction(columns, probes, first_guid, template_guid)

    try:
        _run_mysql(characters, sql.encode())
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        raise ProbeError(f"Failed to create stat probes: {detail or exc}") from exc

    print("Native class stat probes created.")
    print(f"  config:   {conf}")
    print(f"  account:  {account_id}")
    print(f"  template: {args.template} (guid {template_guid})")
    for offset, probe in enumerate(probes):
        print(f"  {probe.name:<8} guid={first_guid + offset:<6} {probe.label}")
    print("  purpose: paper-doll stat audit only; no cloned gear/spells/talents")
    print("  cleanup: delete probes normally after testing")


def cmd_list(args) -> None:
    core = args.core_dir.expanduser().resolve()
    _conf, characters = resolve_character_db(core, args.worldserver_conf)
    validate_connection(characters)
    quoted = ", ".join(sql_string(name) for name in PROBE_NAMES)
    rows = query_rows(
        characters,
        "SELECT `guid`, `account`, `name`, `race`, `class`, `level`, `online` "
        f"FROM `characters` WHERE `name` IN ({quoted}) AND `deleteDate` IS NULL ORDER BY `guid`",
    )
    if not rows:
        print("No active Adventurer stat probes found.")
        return
    print("guid\taccount\tname\trace\tclass\tlevel\tonline")
    for row in rows:
        print("\t".join(row))


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(prog="test_characters.py")
    sub = result.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="create disposable native-class level-1 stat probes")
    create.add_argument("--core-dir", required=True, type=Path)
    create.add_argument("--template", required=True)
    create.add_argument(
        "--classes",
        help="comma-separated subset; default: warrior,paladin,hunter,rogue,priest,shaman,mage,warlock,druid",
    )
    create.add_argument("--worldserver-conf", type=Path)

    listing = sub.add_parser("list", help="list active stat probes")
    listing.add_argument("--core-dir", required=True, type=Path)
    listing.add_argument("--worldserver-conf", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        if args.command == "create":
            cmd_create(args)
        else:
            cmd_list(args)
        return 0
    except (ProbeError, DatabaseError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
