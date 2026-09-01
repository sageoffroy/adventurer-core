#include "Chat.h"
#include "Creature.h"
#include "DatabaseEnv.h"
#include "DBCStores.h"
#include "GameObject.h"
#include "GameObjectScript.h"
#include "Item.h"
#include "ObjectMgr.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "WorldSession.h"

#include <array>
#include <cmath>
#include <limits>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <vector>

namespace
{
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 AccountBankEntry = 910002;
constexpr uint32 BaseSlotCount = 28;
constexpr uint32 BankBagSlotCount = 7;
constexpr uint32 MaxBagCapacity = 36;
constexpr uint32 RangeCheckMs = 500;
constexpr float UseRange = 8.0f;
constexpr char ProtocolPrefix[] = "AGBANK|";

std::unordered_set<uint32> OpenBankPlayers;
std::unordered_map<uint32, uint32> RangeTimers;

struct StoredItem
{
    uint32 slot = 0;
    uint32 entry = 0;
    uint32 count = 0;
};

uint32 GetAccountId(Player* player)
{
    return player && player->GetSession() ? player->GetSession()->GetAccountId() : 0;
}

uint32 EncodeBagItemSlot(uint32 bagIndex, uint32 innerSlot)
{
    return BaseSlotCount + ((bagIndex - 1) * MaxBagCapacity) + innerSlot;
}

bool DecodeBagItemSlot(uint32 slot, uint32& bagIndex, uint32& innerSlot)
{
    if (slot <= BaseSlotCount)
        return false;

    uint32 offset = slot - BaseSlotCount - 1;
    bagIndex = (offset / MaxBagCapacity) + 1;
    innerSlot = (offset % MaxBagCapacity) + 1;
    return bagIndex >= 1 && bagIndex <= BankBagSlotCount;
}

bool IsEquipment(uint32 entry)
{
    ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
    if (!item)
        return false;

    if (item->Class != ITEM_CLASS_WEAPON && item->Class != ITEM_CLASS_ARMOR)
        return false;

    return item->InventoryType != INVTYPE_NON_EQUIP && item->InventoryType != INVTYPE_BAG;
}

bool IsBag(uint32 entry)
{
    ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
    return item && item->InventoryType == INVTYPE_BAG && item->ContainerSlots > 0;
}

uint32 GetBagCapacity(uint32 entry)
{
    ItemTemplate const* item = sObjectMgr->GetItemTemplate(entry);
    if (!item || item->InventoryType != INVTYPE_BAG)
        return 0;

    return std::min<uint32>(item->ContainerSlots, MaxBagCapacity);
}

uint32 GetPurchasedBagSlots(Player* player)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId)
        return 0;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `purchased_bag_slots` FROM `adventurer_gauntlet_account_bank` WHERE `account_id` = {}",
        accountId))
        return std::min<uint32>((*result)[0].Get<uint8>(), BankBagSlotCount);

    return 0;
}

void SetPurchasedBagSlots(Player* player, uint32 count)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId)
        return;

    CharacterDatabase.DirectExecute(
        "INSERT INTO `adventurer_gauntlet_account_bank` (`account_id`, `purchased_bag_slots`) VALUES ({}, {}) "
        "ON DUPLICATE KEY UPDATE `purchased_bag_slots` = VALUES(`purchased_bag_slots`)",
        accountId,
        std::min<uint32>(count, BankBagSlotCount));
}

uint32 GetInstalledBag(Player* player, uint32 bagIndex)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId || bagIndex < 1 || bagIndex > BankBagSlotCount)
        return 0;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `item_entry` FROM `adventurer_gauntlet_account_bank_bags` "
        "WHERE `account_id` = {} AND `bag_index` = {} LIMIT 1",
        accountId,
        bagIndex))
        return (*result)[0].Get<uint32>();

    return 0;
}

