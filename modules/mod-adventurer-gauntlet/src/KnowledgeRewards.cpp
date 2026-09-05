#include "KnowledgeRewards.h"

#include "ItemTemplate.h"
#include "LootMgr.h"
#include "ObjectMgr.h"
#include "Random.h"

#include <vector>

namespace AdventurerGauntlet::KnowledgeRewards
{
namespace
{
constexpr uint32 KnowledgeDropChanceBasisPoints = 200; // 2.00% on a 1..10000 roll.
constexpr uint32 KnowledgeEntryFirst = 910240;
constexpr uint32 KnowledgeEntryLast = 910599;
constexpr uint8 KnowledgeLevelLookahead = 3;

void AddLootItem(Loot& loot, uint32 entry)
{
    LootStoreItem item(entry, 0, 100.0f, false, LOOT_MODE_DEFAULT, 0, 1, 1);
    loot.AddItem(item);
}
}

bool TryAddDrop(Loot& loot, uint8 rewardLevel)
{
    if (urand(1, 10000) > KnowledgeDropChanceBasisPoints)
        return false;

    uint32 levelCap = uint32(rewardLevel) + KnowledgeLevelLookahead;
    std::vector<uint32> eligible;
    for (uint32 entry = KnowledgeEntryFirst; entry <= KnowledgeEntryLast; ++entry)
    {
        ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
        if (!item || !item->RequiredLevel || item->RequiredLevel > levelCap)
            continue;
        eligible.push_back(entry);
    }

    if (eligible.empty())
        return false;

    AddLootItem(loot, eligible[urand(0, static_cast<uint32>(eligible.size() - 1))]);
    return true;
}
}
