#include "CampaignCatalog.h"
#include "Chat.h"
#include "Config.h"
#include "Creature.h"
#include "CreatureScript.h"
#include "DungeonCatalog.h"
#include "Group.h"
#include "Map.h"
#include "ObjectAccessor.h"
#include "Player.h"
#include "Random.h"
#include "RunProgress.h"
#include "ScriptMgr.h"
#include "ScriptedCreature.h"
#include "ScriptedGossip.h"
#include "SharedDefines.h"
#include "TaskScheduler.h"

#include <algorithm>
#include <array>
#include <string>
#include <unordered_map>
#include <unordered_set>
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
std::unordered_map<uint32, std::string> PendingRunCampaigns;
std::unordered_map<uint32, uint8> PendingRunCampaignStages;
std::unordered_map<uint32, uint8> ActiveRunInstanceLevels;
std::unordered_map<uint32, uint8> ActiveRunNativeMinLevels;
std::unordered_map<uint32, uint8> RagefireBossProgress;
std::unordered_set<uint32> AllowedGauntletTeleports;

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
constexpr uint32 RagefireOggleflintEntry = 11517;
constexpr uint32 RagefireJergoshEntry = 11518;
constexpr uint32 RagefireBazzalanEntry = 11519;
constexpr uint32 RagefireFinalBossEntry = 11520;
constexpr uint8 RagefireAllBossesMask = 0x0F;
constexpr uint8 RagefireCompletedMask = 0x80;

constexpr uint32 DeadminesMapId = 36;
constexpr float DeadminesX = -16.4f;
constexpr float DeadminesY = -383.07f;
constexpr float DeadminesZ = 61.78f;
constexpr float DeadminesO = 1.86f;

constexpr uint32 HellfireRampartsMapId = 543;
constexpr float HellfireRampartsX = -1355.24f;
constexpr float HellfireRampartsY = 1641.12f;
constexpr float HellfireRampartsZ = 68.2491f;
constexpr float HellfireRampartsO = 0.6687f;

constexpr uint32 AzjolNerubMapId = 601;
constexpr float AzjolNerubX = 413.314f;
constexpr float AzjolNerubY = 795.968f;
constexpr float AzjolNerubZ = 831.351f;
constexpr float AzjolNerubO = 5.5f;

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
    return AdventurerGauntlet::DungeonCatalog::IsSupportedDungeonMap(mapId);
}

char const* GetGauntletDungeonName(uint32 mapId)
{
    if (auto const* dungeon = AdventurerGauntlet::DungeonCatalog::GetDungeon(mapId))
        return dungeon->Name;

    return "mazmorra";
}

