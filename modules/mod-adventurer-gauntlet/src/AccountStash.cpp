#include "Chat.h"
#include "Creature.h"
#include "DatabaseEnv.h"
#include "GameObject.h"
#include "GameObjectScript.h"
#include "Item.h"
#include "ObjectMgr.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "ScriptedGossip.h"
#include "WorldSession.h"

#include <cmath>
#include <string>
#include <utility>
#include <vector>

namespace
{
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 AccountStashEntry = 910002;
constexpr uint32 GauntletItemMin = 911000;
constexpr uint32 GauntletItemMax = 911999;

constexpr uint32 ActionDepositAll = 10;
constexpr uint32 ActionRefresh = 11;
constexpr uint32 ActionClose = 12;
constexpr uint32 ActionDepositBase = 1000000;
constexpr uint32 ActionWithdrawBase = 2000000;

bool IsGauntletAccountItem(uint32 entry)
{
    return entry >= GauntletItemMin && entry <= GauntletItemMax;
}

uint32 GetAccountId(Player* player)
{
    return player && player->GetSession() ? player->GetSession()->GetAccountId() : 0;
}

std::string GetItemName(uint32 entry)
{
    if (ItemTemplate const* itemTemplate = sObjectMgr->GetItemTemplate(entry))
        return itemTemplate->Name1;

    return std::string("Objeto ") + std::to_string(entry);
}

std::vector<std::pair<uint32, uint32>> GetStashItems(Player* player)
{
    std::vector<std::pair<uint32, uint32>> items;
    uint32 accountId = GetAccountId(player);
    if (!accountId)
        return items;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `item_entry`, `item_count` FROM `adventurer_gauntlet_account_stash` "
        "WHERE `account_id` = {} AND `item_count` > 0 ORDER BY `item_entry`",
        accountId))
    {
        do
        {
            Field* fields = result->Fetch();
            items.emplace_back(fields[0].Get<uint32>(), fields[1].Get<uint32>());
        }
        while (result->NextRow());
    }

    return items;
}

std::vector<uint32> GetDiscoveredAccountItems(Player* player)
{
    std::vector<uint32> items;
    uint32 accountId = GetAccountId(player);
    if (!accountId)
        return items;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `item_entry` FROM `adventurer_gauntlet_account_items` "
        "WHERE `account_id` = {} ORDER BY `item_entry`",
        accountId))
    {
        do
            items.push_back(result->Fetch()[0].Get<uint32>());
        while (result->NextRow());
    }

    return items;
}

uint32 GetStashItemCount(Player* player, uint32 entry)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId || !IsGauntletAccountItem(entry))
        return 0;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `item_count` FROM `adventurer_gauntlet_account_stash` "
        "WHERE `account_id` = {} AND `item_entry` = {} LIMIT 1",
        accountId,
        entry))
        return (*result)[0].Get<uint32>();

    return 0;
}

void RemoveOneFromStash(Player* player, uint32 entry)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId || !IsGauntletAccountItem(entry))
        return;

    CharacterDatabase.Execute(
        "UPDATE `adventurer_gauntlet_account_stash` SET `item_count` = `item_count` - 1 "
        "WHERE `account_id` = {} AND `item_entry` = {} AND `item_count` > 0",
        accountId,
        entry);
    CharacterDatabase.Execute(
        "DELETE FROM `adventurer_gauntlet_account_stash` "
        "WHERE `account_id` = {} AND `item_entry` = {} AND `item_count` = 0",
        accountId,
        entry);
}

void ShowStashMenu(Player* player, GameObject* go)
{
    if (!player || !go)
        return;

    ClearGossipMenuFor(player);

    bool hasDeposit = false;
    for (uint32 entry : GetDiscoveredAccountItems(player))
    {
        if (!IsGauntletAccountItem(entry))
            continue;

        uint32 carried = player->GetItemCount(entry, false);
        if (!carried)
            continue;

        hasDeposit = true;
        AddGossipItemFor(
            player,
            GOSSIP_ICON_CHAT,
            "Guardar: " + GetItemName(entry) + " (x" + std::to_string(carried) + ")",
            GOSSIP_SENDER_MAIN,
            ActionDepositBase + entry);
    }

    if (hasDeposit)
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Guardar todos los objetos de cuenta", GOSSIP_SENDER_MAIN, ActionDepositAll);

    bool hasWithdrawal = false;
    for (auto const& [entry, count] : GetStashItems(player))
    {
        if (!IsGauntletAccountItem(entry) || !count)
            continue;

        hasWithdrawal = true;
        AddGossipItemFor(
            player,
            GOSSIP_ICON_CHAT,
            "Retirar: " + GetItemName(entry) + " (x" + std::to_string(count) + ")",
            GOSSIP_SENDER_MAIN,
            ActionWithdrawBase + entry);
    }

    if (!hasDeposit && !hasWithdrawal)
        AddGossipItemFor(player, GOSSIP_ICON_CHAT, "El baul esta vacio.", GOSSIP_SENDER_MAIN, ActionRefresh);

    AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Actualizar", GOSSIP_SENDER_MAIN, ActionRefresh);
    AddGossipItemFor(player, GOSSIP_ICON_CHAT, "Cerrar", GOSSIP_SENDER_MAIN, ActionClose);
    SendGossipMenuFor(player, DEFAULT_GOSSIP_MESSAGE, go->GetGUID());
}

