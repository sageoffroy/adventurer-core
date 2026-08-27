#!/usr/bin/env python3
"""Localize Dungeon Master's hard-coded dungeon display names to esMX."""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


class DungeonNamePatchError(RuntimeError):
    pass


REL = Path("modules/mod-dungeon-master/src/DMConfig.cpp")
BACKUP_ROOT = Path("env/.adventurer-dungeon-master-dungeon-names-before")
MARKER = "// Aventureros esMX: localized Dungeon Master dungeon names."

NAMES = (
    ("Ragefire Chasm", "Sima Ígnea"),
    ("Deadmines", "Minas de la Muerte"),
    ("Shadowfang Keep", "Castillo de Colmillo Oscuro"),
    ("The Stockade", "Las Mazmorras"),
    ("Wailing Caverns", "Cuevas de los Lamentos"),
    ("Blackfathom Deeps", "Cavernas de Brazanegra"),
    ("Razorfen Kraul", "Horado Rajacieno"),
    ("Gnomeregan", "Gnomeregan"),
    ("Razorfen Downs", "Zahúrda Rajacieno"),
    ("Scarlet Monastery", "Monasterio Escarlata"),
    ("Uldaman", "Uldaman"),
    ("Zul'Farrak", "Zul'Farrak"),
    ("Maraudon", "Maraudon"),
    ("Sunken Temple", "Templo Sumergido"),
    ("Blackrock Depths", "Profundidades de Roca Negra"),
    ("Blackrock Spire", "Cumbre de Roca Negra"),
    ("Scholomance", "Scholomance"),
    ("Stratholme", "Stratholme"),
    ("Hellfire Ramparts", "Murallas del Fuego Infernal"),
    ("Blood Furnace", "Horno de Sangre"),
    ("Slave Pens", "Recinto de los Esclavos"),
    ("Underbog", "La Sotiénaga"),
    ("Mana-Tombs", "Tumbas de Maná"),
    ("Auchenai Crypts", "Criptas Auchenai"),
    ("Sethekk Halls", "Salas Sethekk"),
    ("Shadow Labyrinth", "Laberinto de las Sombras"),
    ("Shattered Halls", "Salas Arrasadas"),
    ("Botanica", "El Invernáculo"),
    ("Mechanar", "El Mechanar"),
    ("Arcatraz", "El Arcatraz"),
    ("Utgarde Keep", "Fortaleza de Utgarde"),
    ("The Nexus", "El Nexo"),
    ("Azjol-Nerub", "Azjol-Nerub"),
    ("Ahn'kahet", "Ahn'kahet: El Antiguo Reino"),
    ("Drak'Tharon Keep", "Fortaleza de Drak'Tharon"),
    ("Violet Hold", "Bastión Violeta"),
    ("Gundrak", "Gundrak"),
    ("Halls of Stone", "Cámaras de Piedra"),
    ("Halls of Lightning", "Cámaras de Relámpagos"),
    ("The Oculus", "El Oculus"),
    ("Utgarde Pinnacle", "Pináculo de Utgarde"),
    ("Culling of Stratholme", "La Matanza de Stratholme"),
    ("Forge of Souls", "La Forja de Almas"),
    ("Pit of Saron", "Foso de Saron"),
    ("Halls of Reflection", "Cámaras de Reflexión"),
)


def target(core: Path) -> Path:
    path = core.expanduser().resolve() / REL
    if not path.is_file():
        raise DungeonNamePatchError(f"Dungeon Master source file not found: {path}")
    return path


def backup_path(core: Path) -> Path:
    return core.expanduser().resolve() / BACKUP_ROOT / REL


def install(core: Path) -> bool:
    path = target(core)
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        verify(core)
        print("Dungeon Master Spanish dungeon names already current.")
        return False

    anchor = "    static const Def kDungeons[] =\n"
    if text.count(anchor) != 1:
        raise DungeonNamePatchError("Dungeon Master dungeon-list anchor not found")

    # Validate every name that actually changes before writing anything.
    for old, new in NAMES:
        if old == new:
            continue
        needle = f'"{old}"'
        if text.count(needle) != 1:
            raise DungeonNamePatchError(
                f"Dungeon name anchor {old!r}: expected 1 occurrence, found {text.count(needle)}"
            )

    patched = text.replace(anchor, f"    {MARKER}\n" + anchor, 1)
    for old, new in NAMES:
        if old != new:
            patched = patched.replace(f'"{old}"', f'"{new}"', 1)

    bp = backup_path(core)
    if not bp.exists():
        bp.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, bp)
    path.write_text(patched, encoding="utf-8")
    verify(core)
    print("Dungeon Master dungeon names localized to Spanish; rebuild required.")
    return True


def verify(core: Path) -> None:
    text = target(core).read_text(encoding="utf-8")
    if MARKER not in text:
        raise DungeonNamePatchError("Dungeon Master Spanish dungeon-name patch is missing")
    for name in ("Minas de la Muerte", "Monasterio Escarlata", "Fortaleza de Utgarde", "Cámaras de Reflexión"):
        if f'"{name}"' not in text:
            raise DungeonNamePatchError(f"Localized dungeon name missing: {name}")
    for english in ("Deadmines", "Scarlet Monastery", "Utgarde Keep", "Halls of Reflection"):
        if f'"{english}"' in text:
            raise DungeonNamePatchError(f"English dungeon name still active: {english}")


def rollback(core: Path) -> bool:
    path = target(core)
    text = path.read_text(encoding="utf-8")
    if MARKER not in text:
        return False
    bp = backup_path(core)
    if not bp.is_file():
        raise DungeonNamePatchError(f"Dungeon Master dungeon-name backup missing: {bp}")
    path.write_bytes(bp.read_bytes())
    shutil.rmtree(core.expanduser().resolve() / BACKUP_ROOT)
    print("Dungeon Master dungeon-name localization rolled back.")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "verify", "rollback"))
    parser.add_argument("--core-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "install":
            install(args.core_dir)
        elif args.command == "verify":
            verify(args.core_dir)
            print("Dungeon Master Spanish dungeon names verify cleanly.")
        else:
            restored = rollback(args.core_dir)
            if not restored:
                print("Dungeon Master dungeon-name localization absent; nothing to restore.")
        return 0
    except (OSError, DungeonNamePatchError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