uint8 GetRagefireBossBit(uint32 entry)
{
    switch (entry)
    {
        case RagefireOggleflintEntry: return 0x01;
        case RagefireJergoshEntry: return 0x02;
        case RagefireBazzalanEntry: return 0x04;
        case RagefireFinalBossEntry: return 0x08;
        default: return 0;
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

bool FindJoinablePartyRun(Player* player, AdventurerGauntlet::RunProgress::ActiveRun& run, Player*& anchor)
{
    anchor = nullptr;
    if (!player)
        return false;

    Group* group = player->GetGroup();
    if (!group)
        return false;

    for (GroupReference* ref = group->GetFirstMember(); ref; ref = ref->next())
    {
        Player* member = ref->GetSource();
        if (!member || member == player)
            continue;

        AdventurerGauntlet::RunProgress::ActiveRun candidate;
        if (!AdventurerGauntlet::RunProgress::LoadActiveRun(member, candidate))
            continue;
        if (!IsGauntletDungeon(candidate.CurrentMap))
            continue;
        if (member->GetMapId() != candidate.CurrentMap || !member->GetInstanceId())
            continue;

        run = candidate;
        anchor = member;
        return true;
    }

    return false;
}

bool CanJoinPartyRun(Player* player, AdventurerGauntlet::RunProgress::ActiveRun const& run, std::string& error)
{
    if (!player || !player->IsAlive())
    {
        error = "Debes estar vivo para unirte a la expedicion.";
        return false;
    }

    int32 difference = int32(player->GetLevel()) - int32(run.RunLevel);
    if (difference > 5)
    {
        error = "Este aventurero ya juega en otra liga.";
        return false;
    }
    if (difference < -5)
    {
        error = "Este aventurero es demasiado debil para acompanar a esta compania.";
        return false;
    }

    return true;
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

void RegisterPendingRun(std::vector<Player*> const& members, std::string const& companyName, uint8 runLevel, std::string const& campaignKey = "", uint8 campaignStage = 0)
{
    for (Player* member : members)
    {
        uint32 guid = member->GetGUID().GetCounter();
        PendingRunNames[guid] = companyName;
        PendingRunLevels[guid] = runLevel;
        if (!campaignKey.empty())
        {
            PendingRunCampaigns[guid] = campaignKey;
            PendingRunCampaignStages[guid] = campaignStage;
        }
        else
        {
            PendingRunCampaigns.erase(guid);
            PendingRunCampaignStages.erase(guid);
        }
        RunReturnPoints[guid] = {
            member->GetMapId(),
            member->GetPositionX(),
            member->GetPositionY(),
            member->GetPositionZ(),
            member->GetOrientation()
        };
    }
}

void UpdatePendingRunLevel(std::vector<Player*> const& members, uint8 runLevel)
{
    for (Player* member : members)
        if (member)
            PendingRunLevels[member->GetGUID().GetCounter()] = runLevel;
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

AdventurerGauntlet::CampaignCatalog::CampaignDefinition const* GetPendingCampaign(Player* player)
{
    if (!player)
        return nullptr;

    auto itr = PendingRunCampaigns.find(player->GetGUID().GetCounter());
    if (itr == PendingRunCampaigns.end())
        return nullptr;

    return AdventurerGauntlet::CampaignCatalog::GetCampaign(itr->second);
}

uint8 GetPendingCampaignStage(Player* player)
{
    if (!player)
        return 0;

    auto itr = PendingRunCampaignStages.find(player->GetGUID().GetCounter());
    return itr == PendingRunCampaignStages.end() ? 0 : itr->second;
}

void SetPendingCampaignStage(std::vector<Player*> const& members, uint8 stage)
{
    for (Player* member : members)
        if (member)
            PendingRunCampaignStages[member->GetGUID().GetCounter()] = stage;
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

bool GetActiveRunNativeMinLevel(Creature const* creature, uint8& level)
{
    if (!creature)
        return false;

    auto itr = ActiveRunNativeMinLevels.find(creature->GetInstanceId());
    if (itr == ActiveRunNativeMinLevels.end())
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

        uint32 guid = member->GetGUID().GetCounter();
        AllowedGauntletTeleports.insert(guid);
        bool teleported = member->TeleportTo(mapId, x, y, z, o, TELE_TO_GM_MODE);
        AllowedGauntletTeleports.erase(guid);

        if (!teleported)
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
            "La primera expedicion queda fijada al nivel |cffffd100{}|r, el mas alto del grupo.",
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

    AdventurerGauntlet::RunProgress::MarkMemberFallen(player, runEnded);

    PendingRunNames.erase(runItr);
    PendingRunLevels.erase(guid);
    PendingRunCampaigns.erase(guid);
    PendingRunCampaignStages.erase(guid);
    RunReturnPoints.erase(returnItr);
    if (runEnded)
    {
        ActiveRunInstanceLevels.erase(instanceId);
        ActiveRunNativeMinLevels.erase(instanceId);
        RagefireBossProgress.erase(instanceId);
    }

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

void RegisterCampaignBossDeathAndTryAdvance(Creature* defeatedBoss)
{
    if (!defeatedBoss)
        return;

    Player* campaignPlayer = nullptr;
    AdventurerGauntlet::CampaignCatalog::CampaignDefinition const* campaign = nullptr;
    for (auto const& ref : defeatedBoss->GetMap()->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!player || !GetPendingRunName(player))
            continue;

        campaign = GetPendingCampaign(player);
        if (campaign)
        {
            campaignPlayer = player;
            break;
        }
    }

    if (!campaignPlayer || !campaign)
        return;

    uint8 stageIndex = GetPendingCampaignStage(campaignPlayer);
    auto const* stage = AdventurerGauntlet::CampaignCatalog::GetStage(*campaign, stageIndex);
    if (!stage || stage->MapId != defeatedBoss->GetMapId() || stage->FinalBossEntry != defeatedBoss->GetEntry())
        return;

    std::vector<Player*> survivors = GetLivingRunMembers(defeatedBoss->GetMap());
    if (survivors.empty())
        return;

    for (Player* survivor : survivors)
        AdventurerGauntlet::RunProgress::SaveCheckpoint(survivor, 0x80);

    Creature* khadgar = defeatedBoss->SummonCreature(
        KhadgarEntry,
        defeatedBoss->GetPositionX() + 2.5f,
        defeatedBoss->GetPositionY() + 1.5f,
        defeatedBoss->GetPositionZ(),
        defeatedBoss->GetOrientation());

    for (Player* survivor : survivors)
    {
        ChatHandler(survivor->GetSession()).PSendSysMessage(
            "|cff00ff00{} - etapa {} completada.|r",
            campaign->Name,
            uint32(stageIndex));
        ChatHandler(survivor->GetSession()).SendSysMessage(stage->TransitionText);
    }

    if (stageIndex == campaign->Stages.size())
    {
        for (Player* survivor : survivors)
            AdventurerGauntlet::RunProgress::CompleteRun(survivor);

        for (Player* survivor : survivors)
            ChatHandler(survivor->GetSession()).SendSysMessage(
                khadgar
                    ? "Khadgar contempla el cuerpo de Onyxia. La expedicion ha terminado."
                    : "La expedicion ha terminado: Onyxia ha caido.");
        return;
    }

    for (Player* survivor : survivors)
        ChatHandler(survivor->GetSession()).SendSysMessage(
            khadgar
                ? "Khadgar ha llegado. Habla con el cuando estes listo para seguir la pista."
                : "Khadgar intento materializarse, pero el portal no respondio.");
}

void RegisterRagefireBossDeathAndTryFinish(Creature* defeatedBoss)
{
    if (!defeatedBoss || defeatedBoss->GetMapId() != RagefireMapId)
        return;

    uint8 bit = GetRagefireBossBit(defeatedBoss->GetEntry());
    if (!bit)
        return;

    uint32 instanceId = defeatedBoss->GetInstanceId();
    uint8& progress = RagefireBossProgress[instanceId];
    progress |= bit;

    for (auto const& ref : defeatedBoss->GetMap()->GetPlayers())
        if (Player* player = ref.GetSource())
            if (GetPendingRunName(player))
                AdventurerGauntlet::RunProgress::SaveCheckpoint(player, progress);

    if ((progress & RagefireAllBossesMask) != RagefireAllBossesMask || (progress & RagefireCompletedMask))
        return;

    progress |= RagefireCompletedMask;

    Map* map = defeatedBoss->GetMap();
    for (auto const& ref : map->GetPlayers())
        if (Player* player = ref.GetSource())
            if (GetPendingRunName(player))
                AdventurerGauntlet::RunProgress::SaveCheckpoint(player, progress);
    std::vector<Player*> survivors = GetLivingRunMembers(map);
    if (survivors.empty())
        return;

    Creature* khadgar = defeatedBoss->SummonCreature(
        KhadgarEntry,
        defeatedBoss->GetPositionX() + 2.5f,
        defeatedBoss->GetPositionY() + 1.5f,
        defeatedBoss->GetPositionZ(),
        defeatedBoss->GetOrientation());

    for (Player* player : survivors)
    {
        ChatHandler(player->GetSession()).SendSysMessage(
            "|cff00ff00Sima Ignea completada.|r Todos los jefes obligatorios han caido.");
        ChatHandler(player->GetSession()).SendSysMessage(
            khadgar
                ? "Khadgar ha llegado con el Baul de Expediciones. Guarda lo que quieras salvar antes de continuar."
                : "Khadgar intento llegar, pero no pudo materializarse junto al ultimo jefe pendiente.");
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
        uint8 nativeMinLevel = 0;
        if (!GauntletEnabled || !GetActiveRunLevel(creature, runLevel) || !GetActiveRunNativeMinLevel(creature, nativeMinLevel))
            return;

        uint8 nativeLevel = level;
        uint8 offset = nativeLevel > nativeMinLevel ? nativeLevel - nativeMinLevel : 0;
        level = std::min<uint8>(80, uint8(runLevel + offset));
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

        player->BindToInstance();

        auto activeItr = ActiveRunInstanceLevels.find(instanceId);
        if (activeItr != ActiveRunInstanceLevels.end())
            return;

        map->LoadAllGrids();

        auto const* dungeon = AdventurerGauntlet::DungeonCatalog::GetDungeon(map->GetId());
        if (!dungeon || !dungeon->NativeBaseLevel)
            return;

        uint8 nativeMinLevel = dungeon->NativeBaseLevel;

        std::vector<Player*> partyMembers = GetPartyMembers(player);
        uint8 runLevel = GetHighestPartyLevel(partyMembers);
        UpdatePendingRunLevel(partyMembers, runLevel);

        ActiveRunInstanceLevels[instanceId] = runLevel;
        ActiveRunNativeMinLevels[instanceId] = nativeMinLevel;
        if (map->GetId() == RagefireMapId)
            RagefireBossProgress[instanceId] = uint8(AdventurerGauntlet::RunProgress::LoadCheckpoint(player));

        for (auto const& [spawnId, creature] : map->GetCreatureBySpawnIdStore())
        {
            (void)spawnId;
            if (!creature || creature->IsPet() || creature->IsTrigger())
                continue;

            creature->SelectLevel();
            if (creature->IsAlive())
                creature->SetHealth(creature->GetMaxHealth());
        }

        ChatHandler(player->GetSession()).PSendSysMessage(
            "{} adapta su curva nativa (base {}) al nivel |cffffd100{}|r de la expedicion.",
            GetGauntletDungeonName(map->GetId()),
            uint32(nativeMinLevel),
            runLevel);
    }

    void OnDestroyInstance(MapInstanced* /*mapInstanced*/, Map* map) override
    {
        if (map && IsGauntletDungeon(map->GetId()))
        {
            uint32 instanceId = map->GetInstanceId();
            ActiveRunInstanceLevels.erase(instanceId);
            ActiveRunNativeMinLevels.erase(instanceId);
            RagefireBossProgress.erase(instanceId);
        }
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

        RegisterCampaignBossDeathAndTryAdvance(creature);

        if (creature->GetMapId() == RagefireMapId)
            RegisterRagefireBossDeathAndTryFinish(creature);
    }
};

class AdventurerGauntletPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletPlayerScript() : PlayerScript("AdventurerGauntletPlayerScript") { }

    void OnPlayerLogin(Player* player) override
    {
        if (!GauntletEnabled || !player)
            return;

        AdventurerGauntlet::RunProgress::ActiveRun run;
        if (!AdventurerGauntlet::RunProgress::LoadActiveRun(player, run))
            return;

        uint32 guid = player->GetGUID().GetCounter();
        PendingRunNames[guid] = run.CompanyName;
        PendingRunLevels[guid] = run.RunLevel;
        if (!run.CampaignKey.empty())
        {
            PendingRunCampaigns[guid] = run.CampaignKey;
            PendingRunCampaignStages[guid] = run.CurrentDungeon;
        }
        RunReturnPoints[guid] = {
            run.ReturnPoint.MapId,
            run.ReturnPoint.X,
            run.ReturnPoint.Y,
            run.ReturnPoint.Z,
            run.ReturnPoint.O
        };
    }

    bool OnPlayerBeforeTeleport(Player* player, uint32 mapId, float /*x*/, float /*y*/, float /*z*/,
        float /*orientation*/, uint32 /*options*/, Unit* /*target*/) override
    {
        if (!GauntletEnabled || !player || !IsGauntletDungeon(player->GetMapId()))
            return true;

        uint32 guid = player->GetGUID().GetCounter();
        if (AllowedGauntletTeleports.find(guid) != AllowedGauntletTeleports.end())
            return true;

        // Same-map teleports are used by reconnect/resume mechanics and do not
        // represent leaving the expedition.
        if (mapId == player->GetMapId())
            return true;

        AdventurerGauntlet::RunProgress::ActiveRun run;
        if (!AdventurerGauntlet::RunProgress::LoadActiveRun(player, run))
            return true;

        ChatHandler(player->GetSession()).SendSysMessage(
            "Khadgar ha sellado esta salida. La expedicion debe continuar.");
        return false;
    }

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
    ACTION_RANDOM_CLASSIC = GOSSIP_ACTION_INFO_DEF + 5,
    ACTION_RANDOM_OUTLAND = GOSSIP_ACTION_INFO_DEF + 6,
    ACTION_RANDOM_NORTHREND = GOSSIP_ACTION_INFO_DEF + 7,
    ACTION_STORMWIND_SHADOW = GOSSIP_ACTION_INFO_DEF + 8,
    ACTION_CAMPAIGN_CONTINUE = GOSSIP_ACTION_INFO_DEF + 9,
    ACTION_SPECIFIC_MENU = GOSSIP_ACTION_INFO_DEF + 10,
    ACTION_SPECIFIC_CLASSIC = GOSSIP_ACTION_INFO_DEF + 11,
    ACTION_SPECIFIC_OUTLAND = GOSSIP_ACTION_INFO_DEF + 12,
    ACTION_SPECIFIC_NORTHREND = GOSSIP_ACTION_INFO_DEF + 13,
    ACTION_JOIN_ACTIVE_PARTY_RUN = GOSSIP_ACTION_INFO_DEF + 14,
    ACTION_SPECIFIC_BASE = GOSSIP_ACTION_INFO_DEF + 100,
};

enum KhadgarTravelDestination
{
    KHADGAR_TRAVEL_NONE = 0,
    KHADGAR_TRAVEL_RAGEFIRE = 1,
    KHADGAR_TRAVEL_DEADMINES = 2,
    KHADGAR_TRAVEL_RAMPARTS = 3,
    KHADGAR_TRAVEL_AZJOL = 4,
};

class npc_adventurer_gauntlet_khadgar : public CreatureScript
{
public:
    npc_adventurer_gauntlet_khadgar() : CreatureScript("npc_adventurer_gauntlet_khadgar") { }

    struct npc_adventurer_gauntlet_khadgarAI : public ScriptedAI
    {
        npc_adventurer_gauntlet_khadgarAI(Creature* creature) : ScriptedAI(creature) { }

        void BeginTravel(std::vector<Player*> const& members, AdventurerGauntlet::DungeonCatalog::DungeonDefinition const& dungeon)
        {
            if (_travelInProgress || members.empty())
                return;

            _travelInProgress = true;
            _destination = KHADGAR_TRAVEL_NONE;
            _randomDestination = dungeon;
            _hasRandomDestination = true;
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

                for (Player* player : travellers)
                    ChatHandler(player->GetSession()).PSendSysMessage(
                        "Khadgar abre el camino hacia |cffffd100{}|r.",
                        _randomDestination.Name);

                bool success = TeleportParty(
                    travellers,
                    _randomDestination.MapId,
                    _randomDestination.X,
                    _randomDestination.Y,
                    _randomDestination.Z,
                    _randomDestination.O);

                if (!success)
                    for (Player* player : travellers)
                        ChatHandler(player->GetSession()).SendSysMessage(
                            "El portal de Khadgar no pudo transportar a toda la expedicion.");

                me->CastSpell(me, KhadgarTeleportVisual, true);
                _travellers.clear();
                _travelInProgress = false;
                _hasRandomDestination = false;
                me->ReplaceAllNpcFlags(UNIT_NPC_FLAG_GOSSIP);
            });
        }

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
                else if (_destination == KHADGAR_TRAVEL_RAMPARTS)
                {
                    for (Player* player : travellers)
                        ChatHandler(player->GetSession()).SendSysMessage(
                            "Khadgar abre un portal de prueba hacia |cffffd100Murallas del Fuego Infernal|r.");

                    success = TeleportParty(travellers, HellfireRampartsMapId, HellfireRampartsX, HellfireRampartsY, HellfireRampartsZ, HellfireRampartsO);
                }
                else if (_destination == KHADGAR_TRAVEL_AZJOL)
                {
                    for (Player* player : travellers)
                        ChatHandler(player->GetSession()).SendSysMessage(
                            "Khadgar abre un portal de prueba hacia |cffffd100Azjol-Nerub|r.");

                    success = TeleportParty(travellers, AzjolNerubMapId, AzjolNerubX, AzjolNerubY, AzjolNerubZ, AzjolNerubO);
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
        AdventurerGauntlet::DungeonCatalog::DungeonDefinition _randomDestination{};
        bool _hasRandomDestination = false;
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

        AdventurerGauntlet::RunProgress::ActiveRun joinableRun;
        Player* joinAnchor = nullptr;
        if (!GetPendingRunName(player) && FindJoinablePartyRun(player, joinableRun, joinAnchor))
        {
            AddGossipItemFor(
                player,
                GOSSIP_ICON_CHAT,
                std::string("Unirme a ") + joinableRun.CompanyName + " en " + GetGauntletDungeonName(joinableRun.CurrentMap) + ".",
                GOSSIP_SENDER_MAIN,
                ACTION_JOIN_ACTIVE_PARTY_RUN);
            SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
            return true;
        }

        if (auto const* campaign = GetPendingCampaign(player))
        {
            uint8 stageIndex = GetPendingCampaignStage(player);
            if (auto const* stage = AdventurerGauntlet::CampaignCatalog::GetStage(*campaign, stageIndex))
            {
                if (stage->MapId == creature->GetMapId() && stageIndex < campaign->Stages.size())
                {
                    if (auto const* nextStage = AdventurerGauntlet::CampaignCatalog::GetStage(*campaign, stageIndex + 1))
                        if (auto const* nextDungeon = AdventurerGauntlet::DungeonCatalog::GetDungeon(nextStage->MapId))
                            AddGossipItemFor(
                                player,
                                GOSSIP_ICON_CHAT,
                                std::string("Continuar hacia ") + nextDungeon->Name + ".",
                                GOSSIP_SENDER_MAIN,
                                ACTION_CAMPAIGN_CONTINUE);

                    AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Recuerdame el nombre de nuestra compania.", GOSSIP_SENDER_MAIN, ACTION_STATUS);
                    SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
                    return true;
                }
            }
        }

        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Quiero saber mas.", GOSSIP_SENDER_MAIN, ACTION_LEARN_MORE);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Mazmorra clasica aleatoria.", GOSSIP_SENDER_MAIN, ACTION_RANDOM_CLASSIC);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Mazmorra de Terrallende aleatoria.", GOSSIP_SENDER_MAIN, ACTION_RANDOM_OUTLAND);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Mazmorra de Rasganorte aleatoria.", GOSSIP_SENDER_MAIN, ACTION_RANDOM_NORTHREND);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Elegir mazmorra especifica.", GOSSIP_SENDER_MAIN, ACTION_SPECIFIC_MENU);
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "La sombra sobre Ventormenta.", GOSSIP_SENDER_MAIN, ACTION_STORMWIND_SHADOW);
        SendGossipMenuFor(player, KhadgarIntroText, creature->GetGUID());
        return true;
    }

    bool OnGossipSelect(Player* player, Creature* creature, uint32 /*sender*/, uint32 action) override
    {
        ClearGossipMenuFor(player);

        if (action >= ACTION_SPECIFIC_BASE)
        {
            uint32 index = action - ACTION_SPECIFIC_BASE;
            auto const* dungeon = AdventurerGauntlet::DungeonCatalog::GetSpecificDungeonByMenuIndex(index);
            if (!dungeon)
            {
                CloseGossipMenuFor(player);
                return true;
            }

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
            AdventurerGauntlet::RunProgress::StartRun(members, companyName, runLevel, dungeon->MapId);

            for (Player* member : members)
                ChatHandler(member->GetSession()).PSendSysMessage(
                    "|cffffd100Prueba especifica Gauntlet.|r Khadgar abre {}. Nivel base: {}.",
                    dungeon->Name,
                    runLevel);

            static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                members,
                *dungeon);

            CloseGossipMenuFor(player);
            return true;
        }

        switch (action)
        {
            case ACTION_JOIN_ACTIVE_PARTY_RUN:
            {
                AdventurerGauntlet::RunProgress::ActiveRun run;
                Player* anchor = nullptr;
                if (!FindJoinablePartyRun(player, run, anchor))
                {
                    ChatHandler(player->GetSession()).SendSysMessage(
                        "Khadgar ya no encuentra una expedicion activa de tu grupo.");
                    CloseGossipMenuFor(player);
                    return true;
                }

                std::string error;
                if (!CanJoinPartyRun(player, run, error))
                {
                    ChatHandler(player->GetSession()).SendSysMessage(error.c_str());
                    CloseGossipMenuFor(player);
                    return true;
                }

                if (!AdventurerGauntlet::RunProgress::AddMemberToRun(player, run))
                {
                    ChatHandler(player->GetSession()).SendSysMessage(
                        "Khadgar no pudo incorporarte a esa compania. Puede que ya este completa.");
                    CloseGossipMenuFor(player);
                    return true;
                }

                RegisterPendingRun(
                    { player },
                    run.CompanyName,
                    run.RunLevel,
                    run.CampaignKey,
                    run.CurrentDungeon);

                auto const* dungeon = AdventurerGauntlet::DungeonCatalog::GetDungeon(run.CurrentMap);
                if (!dungeon)
                {
                    CloseGossipMenuFor(player);
                    return true;
                }

                ChatHandler(player->GetSession()).PSendSysMessage(
                    "Khadgar reconoce a tu grupo. Te unes a |cff00ff00{}|r en |cffffd100{}|r.",
                    run.CompanyName,
                    dungeon->Name);

                static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                    { player },
                    *dungeon);

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_LEARN_MORE:
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
                AdventurerGauntlet::RunProgress::StartRun(members, companyName, runLevel);
                AnnounceRunStart(members, companyName, runLevel);

                static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                    members,
                    KHADGAR_TRAVEL_RAGEFIRE);

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_SPECIFIC_MENU:
                AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Classic.", GOSSIP_SENDER_MAIN, ACTION_SPECIFIC_CLASSIC);
                AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Terrallende.", GOSSIP_SENDER_MAIN, ACTION_SPECIFIC_OUTLAND);
                AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Rasganorte.", GOSSIP_SENDER_MAIN, ACTION_SPECIFIC_NORTHREND);
                SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
                return true;
            case ACTION_SPECIFIC_CLASSIC:
            case ACTION_SPECIFIC_OUTLAND:
            case ACTION_SPECIFIC_NORTHREND:
            {
                AdventurerGauntlet::DungeonCatalog::ExpansionPool pool =
                    action == ACTION_SPECIFIC_CLASSIC
                        ? AdventurerGauntlet::DungeonCatalog::ExpansionPool::Classic
                        : action == ACTION_SPECIFIC_OUTLAND
                            ? AdventurerGauntlet::DungeonCatalog::ExpansionPool::Outland
                            : AdventurerGauntlet::DungeonCatalog::ExpansionPool::Northrend;

                std::vector<AdventurerGauntlet::DungeonCatalog::DungeonDefinition const*> dungeons;
                AdventurerGauntlet::DungeonCatalog::GetDungeons(pool, dungeons);

                uint32 offset =
                    pool == AdventurerGauntlet::DungeonCatalog::ExpansionPool::Classic
                        ? 0
                        : pool == AdventurerGauntlet::DungeonCatalog::ExpansionPool::Outland
                            ? 5
                            : 9;

                for (uint32 i = 0; i < dungeons.size(); ++i)
                    AddGossipItemFor(
                        player,
                        GOSSIP_ICON_CHAT,
                        dungeons[i]->Name,
                        GOSSIP_SENDER_MAIN,
                        ACTION_SPECIFIC_BASE + offset + i);

                SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, creature->GetGUID());
                return true;
            }
            case ACTION_STORMWIND_SHADOW:
            {
                std::vector<Player*> members;
                std::string error;
                if (!ValidateParty(player, members, error))
                {
                    ChatHandler(player->GetSession()).SendSysMessage(error.c_str());
                    CloseGossipMenuFor(player);
                    return true;
                }

                auto const* campaign = AdventurerGauntlet::CampaignCatalog::GetCampaign(
                    AdventurerGauntlet::CampaignCatalog::StormwindShadowKey);
                auto const* firstStage = campaign ? AdventurerGauntlet::CampaignCatalog::GetStage(*campaign, 1) : nullptr;
                auto const* firstDungeon = firstStage ? AdventurerGauntlet::DungeonCatalog::GetDungeon(firstStage->MapId) : nullptr;
                if (!campaign || !firstStage || !firstDungeon)
                {
                    ChatHandler(player->GetSession()).SendSysMessage("La campaña no esta disponible.");
                    CloseGossipMenuFor(player);
                    return true;
                }

                uint8 runLevel = GetHighestPartyLevel(members);
                std::string companyName = GenerateCompanyName();

                ResetPartyInstances(player);
                RegisterPendingRun(members, companyName, runLevel, campaign->Key, 1);
                AdventurerGauntlet::RunProgress::StartRun(
                    members,
                    companyName,
                    runLevel,
                    firstStage->MapId,
                    campaign->Key);

                for (Player* member : members)
                {
                    ChatHandler(member->GetSession()).PSendSysMessage(
                        "|cffffd100{}|r comienza. Khadgar ha localizado a Edwin VanCleef en las Minas de la Muerte.",
                        campaign->Name);
                    ChatHandler(member->GetSession()).SendSysMessage(
                        "Derrota a VanCleef. Khadgar intentara arrancar una ultima pista de sus pensamientos antes de que su alma abandone el cuerpo.");
                }

                static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                    members,
                    *firstDungeon);

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_RANDOM_CLASSIC:
            case ACTION_RANDOM_OUTLAND:
            case ACTION_RANDOM_NORTHREND:
            {
                std::vector<Player*> members;
                std::string error;
                if (!ValidateParty(player, members, error))
                {
                    ChatHandler(player->GetSession()).SendSysMessage(error.c_str());
                    CloseGossipMenuFor(player);
                    return true;
                }

                AdventurerGauntlet::DungeonCatalog::ExpansionPool pool =
                    action == ACTION_RANDOM_CLASSIC
                        ? AdventurerGauntlet::DungeonCatalog::ExpansionPool::Classic
                        : action == ACTION_RANDOM_OUTLAND
                            ? AdventurerGauntlet::DungeonCatalog::ExpansionPool::Outland
                            : AdventurerGauntlet::DungeonCatalog::ExpansionPool::Northrend;

                auto const& dungeon = AdventurerGauntlet::DungeonCatalog::GetRandomDungeon(pool);
                uint8 runLevel = GetHighestPartyLevel(members);
                std::string companyName = GenerateCompanyName();

                ResetPartyInstances(player);
                RegisterPendingRun(members, companyName, runLevel);
                AdventurerGauntlet::RunProgress::StartRun(members, companyName, runLevel, dungeon.MapId);

                for (Player* member : members)
                {
                    ChatHandler(member->GetSession()).PSendSysMessage(
                        "|cffffd100Prueba aleatoria Gauntlet.|r Khadgar ha elegido {}. Nivel base: {}.",
                        dungeon.Name,
                        runLevel);
                }

                static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                    members,
                    dungeon);

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_CAMPAIGN_CONTINUE:
            {
                auto const* campaign = GetPendingCampaign(player);
                uint8 stageIndex = GetPendingCampaignStage(player);
                auto const* currentStage = campaign ? AdventurerGauntlet::CampaignCatalog::GetStage(*campaign, stageIndex) : nullptr;
                auto const* nextStage = campaign ? AdventurerGauntlet::CampaignCatalog::GetStage(*campaign, stageIndex + 1) : nullptr;
                auto const* nextDungeon = nextStage ? AdventurerGauntlet::DungeonCatalog::GetDungeon(nextStage->MapId) : nullptr;

                if (!campaign || !currentStage || !nextStage || !nextDungeon ||
                    currentStage->MapId != creature->GetMapId())
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
                    AdventurerGauntlet::RunProgress::AdvanceDungeon(survivor, nextStage->Index, nextStage->MapId);

                SetPendingCampaignStage(survivors, nextStage->Index);

                for (Player* survivor : survivors)
                    ChatHandler(survivor->GetSession()).PSendSysMessage(
                        "Khadgar prepara el portal hacia |cffffd100{}|r.",
                        nextDungeon->Name);

                static_cast<npc_adventurer_gauntlet_khadgarAI*>(creature->AI())->BeginTravel(
                    survivors,
                    *nextDungeon);

                CloseGossipMenuFor(player);
                return true;
            }
            case ACTION_STATUS:
                if (std::string const* companyName = GetPendingRunName(player))
                {
                    uint8 runLevel = 0;
                    GetPendingRunLevel(player, runLevel);
                    ChatHandler(player->GetSession()).PSendSysMessage(
                        "Su compania es |cff00ff00{}|r. Nivel base actual: |cffffd100{}|r.",
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
