#include "Config.h"
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
#include <cctype>
#include <fstream>
#include <iostream>
#include <map>
#include <set>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

void AddAdventurerDKScripts();

namespace
{
constexpr uint32 SKILL_RIDING = 762;
constexpr uint32 SPELL_APPRENTICE_RIDING = 33388;
constexpr uint32 SPELL_BROWN_HORSE = 458;
constexpr uint32 SPELL_DUAL_WIELD = 674;
constexpr uint32 APPRENTICE_RIDING_VALUE = 75;

constexpr uint32 ADVENTURER_MAX_RAGE = 1000;
constexpr uint32 ADVENTURER_MAX_ENERGY = 100;

constexpr uint32 ADVENTURER_COMBO_SYNC_INTERVAL_MS = 100;
constexpr char ADVENTURER_COMBO_PREFIX[] = "AdventurerCP";

// ---------------------------------------------------------------------------
// SpellDraft runtime protocol/state
// ---------------------------------------------------------------------------
constexpr char ADVENTURER_DRAFT_PREFIX[] = "AdventurerDraft";
constexpr char ADVENTURER_DRAFT_SETTINGS_SOURCE[] = "adventurer_draft_v1";
constexpr uint32 ADVENTURER_DRAFT_SCHEMA = 3;
constexpr uint32 ADVENTURER_DRAFT_STANDARD_WEIGHT = 100;
constexpr uint32 ADVENTURER_DRAFT_MAX_OFFER_SIZE = 3;

constexpr char DRAFT_READY_MESSAGE[] = "ADRAFT_READY";
constexpr char DRAFT_PICK_PREFIX[] = "ADRAFT_PICK:";
constexpr char DRAFT_REROLL_MESSAGE[] = "ADRAFT_REROLL";
constexpr char DRAFT_BLESS_PREFIX[] = "ADRAFT_BLESS:";
constexpr char DRAFT_DESTROY_PREFIX[] = "ADRAFT_DESTROY:";
constexpr char DRAFT_DEBUG_POOL_MESSAGE[] = "ADRAFT_POOL";

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
    uint32 cardId = 0;
    uint8 minimumRank = 1;
};

struct DraftCard
{
    uint32 id = 0;
    std::string key;
    DraftCardType type = DraftCardType::None;
    uint8 sourceLevel = 1;
    DraftRarity rarity = DraftRarity::Common;
    uint32 weight = ADVENTURER_DRAFT_STANDARD_WEIGHT;
    std::vector<std::vector<uint32>> rankGrants;
    std::vector<DraftRequirement> requirementsAll;
    std::vector<DraftRequirement> requirementsAny;
    std::vector<uint32> unlocks;
    bool replacesPreviousRank = false;
    std::string name;
};

struct DraftRuntimeConfig
{
    uint8 offerSize = 3;
    uint16 initialActivePicks = 3;
    uint8 initialActiveSourceLevelCap = 10;
    uint8 activeSourceLevelLookahead = 3;
    uint8 activeDraftFirstLevel = 5;
    uint8 activeDraftEveryLevels = 5;
    uint8 talentDraftFirstLevel = 10;
    uint8 talentDraftEveryLevels = 1;

    std::array<uint32, 5> rarityMultipliers = { 100, 55, 25, 10, 3 };

    uint16 rerollStartingCharges = 10;
    uint8 rerollGainEveryLevels = 5;
    uint16 rerollGainAmount = 1;
    uint16 rerollMaxCharges = 0;

    uint16 blessStartingCharges = 1;
    uint8 blessGainEveryLevels = 10;
    uint16 blessGainAmount = 1;
    uint16 blessMaxCharges = 0;
    uint8 blessMaxActive = 1;
    uint32 blessWeightMultiplierPercent = 300;

    uint16 destroyStartingCharges = 1;
    uint8 destroyGainEveryLevels = 10;
    uint16 destroyGainAmount = 1;
    uint16 destroyMaxCharges = 0;
};

struct DraftRuntimeData
{
    bool loaded = false;
    DraftRuntimeConfig config;
    std::vector<DraftCard> cards;
};

struct DraftState
{
    uint8 processedLevel = 0;
    uint16 pendingActive = 0;
    uint16 pendingTalent = 0;
    DraftCardType offerType = DraftCardType::None;
    std::array<uint32, ADVENTURER_DRAFT_MAX_OFFER_SIZE> offeredCards = { 0, 0, 0 };
    std::map<uint32, uint8> ownedRanks;

    uint16 rerollCharges = 0;
    uint16 blessCharges = 0;
    uint16 destroyCharges = 0;
    uint32 blessedCardId = 0;
    std::set<uint32> destroyedCards;
};

struct ComboSyncState
{
    uint32 elapsed = 0;
    ObjectGuid selectedTarget = ObjectGuid::Empty;
    uint8 points = 0xFF;
};

std::unordered_map<uint64, ComboSyncState> comboSyncStates;
std::unordered_map<uint64, DraftState> draftStates;
DraftRuntimeData draftRuntime;

constexpr uint32 UNIVERSAL_SKILLS[] =
{
    43, 44, 45, 46, 54, 55, 95, 136, 160, 162, 172, 173, 176,
    226, 228, 229, 293, 413, 414, 415, 433, 473
};

constexpr uint32 UNIVERSAL_SPELLS[] =
{
    81,
    107,
    3127,
    SPELL_DUAL_WIELD,

    9078, 9077, 8737, 750,

    196, 197, 198, 199, 201, 202, 227, 1180, 200, 15590,
    264, 5011, 266, 2567, 5009,

    75,
    5019,
    2764,
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
    data << uint8(0);
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
    player->SaveToDB(false, false);
}

// ---------------------------------------------------------------------------
// External SpellDraft runtime data
// ---------------------------------------------------------------------------
std::string Trim(std::string value)
{
    auto notSpace = [](unsigned char c) { return !std::isspace(c); };
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), notSpace));
    value.erase(std::find_if(value.rbegin(), value.rend(), notSpace).base(), value.end());
    return value;
}

