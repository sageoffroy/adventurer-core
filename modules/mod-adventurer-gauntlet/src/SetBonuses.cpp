#include "Item.h"
#include "Player.h"
#include "ScriptMgr.h"

#include <array>
#include <string_view>
#include <unordered_map>
#include <unordered_set>

namespace
{
enum GauntletSetBonusType
{
    GAUNTLET_SET_BONUS_ARMOR,
    GAUNTLET_SET_BONUS_DEFENSE_SKILL,
    GAUNTLET_SET_BONUS_EXPERTISE_RATING,
    GAUNTLET_SET_BONUS_SPELL,
};

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
    GauntletSetBonusType Type;
    int32 Value;
    uint32 SpellId;
    char const* Description;
};

#include "GeneratedGauntletSets.inc"

std::unordered_map<uint32, std::unordered_set<uint32>> AppliedSetBonuses;

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

void ApplyGauntletSetBonus(Player* player, GauntletSetBonus const& bonus, bool apply)
{
    if (!player)
        return;

    switch (bonus.Type)
    {
        case GAUNTLET_SET_BONUS_ARMOR:
            player->ApplyStatFlatModifier(
                UNIT_MOD_ARMOR,
                TOTAL_VALUE,
                apply ? float(bonus.Value) : -float(bonus.Value));
            player->UpdateArmor();
            break;
        case GAUNTLET_SET_BONUS_DEFENSE_SKILL:
            player->ModifySkillBonus(SKILL_DEFENSE, apply ? bonus.Value : -bonus.Value, false);
            player->UpdateDefenseBonusesMod();
            break;
        case GAUNTLET_SET_BONUS_EXPERTISE_RATING:
            player->ApplyRatingMod(CR_EXPERTISE, bonus.Value, apply);
            break;
        case GAUNTLET_SET_BONUS_SPELL:
            if (apply)
                player->CastSpell(player, bonus.SpellId, true);
            else
                player->RemoveAurasDueToSpell(bonus.SpellId);
            break;
    }
}

void RefreshGauntletSetBonuses(Player* player)
{
    if (!player)
        return;

    uint32 guid = player->GetGUID().GetCounter();
    auto counts = CountEquippedSetPieces(player);
    std::unordered_set<uint32> desiredBonuses;

    for (uint32 index = 0; index < GauntletSetBonuses.size(); ++index)
    {
        GauntletSetBonus const& bonus = GauntletSetBonuses[index];
        auto itr = counts.find(bonus.SetKey);
        uint32 count = itr == counts.end() ? 0 : itr->second;
        if (count >= bonus.PiecesRequired)
            desiredBonuses.insert(index);
    }

    auto& appliedBonuses = AppliedSetBonuses[guid];

    for (auto itr = appliedBonuses.begin(); itr != appliedBonuses.end();)
    {
        if (desiredBonuses.find(*itr) != desiredBonuses.end())
        {
            ++itr;
            continue;
        }

        ApplyGauntletSetBonus(player, GauntletSetBonuses[*itr], false);
        itr = appliedBonuses.erase(itr);
    }

    for (uint32 index : desiredBonuses)
    {
        if (appliedBonuses.find(index) != appliedBonuses.end())
            continue;

        ApplyGauntletSetBonus(player, GauntletSetBonuses[index], true);
        appliedBonuses.insert(index);
    }

    if (appliedBonuses.empty())
        AppliedSetBonuses.erase(guid);
}

void ClearGauntletSetBonuses(Player* player)
{
    if (!player)
        return;

    uint32 guid = player->GetGUID().GetCounter();
    auto itr = AppliedSetBonuses.find(guid);
    if (itr == AppliedSetBonuses.end())
        return;

    for (uint32 index : itr->second)
        ApplyGauntletSetBonus(player, GauntletSetBonuses[index], false);

    AppliedSetBonuses.erase(itr);
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
        // Server-side set modifiers are reconstructed from the equipped pieces
        // on login and therefore must not persist independently of the items.
        ClearGauntletSetBonuses(player);
    }
};

void AddAdventurerGauntletSetsScripts()
{
    new AdventurerGauntletSetBonusPlayerScript();
}
