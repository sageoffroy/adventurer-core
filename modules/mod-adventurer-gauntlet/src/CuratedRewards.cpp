#include "Config.h"
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
constexpr uint32 GauntletItemMin = 911100;
constexpr uint32 GauntletItemMax = 911399;

struct RewardPools
{
    std::array<std::vector<uint32>, 3> Items;
};

std::unordered_set<ObjectGuid::LowType> ProcessedChests;

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

        // Greens stay unpredictable and come from AzerothCore's stock world pool.
        if (item.Quality == ITEM_QUALITY_UNCOMMON)
        {
            if (!customGauntletItem)
                pools.Items[0].push_back(entry);
            continue;
        }

        // Blue and purple rewards are deliberately restricted to our curated
        // Gauntlet catalog. Stock rares/epics can no longer leak into the chest.
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

bool RefillChest(GameObject* chest)
{
    if (!chest || !chest->GetMap())
        return false;

    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    for (auto const& ref : chest->GetMap()->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!player || !player->IsAlive())
            continue;
        ++survivorCount;
        rewardLevel = rewardLevel == 0 ? player->GetLevel() : std::min<uint8>(rewardLevel, player->GetLevel());
    }
    if (!survivorCount || !rewardLevel)
        return false;

    RewardPools pools = BuildControlledPools(rewardLevel);
    std::unordered_set<uint32> usedEntries;

    chest->loot.clear();
    chest->loot.loot_type = LOOT_CORPSE;
    for (uint32 reward = 0; reward < survivorCount; ++reward)
    {
        uint32 itemEntry = SelectReward(pools, usedEntries);
        if (!itemEntry)
            break;
        LootStoreItem lootItem(itemEntry, 0, 100.0f, false, LOOT_MODE_DEFAULT, 0, 1, 1);
        chest->loot.AddItem(lootItem);
    }

    chest->SetLootRecipient(chest->GetMap());
    chest->SetLootGenerationTime();
    return true;
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

        // The original celebration fills the chest immediately after summoning
        // it. The first world update runs afterward, so replacing the loot here
        // is deterministic and leaves the celebration/portal flow untouched.
        if (RefillChest(go))
            ProcessedChests.insert(guid);
    }

    void OnGameObjectRemoveWorld(GameObject* go) override
    {
        if (go && go->GetEntry() == ExpeditionChestEntry)
            ProcessedChests.erase(go->GetGUID().GetCounter());
    }
};

void AddAdventurerGauntletCuratedRewardsScripts()
{
    new AdventurerGauntletCuratedRewardsScript();
}