std::string Lower(std::string value)
{
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c)
    {
        return static_cast<char>(std::tolower(c));
    });
    return value;
}

std::vector<std::string> Split(std::string const& value, char separator)
{
    std::vector<std::string> result;
    std::stringstream input(value);
    std::string token;
    while (std::getline(input, token, separator))
        result.push_back(token);
    if (!value.empty() && value.back() == separator)
        result.emplace_back();
    return result;
}

bool ParseUInt(std::string const& raw, uint32& value)
{
    try
    {
        size_t consumed = 0;
        unsigned long parsed = std::stoul(Trim(raw), &consumed);
        std::string clean = Trim(raw);
        if (clean.empty() || consumed != clean.size())
            return false;
        value = static_cast<uint32>(parsed);
        return true;
    }
    catch (...)
    {
        return false;
    }
}

std::string DraftRuntimeDirectory()
{
    std::string dataDir = sConfigMgr->GetOption<std::string>("DataDir", ".");
    if (dataDir.empty())
        dataDir = ".";
    char last = dataDir.back();
    if (last != '/' && last != '\\')
        dataDir += '/';
    return dataDir + "spelldraft/";
}

uint32 ReadOption(std::unordered_map<std::string, std::string> const& values, std::string const& key, uint32 fallback)
{
    auto itr = values.find(key);
    if (itr == values.end())
        return fallback;
    uint32 parsed = fallback;
    return ParseUInt(itr->second, parsed) ? parsed : fallback;
}

bool LoadDraftConfig(std::string const& path, DraftRuntimeConfig& config, std::string& error)
{
    std::ifstream input(path);
    if (!input.is_open())
    {
        error = "cannot open " + path;
        return false;
    }

    std::unordered_map<std::string, std::string> values;
    std::string section;
    std::string line;
    while (std::getline(input, line))
    {
        line = Trim(line);
        if (line.empty() || line[0] == '#' || line[0] == ';')
            continue;
        if (line.front() == '[' && line.back() == ']')
        {
            section = Trim(line.substr(1, line.size() - 2));
            continue;
        }
        size_t equal = line.find('=');
        if (equal == std::string::npos || section.empty())
            continue;
        std::string key = section + "." + Trim(line.substr(0, equal));
        values[key] = Trim(line.substr(equal + 1));
    }

    DraftRuntimeConfig parsed;
    parsed.offerSize = static_cast<uint8>(std::min<uint32>(ADVENTURER_DRAFT_MAX_OFFER_SIZE,
        std::max<uint32>(1, ReadOption(values, "Draft.OfferSize", parsed.offerSize))));
    parsed.initialActivePicks = static_cast<uint16>(ReadOption(values, "Draft.InitialActivePicks", parsed.initialActivePicks));
    parsed.initialActiveSourceLevelCap = static_cast<uint8>(ReadOption(values, "Draft.InitialActiveSourceLevelCap", parsed.initialActiveSourceLevelCap));
    parsed.activeSourceLevelLookahead = static_cast<uint8>(ReadOption(values, "Draft.ActiveSourceLevelLookahead", parsed.activeSourceLevelLookahead));
    parsed.activeDraftFirstLevel = static_cast<uint8>(ReadOption(values, "Draft.ActiveDraftFirstLevel", parsed.activeDraftFirstLevel));
    parsed.activeDraftEveryLevels = static_cast<uint8>(ReadOption(values, "Draft.ActiveDraftEveryLevels", parsed.activeDraftEveryLevels));
    parsed.talentDraftFirstLevel = static_cast<uint8>(ReadOption(values, "Draft.TalentDraftFirstLevel", parsed.talentDraftFirstLevel));
    parsed.talentDraftEveryLevels = static_cast<uint8>(ReadOption(values, "Draft.TalentDraftEveryLevels", parsed.talentDraftEveryLevels));

    parsed.rarityMultipliers[0] = ReadOption(values, "Rarity.CommonWeightMultiplier", parsed.rarityMultipliers[0]);
    parsed.rarityMultipliers[1] = ReadOption(values, "Rarity.UncommonWeightMultiplier", parsed.rarityMultipliers[1]);
    parsed.rarityMultipliers[2] = ReadOption(values, "Rarity.RareWeightMultiplier", parsed.rarityMultipliers[2]);
    parsed.rarityMultipliers[3] = ReadOption(values, "Rarity.EpicWeightMultiplier", parsed.rarityMultipliers[3]);
    parsed.rarityMultipliers[4] = ReadOption(values, "Rarity.LegendaryWeightMultiplier", parsed.rarityMultipliers[4]);

    parsed.rerollStartingCharges = static_cast<uint16>(ReadOption(values, "Reroll.StartingCharges", parsed.rerollStartingCharges));
    parsed.rerollGainEveryLevels = static_cast<uint8>(ReadOption(values, "Reroll.GainEveryLevels", parsed.rerollGainEveryLevels));
    parsed.rerollGainAmount = static_cast<uint16>(ReadOption(values, "Reroll.GainAmount", parsed.rerollGainAmount));
    parsed.rerollMaxCharges = static_cast<uint16>(ReadOption(values, "Reroll.MaxCharges", parsed.rerollMaxCharges));

    parsed.blessStartingCharges = static_cast<uint16>(ReadOption(values, "Bless.StartingCharges", parsed.blessStartingCharges));
    parsed.blessGainEveryLevels = static_cast<uint8>(ReadOption(values, "Bless.GainEveryLevels", parsed.blessGainEveryLevels));
    parsed.blessGainAmount = static_cast<uint16>(ReadOption(values, "Bless.GainAmount", parsed.blessGainAmount));
    parsed.blessMaxCharges = static_cast<uint16>(ReadOption(values, "Bless.MaxCharges", parsed.blessMaxCharges));
    parsed.blessMaxActive = static_cast<uint8>(ReadOption(values, "Bless.MaxActive", parsed.blessMaxActive));
    parsed.blessWeightMultiplierPercent = ReadOption(values, "Bless.WeightMultiplierPercent", parsed.blessWeightMultiplierPercent);

    parsed.destroyStartingCharges = static_cast<uint16>(ReadOption(values, "Destroy.StartingCharges", parsed.destroyStartingCharges));
    parsed.destroyGainEveryLevels = static_cast<uint8>(ReadOption(values, "Destroy.GainEveryLevels", parsed.destroyGainEveryLevels));
    parsed.destroyGainAmount = static_cast<uint16>(ReadOption(values, "Destroy.GainAmount", parsed.destroyGainAmount));
    parsed.destroyMaxCharges = static_cast<uint16>(ReadOption(values, "Destroy.MaxCharges", parsed.destroyMaxCharges));

    config = parsed;
    return true;
}

