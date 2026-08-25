#include "DatabaseEnv.h"
#include "Language.h"
#include "Opcodes.h"
#include "Player.h"
#include "Random.h"
#include "ScriptDefines/PlayerScript.h"
#include "SharedDefines.h"
#include "SpellInfo.h"
#include "SpellMgr.h"
#include "WorldPacket.h"

#include <algorithm>
#include <array>
#include <map>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

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

// The 3.3.5a client refuses to expose combo points through GetComboPoints for a
// non-Rogue/non-Druid class even though AzerothCore's Unit combo-point backend
// is class agnostic. Keep Blizzard's target ComboFrame, but mirror the visible
// server count over the addon-message channel so FrameXML can feed that native
// frame for class 10.
constexpr uint32 ADVENTURER_COMBO_SYNC_INTERVAL_MS = 100;
constexpr char ADVENTURER_COMBO_PREFIX[] = "AdventurerCP";

// ---------------------------------------------------------------------------
// SpellDraft v1 protocol/state
// ---------------------------------------------------------------------------
//
// Cards, rather than individual spells, are the unit of the draft. A card may
// teach one or several spells, may have progressive passive ranks, and may be
// gated by other cards. Rarity and weight are deliberately separate: rarity is
// the broad quality bucket while weight changes the relative chance inside the
// eligible pool. Example: Charge is Common but receives weight 500 (x5 the
// standard 100) once Battle Stance makes it eligible.
constexpr char ADVENTURER_DRAFT_PREFIX[] = "AdventurerDraft";
constexpr char ADVENTURER_DRAFT_SETTINGS_SOURCE[] = "adventurer_draft_v1";
constexpr uint32 ADVENTURER_DRAFT_SCHEMA = 1;
constexpr uint32 ADVENTURER_DRAFT_STANDARD_WEIGHT = 100;

constexpr char DRAFT_READY_MESSAGE[] = "ADRAFT_READY";
constexpr char DRAFT_PICK_PREFIX[] = "ADRAFT_PICK:";

enum class DraftCardType : uint8
{
    None = 0,
    Active = 1,
    Talent = 2,
};

enum class DraftRarity : uint8
{
    Common = 0,
    Uncommon = 1,
    Rare = 2,
    Epic = 3,
    Legendary = 4,
};

struct DraftRequirement
{
    uint32 cardId;
    uint8 minimumRank;
};

struct DraftCard
{
    uint32 id;
    DraftCardType type;
    DraftRarity rarity;
    uint32 weight;

    // Each vector entry is one selectable rank. Active cards normally contain
    // one rank; passive cards may contain several. A rank may grant more than
    // one spell, which is how low-value/required abilities can be bundled into
    // one useful card without costing extra draft picks.
    std::vector<std::vector<uint32>> rankGrants;

    std::vector<DraftRequirement> requirements;
    std::vector<uint32> unlocks; // design/debug graph; eligibility uses requirements
    bool replacesPreviousRank;
};

struct DraftState
{
    uint8 processedLevel = 0;
    uint16 pendingActive = 0;
    uint16 pendingTalent = 0;
    DraftCardType offerType = DraftCardType::None;
    std::array<uint32, 3> offeredCards = { 0, 0, 0 };
    std::map<uint32, uint8> ownedRanks;
};

struct ComboSyncState
{
    uint32 elapsed = 0;
    ObjectGuid selectedTarget = ObjectGuid::Empty;
    uint8 points = 0xFF; // impossible sentinel: force the first sync
};

std::unordered_map<uint64, ComboSyncState> comboSyncStates;
std::unordered_map<uint64, DraftState> draftStates;

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

