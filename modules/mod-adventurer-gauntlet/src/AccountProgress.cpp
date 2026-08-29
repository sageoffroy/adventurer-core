#include "Chat.h"
#include "DatabaseEnv.h"
#include "Item.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "WorldSession.h"

#include <unordered_set>

uint32 GetAdventurerGauntletAccountStashTotal(Player* player);
bool HandleAdventurerGauntletStashAddonCommand(Player* player, std::string const& rawMessage);

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

void LoseUnsecuredRunItems(Player* player)
{
    if (!player)
        return;

    uint32 lost = 0;

    // Curated/account expedition items are only safe if the player manually
    // deposited them in the account stash before the run. Anything still carried
    // at death is part of the failed expedition and is destroyed.
    for (uint32 entry = GauntletItemMin; entry <= GauntletItemMax; ++entry)
    {
        uint32 carried = player->GetItemCount(entry, false);
        if (!carried)
            continue;

        player->DestroyItemCount(entry, carried, true, true);
        lost += carried;
    }

    // Remaining equipped stock gear is also lost with the fallen Adventurer.
    for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
    {
        Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot);
        if (!item)
            continue;

        lost += item->GetCount();
        player->DestroyItem(INVENTORY_SLOT_BAG_0, slot, true);
    }

    // Destroying equipment while dead can leave stale visible/virtual fields until
    // relog. Rebuild them from the actual inventory immediately.
    RefreshEquipmentVisuals(player);

    if (lost)
        ChatHandler(player->GetSession()).PSendSysMessage(
            "|cffff2020{} objeto(s) no asegurado(s) se perdieron con este Aventurero.|r",
            lost);

    ChatHandler(player->GetSession()).SendSysMessage(
        "|cff00ff00Solo los objetos depositados previamente en el Baul de Expediciones permanecen a salvo.|r");
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

bool IsAdventurerGauntletFallen(Player* player)
{
    if (!player)
        return false;

    return bool(CharacterDatabase.Query(
        "SELECT 1 FROM `adventurer_gauntlet_fallen` WHERE `guid` = {} LIMIT 1",
        player->GetGUID().GetCounter()));
}

namespace
{
bool MarkFallen(Player* player)
{
    if (!player || IsAdventurerGauntletFallen(player))
        return false;

    uint32 guid = player->GetGUID().GetCounter();
    uint32 accountId = player->GetSession()->GetAccountId();

    LoseUnsecuredRunItems(player);

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
        "El contenido asegurado en el Baul de Expediciones permanece disponible para futuros Aventureros.");
    return true;
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
            "|cff00ff00Coleccion de Expediciones:|r {} pieza(s) descubierta(s). |cff00ff00Baul:|r {} objeto(s).",
            GetAccountCollectionCount(player),
            GetAdventurerGauntletAccountStashTotal(player));

        if (IsAdventurerGauntletFallen(player))
        {
            ChatHandler(player->GetSession()).SendSysMessage(
                "|cffff2020Este personaje figura como CAIDO en el Desafio de Khadgar.|r");
            ChatHandler(player->GetSession()).SendSysMessage(
                "Puedes conservarlo como recuerdo, pero ya no puede modificar el Baul ni volver a participar.");
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

    void OnPlayerBeforeSendChatMessage(Player* player, uint32& /*type*/, uint32& lang, std::string& msg) override
    {
        if (player && lang == LANG_ADDON && !IsAdventurerGauntletFallen(player))
            HandleAdventurerGauntletStashAddonCommand(player, msg);
    }

    bool OnPlayerBeforeTeleport(Player* player, uint32 mapId, float /*x*/, float /*y*/, float /*z*/, float /*orientation*/, uint32 options, Unit* /*target*/) override
    {
        if (!player || !IsGauntletMap(mapId))
            return true;

        if (IsAdventurerGauntletFallen(player))
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