bool ParseRarity(std::string const& raw, DraftRarity& rarity)
{
    std::string value = Lower(Trim(raw));
    if (value == "common") rarity = DraftRarity::Common;
    else if (value == "uncommon") rarity = DraftRarity::Uncommon;
    else if (value == "rare") rarity = DraftRarity::Rare;
    else if (value == "epic") rarity = DraftRarity::Epic;
    else if (value == "legendary") rarity = DraftRarity::Legendary;
    else return false;
    return true;
}

bool ParseCardType(std::string const& raw, DraftCardType& type)
{
    std::string value = Lower(Trim(raw));
    if (value == "active") type = DraftCardType::Active;
    else if (value == "talent") type = DraftCardType::Talent;
    else return false;
    return true;
}

bool ParseRankGrants(std::string const& raw, std::vector<std::vector<uint32>>& ranks)
{
    ranks.clear();
    for (std::string const& rankRaw : Split(Trim(raw), '/'))
    {
        if (Trim(rankRaw).empty())
            return false;
        std::vector<uint32> grants;
        for (std::string const& spellRaw : Split(rankRaw, '+'))
        {
            uint32 spellId = 0;
            if (!ParseUInt(spellRaw, spellId) || !spellId)
                return false;
            grants.push_back(spellId);
        }
        if (grants.empty())
            return false;
        ranks.push_back(grants);
    }
    return !ranks.empty();
}

bool ParseRequirements(std::string const& raw, char separator, std::vector<DraftRequirement>& requirements)
{
    requirements.clear();
    std::string clean = Trim(raw);
    if (clean.empty())
        return true;

    for (std::string const& itemRaw : Split(clean, separator))
    {
        std::string item = Trim(itemRaw);
        if (item.empty())
            continue;
        size_t colon = item.find(':');
        if (colon == std::string::npos)
            return false;
        uint32 cardId = 0;
        uint32 rank = 0;
        if (!ParseUInt(item.substr(0, colon), cardId) || !ParseUInt(item.substr(colon + 1), rank) || !cardId || !rank || rank > 255)
            return false;
        requirements.push_back({ cardId, static_cast<uint8>(rank) });
    }
    return true;
}

bool ParseUnlocks(std::string const& raw, std::vector<uint32>& unlocks)
{
    unlocks.clear();
    std::string clean = Trim(raw);
    if (clean.empty())
        return true;
    for (std::string const& item : Split(clean, ','))
    {
        uint32 cardId = 0;
        if (!ParseUInt(item, cardId) || !cardId)
            return false;
        unlocks.push_back(cardId);
    }
    return true;
}

bool LoadDraftCards(std::string const& path, std::vector<DraftCard>& cards, std::string& error)
{
    std::ifstream input(path);
    if (!input.is_open())
    {
        error = "cannot open " + path;
        return false;
    }

    std::string header;
    if (!std::getline(input, header) || header.find("id;key;type;source_level;rarity;weight;rank_grants;") != 0)
    {
        error = "unexpected cards.csv header";
        return false;
    }

    std::vector<DraftCard> parsed;
    std::set<uint32> ids;
    std::set<std::string> keys;
    std::string line;
    uint32 lineNumber = 1;
    while (std::getline(input, line))
    {
        ++lineNumber;
        if (Trim(line).empty() || Trim(line).front() == '#')
            continue;

        std::vector<std::string> fields = Split(line, ';');
        if (fields.size() != 12)
        {
            error = "cards.csv line " + std::to_string(lineNumber) + " must contain 12 fields";
            return false;
        }

        DraftCard card;
        uint32 sourceLevel = 0;
        uint32 weight = 0;
        uint32 cardId = 0;
        if (!ParseUInt(fields[0], cardId) || !cardId || !ids.insert(cardId).second)
        {
            error = "invalid/duplicate card id at line " + std::to_string(lineNumber);
            return false;
        }
        card.id = cardId;
        card.key = Trim(fields[1]);
        if (card.key.empty() || !keys.insert(card.key).second)
        {
            error = "invalid/duplicate card key at line " + std::to_string(lineNumber);
            return false;
        }
        if (!ParseCardType(fields[2], card.type) || !ParseUInt(fields[3], sourceLevel) || sourceLevel == 0 || sourceLevel > 255)
        {
            error = "invalid type/source level at line " + std::to_string(lineNumber);
            return false;
        }
        card.sourceLevel = static_cast<uint8>(sourceLevel);
        if (!ParseRarity(fields[4], card.rarity) || !ParseUInt(fields[5], weight) || !weight)
        {
            error = "invalid rarity/weight at line " + std::to_string(lineNumber);
            return false;
        }
        card.weight = weight;
        if (!ParseRankGrants(fields[6], card.rankGrants)
            || !ParseRequirements(fields[7], ',', card.requirementsAll)
            || !ParseRequirements(fields[8], '|', card.requirementsAny)
            || !ParseUnlocks(fields[9], card.unlocks))
        {
            error = "invalid grants/requirements/unlocks at line " + std::to_string(lineNumber);
            return false;
        }
        std::string replace = Lower(Trim(fields[10]));
        card.replacesPreviousRank = (replace == "1" || replace == "true" || replace == "yes");
        card.name = Trim(fields[11]);
        parsed.push_back(card);
    }

    if (parsed.empty())
    {
        error = "cards.csv contains no cards";
        return false;
    }

    for (DraftCard const& card : parsed)
    {
        for (DraftRequirement const& requirement : card.requirementsAll)
            if (!ids.count(requirement.cardId))
            {
                error = "card " + std::to_string(card.id) + " requires missing card " + std::to_string(requirement.cardId);
                return false;
            }
        for (DraftRequirement const& requirement : card.requirementsAny)
            if (!ids.count(requirement.cardId))
            {
                error = "card " + std::to_string(card.id) + " requires missing card " + std::to_string(requirement.cardId);
                return false;
            }
        for (uint32 unlock : card.unlocks)
            if (!ids.count(unlock))
            {
                error = "card " + std::to_string(card.id) + " unlocks missing card " + std::to_string(unlock);
                return false;
            }
    }

    cards = std::move(parsed);
    return true;
}

