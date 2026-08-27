#!/usr/bin/env python3
"""Versioned Adventurer compatibility for mod-dungeon-master source.

Normal challenges keep each instance's native creatures, scripts, movement,
faction and encounter mechanics. Roguelike retains upstream procedural themes.
The patch also scales native creature abilities and adds a low-level safety cap.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


class DungeonMasterSourcePatchError(RuntimeError):
    pass


FILES = (
    "modules/mod-dungeon-master/src/DungeonMasterMgr.h",
    "modules/mod-dungeon-master/src/DungeonMasterMgr.cpp",
    "modules/mod-dungeon-master/src/scripts/dm_unit_script.cpp",
    "modules/mod-dungeon-master/src/scripts/npc_dungeon_master.cpp",
)
BACKUP_ROOT = Path("env/.adventurer-dungeon-master-source-before")

PATCH_MARKERS = (
    (FILES[0], "PrepareOriginalCreature(Creature* creature"),
    (FILES[1], "// Aventureros: preserve and scale the dungeon's original inhabitants."),
    (FILES[1], "// Aventureros normal mode: keep the original dungeon."),
    (FILES[1], "DungeonMaster: original ability damage scale"),
    (FILES[1], "// ---- Original dungeon grid activation / roguelike stray cleanup ----"),
    (FILES[1], "// Aventureros phase handling:"),
    (FILES[1], "bool preserveNativeLoot = session->RoguelikeRunId == 0;"),
    (FILES[2], "bool scaleSessionAbility"),
    (FILES[2], "// Guardrail: no single hit can remove more than 35% max HP."),
    (FILES[3], "sSelections[player->GetGUID()].ThemeId = 1;"),
    (FILES[3], "Original inhabitants|r"),
    (FILES[3], "The dungeon keeps its original inhabitants and mechanics"),
)

HELPER = r'''
// Aventureros: preserve and scale the dungeon's original inhabitants.
// This deliberately keeps the creature entry, faction, movement, ScriptName/AI,
// immunities and encounter scripts. We only normalize combat statistics.
bool DungeonMasterMgr::PrepareOriginalCreature(Creature* c, Session* session, bool forceBoss)
{
    if (!c || !session || !c->IsInWorld() || !c->IsAlive())
        return false;
    if (c->IsPet() || c->IsGuardian() || c->IsTotem())
        return false;
    if (c->GetEntry() == sDMConfig->GetNpcEntry() || c->GetEntry() == 500001)
        return false;

    const CreatureTemplate* tmpl = c->GetCreatureTemplate();
    if (!tmpl)
        return false;
    if (tmpl->npcflag != 0 || tmpl->type == 8 || tmpl->VehicleId != 0 || tmpl->rank == 3)
        return false;
    if ((tmpl->flags_extra & CREATURE_FLAG_EXTRA_TRIGGER) != 0)
        return false;

    for (auto& sc : session->SpawnedCreatures)
    {
        if (sc.Guid == c->GetGUID())
        {
            if (forceBoss)
            {
                sc.IsBoss = true;
                sc.IsElite = true;
            }
            return true;
        }
    }

    bool challengeBoss = forceBoss;
    if (!challengeBoss)
    {
        for (const SpawnPoint& sp : session->SpawnPoints)
        {
            if (!sp.IsBossPosition)
                continue;
            float dx = c->GetPositionX() - sp.Pos.GetPositionX();
            float dy = c->GetPositionY() - sp.Pos.GetPositionY();
            float dz = c->GetPositionZ() - sp.Pos.GetPositionZ();
            if ((dx * dx + dy * dy + dz * dz) <= 100.0f)
            {
                challengeBoss = true;
                break;
            }
        }
    }

    bool elite = challengeBoss || tmpl->rank == 1 || tmpl->rank == 2 || tmpl->rank == 4;
    if (!challengeBoss)
    {
        bool hostile = false;
        for (const auto& pd : session->Players)
        {
            Player* player = ObjectAccessor::FindPlayer(pd.PlayerGuid);
            if (player && player->IsInWorld() && player->GetMapId() == session->MapId
                && c->IsHostileTo(player))
            {
                hostile = true;
                break;
            }
        }
        if (!hostile)
            return false;
    }

    const uint8 targetLevel = session->EffectiveLevel;
    c->SetLevel(targetLevel);
    const uint8 unitClass = tmpl->unit_class;
    const ClassLevelStatEntry* baseStats = GetBaseStatsForLevel(unitClass, targetLevel);

    float hpMult = CalculateHealthMultiplier(session);
    float extraHpMult = challengeBoss ? sDMConfig->GetBossHealthMult()
        : (elite ? sDMConfig->GetEliteHealthMult() : 1.0f);
    float finalHP = baseStats
        ? static_cast<float>(baseStats->BaseHP) * hpMult * extraHpMult
        : static_cast<float>(c->GetMaxHealth()) * hpMult * extraHpMult;
    uint32 hp = std::max(1u, static_cast<uint32>(finalHP));
    c->SetMaxHealth(hp);
    c->SetHealth(hp);

    float effectiveDmgMult = CalculateDamageMultiplier(session);
    float extraDmgMult = 1.0f;
    if (challengeBoss)
    {
        uint32 n = session->Players.size();
        effectiveDmgMult = (n <= 1) ? sDMConfig->GetSoloMultiplier()
            : (1.0f + (n - 1) * sDMConfig->GetPerPlayerDamageMult());
        if (session->RoguelikeRunId != 0)
            effectiveDmgMult *= sRoguelikeMgr->GetTierDamageMultiplier(session->RoguelikeRunId);
        extraDmgMult = sDMConfig->GetBossDamageMult();
    }
    else if (elite)
        extraDmgMult = sDMConfig->GetEliteDamageMult();

    if (baseStats)
    {
        float dmgBase = baseStats->BaseDamage;
        float apBonus = static_cast<float>(baseStats->AttackPower) / 14.0f;
        float atkTime = static_cast<float>(tmpl->BaseAttackTime) / 1000.0f;
        if (atkTime <= 0.0f)
            atkTime = 2.0f;
        float minDmg = (dmgBase + apBonus) * atkTime * effectiveDmgMult * extraDmgMult;
        float maxDmg = ((dmgBase * 1.15f) + apBonus) * atkTime * effectiveDmgMult * extraDmgMult;
        minDmg = std::max(1.0f, minDmg);
        maxDmg = std::max(minDmg, maxDmg);
        c->SetBaseWeaponDamage(BASE_ATTACK, MINDAMAGE, minDmg);
        c->SetBaseWeaponDamage(BASE_ATTACK, MAXDAMAGE, maxDmg);
        c->UpdateDamagePhysical(BASE_ATTACK);
        if (baseStats->BaseArmor > 0)
            c->SetArmor(baseStats->BaseArmor);
    }

    // Keep original AI/scripts/faction/movement/flags/immunities/resistances.
    c->UpdateObjectVisibility(true);
    SpawnedCreature sc;
    sc.Guid = c->GetGUID();
    sc.Entry = c->GetEntry();
    sc.IsElite = elite;
    sc.IsBoss = challengeBoss;
    session->SpawnedCreatures.push_back(sc);
    LOG_DEBUG("module",
        "DungeonMaster: original creature '{}' entry {} scaled to level {} "
        "(elite={}, challengeBoss={}, hp={})",
        c->GetName(), c->GetEntry(), targetLevel, elite, challengeBoss, hp);
    return true;
}

'''

NORMAL_BRANCH = r'''

    // Aventureros normal mode: keep the original dungeon.
    // Roguelike intentionally keeps the upstream themed/random population path.
    if (session->RoguelikeRunId == 0)
    {
        session->InstanceId = map->GetInstanceId();
        session->SpawnedCreatures.clear();
        session->PendingPhaseChecks.clear();
        session->SpawnPoints = GetSpawnPointsForMap(session->MapId);

        uint32 challengeBosses = 0;
        uint32 approximateMobs = 0;
        for (const SpawnPoint& sp : session->SpawnPoints)
            sp.IsBossPosition ? ++challengeBosses : ++approximateMobs;
        session->TotalBosses = std::max(1u, challengeBosses);
        session->BossesKilled = 0;
        session->TotalMobs = std::max(1u, approximateMobs);
        session->MobsKilled = 0;

        auto const& store = map->GetCreatureBySpawnIdStore();
        uint32 preparedNow = 0;
        for (auto const& pair : store)
            if (PrepareOriginalCreature(pair.second, session))
                ++preparedNow;

        LOG_INFO("module",
            "DungeonMaster: original mode ready - map {}, loaded/scaled now {}, "
            "challenge bosses {}, original spawn points {}",
            session->MapId, preparedNow, session->TotalBosses, session->SpawnPoints.size());
        return;
    }
'''

DAMAGE_FUNCTION = r'''float DungeonMasterMgr::GetSessionCreatureDamageScale(
    ObjectGuid playerGuid, ObjectGuid creatureGuid)
{
    std::lock_guard<std::mutex> lock(_sessionMutex);
    auto pit = _playerToSession.find(playerGuid);
    if (pit == _playerToSession.end()) return 1.0f;
    auto sit = _activeSessions.find(pit->second);
    if (sit == _activeSessions.end()) return 1.0f;
    const Session& session = sit->second;

    const SpawnedCreature* tracked = nullptr;
    for (const auto& sc : session.SpawnedCreatures)
        if (sc.Guid == creatureGuid) { tracked = &sc; break; }
    if (!tracked) return 1.0f;

    Creature* creature = nullptr;
    for (const auto& pd : session.Players)
    {
        Player* p = ObjectAccessor::FindPlayer(pd.PlayerGuid);
        if (p && p->IsInWorld())
        {
            creature = ObjectAccessor::GetCreature(*p, creatureGuid);
            if (creature) break;
        }
    }
    if (!creature) return 1.0f;
    const CreatureTemplate* tmpl = creature->GetCreatureTemplate();
    if (!tmpl) return 1.0f;

    const uint8 targetLevel = session.EffectiveLevel;
    const uint8 templateLevel = std::max<uint8>(1, tmpl->maxlevel);
    const uint8 unitClass = tmpl->unit_class;
    const ClassLevelStatEntry* targetStats = GetBaseStatsForLevel(unitClass, targetLevel);
    const ClassLevelStatEntry* templateStats = GetBaseStatsForLevel(unitClass, templateLevel);

    float levelScale;
    if (targetStats && templateStats && templateStats->BaseDamage > 0.0f)
        levelScale = targetStats->BaseDamage / templateStats->BaseDamage;
    else
        levelScale = std::pow(static_cast<float>(targetLevel) / static_cast<float>(templateLevel), 1.5f);

    float encounterMult;
    if (tracked->IsBoss)
    {
        uint32 n = session.Players.size();
        encounterMult = (n <= 1) ? sDMConfig->GetSoloMultiplier()
            : (1.0f + (n - 1) * sDMConfig->GetPerPlayerDamageMult());
        if (session.RoguelikeRunId != 0)
            encounterMult *= sRoguelikeMgr->GetTierDamageMultiplier(session.RoguelikeRunId);
        encounterMult *= sDMConfig->GetBossDamageMult();
    }
    else
    {
        encounterMult = CalculateDamageMultiplier(&session);
        if (tracked->IsElite)
            encounterMult *= sDMConfig->GetEliteDamageMult();
    }

    float scale = std::clamp(levelScale * encounterMult, 0.02f, 25.0f);
    LOG_DEBUG("module",
        "DungeonMaster: original ability damage scale - session {}, entry {}, "
        "targetLvl={}, templateLvl={}, scale={:.3f}",
        session.SessionId, creature->GetEntry(), targetLevel, templateLevel, scale);
    return scale;
}
'''

SWEEP = r'''                    // ---- Original dungeon grid activation / roguelike stray cleanup ----
                    Map* m = ref->GetMap();
                    if (m && m->IsDungeon())
                    {
                        uint32 npcEntry = sDMConfig->GetNpcEntry();
                        auto const& dbStore = static_cast<InstanceMap*>(m)->GetCreatureBySpawnIdStore();
                        if (session.RoguelikeRunId == 0)
                        {
                            for (auto const& pair : dbStore)
                            {
                                Creature* native = pair.second;
                                if (native && native->IsInWorld() && native->IsAlive()
                                    && PrepareOriginalCreature(native, &session))
                                    ourGuids.insert(native->GetGUID());
                            }
                        }
                        else
                        {
                            for (auto const& pair : dbStore)
                            {
                                Creature* stray = pair.second;
                                if (stray && stray->IsInWorld() && stray->IsAlive()
                                    && stray->GetEntry() != npcEntry
                                    && !stray->IsPet() && !stray->IsGuardian() && !stray->IsTotem()
                                    && ourGuids.count(stray->GetGUID()) == 0)
                                {
                                    stray->SetRespawnTime(7 * DAY);
                                    stray->DespawnOrUnsummon();
                                }
                            }
                        }
                    }
'''

PHASE = r'''                                // Promote to boss creature
                                // Aventureros phase handling: normal mode preserves native
                                // faction/AI/scripts; roguelike keeps upstream forced behavior.
                                LOG_INFO("module", "DungeonMaster: Phase creature detected! '{}' (entry {}) "
                                    "spawned {:.1f} yds from boss death location — promoting to boss",
                                    nc->GetName(), nc->GetEntry(), dist);
                                if (session.RoguelikeRunId == 0)
                                {
                                    PrepareOriginalCreature(nc, &session, true);
                                    ourGuids.insert(nc->GetGUID());
                                }
                                else
                                {
                                    nc->SetFaction(14);
                                    nc->SetReactState(REACT_AGGRESSIVE);
                                    nc->RemoveFlag(UNIT_FIELD_FLAGS, UNIT_FLAG_NON_ATTACKABLE | UNIT_FLAG_IMMUNE_TO_PC
                                                                    | UNIT_FLAG_IMMUNE_TO_NPC | UNIT_FLAG_PACIFIED);
                                    nc->SetImmuneToPC(false);
                                    nc->SetImmuneToNPC(false);
                                    SpawnedCreature nsc;
                                    nsc.Guid = nc->GetGUID();
                                    nsc.Entry = nc->GetEntry();
                                    nsc.IsElite = true;
                                    nsc.IsBoss = true;
                                    session.SpawnedCreatures.push_back(nsc);
                                    ourGuids.insert(nc->GetGUID());
                                    _instanceCreatureGuids[session.InstanceId].push_back(nc->GetGUID());
                                }
                                phaseCreatureFound = true;
'''

UNIT_SESSION = r'''            // Session creature damage:
            // melee was rebuilt from target-level stats; spells keep original AI/DBC.
            if (sDungeonMasterMgr->IsSessionCreature(playerGuid, attackerGuid))
            {
                if (scaleSessionAbility)
                {
                    float scale = sDungeonMasterMgr->GetSessionCreatureDamageScale(playerGuid, attackerGuid);
                    damage = std::max(1u, static_cast<uint32>(damage * scale));
                }
                // Levels 1-9 were outside the upstream module's original range.
                // Guardrail: no single hit can remove more than 35% max HP.
                if (player->GetLevel() <= 9)
                {
                    uint32 cap = std::max(1u, static_cast<uint32>(player->GetMaxHealth() * 0.35f));
                    damage = std::min(damage, cap);
                }
                return;
            }
'''


def read(path: Path) -> str:
    if not path.is_file():
        raise DungeonMasterSourcePatchError(f"Required Dungeon Master source file is missing: {path}")
    return path.read_text(encoding="utf-8")


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise DungeonMasterSourcePatchError(f"{label}: expected one clean anchor, found {count}")
    return text.replace(old, new, 1)


def replace_section(text: str, start_marker: str, end_marker: str, new: str, label: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        raise DungeonMasterSourcePatchError(f"{label}: section markers not found")
    return text[:start] + new + text[end:]


def transform_header(text: str) -> str:
    return replace_once(
        text,
        "    void PopulateDungeon(Session* session, InstanceMap* map);\n",
        "    void PopulateDungeon(Session* session, InstanceMap* map);\n"
        "    bool PrepareOriginalCreature(Creature* creature, Session* session, bool forceBoss = false);\n",
        "DungeonMasterMgr header",
    )


def transform_mgr(text: str) -> str:
    text = replace_once(
        text,
        "// Populate dungeon with themed creatures and bosses\n",
        HELPER + "// Populate dungeon with themed creatures and bosses\n",
        "native helper",
    )
    anchor = (
        "    const DifficultyTier* diff  = sDMConfig->GetDifficulty(session->DifficultyId);\n"
        "    const Theme*          theme = sDMConfig->GetTheme(session->ThemeId);\n"
        "    if (!diff || !theme) return;\n"
    )
    text = replace_once(text, anchor, anchor + NORMAL_BRANCH, "native PopulateDungeon branch")
    text = replace_section(
        text,
        "float DungeonMasterMgr::GetSessionCreatureDamageScale(\n",
        "// Scale environmental damage to party level\n",
        DAMAGE_FUNCTION + "\n",
        "ability damage scaling",
    )
    text = replace_section(
        text,
        "                    // ---- Sweep for stray creatures (script-spawned, respawned) ----\n",
        "                // ---- Auto-rez when out of combat ----\n",
        SWEEP,
        "native grid sweep",
    )
    phase_start = "                                // Promote to boss creature\n"
    phase_end = "                                phaseCreatureFound = true;\n"
    start = text.find(phase_start)
    end = text.find(phase_end, start + 1) if start >= 0 else -1
    if start < 0 or end < 0:
        raise DungeonMasterSourcePatchError("phase boss handling: section markers not found")
    end += len(phase_end)
    text = text[:start] + PHASE + text[end:]
    text = replace_once(
        text,
        "    Loot& loot = creature->loot;\n    loot.clear();\n",
        "    Loot& loot = creature->loot;\n\n"
        "    // Aventureros: preserve native WoW loot in normal mode and add challenge drops.\n"
        "    bool preserveNativeLoot = session->RoguelikeRunId == 0;\n"
        "    if (!preserveNativeLoot)\n        loot.clear();\n",
        "native loot",
    )
    return text


def transform_unit(text: str) -> str:
    call = "        ScaleDamage(target, attacker, damage);\n"
    if text.count(call) != 2:
        raise DungeonMasterSourcePatchError(
            f"unit damage calls: expected two damage calls, found {text.count(call)}"
        )
    text = text.replace(call, "        ScaleDamage(target, attacker, damage, true);\n", 1)
    text = replace_once(
        text,
        "        ScaleDamage(target, attacker, udmg);\n",
        "        ScaleDamage(target, attacker, udmg, true);\n",
        "spell damage call",
    )
    text = text.replace(call, "        ScaleDamage(target, attacker, damage, false);\n", 1)
    text = replace_once(
        text,
        "    void ScaleDamage(Unit* target, Unit* attacker, uint32& damage)\n",
        "    void ScaleDamage(Unit* target, Unit* attacker, uint32& damage, bool scaleSessionAbility)\n",
        "ScaleDamage signature",
    )
    text = replace_section(
        text,
        "            // Session creature damage — scale bosses, pass through trash\n",
        "        // Non-session attacker (environmental hazards, traps, etc.)\n",
        UNIT_SESSION,
        "session damage block",
    )
    return text


def transform_gossip(text: str) -> str:
    old = r'''        else if (action == GOSSIP_ACTION_SCALE_PARTY)
        {
            { std::lock_guard<std::mutex> lk(sSelMutex); sSelections[player->GetGUID()].ScaleToParty = true; }
            ShowThemeMenu(player, creature);
        }
        else if (action == GOSSIP_ACTION_SCALE_TIER)
        {
            { std::lock_guard<std::mutex> lk(sSelMutex); sSelections[player->GetGUID()].ScaleToParty = false; }
            ShowThemeMenu(player, creature);
        }
'''
    new = r'''        else if (action == GOSSIP_ACTION_SCALE_PARTY)
        {
            { std::lock_guard<std::mutex> lk(sSelMutex);
              sSelections[player->GetGUID()].ScaleToParty = true;
              sSelections[player->GetGUID()].ThemeId = 1;
              sSelections[player->GetGUID()].DungeonPage = 0; }
            ShowDungeonMenu(player, creature);
        }
        else if (action == GOSSIP_ACTION_SCALE_TIER)
        {
            { std::lock_guard<std::mutex> lk(sSelMutex);
              sSelections[player->GetGUID()].ScaleToParty = false;
              sSelections[player->GetGUID()].ThemeId = 1;
              sSelections[player->GetGUID()].DungeonPage = 0; }
            ShowDungeonMenu(player, creature);
        }
'''
    text = replace_once(text, old, new, "normal gossip flow")
    old_summary = (
        '        snprintf(buf, sizeof(buf), "  Theme:      |cFF00FF00%s|r", theme ? theme->Name.c_str() : "?");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage(buf);\n'
    )
    text = replace_once(
        text,
        old_summary,
        '        ChatHandler(player->GetSession()).SendSysMessage(\n'
        '            "  Theme:      |cFF00FF00Original inhabitants|r");\n',
        "normal summary",
    )
    old_info = (
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF3.|r Pick a creature theme");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF4.|r Select a dungeon or go random");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF5.|r You\'ll be teleported to a cleared instance");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF6.|r Defeat the boss to complete the challenge");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF7.|r Collect gold and gear rewards!");\n'
    )
    new_info = (
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF3.|r The dungeon keeps its original inhabitants and mechanics");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF4.|r Select a dungeon or go random");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF5.|r Native creatures are scaled to the challenge level");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF6.|r Defeat the original boss to complete the challenge");\n'
        '        ChatHandler(player->GetSession()).SendSysMessage("|cFFFFFFFF7.|r Collect native loot plus challenge rewards!");\n'
    )
    return replace_once(text, old_info, new_info, "normal info text")


TRANSFORMS = {
    FILES[0]: transform_header,
    FILES[1]: transform_mgr,
    FILES[2]: transform_unit,
    FILES[3]: transform_gossip,
}


def backup_path(core: Path, rel: str) -> Path:
    return core / BACKUP_ROOT / rel


def is_patched(texts: dict[str, str]) -> bool:
    present = [marker in texts[rel] for rel, marker in PATCH_MARKERS]
    if any(present) and not all(present):
        missing = [marker for (rel, marker), ok in zip(PATCH_MARKERS, present) if not ok]
        raise DungeonMasterSourcePatchError(
            "Dungeon Master source is partially patched; missing markers: " + "; ".join(missing)
        )
    return all(present)


def install(core: Path) -> list[str]:
    core = core.expanduser().resolve()
    original = {rel: read(core / rel) for rel in FILES}
    if is_patched(original):
        verify(core)
        print("Dungeon Master Adventurer compatibility already applied.")
        return []

    # Compute every change first. A bad upstream anchor aborts before any write.
    patched = {rel: TRANSFORMS[rel](original[rel]) for rel in FILES}
    for rel in FILES:
        bp = backup_path(core, rel)
        if not bp.exists():
            bp.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(core / rel, bp)
    for rel in FILES:
        (core / rel).write_text(patched[rel], encoding="utf-8")
    verify(core)
    print("Dungeon Master Adventurer compatibility applied:")
    for rel in FILES:
        print(f"  {rel}")
    print("  rebuild required: yes")
    return list(FILES)


def verify(core: Path) -> None:
    core = core.expanduser().resolve()
    texts = {rel: read(core / rel) for rel in FILES}
    if not is_patched(texts):
        raise DungeonMasterSourcePatchError("Dungeon Master Adventurer compatibility is not installed")
    unit = texts[FILES[2]]
    expected = (
        "ScaleDamage(target, attacker, damage, true);",
        "ScaleDamage(target, attacker, udmg, true);",
        "ScaleDamage(target, attacker, damage, false);",
    )
    for needle in expected:
        if unit.count(needle) != 1:
            raise DungeonMasterSourcePatchError(f"damage hook verification failed for {needle}")


def rollback(core: Path) -> list[str]:
    core = core.expanduser().resolve()
    texts = {rel: read(core / rel) for rel in FILES}
    if not is_patched(texts):
        return []
    missing = [rel for rel in FILES if not backup_path(core, rel).is_file()]
    if missing:
        raise DungeonMasterSourcePatchError(
            "Dungeon Master source backup missing: " + ", ".join(missing)
        )
    for rel in FILES:
        target = core / rel
        bp = backup_path(core, rel)
        target.write_bytes(bp.read_bytes())
    shutil.rmtree(core / BACKUP_ROOT)
    print("Dungeon Master Adventurer compatibility rolled back.")
    return list(FILES)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("install", "verify", "rollback"))
    parser.add_argument("--core-dir", required=True, type=Path)
    args = parser.parse_args()
    try:
        {"install": install, "verify": verify, "rollback": rollback}[args.command](args.core_dir)
        return 0
    except (OSError, DungeonMasterSourcePatchError) as exc:
        print(f"ERROR: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
