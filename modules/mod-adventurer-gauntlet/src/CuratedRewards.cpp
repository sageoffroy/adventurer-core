#include "Creature.h"
#include "DatabaseEnv.h"
#include "ItemTemplate.h"
#include "LootMgr.h"
#include "Map.h"
#include "ObjectMgr.h"
#include "Player.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"

#include <algorithm>
#include <array>
#include <unordered_set>
#include <vector>

namespace
{
constexpr uint32 RagefireMapId = 389;
constexpr uint32 GauntletItemMin = 911100;
constexpr uint32 GauntletItemMax = 911399;
constexpr uint32 UniversalMask = 0xFFFFFFFFu;

enum RewardPool : uint8
{
    REWARD_GREEN = 0,
    REWARD_BLUE = 1,
    REWARD_EPIC = 2,
    REWARD_LEGENDARY = 3,
};

enum RewardProfile : uint8
{
    REWARD_PROFILE_NONE = 0,
    REWARD_PROFILE_CHECKPOINT = 1,
    REWARD_PROFILE_FINAL = 2,
};

struct RewardPools
{
    std::array<std::vector<uint32>, 4> Items;
};

std::unordered_set<uint64> ProcessedBosses;

uint8 GetRewardProfile(uint32 creatureEntry)
{
    if (QueryResult result = WorldDatabase.Query(
        "SELECT `reward_profile` FROM `adventurer_gauntlet_loot_rule` WHERE `creature_entry` = {}",
        creatureEntry))
        return (*result)[0].Get<uint8>();

    return REWARD_PROFILE_NONE;
}

uint64 GetBossKey(Creature const* boss)
{
    return boss ? ((uint64(boss->GetInstanceId()) << 32) | uint64(boss->GetGUID().GetCounter())) : 0;
}

bool PassesCommonRewardRules(ItemTemplate const& item, uint8 playerLevel)
{
    if (item.Class != ITEM_CLASS_WEAPON && item.Class != ITEM_CLASS_ARMOR)
        return false;
    if (item.InventoryType == INVTYPE_NON_EQUIP || item.InventoryType == INVTYPE_BAG)
        return false;
    if (item.RequiredLevel > playerLevel)
        return false;

    uint32 minItemLevel = playerLevel > 3 ? playerLevel - 3 : 1;
    uint32 maxItemLevel = playerLevel + 10;
    if (item.ItemLevel < minItemLevel || item.ItemLevel > maxItemLevel)
        return false;

    // Native green rewards must be usable by the classless Adventurer. Items
    // restricted to a stock class or race (for example Warrior-only quest
    // weapons) are invalid rewards even when their level and quality fit.
    if (item.AllowableClass != UniversalMask || item.AllowableRace != UniversalMask)
        return false;

    if (item.RequiredSkill || item.RequiredSpell || item.RequiredReputationFaction ||
        item.RequiredHonorRank || item.RequiredCityRank)
        return false;
    if (item.HasFlag(ITEM_FLAG_DEPRECATED))
        return false;
    return true;
}

RewardPools BuildControlledPools(uint8 playerLevel)
{
    RewardPools pools;
    ItemTemplateContainer const* itemStore = sObjectMgr->GetItemTemplateStore();
    if (!itemStore)
        return pools;

    for (auto const& [entry, item] : *itemStore)
    {
        if (!PassesCommonRewardRules(item, playerLevel))
            continue;

        bool customGauntletItem = entry >= GauntletItemMin && entry <= GauntletItemMax;

        if (item.Quality == ITEM_QUALITY_UNCOMMON)
        {
            if (!customGauntletItem)
                pools.Items[REWARD_GREEN].push_back(entry);
            continue;
        }

        if (!customGauntletItem)
            continue;

        if (item.Quality == ITEM_QUALITY_RARE)
            pools.Items[REWARD_BLUE].push_back(entry);
        else if (item.Quality == ITEM_QUALITY_EPIC)
            pools.Items[REWARD_EPIC].push_back(entry);
        else if (item.Quality == ITEM_QUALITY_LEGENDARY)
            pools.Items[REWARD_LEGENDARY].push_back(entry);
    }

    return pools;
}

uint32 SelectFromPool(std::vector<uint32> const& candidates, std::unordered_set<uint32>& usedEntries)
{
    if (candidates.empty())
        return 0;

    uint32 attempts = std::min<uint32>(static_cast<uint32>(candidates.size()), 32);
    for (uint32 attempt = 0; attempt < attempts; ++attempt)
    {
        uint32 entry = candidates[urand(0, static_cast<uint32>(candidates.size() - 1))];
        if (usedEntries.insert(entry).second)
            return entry;
    }

    return candidates[urand(0, static_cast<uint32>(candidates.size() - 1))];
}

void AddLootItem(Loot& loot, uint32 itemEntry)
{
    if (!itemEntry)
        return;

    LootStoreItem lootItem(itemEntry, 0, 100.0f, false, LOOT_MODE_DEFAULT, 0, 1, 1);
    loot.AddItem(lootItem);
}

bool GetRewardContext(Map* map, uint32& survivorCount, uint8& rewardLevel)
{
    survivorCount = 0;
    rewardLevel = 0;
    if (!map)
        return false;

    for (auto const& ref : map->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!player || !player->IsAlive())
            continue;

        ++survivorCount;
        rewardLevel = rewardLevel == 0 ? player->GetLevel() : std::min<uint8>(rewardLevel, player->GetLevel());
    }