std::vector<DraftCard> BuildFallbackDraftCards()
{
    return
    {
        { 1, "battle_stance", DraftCardType::Active, 1, DraftRarity::Common, 100, {{2457}}, {}, {}, {11, 106}, false, "Battle Stance" },
        { 2, "fireball", DraftCardType::Active, 1, DraftRarity::Common, 100, {{133}}, {}, {}, {104}, false, "Fireball" },
        { 3, "frostbolt", DraftCardType::Active, 4, DraftRarity::Common, 100, {{116}}, {}, {}, {105}, false, "Frostbolt" },
        { 4, "shadow_bolt", DraftCardType::Active, 1, DraftRarity::Common, 100, {{686}}, {}, {}, {}, false, "Shadow Bolt" },
        { 5, "smite", DraftCardType::Active, 1, DraftRarity::Common, 100, {{585}}, {}, {}, {}, false, "Smite" },
        { 6, "lightning_bolt", DraftCardType::Active, 1, DraftRarity::Common, 100, {{403}}, {}, {}, {}, false, "Lightning Bolt" },
        { 7, "wrath", DraftCardType::Active, 1, DraftRarity::Common, 100, {{5176}}, {}, {}, {}, false, "Wrath" },
        { 8, "heroic_strike", DraftCardType::Active, 1, DraftRarity::Common, 110, {{78}}, {}, {}, {107}, false, "Heroic Strike" },
        { 9, "rejuvenation", DraftCardType::Active, 4, DraftRarity::Common, 100, {{774}}, {}, {}, {}, false, "Rejuvenation" },
        { 10, "stealth_kit", DraftCardType::Active, 1, DraftRarity::Uncommon, 120, {{1784, 921}}, {}, {}, {}, false, "Stealth + Pick Pocket" },
        { 11, "charge", DraftCardType::Active, 4, DraftRarity::Common, 500, {{100}}, {{1, 1}}, {}, {}, false, "Charge" },
        { 12, "arcane_intellect", DraftCardType::Active, 1, DraftRarity::Common, 90, {{1459}}, {}, {}, {}, false, "Arcane Intellect" },
        { 13, "healing_wave", DraftCardType::Active, 1, DraftRarity::Common, 100, {{331}}, {}, {}, {}, false, "Healing Wave" },
        { 14, "sinister_strike", DraftCardType::Active, 1, DraftRarity::Common, 100, {{1752}}, {}, {}, {}, false, "Sinister Strike" },
        { 101, "cruelty", DraftCardType::Talent, 10, DraftRarity::Common, 120, {{12320},{12852},{12853},{12855},{12856}}, {}, {}, {}, true, "Cruelty" },
        { 102, "deflection", DraftCardType::Talent, 10, DraftRarity::Common, 100, {{16462},{16463},{16464},{16465},{16466}}, {}, {}, {}, true, "Deflection" },
        { 103, "anticipation", DraftCardType::Talent, 10, DraftRarity::Common, 90, {{12297},{12750},{12751},{12752},{12753}}, {}, {}, {}, true, "Anticipation" },
        { 104, "improved_fireball", DraftCardType::Talent, 10, DraftRarity::Uncommon, 180, {{11069},{12338},{12339},{12340},{12341}}, {{2,1}}, {}, {}, true, "Improved Fireball" },
        { 105, "improved_frostbolt", DraftCardType::Talent, 10, DraftRarity::Uncommon, 180, {{11070},{12473},{16763},{16765},{16766}}, {{3,1}}, {}, {}, true, "Improved Frostbolt" },
        { 106, "tactical_mastery", DraftCardType::Talent, 10, DraftRarity::Uncommon, 250, {{12295},{12676},{12677}}, {{1,1}}, {}, {}, true, "Tactical Mastery" },
        { 107, "improved_heroic_strike", DraftCardType::Talent, 10, DraftRarity::Uncommon, 180, {{12282},{12663},{12664}}, {{8,1}}, {}, {}, true, "Improved Heroic Strike" },
    };
}

void ReloadDraftRuntimeData()
{
    std::string directory = DraftRuntimeDirectory();

    DraftRuntimeConfig nextConfig = draftRuntime.loaded ? draftRuntime.config : DraftRuntimeConfig{};
    std::string configError;
    DraftRuntimeConfig parsedConfig;
    if (LoadDraftConfig(directory + "spelldraft.conf", parsedConfig, configError))
        nextConfig = parsedConfig;
    else if (!draftRuntime.loaded)
        std::cerr << "Adventurer SpellDraft: " << configError << "; using compiled defaults\n";

    std::vector<DraftCard> nextCards;
    std::string cardsError;
    bool cardsLoaded = LoadDraftCards(directory + "cards.csv", nextCards, cardsError);
    if (!cardsLoaded)
    {
        if (draftRuntime.cards.empty())
            nextCards = BuildFallbackDraftCards();
        else
            nextCards = draftRuntime.cards;
        std::cerr << "Adventurer SpellDraft: " << cardsError << "; keeping last valid catalog\n";
    }

    draftRuntime.config = nextConfig;
    draftRuntime.cards = std::move(nextCards);
    draftRuntime.loaded = true;
}

