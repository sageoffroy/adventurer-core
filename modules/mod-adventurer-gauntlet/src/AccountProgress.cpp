#include "Chat.h"
#include "DatabaseEnv.h"
#include "Item.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "WorldSession.h"

#include <unordered_set>

namespace
{
constexpr uint32 GauntletItemMin = 911000;
constexpr uint32 GauntletItemMax = 911999;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;

std::unordered_set<uint32> ActiveGauntletParticipants;

bool IsGauntletMap(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

bool IsGauntletItem(uint32 entry)
{
    return entry >= GauntletItemMin && entry <= GauntletItemMax;
}

uint32 GetAccountCollectionCount(Player* player)
{
    if (!player)
        return 0;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT COUNT(*) FROM `adventurer_gauntlet_account_items` WHERE `account_id` = {}",
        player->GetSession()->GetAccountId()))
        return (*result)[0].Get<uint32>();

    return 0;
}

bool IsFallen(Player* player)
{
    if (!player)
        return false;

    return bool(CharacterDatabase.Query(
        "SELECT 1 FROM `adventurer_gauntlet_fallen` WHERE `guid` = {} LIMIT 1",
        player->GetGUID().GetCounter()));
}

bool MarkFallen(Player* player)
{
    if (!player || IsFallen(player))
        return false;

    uint32 guid = player->GetGUID().GetCounter();
    uint32 accountId = player->GetSession()->GetAccountId();

    CharacterDatabase.Execute(
        "INSERT IGNORE INTO `adventurer_gauntlet_fallen` "
        "(`guid`, `account_id`, `map_id`, `level`) VALUES ({}, {}, {}, {})",
        guid,
        accountId,
        player->GetMapId(),
        player->GetLevel());

    ActiveGauntletParticipants.erase(guid);

    ChatHandler(player->GetSession()).SendSysMessage(
        "|cffff2020Este Aventurero ha quedado CAIDO permanentemente.|r");
    ChatHandler(player->GetSession()).SendSysMessage(
        "Su coleccion de cuenta permanece intacta, pero este personaje no puede iniciar otra expedicion.");
    return true;
}

void UnlockAccountItem(Player* player, Item* item)
{
    if (!player || !item || !IsGauntletItem(item->GetEntry()))
        return;

    uint32 accountId = player->GetSession()->GetAccountId();
    uint32 entry = item->GetEntry();

    if (CharacterDatabase.Query(
        "SELECT 1 FROM `adventurer_gauntlet_account_items` WHERE `account_id` = {} AND `item_entry` = {} LIMIT 1",
        accountId,
        entry))
        return;

    CharacterDatabase.Execute(
        "INSERT IGNORE INTO `adventurer_gauntlet_account_items` "
        "(`account_id`, `item_entry`, `first_character_guid`) VALUES ({}, {}, {})",
        accountId,
        entry,
        player->GetGUID().GetCounter());

    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cff00ff00Coleccion de Expediciones:|r has descubierto |cff0070dd{}|r.",
        item->GetTemplate()->Name1);
}
}

class AdventurerGauntletAccountProgressScript : public PlayerScript
{
public:
    AdventurerGauntletAccountProgressScript()
        : PlayerScript("AdventurerGauntletAccountProgressScript") { }

    void OnPlayerLogin(Player* player) override
    {
        if (!player)
            return;

        ChatHandler(player->GetSession()).PSendSysMessage(
            "|cff00ff00Coleccion de Expediciones:|r {} pieza(s) descubierta(s) en esta cuenta.",
            GetAccountCollectionCount(player));

        if (IsFallen(player))
        {
            ChatHandler(player->GetSession()).SendSysMessage(
                "|cffff2020Este personaje figura como CAIDO en el Desafio de Khadgar.|r");
            ChatHandler(player->GetSession()).SendSysMessage(
                "Puedes conservarlo como recuerdo, pero no puede volver a participar.");
            return;
        }

        if (IsGauntletMap(player->GetMapId()))
            ActiveGauntletParticipants.insert(player->GetGUID().GetCounter());
    }

    void OnPlayerLogout(Player* player) override
    {
        if (player)
            ActiveGauntletParticipants.erase(player->GetGUID().GetCounter());
    }

    bool OnPlayerBeforeTeleport(Player* player, uint32 mapId, float /*x*/, float /*y*/, float /*z*/, float /*orientation*/, uint32 options, Unit* /*target*/) override
    {
        if (!player || !IsGauntletMap(mapId))
            return true;

        if (IsFallen(player))
        {
            ChatHandler(player->GetSession()).SendSysMessage(
                "|cffff2020Khadgar niega el portal: este Aventurero ya ha caido.|r");
            return false;
        }

        if (options & TELE_TO_GM_MODE)
            ActiveGauntletParticipants.insert(player->GetGUID().GetCounter());

        return true;
    }

    void OnPlayerJustDied(Player* player) override
    {
        if (!player)
            return;

        uint32 guid = player->GetGUID().GetCounter();
        if (ActiveGauntletParticipants.find(guid) == ActiveGauntletParticipants.end())
            return;

        MarkFallen(player);
    }

    void OnPlayerResurrect(Player* player, float /*restorePercent*/, bool& /*applySickness*/) override
    {
        if (!player)
            return;

        uint32 guid = player->GetGUID().GetCounter();
        if (ActiveGauntletParticipants.find(guid) != ActiveGauntletParticipants.end())
            MarkFallen(player);
    }

    void OnPlayerStoreNewItem(Player* player, Item* item, uint32 /*count*/) override
    {
        UnlockAccountItem(player, item);
    }
};

void AddAdventurerGauntletAccountProgressScripts()
{
    new AdventurerGauntletAccountProgressScript();
}
