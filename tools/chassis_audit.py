#!/usr/bin/env python3
"""Read-only comparison of native WotLK class chassis data from the World DB.

The report reads the same World-DB mirror tables AzerothCore uses for base class
stats and crit/regen curves. It also shows naked HP/mana using the exact WotLK
stamina/intellect rules and, for Adventurer, the zero-armor runtime crit
baseline used by the class-10 core patch: 80% of the best complete native
formula for the Adventurer's current base Agility/Intellect.

Live physical Agility is additionally reduced by the Adventurer armor tradeoff
(half of physical Armor reduction, capped at 30%). This DB-only report does not
know the character's equipped Armor, so its M.Crit value is the zero-armor
baseline rather than the final geared value.

Death Knight has no player_class_stats rows below level 55, but its DBC crit
curves still exist and the runtime class-10 formula evaluates every native DBC
slot. Therefore crit curves are queried independently from player_class_stats so
level-1 audits exactly mirror the base curves instead of failing on the missing
DK stat row.

No database rows are modified.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
import subprocess
import sys

from database import DatabaseError, _run_mysql, read_database_info, resolve_conf, validate_connection


class AuditError(RuntimeError):
    pass


ADVENTURER_CLASS = 10
ADVENTURER_SCALE = 0.80
NATIVE_CLASSES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 11)
ALL_CLASSES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11)
CLASS_NAMES = {
    1: "Warrior",
    2: "Paladin",
    3: "Hunter",
    4: "Rogue",
    5: "Priest",
    6: "DeathKnight",
    7: "Shaman",
    8: "Mage",
    9: "Warlock",
    10: "Adventurer",
    11: "Druid",
}


@dataclass(frozen=True)
class ChassisRow:
    player_class: int
    level: int
    base_hp: int
    base_mana: int
    strength: int
    agility: int
    stamina: int
    intellect: int
    spirit: int
    melee_crit_base: float
    melee_crit_ratio: float
    spell_crit_base: float
    spell_crit_ratio: float
    regen_hp: float
    regen_hp_per_spirit: float
    regen_mp_per_spirit: float


@dataclass(frozen=True)
class CritCurveRow:
    player_class: int
    level: int
    melee_crit_base: float
    melee_crit_ratio: float
    spell_crit_base: float
    spell_crit_ratio: float


def parse_levels(raw: str) -> tuple[int, ...]:
    values: list[int] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            value = int(part)
        except ValueError as exc:
            raise AuditError(f"Invalid level: {part!r}") from exc
        if not 1 <= value <= 80:
            raise AuditError(f"Level out of WotLK range 1-80: {value}")
        if value not in values:
            values.append(value)
    if not values:
        raise AuditError("--levels did not contain any levels")
    return tuple(values)


def health_bonus_from_stamina(stamina: int | float) -> float:
    base = min(float(stamina), 20.0)
    return base + (float(stamina) - base) * 10.0


def mana_bonus_from_intellect(intellect: int | float, base_mana: int | float) -> float:
    if float(base_mana) <= 0.0:
        return 0.0
    base = min(float(intellect), 20.0)
    return base + (float(intellect) - base) * 15.0


def crit_percent(base: float, ratio: float, stat: int | float) -> float:
    return (base + float(stat) * ratio) * 100.0


def query_rows(info, sql: str) -> list[list[str]]:
    try:
        result = _run_mysql(info, (sql.rstrip(";") + ";\n").encode(), capture=True)
    except subprocess.CalledProcessError as exc:
        detail = exc.stderr.decode(errors="replace").strip()
        raise DatabaseError(f"Database query failed: {detail or exc}") from exc
    text = result.stdout.decode("utf-8", errors="strict")
    return [line.split("\t") for line in text.splitlines()] if text else []


def build_query(levels: tuple[int, ...]) -> str:
    level_list = ",".join(str(level) for level in levels)
    class_list = ",".join(str(player_class) for player_class in ALL_CLASSES)
    return f"""
SELECT
    pcs.`Class`, pcs.`Level`, pcs.`BaseHP`, pcs.`BaseMana`,
    pcs.`Strength`, pcs.`Agility`, pcs.`Stamina`, pcs.`Intellect`, pcs.`Spirit`,
    COALESCE(mcb.`Data`, 0), COALESCE(mc.`Data`, 0),
    COALESCE(scb.`Data`, 0), COALESCE(sc.`Data`, 0),
    COALESCE(rh.`Data`, 0), COALESCE(rhs.`Data`, 0), COALESCE(rms.`Data`, 0)
FROM `player_class_stats` pcs
LEFT JOIN `gtchancetomeleecritbase_dbc` mcb
    ON mcb.`ID` = pcs.`Class` - 1