void SendAddonPayload(Player* player, std::string const& prefix, std::string const& payload)
{
    if (!player || !player->IsInWorld())
        return;

    std::string message = prefix + "\t" + payload;

    WorldPacket data(SMSG_MESSAGECHAT, 100 + message.length());
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

void SendVisibleComboPoints(Player* player, uint8 points)
{
    SendAddonPayload(player, ADVENTURER_COMBO_PREFIX, std::to_string(points));
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

// ---------------------------------------------------------------------------
// Draft card catalog
// ---------------------------------------------------------------------------
std::vector<DraftCard> const& GetDraftCards()
{
    static std::vector<DraftCard> const cards =
    {
        // ACTIVE ROOTS -------------------------------------------------------
        // id, type, rarity, weight, rank grants, requirements, unlocks, replace
        { 1,  DraftCardType::Active, DraftRarity::Common,   100, {{2457}},      {},          {11, 106}, false }, // Battle Stance
        { 2,  DraftCardType::Active, DraftRarity::Common,   100, {{133}},       {},          {104},     false }, // Fireball
        { 3,  DraftCardType::Active, DraftRarity::Common,   100, {{116}},       {},          {105},     false }, // Frostbolt
        { 4,  DraftCardType::Active, DraftRarity::Common,   100, {{686}},       {},          {},        false }, // Shadow Bolt
        { 5,  DraftCardType::Active, DraftRarity::Common,   100, {{585}},       {},          {},        false }, // Smite
        { 6,  DraftCardType::Active, DraftRarity::Common,   100, {{403}},       {},          {},        false }, // Lightning Bolt
        { 7,  DraftCardType::Active, DraftRarity::Common,   100, {{5176}},      {},          {},        false }, // Wrath
        { 8,  DraftCardType::Active, DraftRarity::Common,   110, {{78}},        {},          {107},     false }, // Heroic Strike
        { 9,  DraftCardType::Active, DraftRarity::Common,   100, {{774}},       {},          {},        false }, // Rejuvenation
        { 10, DraftCardType::Active, DraftRarity::Uncommon, 120, {{1784, 921}}, {},          {},        false }, // Stealth + Pick Pocket bundle
        { 11, DraftCardType::Active, DraftRarity::Common,   500, {{100}},       {{1, 1}},    {},        false }, // Charge: x5 weight after Battle Stance
        { 12, DraftCardType::Active, DraftRarity::Common,    90, {{1459}},      {},          {},        false }, // Arcane Intellect
        { 13, DraftCardType::Active, DraftRarity::Common,   100, {{331}},       {},          {},        false }, // Healing Wave
        { 14, DraftCardType::Active, DraftRarity::Common,   100, {{1752}},      {},          {},        false }, // Sinister Strike

        // PASSIVE / TALENT CARDS -------------------------------------------
        // Passive ranks are separate draft investments. Higher ranks replace
        // the previous rank spell so their auras never stack accidentally.
        { 101, DraftCardType::Talent, DraftRarity::Common,   120,
            {{12320}, {12852}, {12853}, {12855}, {12856}}, {}, {}, true }, // Cruelty 1/5 -> 5/5
        { 102, DraftCardType::Talent, DraftRarity::Common,   100,
            {{16462}, {16463}, {16464}, {16465}, {16466}}, {}, {}, true }, // Deflection 1/5 -> 5/5
        { 103, DraftCardType::Talent, DraftRarity::Common,    90,
            {{12297}, {12750}, {12751}, {12752}, {12753}}, {}, {}, true }, // Anticipation 1/5 -> 5/5
        { 104, DraftCardType::Talent, DraftRarity::Uncommon, 180,
            {{11069}, {12338}, {12339}, {12340}, {12341}}, {{2, 1}}, {}, true }, // Improved Fireball
        { 105, DraftCardType::Talent, DraftRarity::Uncommon, 180,
            {{11070}, {12473}, {16763}, {16765}, {16766}}, {{3, 1}}, {}, true }, // Improved Frostbolt
        { 106, DraftCardType::Talent, DraftRarity::Uncommon, 250,
            {{12295}, {12676}, {12677}}, {{1, 1}}, {}, true }, // Tactical Mastery after Battle Stance
        { 107, DraftCardType::Talent, DraftRarity::Uncommon, 180,
            {{12282}, {12663}, {12664}}, {{8, 1}}, {}, true }, // Improved Heroic Strike
    };
    return cards;
}

DraftCard const* FindDraftCard(uint32 cardId)
{
    for (DraftCard const& card : GetDraftCards())
        if (card.id == cardId)
            return &card;
    return nullptr;
}

uint8 GetOwnedRank(DraftState const& state, uint32 cardId)
{
    auto itr = state.ownedRanks.find(cardId);
    return itr == state.ownedRanks.end() ? 0 : itr->second;
}

bool MeetsRequirements(DraftState const& state, DraftCard const& card)
{
    for (DraftRequirement const& requirement : card.requirements)
        if (GetOwnedRank(state, requirement.cardId) < requirement.minimumRank)
            return false;
    return true;
}

bool IsCardEligible(DraftState const& state, DraftCard const& card, DraftCardType type)
{
    if (card.type != type || card.rankGrants.empty())
        return false;

    uint8 currentRank = GetOwnedRank(state, card.id);
    if (currentRank >= card.rankGrants.size())
        return false;

    return MeetsRequirements(state, card);
}

uint32 RarityWeightMultiplier(DraftRarity rarity)
{
    switch (rarity)
    {
        case DraftRarity::Common:    return 100;
        case DraftRarity::Uncommon:  return 55;
        case DraftRarity::Rare:      return 25;
        case DraftRarity::Epic:      return 10;
        case DraftRarity::Legendary: return 3;
        default:                     return 1;
    }
}

uint32 EffectiveCardWeight(DraftCard const& card)
{
    uint64 weighted = uint64(card.weight) * RarityWeightMultiplier(card.rarity);
    return std::max<uint32>(1, static_cast<uint32>(weighted / ADVENTURER_DRAFT_STANDARD_WEIGHT));
}

std::vector<uint32> SelectWeightedCards(DraftState const& state, DraftCardType type, uint32 count)
{
    std::vector<DraftCard const*> candidates;
    for (DraftCard const& card : GetDraftCards())
        if (IsCardEligible(state, card, type))
            candidates.push_back(&card);

    std::vector<uint32> selected;
    while (!candidates.empty() && selected.size() < count)
    {
        uint32 totalWeight = 0;
        for (DraftCard const* card : candidates)
            totalWeight += EffectiveCardWeight(*card);

        if (!totalWeight)
            break;

        uint32 roll = urand(1, totalWeight);
        uint32 cursor = 0;
        size_t chosenIndex = 0;
        for (size_t i = 0; i < candidates.size(); ++i)
        {
            cursor += EffectiveCardWeight(*candidates[i]);
            if (roll <= cursor)
            {
                chosenIndex = i;
                break;
            }
        }

        selected.push_back(candidates[chosenIndex]->id);
        candidates.erase(candidates.begin() + chosenIndex);
    }

    return selected;
}

// ---------------------------------------------------------------------------
// Draft state persistence: use AzerothCore's existing character_settings table
// instead of adding a prestige table or another schema dependency.
// Format:
// schema,processedLevel,pendingActive,pendingTalent,offerType,o1,o2,o3,card:rank...
// ---------------------------------------------------------------------------
std::string SerializeDraftState(DraftState const& state)
{
    std::ostringstream out;
    out << ADVENTURER_DRAFT_SCHEMA
        << ',' << uint32(state.processedLevel)
        << ',' << state.pendingActive
        << ',' << state.pendingTalent
        << ',' << uint32(state.offerType)
        << ',' << state.offeredCards[0]
        << ',' << state.offeredCards[1]
        << ',' << state.offeredCards[2];

    for (auto const& [cardId, rank] : state.ownedRanks)
        out << ',' << cardId << ':' << uint32(rank);

    return out.str();
}

bool DeserializeDraftState(std::string const& data, DraftState& state)
{
    std::vector<std::string> tokens;
    std::stringstream input(data);
    std::string token;
    while (std::getline(input, token, ','))
        tokens.push_back(token);

    if (tokens.size() < 8)
        return false;

    try
    {
        if (std::stoul(tokens[0]) != ADVENTURER_DRAFT_SCHEMA)
            return false;

        state = DraftState{};
        state.processedLevel = static_cast<uint8>(std::stoul(tokens[1]));
        state.pendingActive = static_cast<uint16>(std::stoul(tokens[2]));
        state.pendingTalent = static_cast<uint16>(std::stoul(tokens[3]));
        state.offerType = static_cast<DraftCardType>(std::stoul(tokens[4]));
        state.offeredCards[0] = static_cast<uint32>(std::stoul(tokens[5]));
        state.offeredCards[1] = static_cast<uint32>(std::stoul(tokens[6]));
        state.offeredCards[2] = static_cast<uint32>(std::stoul(tokens[7]));

        for (size_t i = 8; i < tokens.size(); ++i)
        {
            size_t separator = tokens[i].find(':');
            if (separator == std::string::npos)
                continue;

            uint32 cardId = static_cast<uint32>(std::stoul(tokens[i].substr(0, separator)));
            uint8 rank = static_cast<uint8>(std::stoul(tokens[i].substr(separator + 1)));
            if (cardId && rank)
                state.ownedRanks[cardId] = rank;
        }
    }
    catch (...)
    {
        return false;
    }

    return true;
}

DraftState BuildFreshDraftState(uint8 currentLevel)
{
    DraftState state;
    state.processedLevel = currentLevel;
    state.pendingActive = 3; // Level 1: three sequential active picks.

    for (uint32 level = 5; level <= currentLevel; level += 5)
        ++state.pendingActive;
    if (currentLevel >= 10)
        state.pendingTalent = currentLevel - 9;

    return state;
}

bool LoadPersistedDraftState(Player* player, DraftState& state)
{
    uint32 guid = player->GetGUID().GetCounter();
    QueryResult result = CharacterDatabase.Query(
        "SELECT data FROM character_settings WHERE guid = {} AND source = 'adventurer_draft_v1'",
        guid);
    if (!result)
        return false;

    return DeserializeDraftState((*result)[0].Get<std::string>(), state);
}

void PersistDraftState(Player* player, DraftState const& state)
{
    uint32 guid = player->GetGUID().GetCounter();
    std::string data = SerializeDraftState(state);
    CharacterDatabase.Execute(
        "REPLACE INTO character_settings (guid, source, data) VALUES ({}, 'adventurer_draft_v1', '{}')",
        guid, data);
}

DraftState& GetDraftState(Player* player)
{
    uint64 key = player->GetGUID().GetRawValue();
    auto itr = draftStates.find(key);
    if (itr != draftStates.end())
        return itr->second;

    DraftState state;
    if (!LoadPersistedDraftState(player, state))
    {
        state = BuildFreshDraftState(player->GetLevel());
        PersistDraftState(player, state);
    }

    return draftStates.emplace(key, state).first->second;
}

void QueueDraftProgressionToLevel(DraftState& state, uint8 currentLevel)
{
    if (state.processedLevel >= currentLevel)
        return;

    for (uint32 level = uint32(state.processedLevel) + 1; level <= currentLevel; ++level)
    {
        if ((level % 5) == 0)
            ++state.pendingActive;
        if (level >= 10)
            ++state.pendingTalent;
    }

    state.processedLevel = currentLevel;
}

DraftCardType NextPendingDraftType(DraftState const& state)
{
    // At 10/15/20/etc. active always resolves first, so it can unlock a passive
    // that is immediately eligible for the same level's talent draft.
    if (state.pendingActive > 0)
        return DraftCardType::Active;
    if (state.pendingTalent > 0)
        return DraftCardType::Talent;
    return DraftCardType::None;
}

void ClearDraftOffer(DraftState& state)
{
    state.offerType = DraftCardType::None;
    state.offeredCards = { 0, 0, 0 };
}

bool ExistingOfferIsValid(DraftState const& state, DraftCardType expectedType)
{
    if (state.offerType != expectedType || state.offeredCards[0] == 0)
        return false;

    for (uint32 cardId : state.offeredCards)
    {
        if (!cardId)
            continue;
        DraftCard const* card = FindDraftCard(cardId);
        if (!card || !IsCardEligible(state, *card, expectedType))
            return false;
    }
    return true;
}

void GenerateDraftOffer(DraftState& state, DraftCardType type)
{
    ClearDraftOffer(state);
    std::vector<uint32> selected = SelectWeightedCards(state, type, 3);
    if (selected.empty())
        return;

    state.offerType = type;
    for (size_t i = 0; i < selected.size() && i < state.offeredCards.size(); ++i)
        state.offeredCards[i] = selected[i];
}

void SendDraftClosed(Player* player)
{
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, "C");
}

void SendDraftError(Player* player, char const* code)
{
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, std::string("E|") + code);
}

