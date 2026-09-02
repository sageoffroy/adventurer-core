#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

HEADERS = [
    "enabled","entry","source_entry","display_id","set_key","name","quality","required_level","item_level",
    "strength","agility","stamina","intellect","spirit","attack_power","spell_power","hit_rating","crit_rating",
    "haste_rating","armor","block","dmg_min1","dmg_max1","delay","equip_spell1","equip_spell2","description",
]
SET_HEADERS = ["enabled","set_key","name","pieces_required","bonus_type","value","spell_id","description"]

SOURCES = {
    "sword1h":25, "sword2h":4939, "dagger":4947, "rare_dagger":1917,
    "mace1h":4948, "mace2h":1195, "axe1h":37, "bow":4763,
    "crossbow":27401, "staff":9514, "shield":7108, "cloak":1372,
    "leather_chest":85, "leather_gloves":2125, "leather_belt":2122,
    "mail_chest":2392, "mail_gloves":2397, "mail_belt":2393,
    "cloth_gloves":2119, "cloth_belt":3599,
}

PIECE_NAMES = {
    "sword2h":"Mandoble", "mace2h":"Gran maza", "sword1h":"Espada", "mace1h":"Maza", "axe1h":"Hacha",
    "shield":"Escudo", "mail_chest":"Coselete", "mail_gloves":"Guanteletes", "mail_belt":"Cinturon",
    "leather_chest":"Jubon", "leather_gloves":"Guantes", "leather_belt":"Cinturon",
    "cloth_gloves":"Guantes", "cloth_belt":"Faja", "cloak":"Capa", "dagger":"Daga", "rare_dagger":"Daga",
    "bow":"Arco", "crossbow":"Ballesta", "staff":"Baston",
}

SETS = [
    ("juramento_coloso","Juramento del Coloso",3,"strength",["sword2h","mail_chest","mail_gloves","mail_belt","cloak"]),
    ("martillo_ceniza","Martillo de Ceniza",5,"strength",["mace2h","mail_chest","mail_gloves","mail_belt","cloak"]),
    ("hoja_errante","Hoja Errante",8,"agility",["sword2h","leather_chest","leather_gloves","leather_belt","cloak"]),
    ("quebrantahuesos","Quebrantahuesos",12,"strength",["mace2h","leather_chest","leather_gloves","leather_belt","cloak"]),
    ("vigilia_titan","Vigilia del Titan",16,"strength",["sword2h","mail_chest","mail_gloves","mail_belt","cloak"]),
    ("guardia_alba","Guardia del Alba",3,"strength",["sword1h","shield","mail_chest","mail_gloves","mail_belt"]),
    ("muro_viajero","Muro del Viajero",8,"strength",["sword1h","shield","leather_chest","leather_gloves","leather_belt"]),
    ("cuero_oso","Cuero de Oso",3,"agility",["leather_chest","leather_gloves","leather_belt","cloak","dagger"]),
    ("colmillo_niebla","Colmillo de Niebla",5,"agility",["leather_chest","leather_gloves","leather_belt","cloak","dagger"]),
    ("cazador_sombra","Cazador de Sombras",8,"agility",["leather_chest","leather_gloves","leather_belt","cloak","bow"]),
    ("vigia_bosque","Vigia del Bosque",12,"agility",["leather_chest","leather_gloves","leather_belt","cloak","bow"]),
    ("tejedor_runas","Tejedor de Runas",16,"caster",["cloth_gloves","cloth_belt","cloak","dagger","leather_chest"]),
    ("sabio_viajero","Sabio del Viajero",20,"caster",["cloth_gloves","cloth_belt","cloak","dagger","leather_chest"]),
    ("malla_tormenta","Malla de Tormenta",25,"strength",["mail_chest","mail_gloves","mail_belt","cloak","sword1h"]),
    ("malla_grifo","Malla del Grifo",30,"agility",["mail_chest","mail_gloves","mail_belt","cloak","bow"]),
    ("sangre_antigua","Sangre Antigua",35,"agility",["leather_chest","leather_gloves","leather_belt","cloak","rare_dagger"]),
    ("acero_rey","Acero del Rey",40,"strength",["mail_chest","mail_gloves","mail_belt","cloak","sword1h"]),
    ("eco_karazhan","Eco de Karazhan",45,"caster",["cloth_gloves","cloth_belt","cloak","rare_dagger","leather_chest"]),
    ("juramento_norte","Juramento del Norte",50,"strength",["mail_chest","mail_gloves","mail_belt","cloak","sword1h"]),
    ("ultimo_errante","Ultimo Errante",60,"agility",["leather_chest","leather_gloves","leather_belt","cloak","rare_dagger"]),
]

