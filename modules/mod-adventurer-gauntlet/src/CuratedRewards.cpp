#include "Creature.h"
#include "GameObject.h"
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
constexpr uint32 ExpeditionChestEntry = 910001;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 RagefireOggleflintEntry = 11517;
constexpr uint32 RagefireJergoshEntry = 11518;
constexpr uint32 RagefireBazzalanEntry = 11519;
constexpr uint32 GauntletItemMin = 911100;
constexpr uint32 GauntletItemMax = 911399;

enum RewardPool : uint8
{
    REWARD_GREEN = 0,
    REWARD_BLUE = 1,
    REWARD_EPIC = 2,
    REWARD_LEGENDARY = 3,
};

struct RewardPools
{
    std::array<std::vector<uint32>, 4> Items;
};

std::unordered_set<ObjectGuid::LowType> ProcessedChests;
std::unordered_set<uint64> ProcessedBosses;

bool IsRagefireCheckpointBoss(uint32 entry)
{
    return entry == RagefireOggleflintEntry || entry == RagefireJergoshEntry || entry == RagefireBazzalanEntry;
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

        // Uncommon rewards remain unpredictable stock AzerothCore equipment.
        if (item.Quality == ITEM_QUALITY_UNCOMMON)
        {
            if (!customGauntletItem)
                pools.Items[REWARD_GREEN].push_back(entry);
            continue;
        }

        // Rare, epic and legendary rewards are Gauntlet-only discoveries.
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
    // One group-wide bonus roll: 50% nothing, 30% uncommon, 10% rare,
    // 9% epic, 1% legendary.
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
    // One group-wide bonus roll: 25% nothing, 50% uncommon, 15% rare,
    // 7% epic, 3% legendary.
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

    // Guaranteed base reward: one uncommon stock item per living survivor.
    for (uint32 reward = 0; reward < survivorCount; ++reward)
        AddLootItem(loot, SelectFromPool(pools.Items[REWARD_GREEN], usedEntries));

    AddCheckpointExtraRoll(loot, pools, usedEntries);
    return !loot.empty();
}

bool FillFinalChest(GameObject* chest)
{
    if (!chest || !chest->GetMap())
        return false;

    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(chest->GetMap(), survivorCount, rewardLevel))
        return false;

    RewardPools pools = BuildControlledPools(rewardLevel);
    std::unordered_set<uint32> usedEntries;

    chest->loot.clear();
    chest->loot.loot_type = LOOT_CORPSE;

    // Final boss base reward: exactly one controlled rare item for the group.
    AddLootItem(chest->loot, SelectFromPool(pools.Items[REWARD_BLUE], usedEntries));
    AddFinalExtraRoll(chest->loot, pools, usedEntries);

    chest->SetLootRecipient(chest->GetMap());
    chest->SetLootGenerationTime();
    return !chest->loot.empty();
}

void RefillCheckpointBossAfterDeath(Creature* boss)
{
    if (!boss || boss->IsAlive() || boss->GetMapId() != RagefireMapId || !IsRagefireCheckpointBoss(boss->GetEntry()))
        return;

    uint64 key = GetBossKey(boss);
    if (!key || ProcessedBosses.find(key) != ProcessedBosses.end())
        return;

    if (FillCheckpointLoot(boss->loot, boss->GetMap()))
    {
        boss->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        ProcessedBosses.insert(key);
    }
}
}

class AdventurerGauntletCuratedRewardsScript : public AllGameObjectScript
{
public:
    AdventurerGauntletCuratedRewardsScript()
        : AllGameObjectScript("AdventurerGauntletCuratedRewardsScript") { }

    void OnGameObjectUpdate(GameObject* go, uint32 /*diff*/) override
    {
        if (!go || go->GetEntry() != ExpeditionChestEntry || go->GetMapId() != RagefireMapId)
            return;

        ObjectGuid::LowType guid = go->GetGUID().GetCounter();
        if (ProcessedChests.find(guid) != ProcessedChests.end())
            return;

        if (FillFinalChest(go))
            ProcessedChests.insert(guid);
    }

    void OnGameObjectRemoveWorld(GameObject* go) override
    {
        if (go && go->GetEntry() == ExpeditionChestEntry)
            ProcessedChests.erase(go->GetGUID().GetCounter());
    }
};

class AdventurerGauntletBossRewardsScript : public AllCreatureScript
{
public:
    AdventurerGauntletBossRewardsScript()
        : AllCreatureScript("AdventurerGauntletBossRewardsScript") { }

    void OnAllCreatureUpdate(Creature* creature, uint32 /*diff*/) override
    {
        RefillCheckpointBossAfterDeath(creature);
    }

    void OnCreatureRemoveWorld(Creature* creature) override
    {
        if (!creature || creature->GetMapId() != RagefireMapId || !IsRagefireCheckpointBoss(creature->GetEntry()))
            return;

        uint64 key = GetBossKey(creature);
        if (key)
            ProcessedBosses.erase(key);
    }
};

void AddAdventurerGauntletCuratedRewardsScripts()
{
    new AdventurerGauntletCuratedRewardsScript();
    new AdventurerGauntletBossRewardsScript();
}