void EnsureDraftRuntimeLoaded()
{
    if (!draftRuntime.loaded)
        ReloadDraftRuntimeData();
}

DraftRuntimeConfig const& GetDraftConfig()
{
    EnsureDraftRuntimeLoaded();
    return draftRuntime.config;
}

std::vector<DraftCard> const& GetDraftCards()
{
    EnsureDraftRuntimeLoaded();
    return draftRuntime.cards;
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

bool RequirementMet(DraftState const& state, DraftRequirement const& requirement)
{
    return GetOwnedRank(state, requirement.cardId) >= requirement.minimumRank;
}

bool MeetsRequirements(DraftState const& state, DraftCard const& card)
{
    for (DraftRequirement const& requirement : card.requirementsAll)
        if (!RequirementMet(state, requirement))
            return false;

    if (!card.requirementsAny.empty())
    {
        bool any = false;
        for (DraftRequirement const& requirement : card.requirementsAny)
            if (RequirementMet(state, requirement))
            {
                any = true;
                break;
            }
        if (!any)
            return false;
    }

    return true;
}

bool IsCardEligible(Player const* player, DraftState const& state, DraftCard const& card, DraftCardType type)
{
    if (card.type != type || card.rankGrants.empty() || state.destroyedCards.count(card.id))
        return false;

    uint8 currentRank = GetOwnedRank(state, card.id);
    if (currentRank >= card.rankGrants.size())
        return false;

    uint32 playerLevel = player ? player->GetLevel() : 1;
    // Adapted DK roots have actual low-level cast requirements. Do not offer
    // them early through the normal source-level lookahead used by stock cards.
    if (type == DraftCardType::Active)
        for (uint32 spellId : card.rankGrants.front())
            if (spellId >= 280001 && spellId <= 281180)
                if (SpellInfo const* info = sSpellMgr->GetSpellInfo(spellId))
                    if (std::max(info->BaseLevel, info->SpellLevel) > playerLevel)
                        return false;
    uint32 sourceCap = playerLevel;
    if (type == DraftCardType::Active)
    {
        DraftRuntimeConfig const& config = GetDraftConfig();
        sourceCap = playerLevel <= config.initialActiveSourceLevelCap
            ? config.initialActiveSourceLevelCap
            : playerLevel + config.activeSourceLevelLookahead;
    }
    if (card.sourceLevel > sourceCap)
        return false;

    return MeetsRequirements(state, card);
}

bool IsCardDebugEligible(Player const* player, DraftState const& state, DraftCard const& card)
{
    if (card.rankGrants.empty() || state.destroyedCards.count(card.id))
        return false;

    uint8 currentRank = GetOwnedRank(state, card.id);
    if (currentRank >= card.rankGrants.size())
        return false;

    uint32 playerLevel = player ? player->GetLevel() : 1;
    DraftRuntimeConfig const& config = GetDraftConfig();
    uint32 sourceCap = playerLevel;
    if (card.type == DraftCardType::Active)
    {
        sourceCap = playerLevel <= config.initialActiveSourceLevelCap
            ? config.initialActiveSourceLevelCap
            : playerLevel + config.activeSourceLevelLookahead;
    }
    else if (card.type == DraftCardType::Talent)
    {
        // The debug window previews the talent pool from the first talent-draft
        // level onward. Actual talent offers remain level-gated by IsCardEligible.
        sourceCap = std::max<uint32>(playerLevel, config.talentDraftFirstLevel);
    }
    else
        return false;

    if (card.sourceLevel > sourceCap)
        return false;

    return MeetsRequirements(state, card);
}

uint32 RarityWeightMultiplier(DraftRarity rarity)
{
    size_t index = static_cast<size_t>(rarity);
    auto const& values = GetDraftConfig().rarityMultipliers;
    return index < values.size() ? values[index] : 1;
}

uint32 EffectiveCardWeight(DraftState const& state, DraftCard const& card)
{
    uint64 weighted = uint64(card.weight) * RarityWeightMultiplier(card.rarity);
    weighted = std::max<uint64>(1, weighted / ADVENTURER_DRAFT_STANDARD_WEIGHT);

    DraftRuntimeConfig const& config = GetDraftConfig();
    if (config.blessMaxActive > 0 && state.blessedCardId == card.id)
        weighted = std::max<uint64>(1, weighted * config.blessWeightMultiplierPercent / 100);

    return static_cast<uint32>(std::min<uint64>(weighted, 0xFFFFFFFFull));
}

std::vector<uint32> SelectWeightedCards(Player* player, DraftState const& state, DraftCardType type, uint32 count, std::set<uint32> const& excluded)
{
    std::vector<DraftCard const*> candidates;
    for (DraftCard const& card : GetDraftCards())
        if (!excluded.count(card.id) && IsCardEligible(player, state, card, type))
            candidates.push_back(&card);

    std::vector<uint32> selected;
    while (!candidates.empty() && selected.size() < count)
    {
        uint64 total64 = 0;
        for (DraftCard const* card : candidates)
            total64 += EffectiveCardWeight(state, *card);
        uint32 totalWeight = static_cast<uint32>(std::min<uint64>(total64, 0xFFFFFFFFull));
        if (!totalWeight)
            break;

        uint32 roll = urand(1, totalWeight);
        uint64 cursor = 0;
        size_t chosenIndex = 0;
        for (size_t i = 0; i < candidates.size(); ++i)
        {
            cursor += EffectiveCardWeight(state, *candidates[i]);
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
// Draft persistence
// v1: schema,level,pendingA,pendingT,type,o1,o2,o3,card:rank...
// v2: schema,level,pendingA,pendingT,type,o1,o2,o3,rerolls,destroys,blessed,
//     oCARD:RANK...,xCARD...
// v3: schema,level,pendingA,pendingT,type,o1,o2,o3,rerolls,blesses,destroys,
//     blessed,oCARD:RANK...,xCARD...
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
        << ',' << state.offeredCards[2]
        << ',' << state.rerollCharges
        << ',' << state.blessCharges
        << ',' << state.destroyCharges
        << ',' << state.blessedCardId;

    for (auto const& [cardId, rank] : state.ownedRanks)
        out << ",o" << cardId << ':' << uint32(rank);
    for (uint32 cardId : state.destroyedCards)
        out << ",x" << cardId;

    return out.str();
}

bool DeserializeDraftState(std::string const& data, DraftState& state)
{
    EnsureDraftRuntimeLoaded();
    std::vector<std::string> tokens = Split(data, ',');
    if (tokens.size() < 8)
        return false;

    try
    {
        uint32 schema = std::stoul(tokens[0]);
        if (schema != 1 && schema != 2 && schema != ADVENTURER_DRAFT_SCHEMA)
            return false;

        state = DraftState{};
        state.processedLevel = static_cast<uint8>(std::stoul(tokens[1]));
        state.pendingActive = static_cast<uint16>(std::stoul(tokens[2]));
        state.pendingTalent = static_cast<uint16>(std::stoul(tokens[3]));
        state.offerType = static_cast<DraftCardType>(std::stoul(tokens[4]));
        state.offeredCards[0] = static_cast<uint32>(std::stoul(tokens[5]));
        state.offeredCards[1] = static_cast<uint32>(std::stoul(tokens[6]));
        state.offeredCards[2] = static_cast<uint32>(std::stoul(tokens[7]));

        size_t firstDynamic = 8;
        if (schema == ADVENTURER_DRAFT_SCHEMA)
        {
            if (tokens.size() < 12)
                return false;
            state.rerollCharges = static_cast<uint16>(std::stoul(tokens[8]));
            state.blessCharges = static_cast<uint16>(std::stoul(tokens[9]));
            state.destroyCharges = static_cast<uint16>(std::stoul(tokens[10]));
            state.blessedCardId = static_cast<uint32>(std::stoul(tokens[11]));
            firstDynamic = 12;
        }
        else if (schema == 2)
        {
            if (tokens.size() < 11)
                return false;
            state.rerollCharges = static_cast<uint16>(std::stoul(tokens[8]));
            state.blessCharges = GetDraftConfig().blessStartingCharges;
            state.destroyCharges = static_cast<uint16>(std::stoul(tokens[9]));
            state.blessedCardId = static_cast<uint32>(std::stoul(tokens[10]));
            firstDynamic = 11;
        }
        else
        {
            state.rerollCharges = GetDraftConfig().rerollStartingCharges;
            state.blessCharges = GetDraftConfig().blessStartingCharges;
            state.destroyCharges = GetDraftConfig().destroyStartingCharges;
        }

        for (size_t i = firstDynamic; i < tokens.size(); ++i)
        {
            std::string token = tokens[i];
            if (token.empty())
                continue;

            if (schema == 1)
            {
                size_t separator = token.find(':');
                if (separator == std::string::npos)
                    continue;
                uint32 cardId = static_cast<uint32>(std::stoul(token.substr(0, separator)));
                uint8 rank = static_cast<uint8>(std::stoul(token.substr(separator + 1)));
                if (cardId && rank)
                    state.ownedRanks[cardId] = rank;
                continue;
            }

            if (token[0] == 'o')
            {
                size_t separator = token.find(':');
                if (separator == std::string::npos)
                    continue;
                uint32 cardId = static_cast<uint32>(std::stoul(token.substr(1, separator - 1)));
                uint8 rank = static_cast<uint8>(std::stoul(token.substr(separator + 1)));
                if (cardId && rank)
                    state.ownedRanks[cardId] = rank;
            }
            else if (token[0] == 'x')
            {
                uint32 cardId = static_cast<uint32>(std::stoul(token.substr(1)));
                if (cardId)
                    state.destroyedCards.insert(cardId);
            }
        }
    }
    catch (...)
    {
        return false;
    }

    return true;
}

bool IsScheduledLevel(uint32 level, uint32 firstLevel, uint32 everyLevels)
{
    return everyLevels > 0 && level >= firstLevel && ((level - firstLevel) % everyLevels) == 0;
}

void AddCharge(uint16& charges, uint16 amount, uint16 maximum)
{
    uint32 next = uint32(charges) + amount;
    if (maximum > 0)
        next = std::min<uint32>(next, maximum);
    charges = static_cast<uint16>(std::min<uint32>(next, 65535));
}

void ApplyLevelRewards(DraftState& state, uint32 level)
{
    DraftRuntimeConfig const& config = GetDraftConfig();
    if (IsScheduledLevel(level, config.activeDraftFirstLevel, config.activeDraftEveryLevels))
        ++state.pendingActive;
    if (IsScheduledLevel(level, config.talentDraftFirstLevel, config.talentDraftEveryLevels))
        ++state.pendingTalent;

    if (config.rerollGainEveryLevels > 0 && level > 1 && (level % config.rerollGainEveryLevels) == 0)
        AddCharge(state.rerollCharges, config.rerollGainAmount, config.rerollMaxCharges);
    if (config.blessGainEveryLevels > 0 && level > 1 && (level % config.blessGainEveryLevels) == 0)
        AddCharge(state.blessCharges, config.blessGainAmount, config.blessMaxCharges);
    if (config.destroyGainEveryLevels > 0 && level > 1 && (level % config.destroyGainEveryLevels) == 0)
        AddCharge(state.destroyCharges, config.destroyGainAmount, config.destroyMaxCharges);
}

DraftState BuildFreshDraftState(uint8 currentLevel)
{
    ReloadDraftRuntimeData();
    DraftRuntimeConfig const& config = GetDraftConfig();
    DraftState state;
    state.processedLevel = currentLevel;
    state.pendingActive = config.initialActivePicks;
    state.rerollCharges = config.rerollStartingCharges;
    state.blessCharges = config.blessStartingCharges;
    state.destroyCharges = config.destroyStartingCharges;

    for (uint32 level = 1; level <= currentLevel; ++level)
        ApplyLevelRewards(state, level);

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
        ApplyLevelRewards(state, level);

    state.processedLevel = currentLevel;
}

DraftCardType NextPendingDraftType(DraftState const& state)
{
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

uint32 OfferedCardCount(DraftState const& state)
{
    uint32 count = 0;
    for (uint32 cardId : state.offeredCards)
        if (cardId)
            ++count;
    return count;
}

uint32 SelectableOfferCount(Player* player, DraftState const& state)
{
    uint32 count = 0;
    for (uint32 cardId : state.offeredCards)
    {
        if (!cardId || state.destroyedCards.count(cardId))
            continue;
        DraftCard const* card = FindDraftCard(cardId);
        if (card && IsCardEligible(player, state, *card, state.offerType))
            ++count;
    }
    return count;
}

bool ExistingOfferIsValid(Player* player, DraftState const& state, DraftCardType expectedType)
{
    if (state.offerType != expectedType || state.offeredCards[0] == 0)
        return false;
    if (OfferedCardCount(state) != GetDraftConfig().offerSize)
        return false;

    bool hasSelectableCard = false;
    for (uint32 cardId : state.offeredCards)
    {
        if (!cardId)
            continue;

        DraftCard const* card = FindDraftCard(cardId);
        if (!card)
            return false;

        if (state.destroyedCards.count(cardId))
            continue;

        if (!IsCardEligible(player, state, *card, expectedType))
            return false;
        hasSelectableCard = true;
    }
    return hasSelectableCard;
}

void GenerateDraftOffer(Player* player, DraftState& state, DraftCardType type, bool avoidCurrent)
{
    std::set<uint32> previous;
    if (avoidCurrent)
        for (uint32 cardId : state.offeredCards)
            if (cardId)
                previous.insert(cardId);

    ClearDraftOffer(state);
    uint32 desired = GetDraftConfig().offerSize;
    std::vector<uint32> selected = SelectWeightedCards(player, state, type, desired, previous);

    if (selected.size() < desired && avoidCurrent)
    {
        std::set<uint32> excluded(selected.begin(), selected.end());
        std::vector<uint32> fallback = SelectWeightedCards(player, state, type, desired - selected.size(), excluded);
        for (uint32 cardId : fallback)
            if (std::find(selected.begin(), selected.end(), cardId) == selected.end())
                selected.push_back(cardId);
    }

    if (selected.empty())
        return;

    state.offerType = type;
    for (size_t i = 0; i < selected.size() && i < state.offeredCards.size(); ++i)
        state.offeredCards[i] = selected[i];
}

void SendDraftDebugPool(Player* player, DraftState const& state)
{
    uint32 activeCount = 0;
    uint32 talentCount = 0;

    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX,
        std::string("D|B|") + std::to_string(GetDraftCards().size()));

    for (DraftCard const& card : GetDraftCards())
    {
        if (!IsCardDebugEligible(player, state, card))
            continue;

        uint8 currentRank = GetOwnedRank(state, card.id);
        uint8 nextRank = currentRank + 1;
        if (nextRank == 0 || nextRank > card.rankGrants.size())
            continue;
        std::vector<uint32> const& grants = card.rankGrants[nextRank - 1];
        if (grants.empty())
            continue;

        if (card.type == DraftCardType::Active)
            ++activeCount;
        else if (card.type == DraftCardType::Talent)
            ++talentCount;

        std::ostringstream payload;
        payload << "D|C|" << (card.type == DraftCardType::Active ? 'A' : 'T')
                << '|' << card.id
                << '|' << grants.front()
                << '|' << uint32(card.rarity)
                << '|' << uint32(card.sourceLevel)
                << '|' << uint32(currentRank)
                << '|' << card.rankGrants.size();
        SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, payload.str());
    }

    std::ostringstream end;
    end << "D|E|" << activeCount << '|' << talentCount;
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, end.str());
}

void SendDraftMeta(Player* player, DraftState const& state)
{
    DraftRuntimeConfig const& config = GetDraftConfig();
    std::ostringstream payload;
    payload << "M|" << state.rerollCharges
            << '|' << state.destroyCharges
            << '|' << state.blessedCardId
            << '|' << (config.blessMaxActive > 0 ? config.blessWeightMultiplierPercent : 0)
            << '|' << state.blessCharges
            << '|' << config.rerollStartingCharges
            << '|' << config.blessStartingCharges
            << '|' << config.destroyStartingCharges
            << '|' << uint32(config.initialActiveSourceLevelCap)
            << '|' << GetDraftCards().size();
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, payload.str());
}