bool DepositOne(Player* player, uint32 entry)
{
    if (!player || !IsGauntletAccountItem(entry) || player->GetItemCount(entry, false) == 0)
        return false;

    player->DestroyItemCount(entry, 1, true, true);
    CharacterDatabase.Execute(
        "INSERT INTO `adventurer_gauntlet_account_stash` (`account_id`, `item_entry`, `item_count`) "
        "VALUES ({}, {}, 1) ON DUPLICATE KEY UPDATE `item_count` = `item_count` + 1",
        GetAccountId(player),
        entry);

    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cff00ff00Baul de Expediciones:|r guardaste |cff0070dd{}|r.",
        GetItemName(entry));
    return true;
}

void DepositAll(Player* player)
{
    if (!player)
        return;

    uint32 deposited = 0;
    for (uint32 entry : GetDiscoveredAccountItems(player))
    {
        if (!IsGauntletAccountItem(entry))
            continue;

        uint32 carried = player->GetItemCount(entry, false);
        if (!carried)
            continue;

        player->DestroyItemCount(entry, carried, true, true);
        CharacterDatabase.Execute(
            "INSERT INTO `adventurer_gauntlet_account_stash` (`account_id`, `item_entry`, `item_count`) "
            "VALUES ({}, {}, {}) ON DUPLICATE KEY UPDATE `item_count` = `item_count` + {}",
            GetAccountId(player),
            entry,
            carried,
            carried);
        deposited += carried;
    }

    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cff00ff00Baul de Expediciones:|r guardaste {} objeto(s) de cuenta.",
        deposited);
}

bool WithdrawOne(Player* player, uint32 entry)
{
    if (!player || !IsGauntletAccountItem(entry) || !GetStashItemCount(player, entry))
        return false;

    ItemPosCountVec dest;
    InventoryResult result = player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, entry, 1);
    if (result != EQUIP_ERR_OK)
    {
        ChatHandler(player->GetSession()).SendSysMessage("No tienes espacio para retirar ese objeto.");
        return false;
    }

    Item* item = player->StoreNewItem(dest, entry, true);
    if (!item)
        return false;

    RemoveOneFromStash(player, entry);
    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cff00ff00Baul de Expediciones:|r retiraste |cff0070dd{}|r.",
        GetItemName(entry));
    return true;
}
}

void AddAdventurerGauntletAccountStashItem(Player* player, uint32 entry, uint32 count)
{
    if (!player || !count || !IsGauntletAccountItem(entry))
        return;

    CharacterDatabase.Execute(
        "INSERT INTO `adventurer_gauntlet_account_stash` (`account_id`, `item_entry`, `item_count`) "
        "VALUES ({}, {}, {}) ON DUPLICATE KEY UPDATE `item_count` = `item_count` + {}",
        GetAccountId(player),
        entry,
        count,
        count);
}

uint32 GetAdventurerGauntletAccountStashTotal(Player* player)
{
    if (!player)
        return 0;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT COALESCE(SUM(`item_count`), 0) FROM `adventurer_gauntlet_account_stash` WHERE `account_id` = {}",
        GetAccountId(player)))
        return (*result)[0].Get<uint32>();

    return 0;
}

void EnsureAdventurerGauntletAccountStash(Creature* khadgar)
{
    if (!khadgar)
        return;

    if (khadgar->FindNearestGameObject(AccountStashEntry, 8.0f))
        return;

    constexpr float HalfPi = 1.57079632679f;
    float angle = khadgar->GetOrientation() + HalfPi;
    float x = khadgar->GetPositionX() + std::cos(angle) * 2.5f;
    float y = khadgar->GetPositionY() + std::sin(angle) * 2.5f;

    khadgar->SummonGameObject(
        AccountStashEntry,
        x,
        y,
        khadgar->GetPositionZ(),
        khadgar->GetOrientation(),
        0.0f,
        0.0f,
        0.0f,
        1.0f,
        0);
}

class go_adventurer_gauntlet_account_stash : public GameObjectScript
{
public:
    go_adventurer_gauntlet_account_stash()
        : GameObjectScript("go_adventurer_gauntlet_account_stash") { }

    bool OnGossipHello(Player* player, GameObject* go) override
    {
        ShowStashMenu(player, go);
        return true;
    }

    bool OnGossipSelect(Player* player, GameObject* go, uint32 /*sender*/, uint32 action) override
    {
        ClearGossipMenuFor(player);

        if (action == ActionClose)
        {
            CloseGossipMenuFor(player);
            return true;
        }

        if (action == ActionRefresh)
        {
            ShowStashMenu(player, go);
            return true;
        }

        if (action == ActionDepositAll)
        {
            DepositAll(player);
            ShowStashMenu(player, go);
            return true;
        }

        if (action >= ActionWithdrawBase + GauntletItemMin && action <= ActionWithdrawBase + GauntletItemMax)
        {
            WithdrawOne(player, action - ActionWithdrawBase);
            ShowStashMenu(player, go);
            return true;
        }

        if (action >= ActionDepositBase + GauntletItemMin && action <= ActionDepositBase + GauntletItemMax)
        {
            DepositOne(player, action - ActionDepositBase);
            ShowStashMenu(player, go);
            return true;
        }

        ShowStashMenu(player, go);
        return true;
    }
};

class AdventurerGauntletAccountStashKhadgarScript : public AllCreatureScript
{
public:
    AdventurerGauntletAccountStashKhadgarScript()
        : AllCreatureScript("AdventurerGauntletAccountStashKhadgarScript") { }

    void OnCreatureAddWorld(Creature* creature) override
    {
        if (creature && creature->GetEntry() == KhadgarEntry)
            EnsureAdventurerGauntletAccountStash(creature);
    }
};

void AddAdventurerGauntletAccountStashScripts()
{
    new go_adventurer_gauntlet_account_stash();
    new AdventurerGauntletAccountStashKhadgarScript();
}