    return survivorCount && rewardLevel;
}

void AddCheckpointExtraRoll(Loot& loot, RewardPools const& pools, std::unordered_set<uint32>& usedEntries)
{
    uint32 roll = urand(1, 100);
    if (roll <= 50)
        return;
    if (roll <= 80)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_GREEN], usedEntries));
    else if (roll <= 90)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_BLUE], usedEntries));
    else if (roll <= 99)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_EPIC], usedEntries));
    else
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_LEGENDARY], usedEntries));
}

void AddFinalExtraRoll(Loot& loot, RewardPools const& pools, std::unordered_set<uint32>& usedEntries)
{
    uint32 roll = urand(1, 100);
    if (roll <= 25)
        return;
    if (roll <= 75)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_GREEN], usedEntries));
    else if (roll <= 90)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_BLUE], usedEntries));
    else if (roll <= 97)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_EPIC], usedEntries));
    else
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_LEGENDARY], usedEntries));
}

bool FillCheckpointLoot(Loot& loot, Map* map)
{
    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(map, survivorCount, rewardLevel))
        return false;

    RewardPools pools = BuildControlledPools(rewardLevel);
    std::unordered_set<uint32> usedEntries;
    uint32 gold = loot.gold;

    loot.clear();
    loot.loot_type = LOOT_CORPSE;
    loot.gold = gold;

    for (uint32 reward = 0; reward < survivorCount; ++reward)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_GREEN], usedEntries));

    AddCheckpointExtraRoll(loot, pools, usedEntries);
    return !loot.empty();
}

bool FillFinalBossLoot(Loot& loot, Map* map)
{
    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(map, survivorCount, rewardLevel))
        return false;

    RewardPools pools = BuildControlledPools(rewardLevel);
    std::unordered_set<uint32> usedEntries;
    uint32 gold = loot.gold;

    loot.clear();
    loot.loot_type = LOOT_CORPSE;
    loot.gold = gold;

    AddLootItem(loot, SelectFromPool(pools.Items[REWARD_BLUE], usedEntries));
    AddFinalExtraRoll(loot, pools, usedEntries);
    return !loot.empty();
}

void RefillBossAfterDeath(Creature* boss)
{
    if (!boss || boss->IsAlive() || boss->GetMapId() != RagefireMapId)
        return;

    uint8 rewardProfile = GetRewardProfile(boss->GetEntry());
    if (rewardProfile == REWARD_PROFILE_NONE)
        return;

    uint64 key = GetBossKey(boss);
    if (!key || ProcessedBosses.find(key) != ProcessedBosses.end())
        return;

    bool filled = rewardProfile == REWARD_PROFILE_FINAL
        ? FillFinalBossLoot(boss->loot, boss->GetMap())
        : FillCheckpointLoot(boss->loot, boss->GetMap());

    if (filled)
    {
        boss->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        ProcessedBosses.insert(key);
    }
}
}

class AdventurerGauntletBossRewardsScript : public AllCreatureScript
{
public:
    AdventurerGauntletBossRewardsScript()
        : AllCreatureScript("AdventurerGauntletBossRewardsScript") { }

    void OnAllCreatureUpdate(Creature* creature, uint32 /*diff*/) override
    {
        RefillBossAfterDeath(creature);
    }

    void OnCreatureRemoveWorld(Creature* creature) override
    {
        if (!creature || creature->GetMapId() != RagefireMapId || GetRewardProfile(creature->GetEntry()) == REWARD_PROFILE_NONE)
            return;

        uint64 key = GetBossKey(creature);
        if (key)
            ProcessedBosses.erase(key);
    }
};

void AddAdventurerGauntletCuratedRewardsScripts()
{
    new AdventurerGauntletBossRewardsScript();
}
