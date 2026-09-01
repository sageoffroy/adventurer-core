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

#include <array>
#include <cmath>
#include <limits>
#include <string>
#include <unordered_map>
#include <unordered_set>
#include <utility>
#include <vector>

namespace
{
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 AccountStashEntry = 910002;
constexpr uint32 AccountStashSlots = 28;
constexpr uint32 StashRangeCheckMs = 500;
constexpr float StashUseRange = 8.0f;
constexpr char ProtocolPrefix[] = "AGSTASH|";

std::unordered_set<uint32> OpenStashPlayers;
std::unordered_map<uint32, uint32> StashRangeTimers;

struct StashItem
{
    uint32 slot = 0;
    uint32 entry = 0;
    uint32 count = 0;
};

uint32 GetAccountId(Player* player)
{
    return player && player->GetSession() ? player->GetSession()->GetAccountId() : 0;
}

bool IsValidStashSlot(uint32 slot)
{
    return slot >= 1 && slot <= AccountStashSlots;
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

std::vector<StashItem> GetStashItems(Player* player)
{
    std::vector<StashItem> items;
    uint32 accountId = GetAccountId(player);
    if (!accountId)
        return items;

    if (QueryResult result = CharacterDatabase.Query(
        "SELECT `slot_index`, `item_entry`, `item_count` FROM `adventurer_gauntlet_account_stash` "
        "WHERE `account_id` = {} AND `item_count` > 0 ORDER BY `slot_index`",
        accountId))
    {
        do
        {
            Field* fields = result->Fetch();
            items.push_back({ fields[0].Get<uint32>(), fields[1].Get<uint32>(), fields[2].Get<uint32>() });
        }
        while (result->NextRow());
    }

    return items;
}

bool GetStashItemAtSlot(Player* player, uint32 slot, StashItem& item)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId || !IsValidStashSlot(slot))
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

uint32 FindFirstFreeStashSlot(Player* player)
{
    std::array<bool, AccountStashSlots + 1> used{};
    for (StashItem const& item : GetStashItems(player))
        if (IsValidStashSlot(item.slot))
            used[item.slot] = true;

    for (uint32 slot = 1; slot <= AccountStashSlots; ++slot)
        if (!used[slot])
            return slot;

    return 0;
}

void RemoveOneFromStashSlot(Player* player, uint32 slot)
{
    uint32 accountId = GetAccountId(player);
    if (!accountId || !IsValidStashSlot(slot))
        return;

    CharacterDatabase.DirectExecute(
        "UPDATE `adventurer_gauntlet_account_stash` SET `item_count` = `item_count` - 1 "
        "WHERE `account_id` = {} AND `slot_index` = {} AND `item_count` > 0",
        accountId,
        slot);
    CharacterDatabase.DirectExecute(
        "DELETE FROM `adventurer_gauntlet_account_stash` "
        "WHERE `account_id` = {} AND `slot_index` = {} AND `item_count` = 0",
        accountId,
        slot);
}

void SendStashState(Player* player)
{
    if (!player || !player->GetSession())
        return;

    ChatHandler handler(player->GetSession());
    handler.SendSysMessage("AGSTASH|OPEN");

    for (StashItem const& item : GetStashItems(player))
        if (IsValidStashSlot(item.slot) && IsStashableItem(item.entry) && item.count)
            handler.PSendSysMessage("AGSTASH|S|{}|{}|{}", item.slot, item.entry, item.count);

    handler.SendSysMessage("AGSTASH|DONE");
}

void CloseStash(Player* player)
{
    if (!player || !player->GetSession())
        return;

    ChatHandler(player->GetSession()).SendSysMessage("AGSTASH|CLOSE");
    uint32 guid = player->GetGUID().GetCounter();
    OpenStashPlayers.erase(guid);
    StashRangeTimers.erase(guid);
}

bool DepositOne(Player* player, uint32 entry, uint32 targetSlot)
{
    if (!player || !IsStashableItem(entry))
    {
        if (player)
            ChatHandler(player->GetSession()).SendSysMessage(
                "El Baul de Expediciones solo acepta armas y armaduras equipables.");
        return false;
    }

    if (!IsValidStashSlot(targetSlot))
    {
        ChatHandler(player->GetSession()).SendSysMessage("Esa casilla del Baul de Expediciones no existe.");
        return false;
    }

    StashItem occupied;
    if (GetStashItemAtSlot(player, targetSlot, occupied))
    {
        ChatHandler(player->GetSession()).SendSysMessage("Esa casilla del Baul de Expediciones ya esta ocupada.");
        return false;
    }

    if (player->GetItemCount(entry, false) == 0)
        return false;

    player->DestroyItemCount(entry, 1, true, true);
    RefreshEquipmentVisuals(player);

    CharacterDatabase.DirectExecute(
        "INSERT INTO `adventurer_gauntlet_account_stash` "
        "(`account_id`, `slot_index`, `item_entry`, `item_count`) VALUES ({}, {}, {}, 1)",
        GetAccountId(player),
        targetSlot,
        entry);

    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cff00ff00Baul de Expediciones:|r aseguraste |cff0070dd{}|r.",
        GetItemName(entry));
    return true;
}

