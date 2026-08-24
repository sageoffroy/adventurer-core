#include "DBCStores.h"
#include "Item.h"
#include "Language.h"
#include "Opcodes.h"
#include "Player.h"
#include "ScriptDefines/PlayerScript.h"
#include "SharedDefines.h"
#include "WorldPacket.h"

#include <algorithm>
#include <cmath>
#include <string>
#include <unordered_map>

namespace
{
constexpr uint32 SKILL_RIDING = 762;
constexpr uint32 SPELL_APPRENTICE_RIDING = 33388;
constexpr uint32 SPELL_BROWN_HORSE = 458;
constexpr uint32 SPELL_DUAL_WIELD = 674;
constexpr uint32 APPRENTICE_RIDING_VALUE = 75;

// Rage is stored at ten times the value shown by the 3.3.5a client. Energy is
// stored 1:1. Mana remains the Adventurer's native primary pool.
constexpr uint32 ADVENTURER_MAX_RAGE = 1000;
constexpr uint32 ADVENTURER_MAX_ENERGY = 100;

// Guardian Consistency owns these stable custom rank spell IDs. The talent is
// intentionally kept at Guardian definition index 6 so this range never moves.
constexpr uint32 CONSISTENCY_RANK_1 = 290060;
constexpr uint8 CONSISTENCY_RANKS = 5;
constexpr uint32 CONSISTENCY_ARMOR_SYNC_INTERVAL_MS = 500;

// The 3.3.5a client refuses to expose combo points through GetComboPoints for a
// non-Rogue/non-Druid class even though AzerothCore's Unit combo-point backend
// is class agnostic. Keep Blizzard's target ComboFrame, but mirror the visible
// server count over the addon-message channel so FrameXML can feed that native
// frame for class 10.
constexpr uint32 ADVENTURER_COMBO_SYNC_INTERVAL_MS = 100;
constexpr char ADVENTURER_COMBO_PREFIX[] = "AdventurerCP";

struct ComboSyncState
{
    uint32 elapsed = 0;
    ObjectGuid selectedTarget = ObjectGuid::Empty;
    uint8 points = 0xFF; // impossible sentinel: force the first sync
};

struct ConsistencyArmorState
{
    uint32 elapsed = 0;
    float appliedBonus = 0.0f;
};

std::unordered_map<uint64, ComboSyncState> comboSyncStates;
std::unordered_map<uint64, ConsistencyArmorState> consistencyArmorStates;

constexpr uint32 UNIVERSAL_SKILLS[] =
{
    43, 44, 45, 46, 54, 55, 95, 136, 160, 162, 172, 173, 176,
    226, 228, 229, 293, 413, 414, 415, 433, 473
};

constexpr uint32 UNIVERSAL_SPELLS[] =
{
    81,    // Dodge (Passive)
    107,   // Block
    3127,  // Parry (Passive)
    SPELL_DUAL_WIELD,

    9078, 9077, 8737, 750, // Cloth, Leather, Mail, Plate

    196, 197, 198, 199, 201, 202, 227, 1180, 200, 15590,
    264, 5011, 266, 2567, 5009,

    75,    // Auto Shot
    5019,  // Shoot
    2764,  // Throw
    SPELL_APPRENTICE_RIDING,
    SPELL_BROWN_HORSE
};

constexpr uint32 HUMAN_SPELLS[] = { 59752, 20598, 20599, 20597, 20864 };
constexpr uint32 ORC_SPELLS[] = { 20572, 20573, 20575, 20574 };
constexpr uint32 DWARF_SPELLS[] = { 20594, 20596, 20595, 2481, 59224 };
constexpr uint32 NIGHT_ELF_SPELLS[] = { 58984, 20582, 20585, 20583 };
constexpr uint32 UNDEAD_SPELLS[] = { 7744, 20577, 5227, 20579 };
constexpr uint32 TAUREN_SPELLS[] = { 20549, 20550, 20552, 20551 };
constexpr uint32 GNOME_SPELLS[] = { 20589, 20591, 20593, 20592 };
constexpr uint32 TROLL_SPELLS[] = { 26297, 20555, 20557, 20558, 26290, 58943 };
constexpr uint32 BLOOD_ELF_SPELLS[] = { 28730, 28877, 822 };
constexpr uint32 DRAENEI_SPELLS[] = { 59547, 28878, 28875 };

bool IsAdventurer(Player const* player)
{
    return player && player->getClass() == CLASS_ADVENTURER;
}

uint8 GetConsistencyRank(Player const* player)
{
    if (!IsAdventurer(player))
        return 0;

    for (uint8 rank = CONSISTENCY_RANKS; rank > 0; --rank)
        if (player->HasAura(CONSISTENCY_RANK_1 + rank - 1))
            return rank;

    return 0;
}

uint32 GetEffectiveItemArmor(Player* player, ItemTemplate const* proto)
{
    if (!player || !proto)
        return 0;

    uint32 level = player->GetLevel();
    ScalingStatDistributionEntry const* distribution = proto->ScalingStatDistribution
        ? sScalingStatDistributionStore.LookupEntry(proto->ScalingStatDistribution)
        : nullptr;

    if (distribution && level > distribution->MaxLevel)
        level = distribution->MaxLevel;

    ScalingStatValuesEntry const* scaling = proto->ScalingStatValue
        ? sScalingStatValuesStore.LookupEntry(level)
        : nullptr;

    uint32 armor = proto->Armor;
    if (scaling)
    {
        if (uint32 scaledArmor = scaling->getArmorMod(proto->ScalingStatValue))
            if (proto->ScalingStatValue > 0 || scaledArmor < proto->Armor)
                armor = scaledArmor;
    }
    else if (armor && proto->ArmorDamageModifier)
        armor -= uint32(proto->ArmorDamageModifier);

    return armor;
}

float CalculateConsistencyArmorBonus(Player* player)
{
    uint8 rank = GetConsistencyRank(player);
    if (!rank)
        return 0.0f;

    float bonus = 0.0f;
    for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
    {
        Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot);
        if (!item || item->IsBroken())
            continue;

        ItemTemplate const* proto = item->GetTemplate();
        if (!proto || proto->Class != ITEM_CLASS_ARMOR)
            continue;

        uint32 percentPerRank = 0;
        switch (proto->SubClass)
        {
            case ITEM_SUBCLASS_ARMOR_CLOTH:
            case ITEM_SUBCLASS_ARMOR_LEATHER:
                percentPerRank = 4;
                break;
            case ITEM_SUBCLASS_ARMOR_MAIL:
                percentPerRank = 3;
                break;
            case ITEM_SUBCLASS_ARMOR_PLATE:
                percentPerRank = 2;
                break;
            default:
                // Shields and miscellaneous/relic subclasses deliberately do
                // not benefit. Shield progression has its own Guardian tools.
                continue;
        }

        uint32 armor = GetEffectiveItemArmor(player, proto);
        bonus += float(armor) * float(percentPerRank * rank) / 100.0f;
    }