void SendDraftClosed(Player* player, DraftState const* state = nullptr)
{
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, "C");
    if (state)
        SendDraftMeta(player, *state);
}

void SendDraftError(Player* player, char const* code, DraftState const* state = nullptr)
{
    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, std::string("E|") + code);
    if (state)
        SendDraftMeta(player, *state);
}

void SendDraftOffer(Player* player, DraftState const& state)
{
    if (state.offerType == DraftCardType::None || !state.offeredCards[0])
    {
        SendDraftClosed(player, &state);
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
                << ':' << card->rankGrants.size()
                << ':' << (state.destroyedCards.count(card->id) ? 1 : 0);
    }

    SendAddonPayload(player, ADVENTURER_DRAFT_PREFIX, payload.str());
    SendDraftMeta(player, state);
}

void EnsureDraftOffer(Player* player, DraftState& state)
{
    ReloadDraftRuntimeData();
    DraftCardType nextType = NextPendingDraftType(state);
    if (nextType == DraftCardType::None)
    {
        ClearDraftOffer(state);
        PersistDraftState(player, state);
        SendDraftClosed(player, &state);
        return;
    }

    if (!ExistingOfferIsValid(player, state, nextType))
    {
        GenerateDraftOffer(player, state, nextType, false);
        PersistDraftState(player, state);
    }

    if (state.offerType == DraftCardType::None || !state.offeredCards[0])
    {
        SendDraftError(player, nextType == DraftCardType::Active ? "NO_ACTIVE_CARDS" : "NO_TALENT_CARDS", &state);
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
                        player->removeSpell(spellId, SPEC_MASK_ALL, false);
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
                player->removeSpell(spellId, SPEC_MASK_ALL, false);
    }

    for (uint32 spellId : card.rankGrants[nextRank - 1])
        if (!player->HasSpell(spellId))
            player->learnSpell(spellId);

    state.ownedRanks[card.id] = nextRank;
    if (state.blessedCardId == card.id && nextRank >= card.rankGrants.size())
        state.blessedCardId = 0;

    if (card.type == DraftCardType::Active && state.pendingActive > 0)
        --state.pendingActive;
    else if (card.type == DraftCardType::Talent && state.pendingTalent > 0)
        --state.pendingTalent;

    ClearDraftOffer(state);
    UpgradeDraftedActiveSpells(player, state);
    PersistDraftState(player, state);
    player->SaveToDB(false, false);
    EnsureDraftOffer(player, state);
}

