#include "Chat.h"
#include "Config.h"
#include "Creature.h"
#include "CreatureScript.h"
#include "Group.h"
#include "Map.h"
#include "Player.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "ScriptedGossip.h"

#include <array>
#include <string>
#include <unordered_map>
#include <vector>

namespace
{
bool GauntletEnabled = true;
uint8 GauntletStartLevel = 1;
uint8 GauntletMinPlayers = 1;
uint8 GauntletMaxPlayers = 5;

struct RunReturnPoint
{
    uint32 MapId = 0;
    float X = 0.0f;
    float Y = 0.0f;
    float Z = 0.0f;
    float O = 0.0f;
};

std::unordered_map<uint32, std::string> PendingRunNames;
std::unordered_map<uint32, RunReturnPoint> RunReturnPoints;
std::unordered_map<uint32, uint8> ActiveRunInstanceLevels;

constexpr uint32 RagefireMapId = 389;
constexpr float RagefireX = 3.81f;
constexpr float RagefireY = -14.82f;
constexpr float RagefireZ = -17.84f;
constexpr float RagefireO = 4.39f;
constexpr uint32 RagefireFinalBossEntry = 11520; // Taragaman the Hungerer

constexpr uint32 DeadminesMapId = 36;
constexpr float DeadminesX = -16.4f;
constexpr float DeadminesY = -383.07f;
constexpr float DeadminesZ = 61.78f;
constexpr float DeadminesO = 1.86f;

constexpr std::array<char const*, 12> CompanyTitles = {
    "Retirados", "Cuervos", "Exiliados", "Errantes", "Juramentados", "Centinelas",
    "Desventurados", "Veteranos", "Herederos", "Escudos", "Perdidos", "Caminantes"
};

constexpr std::array<char const*, 12> CompanyPlaces = {
    "Lordaeron", "Karazhan", "Stromgarde", "Gilneas", "Forjaz", "Dalaran",
    "Quel'Thalas", "Alterac", "Tirisfal", "Arathi", "Dun Morogh", "Kalimdor"
};

bool IsGauntletDungeon(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

char const* GetGauntletDungeonName(uint32 mapId)
{
    switch (mapId)
    {
        case RagefireMapId:
            return "Sima Ignea";
        case DeadminesMapId:
            return "Minas de la Muerte";
        default:
            return "mazmorra";
    }
}

bool IsRareCreature(Creature const* creature)
{
    if (!creature)
        return false;

    uint32 rank = creature->GetCreatureTemplate()->rank;
    return rank == CREATURE_ELITE_RARE || rank == CREATURE_ELITE_RAREELITE;
}

bool IsRewardCreature(Creature const* creature)
{
    return creature && (creature->IsDungeonBoss() || IsRareCreature(creature));
}

std::string GenerateCompanyName()
{
    return std::string("Los ") + CompanyTitles[urand(0, CompanyTitles.size() - 1)] +
        " de " + CompanyPlaces[urand(0, CompanyPlaces.size() - 1)];
}

std::vector<Player*> GetPartyMembers(Player* leader)
{
    std::vector<Player*> members;
    Group* group = leader->GetGroup();

    if (!group)
    {
        members.push_back(leader);
        return members;
    }

    for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
        if (Player* member = ref->GetSource())
            members.push_back(member);

    return members;
}

bool ValidateParty(Player* player, std::vector<Player*>& members, std::string& error)
{
    Group* group = player->GetGroup();
    if (group && !group->IsLeader(player->GetGUID()))
    {
        error = "Solo el lider del grupo puede aceptar el Desafio de Khadgar.";
        return false;
    }

    members = GetPartyMembers(player);
    uint32 expectedCount = group ? group->GetMembersCount() : 1;
    if (members.size() != expectedCount)
    {
        error = "Todos los integrantes del grupo deben estar conectados para comenzar.";
        return false;
    }

    if (members.size() < GauntletMinPlayers || members.size() > GauntletMaxPlayers)
    {
        error = "El grupo no tiene una cantidad valida de aventureros para este desafio.";
        return false;
    }

    for (Player* member : members)
    {
        if (member->GetLevel() != GauntletStartLevel)
        {
            error = "Todos los integrantes deben comenzar el desafio en el nivel requerido.";
            return false;
        }

        if (!member->IsAlive())
        {
            error = "Todos los integrantes deben estar vivos para comenzar.";
            return false;
        }
    }

    return true;
}

void RegisterPendingRun(std::vector<Player*> const& members, std::string const& companyName)
{
    for (Player* member : members)
    {
        uint32 guid = member->GetGUID().GetCounter();
        PendingRunNames[guid] = companyName;
        RunReturnPoints[guid] = {
            member->GetMapId(),
            member->GetPositionX(),
            member->GetPositionY(),
            member->GetPositionZ(),
            member->GetOrientation()
        };
    }
}

std::string const* GetPendingRunName(Player* player)
{
    auto itr = PendingRunNames.find(player->GetGUID().GetCounter());
    return itr == PendingRunNames.end() ? nullptr : &itr->second;
}

bool GetActiveRunLevel(Creature const* creature, uint8& level)
{
    if (!creature || !IsGauntletDungeon(creature->GetMapId()) || creature->IsPet() || creature->IsTrigger())
        return false;

    auto itr = ActiveRunInstanceLevels.find(creature->GetInstanceId());
    if (itr == ActiveRunInstanceLevels.end())
        return false;

    level = itr->second;
    return true;
}

bool IsActiveRunCreature(Creature const* creature)
{
    uint8 level = 0;
    return GetActiveRunLevel(creature, level);
}

void ResetPartyInstances(Player* leader)
{
    if (Group* group = leader->GetGroup())
        group->ResetInstances(INSTANCE_RESET_ALL, false, leader);
    else
        Player::ResetInstances(leader->GetGUID(), INSTANCE_RESET_ALL, false);
}

bool TeleportPartyToRagefire(std::vector<Player*> const& members)
{
    bool success = true;

    for (Player* member : members)
    {
        if (!member->TeleportTo(
                RagefireMapId,
                RagefireX,
                RagefireY,
                RagefireZ,
                RagefireO,
                TELE_TO_GM_MODE))
        {
            success = false;
            ChatHandler(member->GetSession()).SendSysMessage(
                "Khadgar no pudo abrir el portal hacia Sima Ignea para este aventurero.");
        }
    }

    return success;
}

void AnnounceRunStart(std::vector<Player*> const& members, std::string const& companyName)
{
    for (Player* member : members)
    {
        ChatHandler(member->GetSession()).PSendSysMessage(
            "Khadgar acepta el desafio. Desde ahora seran conocidos como |cff00ff00{}|r.",
            companyName);
        ChatHandler(member->GetSession()).SendSysMessage(
            "Primer destino: |cffffd100Sima Ignea|r.");
    }
}

bool InstanceStillHasLivingAdventurers(Map* map, Player* fallen)
{
    if (!map)
        return false;

    for (auto const& ref : map->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!player || player == fallen || !player->IsAlive())
            continue;

        if (PendingRunNames.find(player->GetGUID().GetCounter()) != PendingRunNames.end())
            return true;
    }

    return false;
}

void ReturnFallenAdventurer(Player* player)
{
    if (!player || !IsGauntletDungeon(player->GetMapId()))
        return;

    uint32 guid = player->GetGUID().GetCounter();
    auto runItr = PendingRunNames.find(guid);
    auto returnItr = RunReturnPoints.find(guid);
    if (runItr == PendingRunNames.end() || returnItr == RunReturnPoints.end())
        return;

    uint32 instanceId = player->GetInstanceId();
    std::string companyName = runItr->second;
    RunReturnPoint returnPoint = returnItr->second;
    bool runEnded = !InstanceStillHasLivingAdventurers(player->GetMap(), player);

    PendingRunNames.erase(runItr);
    RunReturnPoints.erase(returnItr);
    if (runEnded)
        ActiveRunInstanceLevels.erase(instanceId);

    player->TeleportTo(
        returnPoint.MapId,
        returnPoint.X,
        returnPoint.Y,
        returnPoint.Z,
        returnPoint.O,
        TELE_TO_GM_MODE);

    // Development behavior: keep the loop quick while the permanent Fallen
    // state and leaderboard persistence are still being built.
    player->ResurrectPlayer(1.0f);
    player->SpawnCorpseBones();

    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cffff2020{} ha caido.|r El desafio termina aqui para este aventurero.",
        companyName);
    ChatHandler(player->GetSession()).SendSysMessage(
        "Khadgar te ha devuelto. Durante el desarrollo puedes volver a intentar el desafio.");
}

