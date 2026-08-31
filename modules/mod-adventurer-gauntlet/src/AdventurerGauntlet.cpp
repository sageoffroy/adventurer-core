#include "Chat.h"
#include "Config.h"
#include "Creature.h"
#include "CreatureScript.h"
#include "Group.h"
#include "Map.h"
#include "ObjectAccessor.h"
#include "Player.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "ScriptedCreature.h"
#include "ScriptedGossip.h"
#include "TaskScheduler.h"

#include <algorithm>
#include <array>
#include <string>
#include <unordered_map>
#include <vector>

namespace
{
bool GauntletEnabled = true;
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
std::unordered_map<uint32, uint8> PendingRunLevels;
std::unordered_map<uint32, uint8> ActiveRunInstanceLevels;

constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 KhadgarIntroText = 910000;
constexpr uint32 KhadgarConfirmText = 910001;
constexpr uint32 KhadgarCastVisual = 69659;
constexpr uint32 KhadgarTeleportVisual = 41232;

constexpr uint32 RagefireMapId = 389;
constexpr float RagefireX = 3.81f;
constexpr float RagefireY = -14.82f;
constexpr float RagefireZ = -17.84f;
constexpr float RagefireO = 4.39f;
constexpr uint32 RagefireFinalBossEntry = 11520;

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

uint8 GetHighestPartyLevel(std::vector<Player*> const& members)
{
    uint8 level = 1;
    for (Player* member : members)
        if (member)
            level = std::max<uint8>(level, member->GetLevel());
    return level;
}

std::vector<Player*> GetLivingRunMembers(Map* map)
{
    std::vector<Player*> members;
    if (!map)
        return members;

    for (auto const& ref : map->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!player || !player->IsAlive())
            continue;

        if (PendingRunNames.find(player->GetGUID().GetCounter()) != PendingRunNames.end())
            members.push_back(player);
    }

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
        if (!member->IsAlive())
        {
            error = "Todos los integrantes deben estar vivos para comenzar.";
            return false;
        }
    }

    return true;
}

