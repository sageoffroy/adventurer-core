#include "Creature.h"
#include "DatabaseEnv.h"
#include "ItemTemplate.h"
#include "Log.h"
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
constexpr uint32 StockItemEntryLimit = AdventurerItemRangeFirst;
constexpr uint32 ItemClassConsumable = 0;
constexpr uint32 ItemClassProjectile = 6;
constexpr uint32 ItemSubclassPotion = 1;
constexpr uint32 ItemSubclassArrow = 2;
constexpr uint32 ItemSubclassScroll = 4;
constexpr uint32 AmmoDropChance = 1;
constexpr uint32 ConsumableDropChance = 5;

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
    std::vector<uint32> Arrows;
    std::vector<uint32> Potions;
    std::vector<uint32> Scrolls;
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

bool PassesStockAuxiliaryRules(uint32 entry, ItemTemplate const& item)
{
    if (entry >= StockItemEntryLimit)
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
        if (PassesCommonRewardRules(entry, item))
        {
            if (item.Quality == ITEM_QUALITY_UNCOMMON)
                pools.Items[REWARD_GREEN].push_back(entry);
            else if (item.Quality == ITEM_QUALITY_RARE)
                pools.Items[REWARD_BLUE].push_back(entry);
            else if (item.Quality == ITEM_QUALITY_EPIC)
                pools.Items[REWARD_EPIC].push_back(entry);
        }

        if (!PassesStockAuxiliaryRules(entry, item))
            continue;

        if (item.Class == ItemClassProjectile && item.SubClass == ItemSubclassArrow)
            pools.Arrows.push_back(entry);
        else if (item.Class == ItemClassConsumable)
        {
            if (item.SubClass == ItemSubclassPotion)
                pools.Potions.push_back(entry);
            else if (item.SubClass == ItemSubclassScroll)
                pools.Scrolls.push_back(entry);
        }
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

uint32 SelectUsableAuxiliaryFromPool(std::vector<uint32> const& candidates, uint8 rewardLevel)
{
    if (candidates.empty())
        return 0;

    uint32 bestDistance = UINT32_MAX;
    std::vector<uint32> closest;
    for (uint32 entry : candidates)
    {
        ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
        if (!item || !item->RequiredLevel || item->RequiredLevel > rewardLevel)
            continue;

        uint32 distance = rewardLevel - item->RequiredLevel;
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
    return closest[urand(0, static_cast<uint32>(closest.size() - 1))];
}

void AddLootItem(Loot& loot, uint32 itemEntry, uint8 minCount = 1, uint8 maxCount = 1)
{
    if (!itemEntry)
        return;
    LootStoreItem lootItem(itemEntry, 0, 100.0f, false, LOOT_MODE_DEFAULT, 0, minCount, maxCount);
    loot.AddItem(lootItem);
}

void LogSelectedItem(char const* label, uint32 entry)
{
    ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
    if (!item)
    {
        LOG_INFO("module", "[GauntletLoot] {} item={} TEMPLATE_MISSING", label, entry);
        return;
    }

    LOG_INFO("module",
        "[GauntletLoot] {} item={} class={} subclass={} quality={} requiredLevel={} itemLevel={} inventoryType={}",
        label, entry, item->Class, item->SubClass, item->Quality, item->RequiredLevel, item->ItemLevel, item->InventoryType);
}

void AddAuxiliaryDrops(Loot& loot, RewardPools const& pools, uint8 rewardLevel)
{
    uint32 ammoRoll = urand(1, 100);
    LOG_INFO("module",
        "[GauntletLoot] AUX level={} ammoRoll={} ammoChance={} arrowPool={} potionPool={} scrollPool={}",
        rewardLevel, ammoRoll, AmmoDropChance, pools.Arrows.size(), pools.Potions.size(), pools.Scrolls.size());

    if (ammoRoll <= AmmoDropChance)
    {
        uint32 arrowEntry = SelectUsableAuxiliaryFromPool(pools.Arrows, rewardLevel);
        LOG_INFO("module", "[GauntletLoot] >>> AMMO SUCCESS roll={} selected={}", ammoRoll, arrowEntry);
        if (arrowEntry)
            LogSelectedItem("AMMO_SELECTED", arrowEntry);
        AddLootItem(loot, arrowEntry, 40, 100);
    }

    uint32 consumableRoll = urand(1, 100);
    LOG_INFO("module", "[GauntletLoot] AUX consumableRoll={} consumableChance={}", consumableRoll, ConsumableDropChance);

    if (consumableRoll <= ConsumableDropChance)
    {
        bool choosePotion = urand(0, 1) == 0;
        std::vector<uint32> const& primary = choosePotion ? pools.Potions : pools.Scrolls;
        std::vector<uint32> const& fallback = choosePotion ? pools.Scrolls : pools.Potions;
        uint32 itemEntry = SelectUsableAuxiliaryFromPool(primary, rewardLevel);
        if (!itemEntry)
            itemEntry = SelectUsableAuxiliaryFromPool(fallback, rewardLevel);

        LOG_INFO("module", "[GauntletLoot] >>> CONSUMABLE SUCCESS roll={} type={} selected={}",
            consumableRoll, choosePotion ? "potion" : "scroll", itemEntry);
        if (itemEntry)
            LogSelectedItem("CONSUMABLE_SELECTED", itemEntry);
        AddLootItem(loot, itemEntry, 1, 2);
    }
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
    AddAuxiliaryDrops(loot, pools, rewardLevel);
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
    AddAuxiliaryDrops(loot, pools, rewardLevel);
    return !loot.empty();
}

bool AddCommonMobTestDrop(Creature* creature)
{
    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;
    if (!GetRewardContext(creature->GetMap(), survivorCount, rewardLevel))
        return false;

    RewardPools pools = BuildControlledPools();
    bool added = false;

    uint32 roll = urand(1, 10000);
    LOG_INFO("module",
        "[GauntletLoot] COMMON entry={} guid={} instance={} rewardLevel={} survivors={} equipRoll={}",
        creature->GetEntry(), creature->GetGUID().GetCounter(), creature->GetInstanceId(), rewardLevel, survivorCount, roll);

    RewardPool pool;
    if (roll <= 2000)
        pool = REWARD_GREEN;
    else if (roll <= 2400)
        pool = REWARD_BLUE;
    else if (roll <= 2500)
        pool = REWARD_EPIC;
    else
        pool = REWARD_LEGENDARY;

    if (pool != REWARD_LEGENDARY)
    {
        std::unordered_set<uint32> usedEntries;
        uint32 itemEntry = SelectClosestFromPool(pools.Items[pool], rewardLevel, usedEntries);
        LOG_INFO("module", "[GauntletLoot] EQUIPMENT pool={} selected={}", static_cast<uint32>(pool), itemEntry);
        if (itemEntry)
        {
            LogSelectedItem("EQUIPMENT_SELECTED", itemEntry);
            AddLootItem(creature->loot, itemEntry);
            added = true;
        }
    }
    else
        LOG_INFO("module", "[GauntletLoot] EQUIPMENT no drop");

    size_t beforeAuxiliary = creature->loot.items.size();
    AddAuxiliaryDrops(creature->loot, pools, rewardLevel);
    added = added || creature->loot.items.size() > beforeAuxiliary;

    LOG_INFO("module", "[GauntletLoot] COMMON done entry={} guid={} lootItemsBeforeAux={} lootItemsAfterAux={} added={}",
        creature->GetEntry(), creature->GetGUID().GetCounter(), beforeAuxiliary, creature->loot.items.size(), added);

    if (added)
        creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
    return added;
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
    LOG_INFO("module",
        "[GauntletLoot] DEATH entry={} guid={} instance={} key={} profile={} level={}",
        creature->GetEntry(), creature->GetGUID().GetCounter(), creature->GetInstanceId(), key,
        static_cast<uint32>(rewardProfile), creature->GetLevel());

    if (rewardProfile == REWARD_PROFILE_FINAL)
    {
        LOG_INFO("module", "[GauntletLoot] ROUTE final boss");
        if (FillFinalBossLoot(creature->loot, creature->GetMap()))
            creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        return;
    }
    if (rewardProfile == REWARD_PROFILE_CHECKPOINT)
    {
        LOG_INFO("module", "[GauntletLoot] ROUTE checkpoint");
        if (FillCheckpointLoot(creature->loot, creature->GetMap()))
            creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        return;
    }

    LOG_INFO("module", "[GauntletLoot] ROUTE common mob");
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
