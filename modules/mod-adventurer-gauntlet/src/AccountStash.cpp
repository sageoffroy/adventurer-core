#include "Chat.h"
#include "Creature.h"
#include "DatabaseEnv.h"
#include "GameObject.h"
#include "GameObjectScript.h"
#include "Item.h"
#include "ObjectMgr.h"
#include "Player.h"
#include "ScriptMgr.h"
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
constexpr char ProtocolPrefix[] = "AGSTASH|";

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

void RefreshEquipmentVisuals(Player* player)
{
    if (!player)
        return;

    for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
        player->SetVisibleItemSlot(slot, player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot));

    player->SetVirtualItemSlot(0, player->GetWeaponForAttack(BASE_ATTACK, true));
    player->SetVirtualItemSlot(1, player->GetWeaponForAttack(OFF_ATTACK, true));
    player->SetVirtualItemSlot(2, player->GetWeaponForAttack(RANGED_ATTACK, true));
}

std::vector<std::pair<uint32, uint32>> GetCarriedAccountItems(Player* player)
{
    std::vector<std::pair<uint32, uint32>> items;
    if (!player)
        return items;

    for (uint32 entry = GauntletItemMin; entry <= GauntletItemMax; ++entry)
    {
        uint32 count = player->GetItemCount(entry, false);
        if (count)
            items.emplace_back(entry, count);
    }

    return items;
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

void SendStashState(Player* player)
{
    if (!player || !player->GetSession())
        return;

    ChatHandler handler(player->GetSession());
    handler.SendSysMessage("AGSTASH|OPEN");

    for (auto const& [entry, count] : GetCarriedAccountItems(player))
        handler.PSendSysMessage("AGSTASH|B|{}|{}", entry, count);

    for (auto const& [entry, count] : GetStashItems(player))
        if (IsGauntletAccountItem(entry) && count)
            handler.PSendSysMessage("AGSTASH|S|{}|{}", entry, count);

    handler.SendSysMessage("AGSTASH|DONE");
}

bool DepositOne(Player* player, uint32 entry)
{
    if (!player || !IsGauntletAccountItem(entry) || player->GetItemCount(entry, false) == 0)
        return false;

    player->DestroyItemCount(entry, 1, true, true);
    RefreshEquipmentVisuals(player);

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
    for (auto const& [entry, carried] : GetCarriedAccountItems(player))
    {
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

    RefreshEquipmentVisuals(player);

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

uint32 ParseEntry(std::string const& value)
{
    try
    {
        size_t consumed = 0;
        unsigned long parsed = std::stoul(value, &consumed, 10);
        if (consumed != value.size() || parsed > GauntletItemMax)
            return 0;
        return static_cast<uint32>(parsed);
    }
    catch (...)
    {
        return 0;
    }
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

bool HandleAdventurerGauntletStashAddonCommand(Player* player, std::string const& rawMessage)
{
    if (!player)
        return false;

    std::string payload;
    std::string addonPrefix = "AGSTASH\t";
    if (rawMessage.rfind(addonPrefix, 0) == 0)
        payload = rawMessage.substr(addonPrefix.size());
    else if (rawMessage.rfind(ProtocolPrefix, 0) == 0)
        payload = rawMessage.substr(sizeof(ProtocolPrefix) - 1);
    else
        return false;

    if (payload == "REFRESH")
    {
        SendStashState(player);
        return true;
    }

    if (payload == "DEPOSITALL")
    {
        DepositAll(player);
        SendStashState(player);
        return true;
    }

    constexpr char DepositPrefix[] = "DEPOSIT|";
    if (payload.rfind(DepositPrefix, 0) == 0)
    {
        uint32 entry = ParseEntry(payload.substr(sizeof(DepositPrefix) - 1));
        if (entry)
            DepositOne(player, entry);
        SendStashState(player);
        return true;
    }

    constexpr char WithdrawPrefix[] = "WITHDRAW|";
    if (payload.rfind(WithdrawPrefix, 0) == 0)
    {
        uint32 entry = ParseEntry(payload.substr(sizeof(WithdrawPrefix) - 1));
        if (entry)
            WithdrawOne(player, entry);
        SendStashState(player);
        return true;
    }

    return false;
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

    bool OnGossipHello(Player* player, GameObject* /*go*/) override
    {
        SendStashState(player);
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