void SendDraftOffer(Player* player, DraftState const& state)
{
    if (state.offerType == DraftCardType::None || !state.offeredCards[0])
    {
        SendDraftClosed(player);
        return;
    }

    std::ostringstream payload;
    payload << "O|" << (state.offerType == DraftCardType::Active ? 'A' : 'T')
            << '|' << state.pendingActive
            << '|' << state.pendingTalent
            << '|';

    bool first = true;
    for (uint32 cardId : state.offeredCards)
    {
        if (!cardId)
            continue;

        DraftCard const* card = FindDraftCard(cardId);
        if (!card)
            continue;

        uint8 currentRank = GetOwnedRank(state, card->id);
        uint8 nextRank = currentRank + 1;
        if (nextRank == 0 || nextRank > card->rankGrants.size())
            continue;

        std::vector<uint32> const& grants = card->rankGrants[nextRank - 1];
        if (grants.empty())
            continue;

        if (!first)
            payload << ';';
        first = false;

        payload << card->id
                << ':' << grants.front()
                << ':' << uint32(card->rarity)
                << ':' << card->weight
                << ':' << grants.size()
                << ':' << uint32(nextRank)
                << ':' << card->rankGrants.size();
    }

    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, payload.str());
}

void EnsureDraftOffer(Player* player, DraftState& state)
{
    DraftCardType nextType = NextPendingDraftType(state);
    if (nextType == DraftCardType::None)
    {
        ClearDraftOffer(state);
        PersistDraftState(player, state);
        SendDraftClosed(player);
        return;
    }

    if (!ExistingOfferIsValid(state, nextType))
    {
        GenerateDraftOffer(state, nextType);
        PersistDraftState(player, state);
    }

    if (state.offerType == DraftCardType::None || !state.offeredCards[0])
    {
        SendDraftError(player, nextType == DraftCardType::Active ? "NO_ACTIVE_CARDS" : "NO_TALENT_CARDS");
        return;
    }

    SendDraftOffer(player, state);
}