LEFT JOIN `gtchancetomeleecrit_dbc` mc
    ON mc.`ID` = (pcs.`Class` - 1) * 100 + pcs.`Level` - 1
LEFT JOIN `gtchancetospellcritbase_dbc` scb
    ON scb.`ID` = pcs.`Class` - 1
LEFT JOIN `gtchancetospellcrit_dbc` sc
    ON sc.`ID` = (pcs.`Class` - 1) * 100 + pcs.`Level` - 1
LEFT JOIN `gtoctregenhp_dbc` rh
    ON rh.`ID` = (pcs.`Class` - 1) * 100 + pcs.`Level` - 1
LEFT JOIN `gtregenhpperspt_dbc` rhs
    ON rhs.`ID` = (pcs.`Class` - 1) * 100 + pcs.`Level` - 1
LEFT JOIN `gtregenmpperspt_dbc` rms
    ON rms.`ID` = (pcs.`Class` - 1) * 100 + pcs.`Level` - 1
WHERE pcs.`Class` IN ({class_list})
  AND pcs.`Level` IN ({level_list})
ORDER BY pcs.`Level`, pcs.`Class`
""".strip()


def _union_values(values: tuple[int, ...], alias: str) -> str:
    first, *rest = values
    parts = [f"SELECT {first} AS `{alias}`"]
    parts.extend(f"SELECT {value}" for value in rest)
    return "\n        UNION ALL ".join(parts)


def build_native_crit_query(levels: tuple[int, ...]) -> str:
    classes = _union_values(NATIVE_CLASSES, "player_class")
    requested_levels = _union_values(levels, "level")
    return f"""
SELECT
    classes.`player_class`, levels.`level`,
    COALESCE(mcb.`Data`, 0), COALESCE(mc.`Data`, 0),
    COALESCE(scb.`Data`, 0), COALESCE(sc.`Data`, 0)
FROM (
        {classes}
) classes
CROSS JOIN (
        {requested_levels}
) levels
LEFT JOIN `gtchancetomeleecritbase_dbc` mcb
    ON mcb.`ID` = classes.`player_class` - 1
LEFT JOIN `gtchancetomeleecrit_dbc` mc
    ON mc.`ID` = (classes.`player_class` - 1) * 100 + levels.`level` - 1
LEFT JOIN `gtchancetospellcritbase_dbc` scb
    ON scb.`ID` = classes.`player_class` - 1
LEFT JOIN `gtchancetospellcrit_dbc` sc
    ON sc.`ID` = (classes.`player_class` - 1) * 100 + levels.`level` - 1
