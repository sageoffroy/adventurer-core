#include "Creature.h"
#include "DatabaseEnv.h"
#include "DungeonCatalog.h"
#include "ItemTemplate.h"
#include "LootMgr.h"
#include "Map.h"
#include "ObjectMgr.h"
#include "Player.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"

#include <array>
#include <iostream>
#include <unordered_set>
#include <vector>

namespace
{
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
constexpr uint32 PotionDropChance = 1;
constexpr uint32 StockScrollDropChance = 1;

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
        std::cout << "[GauntletLoot] " << label << " item=" << entry << " TEMPLATE_MISSING" << std::endl;
        return;
    }

    std::cout << "[GauntletLoot] " << label
              << " item=" << entry
              << " class=" << item->Class
              << " subclass=" << item->SubClass
              << " quality=" << item->Quality
              << " requiredLevel=" << item->RequiredLevel
              << " itemLevel=" << item->ItemLevel
              << " inventoryType=" << item->InventoryType
              << std::endl;
}

void AddAuxiliaryDrops(Loot& loot, RewardPools const& pools, uint8 rewardLevel)
{
    uint32 ammoRoll = urand(1, 100);
    std::cout << "[GauntletLoot] AUX level=" << uint32(rewardLevel)
              << " ammoRoll=" << ammoRoll
              << " ammoChance=" << AmmoDropChance
              << " arrowPool=" << pools.Arrows.size()
              << " potionPool=" << pools.Potions.size()
              << " scrollPool=" << pools.Scrolls.size()
              << std::endl;

    if (ammoRoll <= AmmoDropChance)
    {
        uint32 arrowEntry = SelectUsableAuxiliaryFromPool(pools.Arrows, rewardLevel);
        std::cout << "[GauntletLoot] >>> AMMO SUCCESS roll=" << ammoRoll
                  << " selected=" << arrowEntry << std::endl;
        if (arrowEntry)
            LogSelectedItem("AMMO_SELECTED", arrowEntry);
        AddLootItem(loot, arrowEntry, 40, 100);
    }

    uint32 potionRoll = urand(1, 100);
    std::cout << "[GauntletLoot] AUX potionRoll=" << potionRoll
              << " potionChance=" << PotionDropChance << std::endl;

    if (potionRoll <= PotionDropChance)
    {
        uint32 itemEntry = SelectUsableAuxiliaryFromPool(pools.Potions, rewardLevel);

        std::cout << "[GauntletLoot] >>> POTION SUCCESS roll=" << potionRoll
                  << " selected=" << itemEntry << std::endl;
        if (itemEntry)
            LogSelectedItem("POTION_SELECTED", itemEntry);
        AddLootItem(loot, itemEntry, 1, 1);
    }

    uint32 scrollRoll = urand(1, 100);
    std::cout << "[GauntletLoot] AUX stockScrollRoll=" << scrollRoll
              << " stockScrollChance=" << StockScrollDropChance << std::endl;

    if (scrollRoll <= StockScrollDropChance)
    {
        uint32 itemEntry = SelectUsableAuxiliaryFromPool(pools.Scrolls, rewardLevel);

        std::cout << "[GauntletLoot] >>> STOCK SCROLL SUCCESS roll=" << scrollRoll
                  << " selected=" << itemEntry << std::endl;
        if (itemEntry)
            LogSelectedItem("STOCK_SCROLL_SELECTED", itemEntry);
        AddLootItem(loot, itemEntry, 1, 1);
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

uint32 SelectBossPrimaryReward(RewardPools const& pools, uint8 rewardLevel,
    std::unordered_set<uint32>& usedEntries, uint32 epicChancePercent)
{
    RewardPool pool = urand(1, 100) <= epicChancePercent ? REWARD_EPIC : REWARD_BLUE;
    return SelectClosestFromPool(pools.Items[pool], rewardLevel, usedEntries);
}

void AddBlueExtrasPerSurvivor(Loot& loot, RewardPools const& pools, uint8 rewardLevel,
    uint32 survivorCount, uint32 chancePercent, std::unordered_set<uint32>& usedEntries)
{
    for (uint32 survivor = 0; survivor < survivorCount; ++survivor)
        if (urand(1, 100) <= chancePercent)
            AddLootItem(
                loot,
                SelectClosestFromPool(pools.Items[REWARD_BLUE], rewardLevel, usedEntries));
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

    // Intermediate boss: one guaranteed quality roll.
    // 97% blue / 3% epic, plus one independent 15% blue roll per survivor.
    AddLootItem(
        loot,
        SelectBossPrimaryReward(pools, rewardLevel, usedEntries, 3));
    AddBlueExtrasPerSurvivor(
        loot,
        pools,
        rewardLevel,
        survivorCount,
        15,
        usedEntries);

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

    // Final boss: one guaranteed quality roll.
    // 87% blue / 13% epic, plus one independent 25% blue roll per survivor.
    AddLootItem(
        loot,
        SelectBossPrimaryReward(pools, rewardLevel, usedEntries, 13));
    AddBlueExtrasPerSurvivor(
        loot,
        pools,
        rewardLevel,
        survivorCount,
        25,
        usedEntries);

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
    std::cout << "[GauntletLoot] COMMON entry=" << creature->GetEntry()
              << " guid=" << creature->GetGUID().GetCounter()
              << " instance=" << creature->GetInstanceId()
              << " rewardLevel=" << uint32(rewardLevel)
              << " survivors=" << survivorCount
              << " equipRoll=" << roll << std::endl;

    RewardPool pool;
    if (roll <= 400)
        pool = REWARD_GREEN;
    else if (roll <= 450)
        pool = REWARD_BLUE;
    else if (roll <= 455)
        pool = REWARD_EPIC;
    else
        pool = REWARD_LEGENDARY;

    if (pool != REWARD_LEGENDARY)
    {
        std::unordered_set<uint32> usedEntries;
        uint32 itemEntry = SelectClosestFromPool(pools.Items[pool], rewardLevel, usedEntries);
        std::cout << "[GauntletLoot] EQUIPMENT pool=" << uint32(pool)
                  << " selected=" << itemEntry << std::endl;
        if (itemEntry)
        {
            LogSelectedItem("EQUIPMENT_SELECTED", itemEntry);
            AddLootItem(creature->loot, itemEntry);
            added = true;
        }
    }
    else
        std::cout << "[GauntletLoot] EQUIPMENT no drop" << std::endl;

    size_t beforeAuxiliary = creature->loot.items.size();
    AddAuxiliaryDrops(creature->loot, pools, rewardLevel);
    added = added || creature->loot.items.size() > beforeAuxiliary;

    std::cout << "[GauntletLoot] COMMON done entry=" << creature->GetEntry()
              << " guid=" << creature->GetGUID().GetCounter()
              << " lootItemsBeforeAux=" << beforeAuxiliary
              << " lootItemsAfterAux=" << creature->loot.items.size()
              << " added=" << added << std::endl;

    if (added)
        creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
    return added;
}

void ProcessCreatureAfterDeath(Creature* creature)
{
    if (!creature || creature->IsAlive() ||
        !AdventurerGauntlet::DungeonCatalog::IsSupportedDungeonMap(creature->GetMapId()))
        return;

    uint64 key = GetCreatureKey(creature);
    if (!key || ProcessedCreatures.find(key) != ProcessedCreatures.end())
        return;
    ProcessedCreatures.insert(key);

    uint8 rewardProfile = GetRewardProfile(creature->GetEntry());

    // Boss loot is a Gauntlet rule, not something that must be registered
    // creature-by-creature. Explicit DB profiles still win (for example a
    // campaign/final boss), but every unconfigured dungeon boss falls back to
    // the checkpoint boss profile and therefore has its stock loot replaced.
    if (rewardProfile == REWARD_PROFILE_NONE && creature->IsDungeonBoss())
        rewardProfile = REWARD_PROFILE_CHECKPOINT;

    std::cout << "[GauntletLoot] DEATH entry=" << creature->GetEntry()
              << " guid=" << creature->GetGUID().GetCounter()
              << " instance=" << creature->GetInstanceId()
              << " key=" << key
              << " profile=" << uint32(rewardProfile)
              << " level=" << uint32(creature->GetLevel()) << std::endl;

    if (rewardProfile == REWARD_PROFILE_FINAL)
    {
        std::cout << "[GauntletLoot] ROUTE final boss" << std::endl;
        if (FillFinalBossLoot(creature->loot, creature->GetMap()))
            creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        return;
    }
    if (rewardProfile == REWARD_PROFILE_CHECKPOINT)
    {
        std::cout << "[GauntletLoot] ROUTE checkpoint" << std::endl;
        if (FillCheckpointLoot(creature->loot, creature->GetMap()))
            creature->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        return;
    }

    std::cout << "[GauntletLoot] ROUTE common mob" << std::endl;
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
        if (!creature ||
            !AdventurerGauntlet::DungeonCatalog::IsSupportedDungeonMap(creature->GetMapId()))
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
