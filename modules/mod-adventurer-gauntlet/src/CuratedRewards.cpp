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

#include <array>
#include <unordered_set>
#include <vector>

namespace
{
constexpr uint32 RagefireMapId = 389;
constexpr uint32 UniversalMask = 0xFFFFFFFFu;
constexpr uint32 AdventurerItemRangeFirst = 910000;
constexpr uint32 AdventurerItemRangeLast = 910999;

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

std::unordered_set<uint64> ProcessedCreatures;

uint8 GetRewardProfile(uint32 creatureEntry)
{
    if (QueryResult result = WorldDatabase.Query(
        "SELECT `reward_profile` FROM `adventurer_gauntlet_loot_rule` WHERE `creature_entry` = {}",
        creatureEntry))
        return (*result)[0].Get<uint8>();
    return REWARD_PROFILE_NONE;
}

uint64 GetCreatureKey(Creature const* creature)
{
    return creature ? ((uint64(creature->GetInstanceId()) << 32) | uint64(creature->GetGUID().GetCounter())) : 0;
}

uint32 LevelDistance(uint32 requiredLevel, uint8 rewardLevel)
{
    return requiredLevel > rewardLevel ? requiredLevel - rewardLevel : rewardLevel - requiredLevel;
}

bool PassesCommonRewardRules(uint32 entry, ItemTemplate const& item)
{
    // 910xxx are fixed Adventurer/vendor/starting items, not Gauntlet rewards.
    // Keeping them out of the procedural pool also prevents retired legacy
    // "contrabando" rows left in a development DB from resurfacing as loot.
    if (entry >= AdventurerItemRangeFirst && entry <= AdventurerItemRangeLast)
        return false;
    if (item.Class != ITEM_CLASS_WEAPON && item.Class != ITEM_CLASS_ARMOR)
        return false;
    if (item.InventoryType == INVTYPE_NON_EQUIP || item.InventoryType == INVTYPE_BAG)
        return false;
    if (!item.RequiredLevel)
        return false;
    if (item.ItemLevel < item.RequiredLevel || item.ItemLevel > item.RequiredLevel + 15)
        return false;
    if (item.AllowableClass != UniversalMask || item.AllowableRace != UniversalMask)
        return false;
    if (item.RequiredSkill || item.RequiredSpell || item.RequiredReputationFaction ||
        item.RequiredHonorRank || item.RequiredCityRank)
        return false;
    if (item.HasFlag(ITEM_FLAG_DEPRECATED))
        return false;
    return true;
}

RewardPools BuildControlledPools()
{
    RewardPools pools;
    ItemTemplateContainer const* itemStore = sObjectMgr->GetItemTemplateStore();
    if (!itemStore)
        return pools;

    for (auto const& [entry, item] : *itemStore)
    {
        if (!PassesCommonRewardRules(entry, item))
            continue;

        if (item.Quality == ITEM_QUALITY_UNCOMMON)
            pools.Items[REWARD_GREEN].push_back(entry);
        else if (item.Quality == ITEM_QUALITY_RARE)
            pools.Items[REWARD_BLUE].push_back(entry);
        else if (item.Quality == ITEM_QUALITY_EPIC)
            pools.Items[REWARD_EPIC].push_back(entry);

        // Legendary rewards remain disabled until we explicitly enable their drop rate.
    }
    return pools;
}

uint32 SelectClosestFromPool(std::vector<uint32> const& candidates, uint8 rewardLevel,
    std::unordered_set<uint32>& usedEntries)
{
    if (candidates.empty())
        return 0;

    uint32 bestDistance = UINT32_MAX;
    std::vector<uint32> closest;

    // Choose uniformly from every valid item at the nearest RequiredLevel.
    // The old implementation sorted ties by entry and then considered only the
    // first five rows. Stock items have much smaller IDs than our 911xxx range,
    // so a dense stock level (notably low-level daggers) could make the entire
    // generated Gauntlet catalog practically unreachable even though it passed
    // every reward filter.
    for (uint32 entry : candidates)
    {
        if (usedEntries.find(entry) != usedEntries.end())
            continue;

        ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
        if (!item)
            continue;

        uint32 distance = LevelDistance(item->RequiredLevel, rewardLevel);
        if (distance < bestDistance)
        {
            bestDistance = distance;
            closest.clear();
            closest.push_back(entry);
        }
        else if (distance == bestDistance)
            closest.push_back(entry);
    }

    if (closest.empty())
        return 0;

    uint32 entry = closest[urand(0, static_cast<uint32>(closest.size() - 1))];
    usedEntries.insert(entry);
    return entry;
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

void AddCheckpointExtraRoll(Loot& loot, RewardPools const& pools, uint8 rewardLevel,
    std::unordered_set<uint32>& usedEntries)
{
    uint32 roll = urand(1, 100);
    if (roll <= 50)
        return;
    if (roll <= 80)
        AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_GREEN], rewardLevel, usedEntries));
    else if (roll <= 90)
        AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_BLUE], rewardLevel, usedEntries));
    else if (roll <= 99)
        AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_EPIC], rewardLevel, usedEntries));
}

