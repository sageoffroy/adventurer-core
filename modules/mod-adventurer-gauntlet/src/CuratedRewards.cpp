#include "Config.h"
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

struct RewardPools
{
    std::array<std::vector<uint32>, 3> Items;
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
    uint32 maxItemLevel = playerLevel + 7;
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

        if (item.Quality == ITEM_QUALITY_UNCOMMON)
        {
            if (!customGauntletItem)
                pools.Items[0].push_back(entry);
            continue;
        }

        if (!customGauntletItem)
            continue;
        if (item.Quality == ITEM_QUALITY_RARE)
            pools.Items[1].push_back(entry);
        else if (item.Quality == ITEM_QUALITY_EPIC)
            pools.Items[2].push_back(entry);
    }

    return pools;
}

uint8 RollRewardPoolIndex()
{
    uint32 greenWeight = sConfigMgr->GetOption<uint32>("AdventurerGauntlet.RewardGreenWeight", 70);
    uint32 blueWeight = sConfigMgr->GetOption<uint32>("AdventurerGauntlet.RewardBlueWeight", 25);
    uint32 purpleWeight = sConfigMgr->GetOption<uint32>("AdventurerGauntlet.RewardPurpleWeight", 5);
    uint32 totalWeight = greenWeight + blueWeight + purpleWeight;
    if (!totalWeight)
        return 0;

    uint32 roll = urand(1, totalWeight);
    if (roll <= greenWeight)
        return 0;
    if (roll <= greenWeight + blueWeight)
        return 1;
    return 2;
}

uint32 SelectReward(RewardPools const& pools, std::unordered_set<uint32>& usedEntries)
{
    uint8 preferred = RollRewardPoolIndex();
    for (uint8 offset = 0; offset < 3; ++offset)
    {
        uint8 index = (preferred + offset) % 3;
        auto const& candidates = pools.Items[index];
        if (candidates.empty())
            continue;

        uint32 attempts = std::min<uint32>(static_cast<uint32>(candidates.size()), 32);
        for (uint32 attempt = 0; attempt < attempts; ++attempt)
        {
            uint32 entry = candidates[urand(0, static_cast<uint32>(candidates.size() - 1))];
            if (usedEntries.insert(entry).second)
                return entry;
        }
    }

    for (auto const& candidates : pools.Items)
        if (!candidates.empty())
            return candidates[urand(0, static_cast<uint32>(candidates.size() - 1))];
    return 0;
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

bool FillControlledLoot(Loot& loot, Map* map, bool preserveGold)
{
    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(map, survivorCount, rewardLevel))
        return false;

    RewardPools pools = BuildControlledPools(rewardLevel);
    std::unordered_set<uint32> usedEntries;
    uint32 gold = preserveGold ? loot.gold : 0;

    loot.clear();
    loot.loot_type = LOOT_CORPSE;
    loot.gold = gold;

    for (uint32 reward = 0; reward < survivorCount; ++reward)
    {
        uint32 itemEntry = SelectReward(pools, usedEntries);
        if (!itemEntry)
            break;
        LootStoreItem lootItem(itemEntry, 0, 100.0f, false, LOOT_MODE_DEFAULT, 0, 1, 1);
        loot.AddItem(lootItem);
    }

    return !loot.empty() || loot.gold;
}

bool RefillChest(GameObject* chest)
{
    if (!chest || !chest->GetMap())
        return false;

    if (!FillControlledLoot(chest->loot, chest->GetMap(), false))
        return false;

    chest->SetLootRecipient(chest->GetMap());
    chest->SetLootGenerationTime();
    return true;
}

void RefillCheckpointBossAfterDeath(Creature* boss)
{
    if (!boss || boss->IsAlive() || boss->GetMapId() != RagefireMapId || !IsRagefireCheckpointBoss(boss->GetEntry()))
        return;

    uint64 key = GetBossKey(boss);
    if (!key || ProcessedBosses.find(key) != ProcessedBosses.end())
        return;

    if (FillControlledLoot(boss->loot, boss->GetMap(), true))
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

        if (RefillChest(go))
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
