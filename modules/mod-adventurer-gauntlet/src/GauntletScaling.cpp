#include "Creature.h"
#include "Group.h"
#include "Map.h"
#include "Player.h"
#include "PlayerSettings.h"
#include "ScriptMgr.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <unordered_map>

namespace
{
constexpr char const* GauntletSettingsSource = "adventurer_gauntlet";
constexpr uint32 GauntletSettingPledged = 0;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;
constexpr uint32 HellfireRampartsMapId = 543;
constexpr uint32 AzjolNerubMapId = 601;
constexpr uint32 LoneWolfSpellId = 910501;
constexpr uint32 LoneWolfDamagePct = 120;
constexpr uint32 LoneWolfRefreshMs = 1000;

constexpr std::array<uint32, 5> TrashHealthPct = { 50, 150, 200, 250, 300 };
constexpr std::array<uint32, 5> RareHealthPct  = { 50, 160, 225, 290, 355 };
constexpr std::array<uint32, 5> BossHealthPct  = { 50, 175, 250, 325, 400 };
constexpr std::array<uint32, 5> DamagePct      = { 75, 115, 130, 145, 160 };

struct CreatureScaleState
{
    uint32 BaseMaxHealth = 0;
    uint8 PartySize = 0;
};

std::unordered_map<uint64, CreatureScaleState> CreatureScaleStates;
std::unordered_map<uint32, uint8> InstancePeakPartySizes;
std::unordered_map<uint32, uint32> LoneWolfRefreshTimers;

bool IsGauntletMap(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId ||
        mapId == HellfireRampartsMapId || mapId == AzjolNerubMapId;
}

bool IsPledged(Player* player)
{
    return player && player->GetPlayerSetting(GauntletSettingsSource, GauntletSettingPledged).IsEnabled();
}

bool IsSoloGauntletPlayer(Player* player)
{
    if (!player || !IsPledged(player) || !IsGauntletMap(player->GetMapId()))
        return false;

    Group* group = player->GetGroup();
    return !group || group->GetMembersCount() == 1;
}

void RefreshLoneWolf(Player* player)
{
    if (!player)
        return;

    if (IsSoloGauntletPlayer(player))
    {
        if (!player->HasAura(LoneWolfSpellId))
            player->CastSpell(player, LoneWolfSpellId, true);
    }
    else
        player->RemoveAurasDueToSpell(LoneWolfSpellId);
}

uint8 GetRunPartySize(Map* map)
{
    if (!map || !IsGauntletMap(map->GetId()))
        return 0;

    uint8 presentPlayers = 0;
    for (auto const& ref : map->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!IsPledged(player))
            continue;

        presentPlayers = std::min<uint8>(5, uint8(presentPlayers + 1));
    }

    if (!map->GetInstanceId())
        return presentPlayers;

    uint8& peakPartySize = InstancePeakPartySizes[map->GetInstanceId()];
    peakPartySize = std::max<uint8>(peakPartySize, presentPlayers);
    return peakPartySize;
}

uint32 GetHealthPercent(Creature const* creature, uint8 partySize)
{
    uint8 index = std::clamp<uint8>(partySize, 1, 5) - 1;
    if (creature->IsDungeonBoss())
        return BossHealthPct[index];

    uint32 rank = creature->GetCreatureTemplate()->rank;
    if (rank == CREATURE_ELITE_RARE || rank == CREATURE_ELITE_RAREELITE)
        return RareHealthPct[index];

    return TrashHealthPct[index];
}

uint64 GetCreatureScaleKey(Creature const* creature)
{
    return (uint64(creature->GetInstanceId()) << 32) | uint64(creature->GetGUID().GetCounter());
}

void ApplyHealthScaling(Creature* creature, uint8 partySize)
{
    if (!creature || !partySize || !IsGauntletMap(creature->GetMapId()) || creature->IsPet() || creature->IsTrigger())
        return;

    uint64 key = GetCreatureScaleKey(creature);
    CreatureScaleState& state = CreatureScaleStates[key];

    if (!state.BaseMaxHealth)
        state.BaseMaxHealth = creature->GetMaxHealth();

    if (state.PartySize == partySize)
        return;

    uint32 healthPct = GetHealthPercent(creature, partySize);
    uint32 newMaxHealth = std::max<uint32>(1, uint32((uint64(state.BaseMaxHealth) * healthPct) / 100));
    float currentPct = creature->GetHealthPct();

    creature->SetMaxHealth(newMaxHealth);
    creature->SetHealth(std::max<uint32>(1, uint32((double(newMaxHealth) * currentPct) / 100.0)));
    state.PartySize = partySize;
}