bool PlayerKnowsAnyRank(Player* player, uint32 spellId)
{
    uint32 current = sSpellMgr->GetFirstSpellInChain(spellId);
    while (current)
    {
        if (player->HasSpell(current))
            return true;
        current = sSpellMgr->GetNextSpellInChain(current);
    }
    return false;
}

void UpgradeActiveSpellFamily(Player* player, uint32 rootSpellId)
{
    uint32 current = sSpellMgr->GetFirstSpellInChain(rootSpellId);
    uint32 best = 0;
    uint32 level = player->GetLevel();

    while (current)
    {
        SpellInfo const* info = sSpellMgr->GetSpellInfo(current);
        if (!info)
            break;

        uint32 requiredLevel = std::max(info->BaseLevel, info->SpellLevel);
        if (requiredLevel <= level)
            best = current;

        current = sSpellMgr->GetNextSpellInChain(current);
    }

    if (best && !player->HasSpell(best))
        player->learnSpell(best);
}

void UpgradeDraftedActiveSpells(Player* player, DraftState const& state)
{
    for (auto const& [cardId, ownedRank] : state.ownedRanks)
    {
        if (!ownedRank)
            continue;
        DraftCard const* card = FindDraftCard(cardId);
        if (!card || card->type != DraftCardType::Active || card->rankGrants.empty())
            continue;

        for (uint32 spellId : card->rankGrants.front())
            UpgradeActiveSpellFamily(player, spellId);
    }
}