    return bonus;
}

void RefreshConsistencyArmor(Player* player, uint32 diff = 0, bool force = false)
{
    if (!IsAdventurer(player) || !player->IsInWorld())
        return;

    uint64 key = player->GetGUID().GetRawValue();
    ConsistencyArmorState& state = consistencyArmorStates[key];
    state.elapsed += diff;
    if (!force && state.elapsed < CONSISTENCY_ARMOR_SYNC_INTERVAL_MS)
        return;
    state.elapsed = 0;

    float desiredBonus = CalculateConsistencyArmorBonus(player);
    if (std::fabs(desiredBonus - state.appliedBonus) < 0.01f)
        return;

    if (state.appliedBonus > 0.0f)
        player->HandleStatFlatModifier(UNIT_MOD_ARMOR, BASE_VALUE, state.appliedBonus, false);
    if (desiredBonus > 0.0f)
        player->HandleStatFlatModifier(UNIT_MOD_ARMOR, BASE_VALUE, desiredBonus, true);

    state.appliedBonus = desiredBonus;
}

void SendVisibleComboPoints(Player* player, uint8 points)
{
    std::string message = std::string(ADVENTURER_COMBO_PREFIX) + "\t" + std::to_string(points);

    WorldPacket data(SMSG_MESSAGECHAT, 100);
    data << uint8(0); // CHAT_MSG_ADDON
    data << int32(LANG_ADDON);
    data << player->GetGUID();
    data << uint32(0);
    data << player->GetGUID();
    data << uint32(message.length() + 1);
    data << message;
    data << uint8(0);
    player->SendDirectMessage(&data);
}

