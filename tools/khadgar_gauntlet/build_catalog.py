#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

HEADERS = [
    "enabled","entry","source_entry","display_id","set_key","name","quality","required_level","item_level",
    "strength","agility","stamina","intellect","spirit","attack_power","spell_power","hit_rating","crit_rating",
    "haste_rating","armor","dmg_min1","dmg_max1","delay","equip_spell1","equip_spell2","description",
]
SET_HEADERS = ["enabled","set_key","name","pieces_required","bonus_type","value","spell_id","description"]

SOURCES = {
    "sword1h":25, "sword2h":8178, "dagger":2092, "bow":2504, "cloak":1372,
    "leather_chest":85, "mail_chest":2392, "leather_gloves":2125, "mail_gloves":2397,
    "cloth_gloves":2119, "shield":2133, "cloth_belt":3599, "leather_belt":2122,
    "mail_belt":2393, "mace2h":1195, "rare_dagger":1917, "mace1h":36, "axe1h":37,
}

PIECE_NAMES = {
    "sword2h":"Mandoble", "mace2h":"Gran maza", "sword1h":"Espada", "mace1h":"Maza", "axe1h":"Hacha", "shield":"Escudo",
    "mail_chest":"Coselete", "mail_gloves":"Guanteletes", "mail_belt":"Cinturon",
    "leather_chest":"Jubon", "leather_gloves":"Guantes", "leather_belt":"Cinturon",
    "cloth_gloves":"Guantes", "cloth_belt":"Faja", "cloak":"Capa", "dagger":"Daga", "rare_dagger":"Daga", "bow":"Arco",
}

SETS = [
    ("juramento_coloso","Juramento del Coloso",3,"2h",["sword2h","mail_chest","mail_gloves","mail_belt","cloak"]),
    ("martillo_ceniza","Martillo de Ceniza",5,"2h",["mace2h","mail_chest","mail_gloves","mail_belt","cloak"]),
    ("hoja_errante","Hoja Errante",8,"2h",["sword2h","leather_chest","leather_gloves","leather_belt","cloak"]),
    ("quebrantahuesos","Quebrantahuesos",12,"2h",["mace2h","leather_chest","leather_gloves","leather_belt","cloak"]),
    ("vigilia_titan","Vigilia del Titan",16,"2h",["sword2h","mail_chest","mail_gloves","mail_belt","cloak"]),
    ("guardia_alba","Guardia del Alba",3,"1hshield",["sword1h","shield","mail_chest","mail_gloves","mail_belt"]),
    ("muro_viajero","Muro del Viajero",8,"1hshield",["sword1h","shield","leather_chest","leather_gloves","leather_belt"]),
    ("cuero_oso","Cuero de Oso",3,"armor",["leather_chest","leather_gloves","leather_belt","cloak","dagger"]),
    ("colmillo_niebla","Colmillo de Niebla",5,"armor",["leather_chest","leather_gloves","leather_belt","cloak","dagger"]),
    ("cazador_sombra","Cazador de Sombras",8,"armor",["leather_chest","leather_gloves","leather_belt","cloak","bow"]),
    ("vigia_bosque","Vigia del Bosque",12,"armor",["leather_chest","leather_gloves","leather_belt","cloak","bow"]),
    ("tejedor_runas","Tejedor de Runas",16,"caster",["cloth_gloves","cloth_belt","cloak","dagger","leather_chest"]),
    ("sabio_viajero","Sabio del Viajero",20,"caster",["cloth_gloves","cloth_belt","cloak","dagger","leather_chest"]),
    ("malla_tormenta","Malla de Tormenta",25,"armor",["mail_chest","mail_gloves","mail_belt","cloak","sword1h"]),
    ("malla_grifo","Malla del Grifo",30,"armor",["mail_chest","mail_gloves","mail_belt","cloak","bow"]),
    ("sangre_antigua","Sangre Antigua",35,"armor",["leather_chest","leather_gloves","leather_belt","cloak","rare_dagger"]),
    ("acero_rey","Acero del Rey",40,"armor",["mail_chest","mail_gloves","mail_belt","cloak","sword1h"]),
    ("eco_karazhan","Eco de Karazhan",45,"caster",["cloth_gloves","cloth_belt","cloak","rare_dagger","leather_chest"]),
    ("juramento_norte","Juramento del Norte",50,"armor",["mail_chest","mail_gloves","mail_belt","cloak","sword1h"]),
    ("ultimo_errante","Ultimo Errante",60,"armor",["leather_chest","leather_gloves","leather_belt","cloak","rare_dagger"]),
]

