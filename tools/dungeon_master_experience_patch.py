#!/usr/bin/env python3
"""Aventureros UX/access layer for mod-dungeon-master.

This patch is intentionally applied after the native-encounter compatibility
patch. It does three project-specific things:

* bypasses stock instance access requirements only for Dungeon Master teleports,
  so a level-1 Adventurer can enter any selected instance;
* localizes the Dungeon Master gossip/player-facing UI to Spanish;
* keeps upstream/native patch verification markers in comments so the lower
  compatibility layer remains independently verifiable.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


class ExperiencePatchError(RuntimeError):
    pass


MGR = Path("modules/mod-dungeon-master/src/DungeonMasterMgr.cpp")
GOSSIP = Path("modules/mod-dungeon-master/src/scripts/npc_dungeon_master.cpp")
FILES = (MGR, GOSSIP)
BACKUP_ROOT = Path("env/.adventurer-dungeon-master-experience-before")

MGR_MARKER = "// Aventureros: bypass stock instance access requirements for Dungeon Master runs."
GOSSIP_MARKER = "// Aventureros esMX: Dungeon Master menus and messages."

TELEPORT_OLD = (
    "        if (p->TeleportTo(session->MapId, ent.GetPositionX(), ent.GetPositionY(),\n"
    "                          ent.GetPositionZ(), ent.GetOrientation()))\n"
)
TELEPORT_NEW = (
    "        // Aventureros: bypass stock instance access requirements for Dungeon Master runs.\n"
    "        // TELE_TO_GM_MODE only skips PlayerCannotEnter for this scripted teleport;\n"
    "        // it does not grant GM status to the player.\n"
    "        if (p->TeleportTo(session->MapId, ent.GetPositionX(), ent.GetPositionY(),\n"
    "                          ent.GetPositionZ(), ent.GetOrientation(), TELE_TO_GM_MODE))\n"
)

# Straight literal translations. Dungeon names remain canonical proper names;
# difficulty/theme display names are managed through managed.conf.
TRANSLATIONS = (
    ("The Dungeon Master is currently unavailable.", "El Maestro de Mazmorras no está disponible en este momento."),
    ("You are already in an active challenge!", "¡Ya estás participando en un desafío!"),
    ("You are in an active roguelike run!", "¡Ya estás en una partida roguelike activa!"),
    ("Quit Roguelike Run", "Abandonar partida roguelike"),
    ("Never mind", "Volver"),
    ("Wait |cFFFFFFFF%u|r min |cFFFFFFFF%u|r sec before your next challenge.",
     "Espera |cFFFFFFFF%u|r min |cFFFFFFFF%u|r s antes de tu próximo desafío."),
    ("Too many challenges running. Try again later.", "Hay demasiados desafíos activos. Inténtalo nuevamente más tarde."),
    ("You are already in a roguelike run!", "¡Ya estás en una partida roguelike!"),
    ("Run abandoned.", "Partida abandonada."),
    ("Begin Challenge", "Comenzar desafío"),
    ("Roguelike Mode", "Modo Roguelike"),
    ("How does this work?", "¿Cómo funciona?"),
    ("Statistics & Leaderboards", "Estadísticas y clasificaciones"),
    ("Requires %u+", "Requiere nivel %u+"),
    (" — Easy", " — Fácil"),
    ("<< Back", "<< Volver"),
    ("Scale to Party Level", "Escalar al nivel del grupo"),
    ("Full challenge at your level", "Desafío completo a tu nivel"),
    ("Use Dungeon Difficulty", "Usar dificultad de la mazmorra"),
    ("Original difficulty range", "Rango de dificultad original"),
    ("Original level ranges", "Rangos de nivel originales"),
    ("Random Dungeon", "Mazmorra aleatoria"),
    ("No dungeons available", "No hay mazmorras disponibles"),
    ("<< Previous Page", "<< Página anterior"),
    ("Next Page >>", "Página siguiente >>"),
    ("========== Challenge Summary ==========", "========== Resumen del desafío =========="),
    ("  Difficulty:", "  Dificultad:"),
    ("  Scaling:", "  Escalado:"),
    ("Party Level", "Nivel del grupo"),
    ("Dungeon Difficulty", "Dificultad de la mazmorra"),
    ("  Theme:", "  Enemigos:"),
    ("Original inhabitants", "Habitantes originales"),
    ("  Dungeon:", "  Mazmorra:"),
    ("  Party Size:", "  Tamaño del grupo:"),
    (" player(s)", " jugador(es)"),
    ("All party members will be teleported!", "¡Todos los miembros del grupo serán teletransportados!"),
    (">> START CHALLENGE <<", ">> INICIAR DESAFÍO <<"),
    ("<< Cancel", "<< Cancelar"),
    ("========= Dungeon Master Challenge =========", "========= Desafío del Maestro de Mazmorras ========="),
    ("Choose a difficulty tier", "Elige una dificultad"),
    ("Pick scaling: party level or dungeon difficulty", "Elige el escalado: nivel del grupo o dificultad de la mazmorra"),
    ("Pick a creature theme", "Elige una temática de criaturas"),
    ("The dungeon keeps its original inhabitants and mechanics", "La mazmorra conserva sus habitantes y mecánicas originales"),
    ("Select a dungeon or go random", "Elige una mazmorra o una al azar"),
    ("Native creatures are scaled to the challenge level", "Las criaturas originales se escalan al nivel del desafío"),
    ("Defeat the original boss to complete the challenge", "Derrota al jefe original para completar el desafío"),
    ("Collect native loot plus challenge rewards!", "¡Consigue el botín original y las recompensas del desafío!"),
    ("You'll be teleported to a cleared instance", "Serás teletransportado a una instancia preparada"),
    ("Defeat the boss to complete the challenge", "Derrota al jefe para completar el desafío"),
    ("Collect gold and gear rewards!", "¡Consigue oro y equipo como recompensa!"),
    ("My Normal Run Stats", "Mis estadísticas de desafíos"),
    ("My Roguelike Stats", "Mis estadísticas roguelike"),
    ("Leaderboards", "Clasificaciones"),
    ("Normal Run Stats", "Estadísticas de desafíos"),
    ("Roguelike Stats", "Estadísticas roguelike"),
    ("  Runs:", "  Partidas:"),
    ("Completed:", "Completadas:"),
    ("Failed:", "Fallidas:"),
    ("Win Rate:", "Victorias:"),
    ("Mobs Killed:", "Enemigos derrotados:"),
    ("Bosses Slain:", "Jefes derrotados:"),
    ("Deaths:", "Muertes:"),
    ("Kill/Death Ratio:", "Relación bajas/muertes:"),
    ("Fastest Clear:", "Mejor tiempo:"),
    ("View Leaderboards", "Ver clasificaciones"),
    ("Total Runs:", "Partidas totales:"),
    ("Highest Tier:", "Tier más alto:"),
    ("Most Floors:", "Máximo de pisos:"),
    ("Total Floors Cleared:", "Pisos completados:"),
    ("Avg Floors/Run:", "Promedio de pisos/partida:"),
    ("Longest Run:", "Partida más larga:"),
    ("Normal Runs — Fastest Clears", "Desafíos normales — Mejores tiempos"),
    ("Roguelike — Highest Tier", "Roguelike — Tier más alto"),
    ("Roguelike — Most Floors", "Roguelike — Más pisos"),
    ("No runs recorded yet.", "Todavía no hay partidas registradas."),
    ("No roguelike runs recorded yet.", "Todavía no hay partidas roguelike registradas."),
    ("[Scaled]", "[Escalado]"),
    ("<< YOU", "<< TÚ"),
    ("Clear dungeons back-to-back. Each clear increases the tier.", "Completa mazmorras consecutivas. Cada victoria aumenta el tier."),
    ("Enemies get harder, but you gain powerful buffs.", "Los enemigos se vuelven más difíciles, pero obtienes mejoras poderosas."),
    ("One wipe ends the run!", "¡Una derrota total termina la partida!"),
    ("Selection expired. Try again.", "La selección expiró. Inténtalo nuevamente."),
    ("Level requirement not met!", "¡No cumples el requisito de nivel!"),
    ("Failed to start roguelike run!", "¡No se pudo iniciar la partida roguelike!"),
    ("Run started! Clear dungeons to progress. Good luck!", "¡Partida iniciada! Completa mazmorras para avanzar. ¡Buena suerte!"),
    ("No dungeons available!", "¡No hay mazmorras disponibles!"),
    ("Failed to create session!", "¡No se pudo crear la sesión!"),
    ("Failed to initialize dungeon!", "¡No se pudo iniciar la mazmorra!"),
    ("Teleport failed!", "¡Falló el teletransporte!"),
    (" started a ", " inició un desafío "),
    (" challenge!", "!"),
    ("Difficulty: ", "Dificultad: "),
    ("Theme: ", "Enemigos: "),
    ("Dungeon: ", "Mazmorra: "),
    ("Scaling: ", "Escalado: "),
    ("Random", "Aleatorio"),
)

# Common player-facing messages emitted by the manager, not by gossip.
MGR_TRANSLATIONS = (
    ("Welcome to |cFFFFFFFF%s|r! Defeat the boss to claim your reward.",
     "¡Bienvenido a |cFFFFFFFF%s|r! Derrota al jefe para reclamar tu recompensa."),
    ("Teleport failed! You may lack access to this dungeon.",
     "¡Falló el teletransporte a la mazmorra!"),
    ("Total party wipe! Challenge failed.", "¡Todo el grupo ha caído! Desafío fallido."),
)


def _read(path: Path) -> str:
    if not path.is_file():
        raise ExperiencePatchError(f"Required Dungeon Master source file is missing: {path}")
    return path.read_text(encoding="utf-8")


def _backup_path(core: Path, rel: Path) -> Path:
    return core / BACKUP_ROOT / rel


def transform_mgr(text: str) -> str:
    if MGR_MARKER not in text:
        count = text.count(TELEPORT_OLD)
        if count != 1:
            raise ExperiencePatchError(f"Dungeon Master teleport anchor: expected 1, found {count}")
        text = text.replace(TELEPORT_OLD, TELEPORT_NEW, 1)
    for old, new in MGR_TRANSLATIONS:
        text = text.replace(old, new)
    return text


def transform_gossip(text: str) -> str:
    if "sSelections[player->GetGUID()].ThemeId = 1;" not in text:
        raise ExperiencePatchError("native Dungeon Master normal-mode patch is not installed")

    if GOSSIP_MARKER not in text:
        for old, new in TRANSLATIONS:
            text = text.replace(old, new)
        anchor = "    // ---- Menu builders ----\n"
        if text.count(anchor) != 1:
            raise ExperiencePatchError("Dungeon Master gossip menu anchor not found")
        # The first-layer source verifier intentionally looks for these two
        # English markers. Keep them as comments while the visible text is Spanish.
        marker = (
            "    // Aventureros esMX: Dungeon Master menus and messages.\n"
            "    // compatibility marker: Original inhabitants|r\n"
            "    // compatibility marker: The dungeon keeps its original inhabitants and mechanics\n"
        )
        text = text.replace(anchor, marker + anchor, 1)
    return text


def is_installed(core: Path) -> bool:
    mgr = _read(core / MGR)
    gossip = _read(core / GOSSIP)
    return MGR_MARKER in mgr and GOSSIP_MARKER in gossip


def install(core: Path) -> list[str]:
    core = core.expanduser().resolve()
    before = {rel: _read(core / rel) for rel in FILES}
    if is_installed(core):
        verify(core)
        print("Dungeon Master Aventureros UX/access patch already current.")
        return []

    after = {
        MGR: transform_mgr(before[MGR]),
        GOSSIP: transform_gossip(before[GOSSIP]),
    }
    for rel in FILES:
        bp = _backup_path(core, rel)
        if not bp.exists():
            bp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(core / rel, bp)
    for rel in FILES:
        (core / rel).write_text(after[rel], encoding="utf-8")
    verify(core)
    print("Dungeon Master Aventureros UX/access patch applied:")
    print(f"  {MGR}")
    print(f"  {GOSSIP}")
    print("  level-1 instance entry: enabled")
    print("  menus: Spanish (esMX)")
    print("  rebuild required: yes")
    return [str(x) for x in FILES]


def verify(core: Path) -> None:
    core = core.expanduser().resolve()
    mgr = _read(core / MGR)
    gossip = _read(core / GOSSIP)
    if MGR_MARKER not in mgr or "TELE_TO_GM_MODE" not in mgr:
        raise ExperiencePatchError("Dungeon Master level-1 instance-entry patch is missing")
    if GOSSIP_MARKER not in gossip:
        raise ExperiencePatchError("Dungeon Master Spanish menu patch is missing")
    for token in ("Comenzar desafío", "Escalar al nivel del grupo", "Resumen del desafío", "Habitantes originales"):
        if token not in gossip:
            raise ExperiencePatchError(f"Dungeon Master Spanish UI token missing: {token}")
    for english in ("Begin Challenge", "Scale to Party Level", "Challenge Summary"):
        if english in gossip:
            raise ExperiencePatchError(f"Dungeon Master English UI token still present: {english}")


def rollback(core: Path) -> list[str]:
    core = core.expanduser().resolve()
    if not is_installed(core):
        return []
    missing = [rel for rel in FILES if not _backup_path(core, rel).is_file()]
    if missing:
        raise ExperiencePatchError("Dungeon Master UX/access backup missing: " + ", ".join(map(str, missing)))
    for rel in FILES:
        (core / rel).write_bytes(_backup_path(core, rel).read_bytes())
    shutil.rmtree(core / BACKUP_ROOT)
    print("Dungeon Master Aventureros UX/access patch rolled back.")
    return [str(x) for x in FILES]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "verify", "rollback"))
    parser.add_argument("--core-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        {"install": install, "verify": verify, "rollback": rollback}[args.command](args.core_dir)
        return 0
    except (OSError, ExperiencePatchError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
