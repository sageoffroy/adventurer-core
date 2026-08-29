#include "Creature.h"
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
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 KhadgarTeleportVisual = 41232;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 RagefireFinalBossEntry = 11520;
constexpr uint32 GauntletItemMin = 911000;
constexpr uint32 GauntletItemMax = 911999;

constexpr std::array<char const*, 8> KhadgarVictoryLines = {
    "Pensaba que no llegarian ni al primer jefe.",
    "Admito que esperaba bastante menos de ustedes.",
    "No estuvo mal... para principiantes.",
    "Empiezo a creer que esto puede ponerse interesante.",
    "Bien. Sobrevivieron. No se acostumbren.",
    "Vaya. Tal vez no haya sobreestimado sus posibilidades despues de todo.",
    "Debo admitirlo: ya estaba preparando unas palabras para su funeral.",
    "Excelente. Ahora veamos cuanto dura esa confianza en la siguiente mazmorra."
};

struct RewardPools
{
    std::vector<uint32> GreenItems;
    std::vector<uint32> SetItems;
};

bool IsEquippableReward(ItemTemplate const& item, uint8 playerLevel)
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

    return !item.HasFlag(ITEM_FLAG_DEPRECATED);
}

RewardPools BuildRewardPools(uint8 playerLevel)
{
    RewardPools pools;
    ItemTemplateContainer const* itemStore = sObjectMgr->GetItemTemplateStore();
    if (!itemStore)
        return pools;

    for (auto const& [entry, item] : *itemStore)
    {
        if (!IsEquippableReward(item, playerLevel))
            continue;

        if (entry >= GauntletItemMin && entry <= GauntletItemMax)
        {
            if (item.Quality == ITEM_QUALITY_RARE)
                pools.SetItems.push_back(entry);
            continue;
        }

        if (item.Quality == ITEM_QUALITY_UNCOMMON)
            pools.GreenItems.push_back(entry);
    }

    return pools;
}

uint32 SelectUniqueItem(std::vector<uint32> const& candidates, std::unordered_set<uint32>& usedEntries)
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

void AddLootItem(Creature* boss, uint32 itemEntry)
{
    if (!boss || !itemEntry)
        return;

    LootStoreItem lootItem(itemEntry, 0, 100.0f, false, LOOT_MODE_DEFAULT, 0, 1, 1);
    boss->loot.AddItem(lootItem);
}

void FillBossLoot(Creature* khadgar, Creature* boss)
{
    if (!khadgar || !boss || !khadgar->GetMap())
        return;

    uint32 survivorCount = 0;
    uint8 rewardLevel = 0;

    for (auto const& ref : khadgar->GetMap()->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (!player || !player->IsAlive())
            continue;

        ++survivorCount;
        rewardLevel = rewardLevel == 0 ? player->GetLevel() : std::min<uint8>(rewardLevel, player->GetLevel());
    }

    if (!survivorCount || !rewardLevel)
        return;

    RewardPools pools = BuildRewardPools(rewardLevel);
    std::unordered_set<uint32> usedEntries;

    // The boss corpse is the only reward container. Stock boss loot is removed:
    // one level-appropriate green item is added per survivor, plus one blue
    // Adventurer Gauntlet set piece for the whole group.
    boss->loot.clear();
    boss->loot.loot_type = LOOT_CORPSE;

    for (uint32 reward = 0; reward < survivorCount; ++reward)
        AddLootItem(boss, SelectUniqueItem(pools.GreenItems, usedEntries));

    AddLootItem(boss, SelectUniqueItem(pools.SetItems, usedEntries));

    if (!boss->loot.empty())
        boss->SetDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
    else
        boss->RemoveDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
}
}

class AdventurerGauntletKhadgarCelebrationScript : public AllCreatureScript
{
public:
    AdventurerGauntletKhadgarCelebrationScript()
        : AllCreatureScript("AdventurerGauntletKhadgarCelebrationScript") { }

    void OnCreatureAddWorld(Creature* creature) override
    {
        // The permanent Khadgar is outside the dungeon. A summoned Khadgar in
        // Ragefire is the expedition guide that appears after the final boss.
        if (!creature || creature->GetEntry() != KhadgarEntry || creature->GetMapId() != RagefireMapId || !creature->IsSummon())
            return;

        if (Creature* finalBoss = creature->FindNearestCreature(RagefireFinalBossEntry, 20.0f, false))
            FillBossLoot(creature, finalBoss);

        creature->CastSpell(creature, KhadgarTeleportVisual, true);
        creature->HandleEmoteCommand(EMOTE_ONESHOT_APPLAUD);
        creature->Say(
            KhadgarVictoryLines[urand(0, KhadgarVictoryLines.size() - 1)],
            LANG_UNIVERSAL);

        // AccountStash.cpp observes this summoned Khadgar and creates the
        // expedition stash beside him. No separate reward chest is spawned.
    }
};

void AddAdventurerGauntletCelebrationScripts()
{
    new AdventurerGauntletKhadgarCelebrationScript();
}