LEVELS = [3,5,8,12,16,20,25,30,35,40,45,50,55,60]
EARLY_SPECIAL_LEVELS = [3,5,8,12,15]
NONSET_TYPES = [
    "sword1h","sword2h","mace2h","dagger","rare_dagger","bow","shield","cloak",
    "leather_chest","leather_gloves","leather_belt","mail_chest","mail_gloves","mail_belt","cloth_gloves","cloth_belt",
]
SPECIAL_TYPES = [
    "sword1h","mace1h","axe1h","sword2h","mace2h","dagger","rare_dagger","bow","shield","cloak",
    "leather_chest","leather_gloves","leather_belt","mail_chest","mail_gloves","mail_belt","cloth_gloves","cloth_belt",
]
PREFIXES = ["Errante","Ceniza","Aurora","Cuervo","Bruma","Grifo","Tormenta","Roble","Lobo","Fauce","Estrella","Runas","Hierro","Marfil","Obsidiana","Vigilia","Abismo","Relampago","Escarcha","Fenix"]
SUFFIXES = ["del Camino","de las Ruinas","de la Frontera","del Juramento","del Viajero","de la Noche","del Alba","del Bastion","del Exilio","del Horizonte"]


def blank_row() -> dict[str, str]:
    return {column: "" for column in HEADERS}


def quality_multiplier(quality: str) -> float:
    if quality == "legendary": return 1.80
    if quality == "purple": return 1.35
    return 1.0


def quality_item_bonus(quality: str) -> int:
    if quality == "legendary": return 7
    if quality == "purple": return 5
    return 3


def stat_scale(level: int, quality: str) -> int:
    return max(1, round((1 + level / 10) * quality_multiplier(quality)))


def stats_for(archetype: str, level: int, quality: str) -> dict[str, int]:
    scale = stat_scale(level, quality)
    if archetype in {"2h", "1hshield", "melee"}:
        values = {"strength": scale, "stamina": max(1, round(scale * 0.8))}
        if level >= 12: values["attack_power"] = max(1, round(scale * 1.5))
        return values
    if archetype == "ranged":
        values = {"agility": scale, "stamina": max(1, round(scale * 0.7))}
        if level >= 12: values["attack_power"] = max(1, round(scale * 1.5))
        return values
    values = {"intellect": scale, "spirit": max(1, round(scale * 0.8))}
    if level >= 12: values["spell_power"] = max(1, round(scale * 1.2))
    return values


def apply_chassis_values(row: dict[str, str], item_type: str, level: int, quality: str) -> None:
    multiplier = quality_multiplier(quality)
    if "chest" in item_type:
        row["armor"] = str(max(10, round((12 + level * 1.5) * multiplier)))
    elif any(token in item_type for token in ("gloves", "belt")) or item_type in {"cloak", "shield"}:
        row["armor"] = str(max(4, round((6 + level * 0.8) * multiplier)))

    if item_type in {"sword2h", "mace2h"}:
        base = (5 + level * 0.55) * multiplier
        row["dmg_min1"], row["dmg_max1"], row["delay"] = f"{base:.1f}", f"{base * 1.45:.1f}", "3200"
    elif item_type in {"sword1h", "mace1h", "axe1h", "dagger", "rare_dagger"}:
        base = (3 + level * 0.32) * multiplier
        delay = "1800" if "dagger" in item_type else ("2000" if item_type == "axe1h" else "2400")
        row["dmg_min1"], row["dmg_max1"], row["delay"] = f"{base:.1f}", f"{base * 1.4:.1f}", delay
    elif item_type == "bow":
        base = (3 + level * 0.28) * multiplier
        row["dmg_min1"], row["dmg_max1"], row["delay"] = f"{base:.1f}", f"{base * 1.5:.1f}", "2600"


def make_row(entry: int, item_type: str, level: int, quality: str, name: str, archetype: str, description: str, set_key: str = "") -> dict[str, str]:
    row = blank_row()
    row.update(
        enabled="1", entry=str(entry), source_entry=str(SOURCES[item_type]), set_key=set_key,
        name=name, quality=quality, required_level=str(level), item_level=str(level + quality_item_bonus(quality)),
        description=description,
    )
    for stat, value in stats_for(archetype, level, quality).items(): row[stat] = str(value)
    apply_chassis_values(row, item_type, level, quality)
    return row


