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
constexpr uint32 ClosestCandidateCount = 5;
constexpr std::array<uint32, 6> CuratedStandaloneRewardEntries = {
    911200, 911201, 911202, 911203, 911204, 911205
};

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

bool IsCuratedCustomReward(uint32 entry)
{
    // Curated early sets:
    // 911100-911109  Juramento del Coloso + Martillo de Ceniza
    // 911125-911129  Guardia del Alba
    // 911135-911144  Cuero de Oso + Colmillo de Niebla
    if ((entry >= 911100 && entry <= 911109) ||
        (entry >= 911125 && entry <= 911129) ||
        (entry >= 911135 && entry <= 911144))
        return true;

    return std::find(CuratedStandaloneRewardEntries.begin(), CuratedStandaloneRewardEntries.end(), entry)
        != CuratedStandaloneRewardEntries.end();
}

bool PassesCommonRewardRules(ItemTemplate const& item)
{
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
        // The old generated catalog stays excluded. Only curated low-level
        // custom pieces participate alongside valid Blizzard items.
        if (entry >= GauntletItemMin && entry <= GauntletItemMax && !IsCuratedCustomReward(entry))
            continue;

        if (!PassesCommonRewardRules(item))
            continue;

        if (item.Quality == ITEM_QUALITY_UNCOMMON)
            pools.Items[REWARD_GREEN].push_back(entry);
        else if (item.Quality == ITEM_QUALITY_RARE)
            pools.Items[REWARD_BLUE].push_back(entry);
        else if (item.Quality == ITEM_QUALITY_EPIC)
            pools.Items[REWARD_EPIC].push_back(entry);

        // Legendary rewards are intentionally disabled until their curated
        // catalog is ready.
    }

    return pools;
}

uint32 SelectClosestFromPool(std::vector<uint32> const& candidates, uint8 rewardLevel,
    std::unordered_set<uint32>& usedEntries)
{
    if (candidates.empty())
        return 0;

    std::vector<uint32> ordered;
    ordered.reserve(candidates.size());
    for (uint32 entry : candidates)
        if (usedEntries.find(entry) == usedEntries.end())
            ordered.push_back(entry);

    if (ordered.empty())
        return 0;

    std::sort(ordered.begin(), ordered.end(), [rewardLevel](uint32 leftEntry, uint32 rightEntry)
    {
        ItemTemplate const* left = sObjectMgr->GetItemTemplate(leftEntry);
        ItemTemplate const* right = sObjectMgr->GetItemTemplate(rightEntry);
        if (!left || !right)
            return leftEntry < rightEntry;

        uint32 leftDistance = LevelDistance(left->RequiredLevel, rewardLevel);
        uint32 rightDistance = LevelDistance(right->RequiredLevel, rewardLevel);
        if (leftDistance != rightDistance)
            return leftDistance < rightDistance;

        return leftEntry < rightEntry;
    });

    uint32 closestCount = std::min<uint32>(ClosestCandidateCount, static_cast<uint32>(ordered.size()));
    uint32 entry = ordered[urand(0, closestCount - 1)];
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

    // Temporary testing rates: one extra equipment item at most.
    // 20% green, 4% blue, 1% epic, 75% nothing. Legendary is disabled.
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
