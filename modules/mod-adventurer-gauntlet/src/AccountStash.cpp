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
#include <limits>
#include <string>
#include <utility>
#include <vector>

namespace
{
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 AccountStashEntry = 910002;
constexpr char ProtocolPrefix[] = "AGSTASH|";

uint32 GetAccountId(Player* player)
{
    return player && player->GetSession() ? player->GetSession()->GetAccountId() : 0;
}

bool IsStashableItem(uint32 entry)
{
    ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
    if (!item)
        return false;

    if (item->Class != ITEM_CLASS_WEAPON && item->Class != ITEM_CLASS_ARMOR)
        return false;

    return item->InventoryType != INVTYPE_NON_EQUIP && item->InventoryType != INVTYPE_BAG;
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
    if (!accountId || !IsStashableItem(entry))
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
    if (!accountId || !IsStashableItem(entry))
        return;

    CharacterDatabase.DirectExecute(
        "UPDATE `adventurer_gauntlet_account_stash` SET `item_count` = `item_count` - 1 "
        "WHERE `account_id` = {} AND `item_entry` = {} AND `item_count` > 0",
        accountId,
        entry);
    CharacterDatabase.DirectExecute(
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

    for (auto const& [entry, count] : GetStashItems(player))
        if (IsStashableItem(entry) && count)
            handler.PSendSysMessage("AGSTASH|S|{}|{}", entry, count);

    handler.SendSysMessage("AGSTASH|DONE");
}

bool DepositOne(Player* player, uint32 entry)
{
    if (!player || !IsStashableItem(entry))
    {
        if (player)
            ChatHandler(player->GetSession()).SendSysMessage(
                "El Baul de Expediciones solo acepta armas y armaduras equipables.");
        return false;
    }

    if (player->GetItemCount(entry, false) == 0)
        return false;

    player->DestroyItemCount(entry, 1, true, true);
    RefreshEquipmentVisuals(player);

    // The UI refreshes immediately after a deposit. Keep this write synchronous so
    // the snapshot sent below already contains the newly secured item.
    CharacterDatabase.DirectExecute(
        "INSERT INTO `adventurer_gauntlet_account_stash` (`account_id`, `item_entry`, `item_count`) "
        "VALUES ({}, {}, 1) ON DUPLICATE KEY UPDATE `item_count` = `item_count` + 1",
        GetAccountId(player),
        entry);

    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cff00ff00Baul de Expediciones:|r aseguraste |cff0070dd{}|r.",
        GetItemName(entry));
    return true;
}

bool WithdrawOne(Player* player, uint32 entry)
{
    if (!player || !IsStashableItem(entry) || !GetStashItemCount(player, entry))
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
        if (consumed != value.size() || parsed > std::numeric_limits<uint32>::max())
            return 0;
        return static_cast<uint32>(parsed);
    }
    catch (...)
    {
        return 0;
    }
}
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