LEVELS = [3,4,5,8,12,16,20,25,30,35,40,45,50,55,60]
SPECIAL_LEVELS = [3,4,5,8,12,15]
NONSET_TYPES = [
    "sword1h","sword2h","mace1h","mace2h","axe1h","dagger","rare_dagger","staff","bow","crossbow","shield","cloak",
    "leather_chest","leather_gloves","leather_belt","mail_chest","mail_gloves","mail_belt","cloth_gloves","cloth_belt",
]
SPECIAL_TYPES = NONSET_TYPES
PREFIXES = ["Errante","Ceniza","Aurora","Cuervo","Bruma","Grifo","Tormenta","Roble","Lobo","Fauce","Estrella","Runas","Hierro","Marfil","Obsidiana","Vigilia","Abismo","Relampago","Escarcha","Fenix"]
SUFFIXES = ["del Camino","de las Ruinas","de la Frontera","del Juramento","del Viajero","de la Noche","del Alba","del Bastion","del Exilio","del Horizonte"]

QUALITY_ILVL_BAND = {
    "blue": (5, 7),
    "purple": (5, 9),
    "legendary": (7, 11),
}
QUALITY_DPS = {"blue": 1.105, "purple": 1.215, "legendary": 1.35}
QUALITY_STATS = {"blue": 1.00, "purple": 1.18, "legendary": 1.35}

WEAPON_SPEEDS = {
    "sword1h": (2200,2400,2600), "mace1h": (2200,2400,2600), "axe1h": (2200,2400,2600),
    "dagger": (1500,1700,1800), "rare_dagger": (1500,1700,1800),
    "sword2h": (2800,3000,3200), "mace2h": (3000,3200,3400), "staff": (2800,3000,3200),
    "bow": (2400,2600,2800), "crossbow": (2600,2800,3000),
}


def blank_row() -> dict[str, str]:
    return {column: "" for column in HEADERS}


def item_level_for(required_level: int, quality: str, salt: int) -> int:
    low, high = QUALITY_ILVL_BAND[quality]
    return required_level + low + (salt % (high - low + 1))


def archetype_for(item_type: str) -> str:
    if item_type in {"cloth_gloves", "cloth_belt", "staff"}:
        return "caster"
    if item_type in {"bow", "crossbow", "dagger", "rare_dagger", "leather_chest", "leather_gloves", "leather_belt"}:
        return "agility"
    return "strength"


def stat_values(archetype: str, item_level: int, quality: str) -> dict[str, int]:
    base = max(1, round((item_level / 6.0) * QUALITY_STATS[quality]))
    if archetype == "caster":
        result = {"intellect": base, "spirit": max(1, round(base * 0.7))}
        if item_level >= 18:
            result["spell_power"] = max(1, round(base * 1.4))
        return result
    primary = "agility" if archetype == "agility" else "strength"
    result = {primary: base, "stamina": max(1, round(base * 0.75))}
    if item_level >= 18:
        result["attack_power"] = max(1, round(base * 1.5))
    return result


def armor_value(item_type: str, item_level: int) -> tuple[int | None, int | None]:
    if item_type == "shield":
        return max(1, round(50 + item_level * 14.0)), max(1, round(item_level * 0.35))
    if item_type == "cloak":
        return max(1, round(3 + item_level * 1.4)), None

    material = 0.0
    if item_type.startswith("leather_"):
        material = 3.0
    elif item_type.startswith("mail_"):
        material = 4.2
    elif item_type.startswith("cloth_"):
        material = 2.0
    if not material:
        return None, None

    if "chest" in item_type:
        slot = 1.0
    elif "gloves" in item_type:
        slot = 0.45
    elif "belt" in item_type:
        slot = 0.40
    else:
        return None, None
    return max(1, round((8 + item_level * material) * slot)), None


def apply_weapon(row: dict[str, str], item_type: str, item_level: int, quality: str, salt: int) -> None:
    if item_type not in WEAPON_SPEEDS:
        return
    dps = max(0.1, 0.6 * item_level - 0.4) * QUALITY_DPS[quality]
    if item_type in {"sword2h", "mace2h", "staff"}:
        dps *= 1.305
    elif item_type in {"bow", "crossbow"}:
        dps *= 1.275

    speeds = WEAPON_SPEEDS[item_type]
    delay = speeds[salt % len(speeds)]
    average = dps * delay / 1000.0
    row["dmg_min1"] = f"{average * 0.70:.1f}"
    row["dmg_max1"] = f"{average * 1.30:.1f}"
    row["delay"] = str(delay)


def apply_values(row: dict[str, str], item_type: str, item_level: int, quality: str, archetype: str, salt: int) -> None:
    for stat, value in stat_values(archetype, item_level, quality).items():
        row[stat] = str(value)
    armor, block = armor_value(item_type, item_level)
    if armor is not None:
        row["armor"] = str(armor)
    if block is not None:
        row["block"] = str(block)
    apply_weapon(row, item_type, item_level, quality, salt)