ORDER BY levels.`level`, classes.`player_class`
""".strip()


def parse_row(raw: list[str]) -> ChassisRow:
    if len(raw) != 16:
        raise AuditError(f"Expected 16 columns from chassis query, got {len(raw)}")
    return ChassisRow(
        player_class=int(raw[0]),
        level=int(raw[1]),
        base_hp=int(raw[2]),
        base_mana=int(raw[3]),
        strength=int(raw[4]),
        agility=int(raw[5]),
        stamina=int(raw[6]),
        intellect=int(raw[7]),
        spirit=int(raw[8]),
        melee_crit_base=float(raw[9]),
        melee_crit_ratio=float(raw[10]),
        spell_crit_base=float(raw[11]),
        spell_crit_ratio=float(raw[12]),
        regen_hp=float(raw[13]),
        regen_hp_per_spirit=float(raw[14]),
        regen_mp_per_spirit=float(raw[15]),
    )


def parse_crit_curve_row(raw: list[str]) -> CritCurveRow:
    if len(raw) != 6:
        raise AuditError(f"Expected 6 columns from native crit query, got {len(raw)}")
    return CritCurveRow(
        player_class=int(raw[0]),
        level=int(raw[1]),
        melee_crit_base=float(raw[2]),
        melee_crit_ratio=float(raw[3]),
        spell_crit_base=float(raw[4]),
        spell_crit_ratio=float(raw[5]),
    )


def adventurer_runtime_crits(row: ChassisRow, crit_rows: list[CritCurveRow]) -> tuple[float, float]:
    native = [candidate for candidate in crit_rows if candidate.level == row.level]
    found_classes = {candidate.player_class for candidate in native}
    if found_classes != set(NATIVE_CLASSES):
        missing = sorted(set(NATIVE_CLASSES) - found_classes)
        raise AuditError(
            f"Level {row.level} is missing native DBC crit curve(s) required for runtime comparison: {missing}"
        )
    melee = max(
        crit_percent(candidate.melee_crit_base, candidate.melee_crit_ratio, row.agility)
        for candidate in native
    ) * ADVENTURER_SCALE
    spell = max(
        crit_percent(candidate.spell_crit_base, candidate.spell_crit_ratio, row.intellect)
        for candidate in native
    ) * ADVENTURER_SCALE
    return melee, spell


def derived_values(row: ChassisRow, crit_rows: list[CritCurveRow]) -> dict[str, float]:
    hp = row.base_hp + health_bonus_from_stamina(row.stamina)
    mana = row.base_mana + mana_bonus_from_intellect(row.intellect, row.base_mana)
    melee_dbc = crit_percent(row.melee_crit_base, row.melee_crit_ratio, row.agility)
    spell_dbc = crit_percent(row.spell_crit_base, row.spell_crit_ratio, row.intellect)
    melee_runtime = melee_dbc
    spell_runtime = spell_dbc
    if row.player_class == ADVENTURER_CLASS:
        melee_runtime, spell_runtime = adventurer_runtime_crits(row, crit_rows)
    return {
        "hp": hp,
        "mana": mana,
        "melee_dbc": melee_dbc,
        "spell_dbc": spell_dbc,
        "melee_runtime": melee_runtime,
        "spell_runtime": spell_runtime,
    }


def format_table(rows: list[ChassisRow], crit_rows: list[CritCurveRow], level: int) -> str:
    level_rows = [row for row in rows if row.level == level]
    if not level_rows:
        return f"LEVEL {level}: no rows found"

    header = (
        f"{'Class':<12} {'HP':>6} {'Mana':>6} {'STR':>4} {'AGI':>4} {'STA':>4} "
        f"{'INT':>4} {'SPI':>4} {'M.Crit':>7} {'S.Crit':>7} {'M.DBC':>7} {'S.DBC':>7} "
        f"{'HPReg':>9} {'HP/SPI':>9} {'MP/SPI':>9}"
    )
    lines = [f"LEVEL {level}", header, "-" * len(header)]
    for row in level_rows:
        derived = derived_values(row, crit_rows)
        lines.append(
            f"{CLASS_NAMES.get(row.player_class, str(row.player_class)):<12} "
            f"{derived['hp']:>6.0f} {derived['mana']:>6.0f} "
            f"{row.strength:>4} {row.agility:>4} {row.stamina:>4} {row.intellect:>4} {row.spirit:>4} "
            f"{derived['melee_runtime']:>6.2f}% {derived['spell_runtime']:>6.2f}% "
            f"{derived['melee_dbc']:>6.2f}% {derived['spell_dbc']:>6.2f}% "
            f"{row.regen_hp:>9.6f} {row.regen_hp_per_spirit:>9.6f} {row.regen_mp_per_spirit:>9.6f}"
        )
    return "\n".join(lines)


def load_rows(
    core: Path, explicit_conf: Path | None, levels: tuple[int, ...]
) -> tuple[Path, object, list[ChassisRow], list[CritCurveRow]]:
    conf = resolve_conf(core, explicit_conf)
    world = read_database_info(conf, "WorldDatabaseInfo")
    validate_connection(world)
    raw_rows = query_rows(world, build_query(levels))
    rows = [parse_row(raw) for raw in raw_rows]
    if not rows:
        raise AuditError("World DB returned no player_class_stats rows for the requested levels")

    raw_crit_rows = query_rows(world, build_native_crit_query(levels))
    crit_rows = [parse_crit_curve_row(raw) for raw in raw_crit_rows]
    expected = len(NATIVE_CLASSES) * len(levels)
    if len(crit_rows) != expected:
        raise AuditError(
            f"World DB returned {len(crit_rows)} native crit curve rows; expected {expected}"
        )
    return conf, world, rows, crit_rows


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(
        prog="chassis_audit.py",
        description="Read-only native-vs-Adventurer chassis table from the AzerothCore World DB",
    )
    result.add_argument("--core-dir", required=True, type=Path)
    result.add_argument("--levels", default="1", help="comma-separated WotLK levels, e.g. 1,10,20,40,60,80")
    result.add_argument("--worldserver-conf", type=Path)
    return result


def main() -> int:
    args = parser().parse_args()
    try:
        levels = parse_levels(args.levels)
        conf, world, rows, crit_rows = load_rows(
            args.core_dir.expanduser().resolve(), args.worldserver_conf, levels
        )
        print("Adventurer chassis audit (read-only)")
        print(f"config: {conf}")
        print(f"world DB: {world.database}")
        print("M.Crit/S.Crit = zero-armor runtime baseline; M.DBC/S.DBC = this class's DB slot formula.")
        print("For native classes those pairs are equal. Adventurer physical crit is further reduced by equipped Armor at runtime.")
        print("Death Knight has no stat row below 55; its DBC crit curve is still included in Adventurer runtime comparisons.")
        print()
        for index, level in enumerate(levels):
            if index:
                print()
            print(format_table(rows, crit_rows, level))
        return 0
    except (AuditError, DatabaseError, OSError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())