bool IsAccessibleItemSlot(Player* player, uint32 slot)
{
    if (slot >= 1 && slot <= BaseSlotCount)
        return true;

    uint32 bagIndex = 0;
    uint32 innerSlot = 0;
    if (!DecodeBagItemSlot(slot, bagIndex, innerSlot))
        return false;

    if (bagIndex > GetPurchasedBagSlots(player))
        return false;

    uint32 bagEntry = GetInstalledBag(player, bagIndex);
    return bagEntry && innerSlot <= GetBagCapacity(bagEntry);
}

bool GetStoredItem(Player* player, uint32 slot, StoredItem& item)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId || !IsAccessibleItemSlot(player, slot))
        return false;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `item_entry`, `item_count` FROM `adventurer_gauntlet_account_stash` "
        "WHERE `account_id` = {} AND `slot_index` = {} AND `item_count` > 0 LIMIT 1",
        accountId,
        slot))
    {
        Field* fields = result->Fetch();
        item = { slot, fields[0].Get<uint32>(), fields[1].Get<uint32>() };
        return true;
    }

    return false;
}

bool BagIsEmpty(Player* player, uint32 bagIndex)
{
    uint32 accountId = GetAccountId(player);
    uint32 bagEntry = GetInstalledBag(player, bagIndex);
    uint32 capacity = GetBagCapacity(bagEntry);
    if (!accountId || !capacity)
        return true;

    uint32 first = EncodeBagItemSlot(bagIndex, 1);
    uint32 last = EncodeBagItemSlot(bagIndex, capacity);
    if (QueryResult result = CharacterDatabase.Query(
        "SELECT 1 FROM `adventurer_gauntlet_account_stash` "
        "WHERE `account_id` = {} AND `slot_index` BETWEEN {} AND {} AND `item_count` > 0 LIMIT 1",
        accountId,
        first,
        last))
        return false;

    return true;
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

uint32 GetNextBagSlotPrice(Player* player)
{
    uint32 nextSlot = GetPurchasedBagSlots(player) + 1;
    if (nextSlot > BankBagSlotCount)
        return 0;

    if (BankBagSlotPricesEntry const* entry = sBankBagSlotPricesStore.LookupEntry(nextSlot))
        return entry->price;

    return 0;
}

void SendBankState(Player* player)
{
    if (!player || !player->GetSession())
        return;

    ChatHandler handler(player->GetSession());
    uint32 purchased = GetPurchasedBagSlots(player);
    uint32 price = GetNextBagSlotPrice(player);

    handler.SendSysMessage("AGBANK|OPEN");
    handler.PSendSysMessage("AGBANK|META|{}|{}", purchased, price);

    for (uint32 bagIndex = 1; bagIndex <= BankBagSlotCount; ++bagIndex)
    {
        uint32 entry = GetInstalledBag(player, bagIndex);
        if (entry)
            handler.PSendSysMessage("AGBANK|BAG|{}|{}|{}", bagIndex, entry, GetBagCapacity(entry));
    }

    uint32 accountId = GetAccountId(player);
    if (accountId)
    {
        if (QueryResult result = CharacterDatabase.Query(
            "SELECT `slot_index`, `item_entry`, `item_count` FROM `adventurer_gauntlet_account_stash` "
            "WHERE `account_id` = {} AND `item_count` > 0 ORDER BY `slot_index`",
            accountId))
        {
            do
            {
                Field* fields = result->Fetch();
                uint32 slot = fields[0].Get<uint32>();
                uint32 entry = fields[1].Get<uint32>();
                uint32 count = fields[2].Get<uint32>();
                if (IsAccessibleItemSlot(player, slot) && IsEquipment(entry))
                    handler.PSendSysMessage("AGBANK|ITEM|{}|{}|{}", slot, entry, count);
            }
            while (result->NextRow());
        }
    }

    handler.SendSysMessage("AGBANK|DONE");
}

void CloseBank(Player* player)
{
    if (!player || !player->GetSession())
        return;

    ChatHandler(player->GetSession()).SendSysMessage("AGBANK|CLOSE");
    uint32 guid = player->GetGUID().GetCounter();
    OpenBankPlayers.erase(guid);
    RangeTimers.erase(guid);
}

bool DepositItem(Player* player, uint32 entry, uint32 slot)
{
    if (!player || !IsEquipment(entry) || !IsAccessibleItemSlot(player, slot))
        return false;

    StoredItem occupied;
    if (GetStoredItem(player, slot, occupied))
        return false;

    if (player->GetItemCount(entry, false) == 0)
        return false;

    player->DestroyItemCount(entry, 1, true, true);
    RefreshEquipmentVisuals(player);

    CharacterDatabase.DirectExecute(
        "INSERT INTO `adventurer_gauntlet_account_stash` "
        "(`account_id`, `slot_index`, `item_entry`, `item_count`) VALUES ({}, {}, {}, 1)",
        GetAccountId(player),
        slot,
        entry);
    return true;
}

bool WithdrawItem(Player* player, uint32 slot)
{
    StoredItem stored;
    if (!player || !GetStoredItem(player, slot, stored) || !IsEquipment(stored.entry))
        return false;

    ItemPosCountVec dest;
    if (player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, stored.entry, 1) != EQUIP_ERR_OK)
        return false;

    if (!player->StoreNewItem(dest, stored.entry, true))
        return false;

    CharacterDatabase.DirectExecute(
        "DELETE FROM `adventurer_gauntlet_account_stash` WHERE `account_id` = {} AND `slot_index` = {}",
        GetAccountId(player),
        slot);
    return true;
}