def make_row(entry: int, item_type: str, required_level: int, quality: str, name: str, archetype: str,
             description: str, set_key: str = "") -> dict[str, str]:
    item_level = item_level_for(required_level, quality, entry)
    row = blank_row()
    row.update(
        enabled="1", entry=str(entry), source_entry=str(SOURCES[item_type]), set_key=set_key,
        name=name, quality=quality, required_level=str(required_level), item_level=str(item_level), description=description,
    )
    apply_values(row, item_type, item_level, quality, archetype, entry)
    return row


def build_catalog() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    bonuses: list[dict[str, str]] = []
    entry = 911100
    set_descriptions: dict[str, str] = {}

    for index, (key, name, level, _archetype, _pieces) in enumerate(SETS):
        set_ilvl = item_level_for(level, "blue", index)
        armor = max(5, round(set_ilvl * 0.75))
        defense = max(2, round(set_ilvl * 0.20))
        expertise = max(1, round(set_ilvl * 0.10))
        set_descriptions[key] = f"Set {name}. 2 piezas: +{armor} armadura. 3 piezas: +{defense} defensa. 5 piezas: +{expertise} pericia."
        bonuses.extend([
            {"enabled":"1","set_key":key,"name":name,"pieces_required":"2","bonus_type":"armor","value":str(armor),"spell_id":"","description":f"+{armor} armadura"},
            {"enabled":"1","set_key":key,"name":name,"pieces_required":"3","bonus_type":"defense_skill","value":str(defense),"spell_id":"","description":f"+{defense} puntos de defensa"},
            {"enabled":"1","set_key":key,"name":name,"pieces_required":"5","bonus_type":"expertise_rating","value":str(expertise),"spell_id":"","description":f"+{expertise} indice de pericia"},
        ])

    for key, name, level, archetype, pieces in SETS:
        for item_type in pieces:
            piece_archetype = archetype if archetype in {"strength","agility","caster"} else archetype_for(item_type)
            rows.append(make_row(entry, item_type, level, "blue", f"{PIECE_NAMES[item_type]} de {name}", piece_archetype,
                                 set_descriptions[key], key))
            entry += 1

    level_cycle = (LEVELS * 10)[:130]
    for index in range(130):
        item_type = NONSET_TYPES[index % len(NONSET_TYPES)]
        level = level_cycle[index]
        rows.append(make_row(entry, item_type, level, "blue",
            f"{PIECE_NAMES[item_type]} {PREFIXES[index % len(PREFIXES)]} {SUFFIXES[(index // len(PREFIXES)) % len(SUFFIXES)]}",
            archetype_for(item_type), "Botin excepcional de las expediciones de Khadgar."))
        entry += 1

    for special_index in range(70):
        quality = "purple" if special_index < 50 else "legendary"
        local_index = special_index if quality == "purple" else special_index - 50
        item_type = SPECIAL_TYPES[(special_index * 7 + 3) % len(SPECIAL_TYPES)]
        level = SPECIAL_LEVELS[local_index % len(SPECIAL_LEVELS)]
        rows.append(make_row(entry, item_type, level, quality,
            f"{PIECE_NAMES[item_type]} {PREFIXES[(special_index * 3 + 7) % len(PREFIXES)]} {SUFFIXES[(special_index * 5 + 2) % len(SUFFIXES)]}",
            archetype_for(item_type), "Reliquia excepcional recuperada en las expediciones de Khadgar."))
        entry += 1

    counts = {q: sum(row["quality"] == q for row in rows) for q in ("blue", "purple", "legendary")}
    if len(rows) != 300 or sum(bool(row["set_key"]) for row in rows) != 100:
        raise RuntimeError("catalog invariant failed")
    if counts != {"blue":230, "purple":50, "legendary":20}:
        raise RuntimeError(f"rarity invariant failed: {counts}")
    for row in rows:
        req = int(row["required_level"]); ilvl = int(row["item_level"]); low, high = QUALITY_ILVL_BAND[row["quality"]]
        if not req + low <= ilvl <= req + high:
            raise RuntimeError(f"item-level band invariant failed for {row['entry']}")
    if not any(row["required_level"] == "4" and row["quality"] == "blue" for row in rows):
        raise RuntimeError("missing level 4 blue rewards")
    return rows, bonuses


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter=";", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--items", required=True, type=Path); parser.add_argument("--sets", required=True, type=Path)
    args = parser.parse_args(); items, bonuses = build_catalog(); write_csv(args.items, HEADERS, items); write_csv(args.sets, SET_HEADERS, bonuses)
    print("Generated unified Gauntlet catalog: 300 items, all using RequiredLevel -> ItemLevel -> quality/type formulas.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
