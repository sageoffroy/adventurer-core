#include "Chat.h"
#include "DatabaseEnv.h"
#include "Item.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "WorldSession.h"

#include <string>

namespace
{
constexpr uint32 GauntletItemMin = 911100;
constexpr uint32 GauntletItemMax = 911399;
constexpr char ProtocolPrefix[] = "AGBOOK|";

uint32 GetAccountId(Player* player)
{
    return player && player->GetSession() ? player->GetSession()->GetAccountId() : 0;
}

bool IsGauntletCollectionItem(uint32 entry)
{
    return entry >= GauntletItemMin && entry <= GauntletItemMax;
}

void DiscoverItem(Player* player, uint32 entry)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId || !IsGauntletCollectionItem(entry))
        return;

    CharacterDatabase.DirectExecute(
        "INSERT IGNORE INTO `adventurer_gauntlet_account_collection` "
        "(`account_id`, `item_entry`, `first_character_guid`) VALUES ({}, {}, {})",
        accountId,
        entry,
        player->GetGUID().GetCounter());
}

void SendCollectionState(Player* player)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId)
        return;

    ChatHandler handler(player->GetSession());
    handler.SendSysMessage("AGBOOK|OPEN");

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `item_entry` FROM `adventurer_gauntlet_account_collection` "
        "WHERE `account_id` = {} ORDER BY `item_entry`",
        accountId))
    {
        do
        {
            uint32 entry = result->Fetch()[0].Get<uint32>();
            if (IsGauntletCollectionItem(entry))
                handler.PSendSysMessage("AGBOOK|I|{}", entry);
        }
        while (result->NextRow());
    }

    handler.SendSysMessage("AGBOOK|DONE");
}

bool HandleCollectionCommand(Player* player, std::string const& rawMessage)
{
    if (!player)
        return false;

    std::string payload;
    std::string addonPrefix = "AGBOOK\t";
    if (rawMessage.rfind(addonPrefix, 0) == 0)
        payload = rawMessage.substr(addonPrefix.size());
    else if (rawMessage.rfind(ProtocolPrefix, 0) == 0)
        payload = rawMessage.substr(sizeof(ProtocolPrefix) - 1);
    else
        return false;

    if (payload == "REFRESH" || payload == "OPEN")
    {
        SendCollectionState(player);
        return true;
    }

    return false;
}
}

class AdventurerGauntletAccountCollectionPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletAccountCollectionPlayerScript()
        : PlayerScript("AdventurerGauntletAccountCollectionPlayerScript") { }

    void OnPlayerLootItem(Player* player, Item* item, uint32 /*count*/, ObjectGuid /*lootGuid*/) override
    {
        if (item)
            DiscoverItem(player, item->GetEntry());
    }

    void OnPlayerBeforeSendChatMessage(Player* player, uint32& /*type*/, uint32& lang, std::string& msg) override
    {
        if (player && lang == LANG_ADDON)
            HandleCollectionCommand(player, msg);
    }
};

void AddAdventurerGauntletAccountCollectionScripts()
{
    new AdventurerGauntletAccountCollectionPlayerScript();
}