def build_catalog() -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    rows: list[dict[str, str]] = []
    bonuses: list[dict[str, str]] = []
    entry = 911100
    set_descriptions: dict[str, str] = {}

    for key, name, level, _kind, _pieces in SETS:
        armor = max(5, round(5 + level * 0.7)); defense = max(2, round(2 + level * 0.12)); expertise = max(1, round(1 + level * 0.05))
        set_descriptions[key] = f"Set {name}. 2 piezas: +{armor} armadura. 3 piezas: +{defense} defensa. 5 piezas: +{expertise} pericia."
        bonuses.extend([
            {"enabled":"1","set_key":key,"name":name,"pieces_required":"2","bonus_type":"armor","value":str(armor),"spell_id":"","description":f"+{armor} armadura"},
            {"enabled":"1","set_key":key,"name":name,"pieces_required":"3","bonus_type":"defense_skill","value":str(defense),"spell_id":"","description":f"+{defense} puntos de defensa"},
            {"enabled":"1","set_key":key,"name":name,"pieces_required":"5","bonus_type":"expertise_rating","value":str(expertise),"spell_id":"","description":f"+{expertise} indice de pericia"},
        ])

    # Set pieces remain blue. Epic/legendary discovery items are separate so the
    # special pools do not reveal set progression or consume set-piece rarity.
    for key, name, level, kind, pieces in SETS:
        for item_type in pieces:
            archetype = kind if kind in {"2h", "1hshield", "caster"} else ("ranged" if item_type == "bow" else "melee")
            rows.append(make_row(entry, item_type, level, "blue", f"{PIECE_NAMES[item_type]} de {name}", archetype, set_descriptions[key], key))
            entry += 1

    # 130 regular blue discovery items retain broad progression. The first two
    # explicitly guarantee level-3 one-handed mace and axe availability.
    level_cycle = (LEVELS * 10)[:130]
    for index in range(130):
        item_type = "mace1h" if index == 0 else ("axe1h" if index == 1 else NONSET_TYPES[index % len(NONSET_TYPES)])
        level = 3 if index < 2 else level_cycle[index]
        archetype = "ranged" if item_type == "bow" else ("caster" if item_type in {"cloth_gloves", "cloth_belt"} else "melee")
        rows.append(make_row(entry, item_type, level, "blue",
            f"{PIECE_NAMES[item_type]} {PREFIXES[index % len(PREFIXES)]} {SUFFIXES[(index // len(PREFIXES)) % len(SUFFIXES)]}",
            archetype, "Botin excepcional de las expediciones de Khadgar."))
        entry += 1

    # Hidden early-game special pool: exactly 50 epics and 20 legendaries,
    # distributed only through levels 3, 5, 8, 12 and 15.
    for special_index in range(70):
        quality = "purple" if special_index < 50 else "legendary"
        local_index = special_index if quality == "purple" else special_index - 50
        item_type = SPECIAL_TYPES[(special_index * 7 + 3) % len(SPECIAL_TYPES)]
        level = EARLY_SPECIAL_LEVELS[local_index % len(EARLY_SPECIAL_LEVELS)]
        archetype = "ranged" if item_type == "bow" else ("caster" if item_type in {"cloth_gloves", "cloth_belt"} else "melee")
        rows.append(make_row(entry, item_type, level, quality,
            f"{PIECE_NAMES[item_type]} {PREFIXES[(special_index * 3 + 7) % len(PREFIXES)]} {SUFFIXES[(special_index * 5 + 2) % len(SUFFIXES)]}",
            archetype, "Reliquia excepcional recuperada en las expediciones de Khadgar."))
        entry += 1

    counts = {q: sum(row["quality"] == q for row in rows) for q in ("blue", "purple", "legendary")}
    if len(rows) != 300 or sum(bool(row["set_key"]) for row in rows) != 100:
        raise RuntimeError("catalog invariant failed")
    if counts != {"blue":230, "purple":50, "legendary":20}:
        raise RuntimeError(f"rarity invariant failed: {counts}")
    if any(int(row["required_level"]) > 15 for row in rows if row["quality"] in {"purple", "legendary"}):
        raise RuntimeError("epic/legendary early pool exceeds level 15")
    for required_type in ("mace1h", "axe1h"):
        if not any(row["required_level"] == "3" and row["source_entry"] == str(SOURCES[required_type]) for row in rows):
            raise RuntimeError(f"missing level 3 {required_type} reward")
    return rows, bonuses


def write_csv(path: Path, headers: list[str], rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers, delimiter=";", lineterminator="\n")
        writer.writeheader(); writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--items", required=True, type=Path); parser.add_argument("--sets", required=True, type=Path)
    args = parser.parse_args(); items, bonuses = build_catalog(); write_csv(args.items, HEADERS, items); write_csv(args.sets, SET_HEADERS, bonuses)
    print("Generated controlled Gauntlet catalog: 300 items (230 blue, 50 epic, 20 legendary), 100 set pieces, 20 sets. Special epic/legendary pool: levels 3-15.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
