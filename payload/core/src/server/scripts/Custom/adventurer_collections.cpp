#include "Config.h"
#include "Language.h"
#include "Opcodes.h"
#include "Player.h"
#include "ScriptDefines/PlayerScript.h"
#include "SharedDefines.h"
#include "WorldPacket.h"

#include <algorithm>
#include <cctype>
#include <fstream>
#include <sstream>
#include <string>
#include <unordered_map>
#include <vector>

namespace
{
constexpr char ADVENTURER_DRAFT_PREFIX[] = "AdventurerDraft";
constexpr char TALENT_COLLECTION_REQUEST[] = "ADRAFT_TALENTS";
constexpr uint32 ADVENTURER_SUBCLASS_SKILLS[] = {900, 901, 902, 903};

struct CollectionTalent
{
    uint32 cardId = 0;
    std::vector<std::vector<uint32>> rankGrants;
};

bool IsAdventurer(Player const* player)
{
    return player && player->getClass() == CLASS_ADVENTURER;
}

std::string Trim(std::string value)
{
    auto notSpace = [](unsigned char c) { return !std::isspace(c); };
    value.erase(value.begin(), std::find_if(value.begin(), value.end(), notSpace));
    value.erase(std::find_if(value.rbegin(), value.rend(), notSpace).base(), value.end());
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
        std::string clean = Trim(raw);
        if (clean.empty())
            return false;
        size_t consumed = 0;
        unsigned long parsed = std::stoul(clean, &consumed);
        if (consumed != clean.size())
            return false;
        value = static_cast<uint32>(parsed);
        return true;
    }
    catch (...)
    {
        return false;
    }
}

bool ParseRankGrants(std::string const& raw, std::vector<std::vector<uint32>>& ranks)
{
    ranks.clear();
    for (std::string const& rankRaw : Split(Trim(raw), '/'))
    {
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

std::string RuntimeDirectory()
{
    std::string dataDir = sConfigMgr->GetOption<std::string>("DataDir", ".");
    if (dataDir.empty())
        dataDir = ".";
    char last = dataDir.back();
    if (last != '/' && last != '\\')
        dataDir += '/';
    return dataDir + "spelldraft/";
}

bool LoadCollectionCatalog(
    std::vector<CollectionTalent>& talents,
    std::unordered_map<uint32, std::string>& subclasses)
{
    talents.clear();
    subclasses.clear();

    std::ifstream cards(RuntimeDirectory() + "cards.csv");
    if (!cards.is_open())
        return false;

    std::string line;
    if (!std::getline(cards, line))
        return false;
    while (std::getline(cards, line))
    {
        if (Trim(line).empty() || Trim(line).front() == '#')
            continue;
        std::vector<std::string> fields = Split(line, ';');
        if (fields.size() != 12 || Trim(fields[2]) != "talent")
            continue;

        uint32 cardId = 0;
        std::vector<std::vector<uint32>> ranks;
        if (!ParseUInt(fields[0], cardId) || !cardId || !ParseRankGrants(fields[6], ranks))
            continue;
        talents.push_back({cardId, std::move(ranks)});
    }

    std::ifstream classMap(RuntimeDirectory() + "card_subclasses.csv");
    if (!classMap.is_open())
        return false;
    if (!std::getline(classMap, line))
        return false;
    while (std::getline(classMap, line))
    {
        if (Trim(line).empty())
            continue;
        std::vector<std::string> fields = Split(line, ';');
        if (fields.size() != 2)
            continue;
        uint32 cardId = 0;
        if (!ParseUInt(fields[0], cardId) || !cardId)
            continue;
        subclasses[cardId] = Trim(fields[1]);
    }

    return !talents.empty() && !subclasses.empty();
}

void SendAddonPayload(Player* player, std::string const& payload)
{
    if (!player || !player->IsInWorld())
        return;

    std::string message = std::string(ADVENTURER_DRAFT_PREFIX) + "\t" + payload;
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

bool HasRank(Player const* player, std::vector<uint32> const& grants)
{
    return !grants.empty() && std::all_of(grants.begin(), grants.end(), [player](uint32 spellId)
    {
        return player->HasSpell(spellId);
    });
}

void SendTalentCollection(Player* player)
{
    std::vector<CollectionTalent> talents;
    std::unordered_map<uint32, std::string> subclasses;
    if (!LoadCollectionCatalog(talents, subclasses))
    {
        SendAddonPayload(player, "T|X|CATALOG");
        return;
    }

    SendAddonPayload(player, "T|B");
    for (CollectionTalent const& talent : talents)
    {
        auto subclassItr = subclasses.find(talent.cardId);
        if (subclassItr == subclasses.end())
            continue;

        uint32 ownedRank = 0;
        uint32 displaySpell = 0;
        for (size_t index = talent.rankGrants.size(); index > 0; --index)
        {
            std::vector<uint32> const& grants = talent.rankGrants[index - 1];
            if (!HasRank(player, grants))
                continue;
            ownedRank = static_cast<uint32>(index);
            displaySpell = grants.front();
            break;
        }
        if (!ownedRank || !displaySpell)
            continue;

        std::ostringstream payload;
        payload << "T|C|" << talent.cardId
                << '|' << subclassItr->second
                << '|' << ownedRank
                << '|' << talent.rankGrants.size()
                << '|' << displaySpell;
        SendAddonPayload(player, payload.str());
    }
    SendAddonPayload(player, "T|E");
}

void EnsureSubclassSkills(Player* player)
{
    if (!IsAdventurer(player))
        return;
    for (uint32 skillId : ADVENTURER_SUBCLASS_SKILLS)
        player->SetSkill(skillId, 1, 1, 1);
}

class AdventurerCollectionsScript final : public PlayerScript
{
public:
    AdventurerCollectionsScript() : PlayerScript("AdventurerCollectionsScript") { }

    void OnPlayerLogin(Player* player) override
    {
        EnsureSubclassSkills(player);
    }

    bool OnPlayerCanUseChat(
        Player* player,
        uint32 /*type*/,
        uint32 /*language*/,
        std::string& msg,
        Player* receiver) override
    {
        if (!IsAdventurer(player) || receiver != player || msg != TALENT_COLLECTION_REQUEST)
            return true;

        SendTalentCollection(player);
        return false;
    }
};
}

void AddAdventurerCollectionScripts()
{
    new AdventurerCollectionsScript();
}