bool InstallBag(Player* player, uint32 bagIndex, uint32 entry)
{
    if (!player || bagIndex < 1 || bagIndex > GetPurchasedBagSlots(player) || !IsBag(entry))
        return false;

    if (GetInstalledBag(player, bagIndex) || player->GetItemCount(entry, false) == 0)
        return false;

    player->DestroyItemCount(entry, 1, true, true);
    CharacterDatabase.DirectExecute(
        "INSERT INTO `adventurer_gauntlet_account_bank_bags` (`account_id`, `bag_index`, `item_entry`) "
        "VALUES ({}, {}, {})",
        GetAccountId(player),
        bagIndex,
        entry);
    return true;
}

bool RemoveBag(Player* player, uint32 bagIndex)
{
    uint32 entry = GetInstalledBag(player, bagIndex);
    if (!player || !entry || !BagIsEmpty(player, bagIndex))
        return false;

    ItemPosCountVec dest;
    if (player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, entry, 1) != EQUIP_ERR_OK)
        return false;

    if (!player->StoreNewItem(dest, entry, true))
        return false;

    CharacterDatabase.DirectExecute(
        "DELETE FROM `adventurer_gauntlet_account_bank_bags` WHERE `account_id` = {} AND `bag_index` = {}",
        GetAccountId(player),
        bagIndex);
    return true;
}

bool BuyBagSlot(Player* player)
{
    if (!player)
        return false;

    uint32 purchased = GetPurchasedBagSlots(player);
    if (purchased >= BankBagSlotCount)
        return false;

    uint32 price = GetNextBagSlotPrice(player);
    if (!price || !player->HasEnoughMoney(price))
        return false;

    player->ModifyMoney(-static_cast<int32>(price));
    SetPurchasedBagSlots(player, purchased + 1);
    return true;
}

uint32 ParseNumber(std::string const& value)
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

bool ParsePair(std::string const& value, uint32& first, uint32& second)
{
    size_t separator = value.find('|');
    if (separator == std::string::npos)
        return false;

    first = ParseNumber(value.substr(0, separator));
    second = ParseNumber(value.substr(separator + 1));
    return first != 0 && second != 0;
}