void TransitionRagefireToDeadmines(Creature* finalBoss)
{
    if (!finalBoss || finalBoss->GetMapId() != RagefireMapId || finalBoss->GetEntry() != RagefireFinalBossEntry)
        return;

    Map* map = finalBoss->GetMap();
    if (!map)
        return;

    std::vector<Player*> survivors;
    for (auto const& ref : map->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!player || !player->IsAlive())
            continue;

        if (PendingRunNames.find(player->GetGUID().GetCounter()) != PendingRunNames.end())
            survivors.push_back(player);
    }

    if (survivors.empty())
        return;

    for (Player* player : survivors)
    {
        ChatHandler(player->GetSession()).SendSysMessage(
            "|cff00ff00Sima Ignea completada.|r Khadgar abre el siguiente portal.");
        ChatHandler(player->GetSession()).SendSysMessage(
            "Segundo destino: |cffffd100Minas de la Muerte|r.");

        if (!player->TeleportTo(
                DeadminesMapId,
                DeadminesX,
                DeadminesY,
                DeadminesZ,
                DeadminesO,
                TELE_TO_GM_MODE))
        {
            ChatHandler(player->GetSession()).SendSysMessage(
                "Khadgar no pudo abrir el portal hacia Minas de la Muerte.");
        }
    }
}
}

