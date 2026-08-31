#include "Creature.h"
#include "Group.h"
#include "Map.h"
#include "Player.h"
#include "PlayerSettings.h"
#include "ScriptMgr.h"

#include <algorithm>
#include <array>
#include <cstdint>
#include <unordered_set>

namespace
{
constexpr char const* GauntletSettingsSource = "adventurer_gauntlet";
constexpr uint32 GauntletSettingPledged = 0;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;
constexpr uint32 LoneWolfSpellId = 910501;

constexpr std::array<uint32, 5> TrashHealthPct = { 50, 150, 200, 250, 300 };
constexpr std::array<uint32, 5> RareHealthPct  = { 50, 160, 225, 290, 355 };
constexpr std::array<uint32, 5> BossHealthPct  = { 50, 175, 250, 325, 400 };
constexpr std::array<uint32, 5> DamagePct      = { 75, 115, 130, 145, 160 };

std::unordered_set<uint64> ScaledCreatures;

bool IsGauntletMap(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
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

    for (auto const& ref : map->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!IsPledged(player))
            continue;

        if (Group* group = player->GetGroup())
            return std::clamp<uint8>(static_cast<uint8>(group->GetMembersCount()), 1, 5);

        return 1;
    }

    return 0;
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

void ApplyHealthScaling(Creature* creature)
{
    if (!creature || !IsGauntletMap(creature->GetMapId()) || creature->IsPet() || creature->IsTrigger())
        return;

    uint8 partySize = GetRunPartySize(creature->GetMap());
    if (!partySize)
        return;

    uint64 key = GetCreatureScaleKey(creature);
    if (!ScaledCreatures.insert(key).second)
        return;

    uint32 healthPct = GetHealthPercent(creature, partySize);
    uint32 oldMaxHealth = creature->GetMaxHealth();
    uint32 newMaxHealth = std::max<uint32>(1, uint32((uint64(oldMaxHealth) * healthPct) / 100));
    float currentPct = creature->GetHealthPct();

    creature->SetMaxHealth(newMaxHealth);
    creature->SetHealth(std::max<uint32>(1, uint32((double(newMaxHealth) * currentPct) / 100.0)));
}

uint32 ScaleOutgoingDamage(Unit* attacker, uint32 damage)
{
    Creature* creature = attacker ? attacker->ToCreature() : nullptr;
    if (!creature || !IsGauntletMap(creature->GetMapId()) || creature->IsPet() || creature->IsTrigger())
        return damage;

    uint8 partySize = GetRunPartySize(creature->GetMap());
    if (!partySize)
        return damage;

    uint32 pct = DamagePct[std::clamp<uint8>(partySize, 1, 5) - 1];
    return uint32((uint64(damage) * pct) / 100);
}
}

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
            ScaledCreatures.erase(GetCreatureScaleKey(creature));
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
    }

    void OnPlayerLogin(Player* player) override
    {
        RefreshLoneWolf(player);
    }
};

void AddAdventurerGauntletScalingScripts()
{
    new AdventurerGauntletScalingUnitScript();
    new AdventurerGauntletLoneWolfPlayerScript();
}
