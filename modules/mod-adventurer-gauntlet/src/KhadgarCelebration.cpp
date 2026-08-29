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
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 ExpeditionChestEntry = 910001;
constexpr uint32 KhadgarTeleportVisual = 41232;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 RagefireFinalBossEntry = 11520;

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
    std::array<std::vector<uint32>, 3> Items;
};

bool IsRewardCandidate(ItemTemplate const& item, uint8 playerLevel)
{
    if (item.Quality < ITEM_QUALITY_UNCOMMON || item.Quality > ITEM_QUALITY_EPIC)
        return false;

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

    // The gauntlet deliberately ignores class/spec, but it should not hand out
    // items gated behind professions, reputation, spells or old PvP ranks.
    if (item.RequiredSkill || item.RequiredSpell || item.RequiredReputationFaction ||
        item.RequiredHonorRank || item.RequiredCityRank)
        return false;

    if (item.HasFlag(ITEM_FLAG_DEPRECATED))
        return false;

    return true;
}

RewardPools BuildRewardPools(uint8 playerLevel)
{
    RewardPools pools;
    ItemTemplateContainer const* itemStore = sObjectMgr->GetItemTemplateStore();
    if (!itemStore)
        return pools;

    for (auto const& [entry, item] : *itemStore)
    {
        if (!IsRewardCandidate(item, playerLevel))
            continue;

        pools.Items[item.Quality - ITEM_QUALITY_UNCOMMON].push_back(entry);
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

uint32 SelectRewardItem(RewardPools const& pools, std::unordered_set<uint32>& usedEntries)
{
    uint8 preferred = RollRewardPoolIndex();

    for (uint8 offset = 0; offset < 3; ++offset)
    {
        uint8 index = (preferred + offset) % 3;
        auto const& candidates = pools.Items[index];
        if (candidates.empty())
            continue;

        // Prefer unique rewards inside a single chest. If the pool is too small,
        // a later fallback may repeat an item rather than reducing reward count.
        uint32 attempts = std::min<uint32>(static_cast<uint32>(candidates.size()), 32);
        for (uint32 attempt = 0; attempt < attempts; ++attempt)
        {
            uint32 entry = candidates[urand(0, static_cast<uint32>(candidates.size() - 1))];
            if (usedEntries.insert(entry).second)
                return entry;
        }
    }

    for (auto const& candidates : pools.Items)
    {
        if (!candidates.empty())
            return candidates[urand(0, static_cast<uint32>(candidates.size() - 1))];
    }

    return 0;
}

void FillExpeditionChest(Creature* khadgar, GameObject* chest)
{
    if (!khadgar || !chest || !khadgar->GetMap())
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

    chest->loot.clear();
    chest->loot.loot_type = LOOT_CORPSE;

    for (uint32 reward = 0; reward < survivorCount; ++reward)
    {
        uint32 itemEntry = SelectRewardItem(pools, usedEntries);
        if (!itemEntry)
            break;

        LootStoreItem lootItem(itemEntry, 0, 100.0f, false, LOOT_MODE_DEFAULT, 0, 1, 1);
        chest->loot.AddItem(lootItem);
    }

    chest->SetLootRecipient(khadgar->GetMap());
    chest->SetLootGenerationTime();
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

        // The final boss no longer has its stock loot. Its reward belongs to the
        // Expedition Chest instead.
        if (Creature* finalBoss = creature->FindNearestCreature(RagefireFinalBossEntry, 20.0f, false))
        {
            finalBoss->loot.clear();
            finalBoss->RemoveDynamicFlag(UNIT_DYNFLAG_LOOTABLE);
        }

        creature->CastSpell(creature, KhadgarTeleportVisual, true);
        creature->HandleEmoteCommand(EMOTE_ONESHOT_APPLAUD);
        creature->Say(
            KhadgarVictoryLines[urand(0, KhadgarVictoryLines.size() - 1)],
            LANG_UNIVERSAL);

        GameObject* chest = creature->SummonGameObject(
            ExpeditionChestEntry,
            creature->GetPositionX(),
            creature->GetPositionY() - 2.5f,
            creature->GetPositionZ(),
            0.0f,
            0.0f,
            0.0f,
            0.0f,
            1.0f,
            0);

        FillExpeditionChest(creature, chest);
    }
};

void AddAdventurerGauntletCelebrationScripts()
{
    new AdventurerGauntletKhadgarCelebrationScript();
}
