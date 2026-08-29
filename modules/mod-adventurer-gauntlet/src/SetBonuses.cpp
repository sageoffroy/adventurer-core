#include "Item.h"
#include "Player.h"
#include "ScriptMgr.h"

#include <array>
#include <string_view>
#include <unordered_map>
#include <unordered_set>

namespace
{
struct GauntletSetPiece
{
    uint32 Entry;
    char const* SetKey;
};

struct GauntletSetBonus
{
    char const* SetKey;
    char const* SetName;
    uint8 PiecesRequired;
    uint32 SpellId;
    char const* Description;
};

#include "GeneratedGauntletSets.inc"

std::unordered_map<uint32, std::unordered_set<uint32>> AppliedSetSpells;

std::unordered_map<std::string_view, uint32> CountEquippedSetPieces(Player* player)
{
    std::unordered_map<std::string_view, uint32> counts;
    if (!player)
        return counts;

    for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
    {
        Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot);
        if (!item)
            continue;

        uint32 entry = item->GetEntry();
        for (GauntletSetPiece const& piece : GauntletSetPieces)
        {
            if (piece.Entry == entry)
            {
                ++counts[piece.SetKey];
                break;
            }
        }
    }

    return counts;
}

void RefreshGauntletSetBonuses(Player* player)
{
    if (!player)
        return;

    uint32 guid = player->GetGUID().GetCounter();
    auto counts = CountEquippedSetPieces(player);
    std::unordered_set<uint32> desiredSpells;

    for (GauntletSetBonus const& bonus : GauntletSetBonuses)
    {
        auto itr = counts.find(bonus.SetKey);
        uint32 count = itr == counts.end() ? 0 : itr->second;
        if (count >= bonus.PiecesRequired)
            desiredSpells.insert(bonus.SpellId);
    }

    auto& appliedSpells = AppliedSetSpells[guid];

    for (auto itr = appliedSpells.begin(); itr != appliedSpells.end();)
    {
        if (desiredSpells.find(*itr) != desiredSpells.end())
        {
            ++itr;
            continue;
        }

        player->RemoveAurasDueToSpell(*itr);
        itr = appliedSpells.erase(itr);
    }

    for (uint32 spellId : desiredSpells)
    {
        if (appliedSpells.find(spellId) != appliedSpells.end())
            continue;

        player->CastSpell(player, spellId, true);
        appliedSpells.insert(spellId);
    }

    if (appliedSpells.empty())
        AppliedSetSpells.erase(guid);
}

void ClearGauntletSetBonuses(Player* player)
{
    if (!player)
        return;

    uint32 guid = player->GetGUID().GetCounter();
    auto itr = AppliedSetSpells.find(guid);
    if (itr == AppliedSetSpells.end())
        return;

    for (uint32 spellId : itr->second)
        player->RemoveAurasDueToSpell(spellId);

    AppliedSetSpells.erase(itr);
}
}

class AdventurerGauntletSetBonusPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletSetBonusPlayerScript()
        : PlayerScript("AdventurerGauntletSetBonusPlayerScript") { }

    void OnPlayerLogin(Player* player) override
    {
        RefreshGauntletSetBonuses(player);
    }

    void OnPlayerEquip(Player* player, Item* /*item*/, uint8 /*bag*/, uint8 /*slot*/, bool /*update*/) override
    {
        RefreshGauntletSetBonuses(player);
    }

    void OnPlayerUnequip(Player* player, Item* /*item*/) override
    {
        RefreshGauntletSetBonuses(player);
    }

    void OnPlayerResurrect(Player* player, float /*restorePercent*/, bool& /*applySickness*/) override
    {
        RefreshGauntletSetBonuses(player);
    }

    void OnPlayerBeforeLogout(Player* player) override
    {
        // Do not persist server-side set auras. They are reconstructed from equipped
        // pieces on the next login, just like a native item-set bonus.
        ClearGauntletSetBonuses(player);
    }
};

void AddAdventurerGauntletSetsScripts()
{
    new AdventurerGauntletSetBonusPlayerScript();
}