void AddFinalExtraRoll(Loot& loot, RewardPools const& pools, uint8 rewardLevel,
    std::unordered_set<uint32>& usedEntries)
{
    uint32 roll = urand(1, 100);
    if (roll <= 25)
        return;
    if (roll <= 75)
        AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_GREEN], rewardLevel, usedEntries));
    else if (roll <= 90)
        AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_BLUE], rewardLevel, usedEntries));
    else if (roll <= 97)
        AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_EPIC], rewardLevel, usedEntries));
}

bool FillCheckpointLoot(Loot& loot, Map* map)
{
    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(map, survivorCount, rewardLevel))
        return false;
    RewardPools pools = BuildControlledPools();
    std::unordered_set<uint32> usedEntries;
    uint32 gold = loot.gold;
    loot.clear();
    loot.loot_type = LOOT_CORPSE;
    loot.gold = gold;
    for (uint32 reward = 0; reward < survivorCount; ++reward)
        AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_GREEN], rewardLevel, usedEntries));
    AddCheckpointExtraRoll(loot, pools, rewardLevel, usedEntries);
    return !loot.empty();
}

bool FillFinalBossLoot(Loot& loot, Map* map)
{
    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(map, survivorCount, rewardLevel))
        return false;
    RewardPools pools = BuildControlledPools();
    std::unordered_set<uint32> usedEntries;
    uint32 gold = loot.gold;
    loot.clear();
    loot.loot_type = LOOT_CORPSE;
    loot.gold = gold;
    AddLootItem(loot, SelectClosestFromPool(pools.Items[REWARD_BLUE], rewardLevel, usedEntries));
    AddFinalExtraRoll(loot, pools, rewardLevel, usedEntries);
    return !loot.empty();
}

bool AddCommonMobTestDrop(Creature* creature)
{
    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(creature->GetMap(), survivorCount, rewardLevel))
        return false;

    // Temporary test rates: 20% green, 4% blue, 1% epic, 75% no extra item.
    uint32 roll = urand(1, 10000);
    RewardPool pool;
    if (roll <= 2000)
        pool = REWARD_GREEN;
    else if (roll <= 2400)
        pool = REWARD_BLUE;
    else if (roll <= 2500)
        pool = REWARD_EPIC;
    else
        return false;

    RewardPools pools = BuildControlledPools();
    std::unordered_set<uint32> usedEntries;
    uint32 itemEntry = SelectClosestFromPool(pools.Items[pool], rewardLevel, usedEntries);
    if (!itemEntry)
        return false;
    AddLootItem(creature->loot, itemEntry);
    creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
    return true;
}

void ProcessCreatureAfterDeath(Creature* creature)
{
    if (!creature || creature->IsAlive() || creature->GetMapId() != RagefireMapId)
        return;
    uint64 key = GetCreatureKey(creature);
    if (!key || ProcessedCreatures.find(key) != ProcessedCreatures.end())
        return;
    ProcessedCreatures.insert(key);

    uint8 rewardProfile = GetRewardProfile(creature->GetEntry());
    if (rewardProfile == REWARD_PROFILE_FINAL)
    {
        if (FillFinalBossLoot(creature->loot, creature->GetMap()))
            creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        return;
    }
    if (rewardProfile == REWARD_PROFILE_CHECKPOINT)
    {
        if (FillCheckpointLoot(creature->loot, creature->GetMap()))
            creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        return;
    }
    AddCommonMobTestDrop(creature);
}
}

class AdventurerGauntletBossRewardsScript : public AllCreatureScript
{
public:
    AdventurerGauntletBossRewardsScript()
        : AllCreatureScript("AdventurerGauntletBossRewardsScript") { }

    void OnAllCreatureUpdate(Creature* creature, uint32 /*diff*/) override
    {
        ProcessCreatureAfterDeath(creature);
    }

    void OnCreatureRemoveWorld(Creature* creature) override
    {
        if (!creature || creature->GetMapId() != RagefireMapId)
            return;
        uint64 key = GetCreatureKey(creature);
        if (key)
            ProcessedCreatures.erase(key);
    }
};

void AddAdventurerGauntletCuratedRewardsScripts()
{
    new AdventurerGauntletBossRewardsScript();
}