void ApplyHealthScaling(Creature* creature)
{
    if (!creature)
        return;

    ApplyHealthScaling(creature, GetRunPartySize(creature->GetMap()));
}

void RefreshOutOfCombatScaling(Map* map)
{
    uint8 partySize = GetRunPartySize(map);
    if (!partySize)
        return;

    for (auto const& [spawnId, creature] : map->GetCreatureBySpawnIdStore())
    {
        (void)spawnId;
        if (!creature || !creature->IsAlive() || creature->IsInCombat())
            continue;

        ApplyHealthScaling(creature, partySize);
    }
}

uint32 ScaleOutgoingDamage(Unit* attacker, uint32 damage)
{
    if (!attacker)
        return damage;

    if (Player* player = attacker->ToPlayer())
    {
        if (IsSoloGauntletPlayer(player))
            return uint32((uint64(damage) * LoneWolfDamagePct) / 100);
        return damage;
    }

    Creature* creature = attacker->ToCreature();
    if (!creature || !IsGauntletMap(creature->GetMapId()) || creature->IsPet() || creature->IsTrigger())
        return damage;

    uint8 partySize = GetRunPartySize(creature->GetMap());
    if (auto itr = CreatureScaleStates.find(GetCreatureScaleKey(creature)); itr != CreatureScaleStates.end() && itr->second.PartySize)
        partySize = itr->second.PartySize;

    if (!partySize)
        return damage;

    uint32 pct = DamagePct[std::clamp<uint8>(partySize, 1, 5) - 1];
    return uint32((uint64(damage) * pct) / 100);
}
}

class AdventurerGauntletScalingMapScript : public AllMapScript
{
public:
    AdventurerGauntletScalingMapScript() : AllMapScript("AdventurerGauntletScalingMapScript") { }

    void OnDestroyInstance(MapInstanced* /*mapInstanced*/, Map* map) override
    {
        if (!map || !IsGauntletMap(map->GetId()))
            return;

        uint32 instanceId = map->GetInstanceId();
        InstancePeakPartySizes.erase(instanceId);

        for (auto itr = CreatureScaleStates.begin(); itr != CreatureScaleStates.end();)
        {
            if (uint32(itr->first >> 32) == instanceId)
                itr = CreatureScaleStates.erase(itr);
            else
                ++itr;
        }
    }
};

class AdventurerGauntletScalingUnitScript : public UnitScript
{
public:
    AdventurerGauntletScalingUnitScript() : UnitScript("AdventurerGauntletScalingUnitScript") { }

    void OnUnitEnterCombat(Unit* unit, Unit* /*victim*/) override
    {
        if (Creature* creature = unit ? unit->ToCreature() : nullptr)
            ApplyHealthScaling(creature);
    }

    void OnDamage(Unit* attacker, Unit* /*victim*/, uint32& damage) override
    {
        damage = ScaleOutgoingDamage(attacker, damage);
    }

    void OnUnitDeath(Unit* unit, Unit* /*killer*/) override
    {
        if (Creature* creature = unit ? unit->ToCreature() : nullptr)
            CreatureScaleStates.erase(GetCreatureScaleKey(creature));
    }
};

class AdventurerGauntletLoneWolfPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletLoneWolfPlayerScript()
        : PlayerScript("AdventurerGauntletLoneWolfPlayerScript") { }

    void OnPlayerMapChanged(Player* player) override
    {
        RefreshLoneWolf(player);
        if (player)
            LoneWolfRefreshTimers[player->GetGUID().GetCounter()] = LoneWolfRefreshMs;
    }

    void OnPlayerLogin(Player* player) override
    {
        RefreshLoneWolf(player);
        if (player)
            LoneWolfRefreshTimers[player->GetGUID().GetCounter()] = LoneWolfRefreshMs;
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        if (!player)
            return;

        uint32 guid = player->GetGUID().GetCounter();
        uint32& timer = LoneWolfRefreshTimers[guid];
        if (timer > diff)
        {
            timer -= diff;
            return;
        }

        timer = LoneWolfRefreshMs;
        RefreshLoneWolf(player);

        if (IsGauntletMap(player->GetMapId()))
            RefreshOutOfCombatScaling(player->GetMap());
    }

    void OnPlayerLogout(Player* player) override
    {
        if (player)
            LoneWolfRefreshTimers.erase(player->GetGUID().GetCounter());
    }
};

void AddAdventurerGauntletScalingScripts()
{
    new AdventurerGauntletScalingMapScript();
    new AdventurerGauntletScalingUnitScript();
    new AdventurerGauntletLoneWolfPlayerScript();
}