void RestoreDraftedSpells(Player* player, DraftState const& state)
{
    for (auto const& [cardId, ownedRank] : state.ownedRanks)
    {
        DraftCard const* card = FindDraftCard(cardId);
        if (!card || ownedRank == 0 || ownedRank > card->rankGrants.size())
            continue;

        if (card->type == DraftCardType::Active)
        {
            for (uint32 spellId : card->rankGrants.front())
                if (!PlayerKnowsAnyRank(player, spellId))
                    player->learnSpell(spellId);
            continue;
        }

        if (card->replacesPreviousRank)
        {
            for (uint8 rank = 1; rank < ownedRank; ++rank)
                for (uint32 spellId : card->rankGrants[rank - 1])
                    if (player->HasSpell(spellId))
                        player->removeSpell(spellId);
        }

        for (uint32 spellId : card->rankGrants[ownedRank - 1])
            if (!player->HasSpell(spellId))
                player->learnSpell(spellId);
    }

    UpgradeDraftedActiveSpells(player, state);
}

bool IsCardInCurrentOffer(DraftState const& state, uint32 cardId)
{
    return std::find(state.offeredCards.begin(), state.offeredCards.end(), cardId) != state.offeredCards.end();
}

void ApplyDraftCard(Player* player, DraftState& state, DraftCard const& card)
{
    uint8 currentRank = GetOwnedRank(state, card.id);
    uint8 nextRank = currentRank + 1;
    if (nextRank == 0 || nextRank > card.rankGrants.size())
        return;

    if (card.replacesPreviousRank && currentRank > 0)
    {
        for (uint32 spellId : card.rankGrants[currentRank - 1])
            if (player->HasSpell(spellId))
                player->removeSpell(spellId);
    }

    for (uint32 spellId : card.rankGrants[nextRank - 1])
        if (!player->HasSpell(spellId))
            player->learnSpell(spellId);

    state.ownedRanks[card.id] = nextRank;

    if (card.type == DraftCardType::Active && state.pendingActive > 0)
        --state.pendingActive;
    else if (card.type == DraftCardType::Talent && state.pendingTalent > 0)
        --state.pendingTalent;

    ClearDraftOffer(state);
    UpgradeDraftedActiveSpells(player, state);
    PersistDraftState(player, state);
    player->SaveToDB(false, false);

    // Generate the next unresolved pick immediately. This is what makes the
    // level-1 three-pick sequence feel like one draft session and also ensures
    // level 10 active -> talent ordering sees newly unlocked passive cards.
    EnsureDraftOffer(player, state);
}