class AdventurerGauntletConfigScript : public WorldScript
{
public:
    AdventurerGauntletConfigScript() : WorldScript("AdventurerGauntletConfigScript") { }

    void OnBeforeConfigLoad(bool /*reload*/) override
    {
        GauntletEnabled = sConfigMgr->GetOption<bool>("AdventurerGauntlet.Enable", true);
        GauntletStartLevel = sConfigMgr->GetOption<uint8>("AdventurerGauntlet.StartLevel", 1);
        GauntletMinPlayers = sConfigMgr->GetOption<uint8>("AdventurerGauntlet.MinPlayers", 1);
        GauntletMaxPlayers = sConfigMgr->GetOption<uint8>("AdventurerGauntlet.MaxPlayers", 5);
    }
};

class AdventurerGauntletCreatureScript : public AllCreatureScript
{
public:
    AdventurerGauntletCreatureScript() : AllCreatureScript("AdventurerGauntletCreatureScript") { }

    void OnBeforeCreatureSelectLevel(CreatureTemplate const* /*creatureTemplate*/, Creature* creature, uint8& level) override
    {
        uint8 runLevel = 0;
        if (GauntletEnabled && GetActiveRunLevel(creature, runLevel))
            level = runLevel;
    }
};

class AdventurerGauntletMapScript : public AllMapScript
{
public:
    AdventurerGauntletMapScript() : AllMapScript("AdventurerGauntletMapScript") { }

    void OnPlayerEnterAll(Map* map, Player* player) override
    {
        if (!GauntletEnabled || !map || !player || !IsGauntletDungeon(map->GetId()) || !GetPendingRunName(player))
            return;

        uint32 instanceId = map->GetInstanceId();
        if (!instanceId)
            return;

        auto [itr, inserted] = ActiveRunInstanceLevels.emplace(instanceId, player->GetLevel());
        if (!inserted)
            return;

        // Mark the instance first, then load its grids. Creatures created while loading
        // pass through OnBeforeCreatureSelectLevel and receive the gauntlet level using
        // AzerothCore's own stock creature-stat calculation.
        map->LoadAllGrids();

        // The entrance grid can already be loaded by the time this hook fires. Re-run
        // stock SelectLevel for those creatures so the whole dungeon uses the same level.
        for (auto const& [spawnId, creature] : map->GetCreatureBySpawnIdStore())
        {
            (void)spawnId;
            uint8 runLevel = 0;
            if (!GetActiveRunLevel(creature, runLevel))
                continue;

            creature->SelectLevel();
            if (creature->IsAlive())
                creature->SetHealth(creature->GetMaxHealth());
        }

        ChatHandler(player->GetSession()).PSendSysMessage(
            "El desafio adapta {} al nivel |cffffd100{}|r.",
            GetGauntletDungeonName(map->GetId()),
            itr->second);
    }

    void OnDestroyInstance(MapInstanced* /*mapInstanced*/, Map* map) override
    {
        if (map && IsGauntletDungeon(map->GetId()))
            ActiveRunInstanceLevels.erase(map->GetInstanceId());
    }
};