void HandleDraftPick(Player* player, uint32 cardId)
{
    DraftState& state = GetDraftState(player);
    DraftCard const* card = FindDraftCard(cardId);
    if (!card || !IsCardInCurrentOffer(state, cardId))
    {
        SendDraftError(player, "INVALID_PICK", &state);
        EnsureDraftOffer(player, state);
        return;
    }

    if (card->type != state.offerType || !IsCardEligible(player, state, *card, state.offerType))
    {
        SendDraftError(player, "INELIGIBLE_PICK", &state);
        ClearDraftOffer(state);
        EnsureDraftOffer(player, state);
        return;
    }

    ApplyDraftCard(player, state, *card);
}

void HandleDraftReroll(Player* player)
{
    DraftState& state = GetDraftState(player);
    QueueDraftProgressionToLevel(state, player->GetLevel());
    EnsureDraftOffer(player, state);
    if (state.offerType == DraftCardType::None || !state.offeredCards[0])
        return;
    if (state.rerollCharges == 0)
    {
        SendDraftError(player, "NO_REROLLS", &state);
        return;
    }

    --state.rerollCharges;
    GenerateDraftOffer(player, state, state.offerType, true);
    PersistDraftState(player, state);
    if (!state.offeredCards[0])
        SendDraftError(player, "NO_REROLL_CARDS", &state);
    else
        SendDraftOffer(player, state);
}