void HandleDraftPick(Player* player, uint32 cardId)
{
    DraftState& state = GetDraftState(player);
    DraftCard const* card = FindDraftCard(cardId);
    if (!card || !IsCardInCurrentOffer(state, cardId))
    {
        SendDraftError(player, "INVALID_PICK");
        EnsureDraftOffer(player, state);
        return;
    }

    if (card->type != state.offerType || !IsCardEligible(state, *card, state.offerType))
    {
        SendDraftError(player, "INELIGIBLE_PICK");
        ClearDraftOffer(state);
        EnsureDraftOffer(player, state);
        return;
    }

    ApplyDraftCard(player, state, *card);
}

void HandleDraftReady(Player* player)
{
    DraftState& state = GetDraftState(player);
    QueueDraftProgressionToLevel(state, player->GetLevel());
    PersistDraftState(player, state);
    EnsureDraftOffer(player, state);
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
        PLAYERHOOK_ON_PLAYER_HAS_ACTIVE_POWER_TYPE,
        PLAYERHOOK_ON_CALCULATE_TALENTS_POINTS,
        PLAYERHOOK_CAN_PLAYER_USE_PRIVATE_CHAT
    }) { }

    void OnPlayerCreate(Player* player) override
    {
        FinalizeNewAdventurer(player);
        if (!IsAdventurer(player))
            return;

        DraftState state = BuildFreshDraftState(player->GetLevel());
        draftStates[player->GetGUID().GetRawValue()] = state;
        PersistDraftState(player, state);
    }

    void OnPlayerLogin(Player* player) override
    {
        if (IsAdventurer(player))
        {
            ApplyRuntimeCapabilities(player);
            player->SetFreeTalentPoints(0);
            player->SetAcceptWhispers(true); // internal self-whisper draft protocol
            comboSyncStates.erase(player->GetGUID().GetRawValue());

            DraftState& state = GetDraftState(player);
            QueueDraftProgressionToLevel(state, player->GetLevel());
            RestoreDraftedSpells(player, state);
            PersistDraftState(player, state);
            EnsureDraftOffer(player, state);
        }
    }

    void OnPlayerLogout(Player* player) override
    {
        comboSyncStates.erase(player->GetGUID().GetRawValue());

        auto itr = draftStates.find(player->GetGUID().GetRawValue());
        if (itr != draftStates.end())
        {
            PersistDraftState(player, itr->second);
            draftStates.erase(itr);
        }
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        UpdateComboPointSync(player, diff);
    }

    void OnPlayerLevelChanged(Player* player, uint8 /*oldLevel*/) override
    {
        if (!IsAdventurer(player))
            return;

        ApplyRuntimeCapabilities(player);
        player->SetFreeTalentPoints(0);

        DraftState& state = GetDraftState(player);
        QueueDraftProgressionToLevel(state, player->GetLevel());
        UpgradeDraftedActiveSpells(player, state);
        PersistDraftState(player, state);
        EnsureDraftOffer(player, state);
    }

    void OnPlayerCalculateTalentsPoints(Player const* player, uint32& talentPointsForLevel) override
    {
        if (IsAdventurer(player))
            talentPointsForLevel = 0;
    }

    bool OnPlayerCanUseChat(Player* player, uint32 /*type*/, uint32 /*language*/, std::string& msg, Player* receiver) override
    {
        if (!IsAdventurer(player) || receiver != player)
            return true;

        if (msg == DRAFT_READY_MESSAGE)
        {
            HandleDraftReady(player);
            return false;
        }

        if (msg.rfind(DRAFT_PICK_PREFIX, 0) == 0)
        {
            try
            {
                uint32 cardId = static_cast<uint32>(std::stoul(msg.substr(sizeof(DRAFT_PICK_PREFIX) - 1)));
                HandleDraftPick(player, cardId);
            }
            catch (...)
            {
                SendDraftError(player, "BAD_PICK_FORMAT");
            }
            return false;
        }

        return true;
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