bool WithdrawOne(Player* player, uint32 sourceSlot)
{
    StashItem stashItem;
    if (!player || !GetStashItemAtSlot(player, sourceSlot, stashItem) || !IsStashableItem(stashItem.entry))
        return false;

    ItemPosCountVec dest;
    InventoryResult result = player->CanStoreNewItem(NULL_BAG, NULL_SLOT, dest, stashItem.entry, 1);
    if (result != EQUIP_ERR_OK)
    {
        ChatHandler(player->GetSession()).SendSysMessage("No tienes espacio para retirar ese objeto.");
        return false;
    }

    Item* item = player->StoreNewItem(dest, stashItem.entry, true);
    if (!item)
        return false;

    RemoveOneFromStashSlot(player, sourceSlot);
    ChatHandler(player->GetSession()).PSendSysMessage(
        "|cff00ff00Baul de Expediciones:|r retiraste |cff0070dd{}|r.",
        GetItemName(stashItem.entry));
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

bool ParseTwoNumbers(std::string const& value, uint32& first, uint32& second)
{
    size_t separator = value.find('|');
    if (separator == std::string::npos)
        return false;

    first = ParseNumber(value.substr(0, separator));
    second = ParseNumber(value.substr(separator + 1));
    return first != 0 && second != 0;
}

bool HandleStashCommand(Player* player, std::string const& rawMessage)
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
        std::string arguments = payload.substr(sizeof(DepositPrefix) - 1);
        uint32 entry = 0;
        uint32 slot = 0;
        if (ParseTwoNumbers(arguments, entry, slot))
            DepositOne(player, entry, slot);
        else
        {
            entry = ParseNumber(arguments);
            slot = FindFirstFreeStashSlot(player);
            if (entry && slot)
                DepositOne(player, entry, slot);
        }
        SendStashState(player);
        return true;
    }

    constexpr char WithdrawPrefix[] = "WITHDRAW|";
    if (payload.rfind(WithdrawPrefix, 0) == 0)
    {
        uint32 slot = ParseNumber(payload.substr(sizeof(WithdrawPrefix) - 1));
        if (slot)
            WithdrawOne(player, slot);
        SendStashState(player);
        return true;
    }

    return false;
}

void EnsureAccountStash(Creature* khadgar)
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
}

class go_adventurer_gauntlet_account_stash : public GameObjectScript
{
public:
    go_adventurer_gauntlet_account_stash()
        : GameObjectScript("go_adventurer_gauntlet_account_stash") { }

    bool OnGossipHello(Player* player, GameObject* /*go*/) override
    {
        if (player)
        {
            uint32 guid = player->GetGUID().GetCounter();
            OpenStashPlayers.insert(guid);
            StashRangeTimers[guid] = StashRangeCheckMs;
        }
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
            EnsureAccountStash(creature);
    }
};

class AdventurerGauntletAccountStashPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletAccountStashPlayerScript()
        : PlayerScript("AdventurerGauntletAccountStashPlayerScript") { }

    void OnPlayerBeforeSendChatMessage(Player* player, uint32& /*type*/, uint32& lang, std::string& msg) override
    {
        if (player && lang == LANG_ADDON)
            HandleStashCommand(player, msg);
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        if (!player)
            return;

        uint32 guid = player->GetGUID().GetCounter();
        if (!OpenStashPlayers.contains(guid))
            return;

        uint32& timer = StashRangeTimers[guid];
        if (timer > diff)
        {
            timer -= diff;
            return;
        }
        timer = StashRangeCheckMs;

        if (!player->FindNearestGameObject(AccountStashEntry, StashUseRange))
            CloseStash(player);
    }

    void OnPlayerLogout(Player* player) override
    {
        if (!player)
            return;
        uint32 guid = player->GetGUID().GetCounter();
        OpenStashPlayers.erase(guid);
        StashRangeTimers.erase(guid);
    }
};

void AddAdventurerGauntletAccountStashScripts()
{
    new go_adventurer_gauntlet_account_stash();
    new AdventurerGauntletAccountStashKhadgarScript();
    new AdventurerGauntletAccountStashPlayerScript();
}