class AdventurerGauntletUnitScript : public UnitScript
{
public:
    AdventurerGauntletUnitScript() : UnitScript("AdventurerGauntletUnitScript") { }

    void OnUnitDeath(Unit* unit, Unit* /*killer*/) override
    {
        if (!GauntletEnabled || !unit)
            return;

        Creature* creature = unit->ToCreature();
        if (!creature || !IsActiveRunCreature(creature))
            return;

        // Trash never drops anything inside the gauntlet. Bosses and rares are
        // deliberately preserved because they will use the expedition reward system.
        if (!IsRewardCreature(creature))
        {
            creature->loot.clear();
            creature->RemoveDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        }

        if (creature->GetMapId() == RagefireMapId && creature->GetEntry() == RagefireFinalBossEntry)
            TransitionRagefireToDeadmines(creature);
    }
};

class AdventurerGauntletPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletPlayerScript() : PlayerScript("AdventurerGauntletPlayerScript") { }

    void OnPlayerJustDied(Player* player) override
    {
        if (GauntletEnabled)
            ReturnFallenAdventurer(player);
    }
};

enum KhadgarGauntletActions
{
    ACTION_START = GOSSIP_ACTION_INFO_DEF + 1,
    ACTION_EXPLAIN = GOSSIP_ACTION_INFO_DEF + 2,
    ACTION_STATUS = GOSSIP_ACTION_INFO_DEF + 3,
};

class npc_adventurer_gauntlet_khadgar : public CreatureScript
{
public:
    npc_adventurer_gauntlet_khadgar() : CreatureScript("npc_adventurer_gauntlet_khadgar") { }

    bool OnGossipHello(Player* player, Creature* creature) override
    {
        if (!GauntletEnabled)
        {
            ChatHandler(player->GetSession()).SendSysMessage("El Desafio de Khadgar esta deshabilitado.");
            CloseGossipMenuFor(player);
            return true;
        }

        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Estamos listos. Proponenos un desafio.", GOSSIP_SENDER_MAIN, ACTION_START);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Explicame como funciona el desafio.", GOSSIP_SENDER_MAIN, ACTION_EXPLAIN);

        if (GetPendingRunName(player))
            AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Recordame el nombre de nuestra compania.", GOSSIP_SENDER_MAIN, ACTION_STATUS);

        SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
        return true;
    }

    bool OnGossipSelect(Player* player, Creature* /*creature*/, uint32 /*sender*/, uint32 action) override
    {
        ClearGossipMenuFor(player);

        switch (action)
        {
            case ACTION_START:
            {
                std::vector<Player*> members;
                std::string error;
                if (!ValidateParty(player, members, error))
                {
                    ChatHandler(player->GetSession()).SendSysMessage(error.c_str());
                    CloseGossipMenuFor(player);
                    return true;
                }

                std::string companyName = GenerateCompanyName();
                ResetPartyInstances(player);
                RegisterPendingRun(members, companyName);
                AnnounceRunStart(members, companyName);

                if (!TeleportPartyToRagefire(members))
                    ChatHandler(player->GetSession()).SendSysMessage(
                        "El portal no pudo transportar a todos los integrantes del grupo.");

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_EXPLAIN:
                ChatHandler(player->GetSession()).SendSysMessage(
                    "El desafio comienza con personajes de nivel 1 y encadena mazmorras hasta que no quede ningun aventurero vivo.");
                ChatHandler(player->GetSession()).SendSysMessage(
                    "Por ahora, la primera prueba comienza en Sima Ignea y continua en Minas de la Muerte.");
                CloseGossipMenuFor(player);
                return true;
            case ACTION_STATUS:
                if (std::string const* companyName = GetPendingRunName(player))
                    ChatHandler(player->GetSession()).PSendSysMessage("Su compania es |cff00ff00{}|r.", *companyName);
                CloseGossipMenuFor(player);
                return true;
            default:
                CloseGossipMenuFor(player);
                return true;
        }
    }
};

void AddAdventurerGauntletScripts()
{
    new AdventurerGauntletConfigScript();
    new AdventurerGauntletCreatureScript();
    new AdventurerGauntletMapScript();
    new AdventurerGauntletUnitScript();
    new AdventurerGauntletPlayerScript();
    new npc_adventurer_gauntlet_khadgar();
}