void UpdateComboPointSync(Player* player, uint32 diff)
{
    if (!IsAdventurer(player) || !player->IsInWorld())
        return;

    uint64 key = player->GetGUID().GetRawValue();
    ComboSyncState& state = comboSyncStates[key];
    state.elapsed += diff;
    if (state.elapsed < ADVENTURER_COMBO_SYNC_INTERVAL_MS)
        return;
    state.elapsed = 0;

    ObjectGuid selectedTarget = player->GetTarget();
    uint8 visiblePoints = selectedTarget ? player->GetComboPoints(selectedTarget) : 0;
    if (state.selectedTarget == selectedTarget && state.points == visiblePoints)
        return;

    state.selectedTarget = selectedTarget;
    state.points = visiblePoints;
    SendVisibleComboPoints(player, visiblePoints);
}

void LearnMissingSpells(Player* player, uint32 const* spells, uint32 count)
{
    for (uint32 i = 0; i < count; ++i)
        if (!player->HasSpell(spells[i]))
            player->learnSpell(spells[i]);
}

template <uint32 N>
void LearnMissingSpells(Player* player, uint32 const (&spells)[N])
{
    LearnMissingSpells(player, spells, N);
}

void LearnRacialBaseline(Player* player)
{
    switch (player->getRace())
    {
        case RACE_HUMAN: LearnMissingSpells(player, HUMAN_SPELLS); break;
        case RACE_ORC: LearnMissingSpells(player, ORC_SPELLS); break;
        case RACE_DWARF: LearnMissingSpells(player, DWARF_SPELLS); break;
        case RACE_NIGHTELF: LearnMissingSpells(player, NIGHT_ELF_SPELLS); break;
        case RACE_UNDEAD_PLAYER: LearnMissingSpells(player, UNDEAD_SPELLS); break;
        case RACE_TAUREN: LearnMissingSpells(player, TAUREN_SPELLS); break;
        case RACE_GNOME: LearnMissingSpells(player, GNOME_SPELLS); break;
        case RACE_TROLL: LearnMissingSpells(player, TROLL_SPELLS); break;
        case RACE_BLOODELF: LearnMissingSpells(player, BLOOD_ELF_SPELLS); break;
        case RACE_DRAENEI: LearnMissingSpells(player, DRAENEI_SPELLS); break;
        default: break;
    }
}

void SetLanguageSkill(Player* player, uint32 skillId)
{
    player->SetSkill(skillId, 1, 300, 300);
}

void SetRacialLanguages(Player* player)
{
    switch (player->getRace())
    {
        case RACE_HUMAN:
            SetLanguageSkill(player, 98);
            break;
        case RACE_DWARF:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 111);
            break;
        case RACE_NIGHTELF:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 113);
            break;
        case RACE_GNOME:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 313);
            break;
        case RACE_DRAENEI:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 759);
            break;
        case RACE_ORC:
            SetLanguageSkill(player, 109);
            break;
        case RACE_UNDEAD_PLAYER:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 673);
            break;
        case RACE_TAUREN:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 115);
            break;
        case RACE_TROLL:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 315);
            break;
        case RACE_BLOODELF:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 137);
            break;
        default:
            break;
    }
}

void ApplyUniversalResources(Player* player, bool initializeCurrent = false)
{
    if (!IsAdventurer(player))
        return;

    // Mana remains native. Rage and Energy are the only auxiliary resource
    // pools owned by Adventurer Core.
    if (player->GetMaxPower(POWER_RAGE) < ADVENTURER_MAX_RAGE)
        player->SetMaxPower(POWER_RAGE, ADVENTURER_MAX_RAGE);
    if (player->GetMaxPower(POWER_ENERGY) < ADVENTURER_MAX_ENERGY)
        player->SetMaxPower(POWER_ENERGY, ADVENTURER_MAX_ENERGY);

    if (initializeCurrent)
    {
        player->SetPower(POWER_RAGE, 0);
        player->SetPower(POWER_ENERGY, ADVENTURER_MAX_ENERGY);
    }
}