void RegisterPendingRun(std::vector<Player*> const& members, std::string const& companyName, uint8 runLevel)
{
    for (Player* member : members)
    {
        uint32 guid = member->GetGUID().GetCounter();
        PendingRunNames[guid] = companyName;
        PendingRunLevels[guid] = runLevel;
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

bool GetPendingRunLevel(Player* player, uint8& level)
{
    if (!player)
        return false;

    auto itr = PendingRunLevels.find(player->GetGUID().GetCounter());
    if (itr == PendingRunLevels.end())
        return false;

    level = itr->second;
    return true;
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

bool TeleportParty(std::vector<Player*> const& members, uint32 mapId, float x, float y, float z, float o)
{
    bool success = true;

    for (Player* member : members)
    {
        if (!member || !member->IsAlive())
            continue;

        member->CastSpell(member, KhadgarTeleportVisual, true);

        if (!member->TeleportTo(mapId, x, y, z, o, TELE_TO_GM_MODE))
        {
            success = false;
            ChatHandler(member->GetSession()).PSendSysMessage(
                "Khadgar no pudo abrir el portal hacia {} para este aventurero.",
                GetGauntletDungeonName(mapId));
        }
    }

    return success;
}

void AnnounceRunStart(std::vector<Player*> const& members, std::string const& companyName, uint8 runLevel)
{
    for (Player* member : members)
    {
        ChatHandler(member->GetSession()).PSendSysMessage(
            "Khadgar acepta el desafio. Desde ahora seran conocidos como |cff00ff00{}|r.",
            companyName);
        ChatHandler(member->GetSession()).PSendSysMessage(
            "La expedicion queda fijada al nivel |cffffd100{}|r, el mas alto del grupo.",
            runLevel);
        ChatHandler(member->GetSession()).SendSysMessage(
            "Khadgar comienza a preparar el portal hacia |cffffd100Sima Ignea|r.");
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
    PendingRunLevels.erase(guid);
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

    player->ResurrectPlayer(1.0f);
    player->SpawnCorpseBones();

    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cffff2020{} ha caido.|r El desafio termina aqui para este aventurero.",
        companyName);
    ChatHandler(player->GetSession()).SendSysMessage(
        "Khadgar te ha devuelto. Durante el desarrollo puedes volver a intentar el desafio.");
}

void FinishRagefireAndSummonKhadgar(Creature* finalBoss)
{
    if (!finalBoss || finalBoss->GetMapId() != RagefireMapId || finalBoss->GetEntry() != RagefireFinalBossEntry)
        return;

    Map* map = finalBoss->GetMap();
    std::vector<Player*> survivors = GetLivingRunMembers(map);
    if (survivors.empty())
        return;

    Creature* khadgar = finalBoss->SummonCreature(
        KhadgarEntry,
        finalBoss->GetPositionX() + 2.5f,
        finalBoss->GetPositionY() + 1.5f,
        finalBoss->GetPositionZ(),
        finalBoss->GetOrientation());

    for (Player* player : survivors)
    {
        ChatHandler(player->GetSession()).SendSysMessage(
            "|cff00ff00Sima Ignea completada.|r");
        ChatHandler(player->GetSession()).SendSysMessage(
            khadgar
                ? "Khadgar ha llegado. Habla con el cuando la expedicion este lista para continuar."
                : "Khadgar intento llegar, pero no pudo materializarse junto al jefe.");
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

        uint8 pendingRunLevel = 0;
        if (!GetPendingRunLevel(player, pendingRunLevel))
            return;

        // Bind the player to the actual Gauntlet instance so logging out and back
        // in does not make the normal instance-login validation eject them.
        player->BindToInstance();

        auto [itr, inserted] = ActiveRunInstanceLevels.emplace(instanceId, pendingRunLevel);
        if (!inserted)
            return;

        map->LoadAllGrids();

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

        if (!IsRewardCreature(creature))
        {
            creature->loot.clear();
            creature->RemoveDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        }

        if (creature->GetMapId() == RagefireMapId && creature->GetEntry() == RagefireFinalBossEntry)
            FinishRagefireAndSummonKhadgar(creature);
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
    ACTION_LEARN_MORE = GOSSIP_ACTION_INFO_DEF + 1,
    ACTION_START = GOSSIP_ACTION_INFO_DEF + 2,
    ACTION_STATUS = GOSSIP_ACTION_INFO_DEF + 3,
    ACTION_CONTINUE = GOSSIP_ACTION_INFO_DEF + 4,
};

enum KhadgarTravelDestination
{
    KHADGAR_TRAVEL_NONE = 0,
    KHADGAR_TRAVEL_RAGEFIRE = 1,
    KHADGAR_TRAVEL_DEADMINES = 2,
};

class npc_adventurer_gauntlet_khadgar : public CreatureScript
{
public:
    npc_adventurer_gauntlet_khadgar() : CreatureScript("npc_adventurer_gauntlet_khadgar") { }

    struct npc_adventurer_gauntlet_khadgarAI : public ScriptedAI
    {
        npc_adventurer_gauntlet_khadgarAI(Creature* creature) : ScriptedAI(creature) { }

        void BeginTravel(std::vector<Player*> const& members, uint8 destination)
        {
            if (_travelInProgress || members.empty())
                return;

            _travelInProgress = true;
            _destination = destination;
            _travellers.clear();
            _travellers.reserve(members.size());
            for (Player* member : members)
                if (member)
                    _travellers.push_back(member->GetGUID());

            me->ReplaceAllNpcFlags(UNIT_NPC_FLAG_NONE);
            DoCastSelf(KhadgarCastVisual, false);

            _scheduler.Schedule(2500ms, [this](TaskContext /*context*/)
            {
                std::vector<Player*> travellers;
                travellers.reserve(_travellers.size());
                for (ObjectGuid const& guid : _travellers)
                    if (Player* player = ObjectAccessor::FindPlayer(guid))
                        travellers.push_back(player);

                bool success = false;
                if (_destination == KHADGAR_TRAVEL_RAGEFIRE)
                    success = TeleportParty(travellers, RagefireMapId, RagefireX, RagefireY, RagefireZ, RagefireO);
                else if (_destination == KHADGAR_TRAVEL_DEADMINES)
                {
                    for (Player* player : travellers)
                        ChatHandler(player->GetSession()).SendSysMessage(
                            "Khadgar abre el camino hacia |cffffd100Minas de la Muerte|r.");

                    success = TeleportParty(travellers, DeadminesMapId, DeadminesX, DeadminesY, DeadminesZ, DeadminesO);
                }

                if (!success)
                    for (Player* player : travellers)
                        ChatHandler(player->GetSession()).SendSysMessage(
                            "El portal de Khadgar no pudo transportar a toda la expedicion.");

                me->CastSpell(me, KhadgarTeleportVisual, true);

                uint8 finishedDestination = _destination;
                _destination = KHADGAR_TRAVEL_NONE;
                _travellers.clear();
                _travelInProgress = false;

                if (finishedDestination == KHADGAR_TRAVEL_DEADMINES)
                    me->DespawnOrUnsummon(1000ms);
                else
                    me->ReplaceAllNpcFlags(UNIT_NPC_FLAG_GOSSIP);
            });
        }

        void UpdateAI(uint32 diff) override
        {
            _scheduler.Update(diff);
        }

    private:
        TaskScheduler _scheduler;
        std::vector<ObjectGuid> _travellers;
        uint8 _destination = KHADGAR_TRAVEL_NONE;
        bool _travelInProgress = false;
    };

    CreatureAI* GetAI(Creature* creature) const override
    {
        return new npc_adventurer_gauntlet_khadgarAI(creature);
    }

    bool OnGossipHello(Player* player, Creature* creature) override
    {
        if (!GauntletEnabled)
        {
            ChatHandler(player->GetSession()).SendSysMessage("El Desafio de Khadgar esta deshabilitado.");
            CloseGossipMenuFor(player);
            return true;
        }

        if (creature->GetMapId() == RagefireMapId && GetPendingRunName(player))
        {
            AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Estamos listos. Abre el camino a la siguiente mazmorra.", GOSSIP_SENDER_MAIN, ACTION_CONTINUE);
            AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Recuerdame el nombre de nuestra compania.", GOSSIP_SENDER_MAIN, ACTION_STATUS);
            SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
            return true;
        }

        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Quiero saber mas.", GOSSIP_SENDER_MAIN, ACTION_LEARN_MORE);
        SendGossipMenuFor(player, KhadgarIntroText, creature->GetGUID());
        return true;
    }

    bool OnGossipSelect(Player* player, Creature* creature, uint32 /*sender*/, uint32 action) override
    {
        ClearGossipMenuFor(player);

        switch (action)
        {
            case ACTION_LEARN_MORE:
                AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Si. Quiero afrontar el desafio.", GOSSIP_SENDER_MAIN, ACTION_START);
                SendGossipMenuFor(player, KhadgarConfirmText, creature->GetGUID());
                return true;
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

                uint8 runLevel = GetHighestPartyLevel(members);
                std::string companyName = GenerateCompanyName();
                ResetPartyInstances(player);
                RegisterPendingRun(members, companyName, runLevel);
                AnnounceRunStart(members, companyName, runLevel);

                static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                    members,
                    KHADGAR_TRAVEL_RAGEFIRE);

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_CONTINUE:
            {
                if (creature->GetMapId() != RagefireMapId || !GetPendingRunName(player))
                {
                    CloseGossipMenuFor(player);
                    return true;
                }

                if (Group* group = player->GetGroup())
                {
                    if (!group->IsLeader(player->GetGUID()))
                    {
                        ChatHandler(player->GetSession()).SendSysMessage(
                            "Solo el lider de la expedicion puede pedirle a Khadgar que abra el siguiente portal.");
                        CloseGossipMenuFor(player);
                        return true;
                    }
                }

                std::vector<Player*> survivors = GetLivingRunMembers(player->GetMap());
                if (survivors.empty())
                {
                    CloseGossipMenuFor(player);
                    return true;
                }

                for (Player* survivor : survivors)
                    ChatHandler(survivor->GetSession()).SendSysMessage(
                        "Khadgar comienza a preparar el siguiente portal.");

                static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                    survivors,
                    KHADGAR_TRAVEL_DEADMINES);

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_STATUS:
                if (std::string const* companyName = GetPendingRunName(player))
                {
                    uint8 runLevel = 0;
                    GetPendingRunLevel(player, runLevel);
                    ChatHandler(player->GetSession()).PSendSysMessage(
                        "Su compania es |cff00ff00{}|r. Nivel de expedicion: |cffffd100{}|r.",
                        *companyName,
                        runLevel);
                }
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