void HandleDraftBless(Player* player, uint32 cardId)
{
    DraftState& state = GetDraftState(player);
    DraftRuntimeConfig const& config = GetDraftConfig();
    if (config.blessMaxActive == 0 || config.blessWeightMultiplierPercent == 0)
    {
        SendDraftError(player, "BLESS_DISABLED", &state);
        return;
    }

    if (state.blessCharges == 0)
    {
        SendDraftError(player, "NO_BLESSES", &state);
        return;
    }

    DraftCard const* card = FindDraftCard(cardId);
    if (!card || !IsCardInCurrentOffer(state, cardId) || !IsCardEligible(player, state, *card, state.offerType))
    {
        SendDraftError(player, "INVALID_BLESS", &state);
        return;
    }

    --state.blessCharges;
    state.blessedCardId = cardId;
    PersistDraftState(player, state);
    SendDraftMeta(player, state);
}

void HandleDraftDestroy(Player* player, uint32 cardId)
{
    DraftState& state = GetDraftState(player);
    if (state.destroyCharges == 0)
    {
        SendDraftError(player, "NO_DESTROYS", &state);
        return;
    }

    DraftCard const* card = FindDraftCard(cardId);
    if (!card || !IsCardInCurrentOffer(state, cardId) || !IsCardEligible(player, state, *card, state.offerType))
    {
        SendDraftError(player, "INVALID_DESTROY", &state);
        return;
    }

    if (SelectableOfferCount(player, state) <= 1)
    {
        SendDraftError(player, "CANNOT_DESTROY_LAST_CARD", &state);
        return;
    }

    --state.destroyCharges;
    state.destroyedCards.insert(cardId);
    if (state.blessedCardId == cardId)
        state.blessedCardId = 0;

    PersistDraftState(player, state);
    SendDraftOffer(player, state);
}

void HandleDraftDebugPool(Player* player)
{
    ReloadDraftRuntimeData();
    DraftState& state = GetDraftState(player);
    QueueDraftProgressionToLevel(state, player->GetLevel());
    PersistDraftState(player, state);
    SendDraftDebugPool(player, state);
}

void HandleDraftReady(Player* player)
{
    ReloadDraftRuntimeData();
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
            player->SetAcceptWhispers(true);
            comboSyncStates.erase(player->GetGUID().GetRawValue());

            ReloadDraftRuntimeData();
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

        ReloadDraftRuntimeData();
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
        if (msg == DRAFT_DEBUG_POOL_MESSAGE)
        {
            HandleDraftDebugPool(player);
            return false;
        }
        if (msg == DRAFT_REROLL_MESSAGE)
        {
            HandleDraftReroll(player);
            return false;
        }

        auto parseCardCommand = [&](char const* prefix, auto handler) -> bool
        {
            size_t length = std::char_traits<char>::length(prefix);
            if (msg.rfind(prefix, 0) != 0)
                return false;
            try
            {
                uint32 cardId = static_cast<uint32>(std::stoul(msg.substr(length)));
                handler(player, cardId);
            }
            catch (...)
            {
                SendDraftError(player, "BAD_PICK_FORMAT");
            }
            return true;
        };

        if (parseCardCommand(DRAFT_PICK_PREFIX, HandleDraftPick))
            return false;
        if (parseCardCommand(DRAFT_BLESS_PREFIX, HandleDraftBless))
            return false;
        if (parseCardCommand(DRAFT_DESTROY_PREFIX, HandleDraftDestroy))
            return false;

        return true;
    }

    void OnPlayerAfterUpdateMaxPower(Player* player, Powers& power, float& value) override
    {
        if (!IsAdventurer(player))
            return;

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
            return false;

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
    AddAdventurerDKScripts();
    new AdventurerCorePlayerScript();
}