void ApplyRuntimeCapabilities(Player* player)
{
    uint32 allWeapons = (1u << MAX_ITEM_SUBCLASS_WEAPON) - 1u;
    uint32 allArmor = (1u << MAX_ITEM_SUBCLASS_ARMOR) - 1u;

    player->AddWeaponProficiency(allWeapons);
    player->AddArmorProficiency(allArmor);
    player->SetCanParry(true);
    player->SetCanBlock(true);
    player->UpdateDefenseBonusesMod();
    ApplyUniversalResources(player);
}

void FinalizeNewAdventurer(Player* player)
{
    if (!IsAdventurer(player))
        return;

    uint32 maxSkillValue = std::min<uint32>(player->GetLevel() * 5u, 400u);
    for (uint32 skillId : UNIVERSAL_SKILLS)
        player->SetSkill(skillId, 0, maxSkillValue, maxSkillValue);

    LearnMissingSpells(player, UNIVERSAL_SPELLS);
    player->SetSkill(SKILL_RIDING, 1, APPRENTICE_RIDING_VALUE, APPRENTICE_RIDING_VALUE);
    LearnRacialBaseline(player);
    SetRacialLanguages(player);
    ApplyRuntimeCapabilities(player);
    ApplyUniversalResources(player, true);

    // PLAYERHOOK_ON_CREATE runs after AzerothCore's original creation
    // transaction. Persist the completed class baseline before the temporary
    // Player object is destroyed.
    player->SaveToDB(false, false);
}
}

class AdventurerCorePlayerScript : public PlayerScript
{
public:
    AdventurerCorePlayerScript() : PlayerScript("AdventurerCorePlayerScript",
    {
        PLAYERHOOK_ON_CREATE,
        PLAYERHOOK_ON_LOGIN,
        PLAYERHOOK_ON_LOGOUT,
        PLAYERHOOK_ON_LEVEL_CHANGED,
        PLAYERHOOK_ON_UPDATE,
        PLAYERHOOK_ON_AFTER_UPDATE_MAX_POWER,
        PLAYERHOOK_ON_PLAYER_HAS_ACTIVE_POWER_TYPE
    }) { }

    void OnPlayerCreate(Player* player) override
    {
        FinalizeNewAdventurer(player);
    }

    void OnPlayerLogin(Player* player) override
    {
        if (IsAdventurer(player))
        {
            ApplyRuntimeCapabilities(player);
            comboSyncStates.erase(player->GetGUID().GetRawValue());
            consistencyArmorStates.erase(player->GetGUID().GetRawValue());
            RefreshConsistencyArmor(player, 0, true);
        }
    }

    void OnPlayerLogout(Player* player) override
    {
        comboSyncStates.erase(player->GetGUID().GetRawValue());
        consistencyArmorStates.erase(player->GetGUID().GetRawValue());
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        UpdateComboPointSync(player, diff);
        RefreshConsistencyArmor(player, diff);
    }

    void OnPlayerLevelChanged(Player* player, uint8 /*oldLevel*/) override
    {
        if (IsAdventurer(player))
        {
            ApplyRuntimeCapabilities(player);
            RefreshConsistencyArmor(player, 0, true);
        }
    }

    void OnPlayerAfterUpdateMaxPower(Player* player, Powers& power, float& value) override
    {
        if (!IsAdventurer(player))
            return;

        // Preserve native-sized floors for the two auxiliary pools while still
        // allowing talents/auras to increase them above the baseline.
        switch (power)
        {
            case POWER_RAGE:
                value = std::max(value, static_cast<float>(ADVENTURER_MAX_RAGE));
                break;
            case POWER_ENERGY:
                value = std::max(value, static_cast<float>(ADVENTURER_MAX_ENERGY));
                break;
            default:
                break;
        }
    }

    bool OnPlayerHasActivePowerType(Player const* player, Powers power) override
    {
        if (!IsAdventurer(player))
            return false;
        if (player->getPowerType() == power)
            return false; // Native Mana continues through AzerothCore's stock path.

        switch (power)
        {
            case POWER_RAGE:
            case POWER_ENERGY:
                return player->GetMaxPower(power) > 0;
            default:
                return false;
        }
    }
};

void AddAdventurerCoreScripts()
{
    new AdventurerCorePlayerScript();
}