bool HandleBankCommand(Player* player, std::string const& rawMessage)
{
    if (!player)
        return false;

    std::string addonPrefix = "AGBANK\t";
    if (rawMessage.rfind(addonPrefix, 0) != 0)
        return false;

    std::string payload = rawMessage.substr(addonPrefix.size());
    if (payload == "BUY")
        BuyBagSlot(player);
    else if (payload == "REFRESH")
    {
    }
    else if (payload.rfind("DEPOSIT|", 0) == 0)
    {
        uint32 entry = 0;
        uint32 slot = 0;
        if (ParsePair(payload.substr(8), entry, slot))
            DepositItem(player, entry, slot);
    }
    else if (payload.rfind("WITHDRAW|", 0) == 0)
        WithdrawItem(player, ParseNumber(payload.substr(9)));
    else if (payload.rfind("INSTALLBAG|", 0) == 0)
    {
        uint32 bagIndex = 0;
        uint32 entry = 0;
        if (ParsePair(payload.substr(11), bagIndex, entry))
            InstallBag(player, bagIndex, entry);
    }
    else if (payload.rfind("REMOVEBAG|", 0) == 0)
        RemoveBag(player, ParseNumber(payload.substr(10)));
    else
        return false;

    SendBankState(player);
    return true;
}

void EnsureAccountBank(Creature* khadgar)
{
    if (!khadgar || khadgar->FindNearestGameObject(AccountBankEntry, 8.0f))
        return;

    constexpr float HalfPi = 1.57079632679f;
    float angle = khadgar->GetOrientation() + HalfPi;
    khadgar->SummonGameObject(
        AccountBankEntry,
        khadgar->GetPositionX() + std::cos(angle) * 2.5f,
        khadgar->GetPositionY() + std::sin(angle) * 2.5f,
        khadgar->GetPositionZ(),
        khadgar->GetOrientation(),
        0.0f,
        0.0f,
        0.0f,
        1.0f,
        0);
}
}

class go_adventurer_gauntlet_account_bank : public GameObjectScript
{
public:
    go_adventurer_gauntlet_account_bank()
        : GameObjectScript("go_adventurer_gauntlet_account_bank") { }

    bool OnGossipHello(Player* player, GameObject* /*go*/) override
    {
        if (player)
        {
            uint32 guid = player->GetGUID().GetCounter();
            OpenBankPlayers.insert(guid);
            RangeTimers[guid] = RangeCheckMs;
        }
        SendBankState(player);
        return true;
    }
};

class AdventurerGauntletAccountBankKhadgarScript : public AllCreatureScript
{
public:
    AdventurerGauntletAccountBankKhadgarScript()
        : AllCreatureScript("AdventurerGauntletAccountBankKhadgarScript") { }

    void OnCreatureAddWorld(Creature* creature) override
    {
        if (creature && creature->GetEntry() == KhadgarEntry)
            EnsureAccountBank(creature);
    }
};

class AdventurerGauntletAccountBankPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletAccountBankPlayerScript()
        : PlayerScript("AdventurerGauntletAccountBankPlayerScript") { }

    void OnPlayerBeforeSendChatMessage(Player* player, uint32& /*type*/, uint32& lang, std::string& msg) override
    {
        if (player && lang == LANG_ADDON)
            HandleBankCommand(player, msg);
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        if (!player)
            return;

        uint32 guid = player->GetGUID().GetCounter();
        if (!OpenBankPlayers.contains(guid))
            return;

        uint32& timer = RangeTimers[guid];
        if (timer > diff)
        {
            timer -= diff;
            return;
        }
        timer = RangeCheckMs;

        if (!player->FindNearestGameObject(AccountBankEntry, UseRange))
            CloseBank(player);
    }

    void OnPlayerLogout(Player* player) override
    {
        if (!player)
            return;

        uint32 guid = player->GetGUID().GetCounter();
        OpenBankPlayers.erase(guid);
        RangeTimers.erase(guid);
    }
};

void AddAdventurerGauntletAccountBankScripts()
{
    new go_adventurer_gauntlet_account_bank();
    new AdventurerGauntletAccountBankKhadgarScript();
    new AdventurerGauntletAccountBankPlayerScript();
}
