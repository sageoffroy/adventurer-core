#include "Chat.h"
#include "Group.h"
#include "Map.h"
#include "Player.h"
#include "ScriptMgr.h"

namespace
{
constexpr uint32 LoneWolfSpellId = 910501;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;

bool IsGauntletDungeon(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

bool IsSoloAdventurer(Player* player)
{
    if (!player)
        return false;

    Group* group = player->GetGroup();
    return !group || group->GetMembersCount() <= 1;
}

void UpdateLoneWolf(Player* player, bool entering)
{
    if (!player)
        return;

    if (!entering || !IsGauntletDungeon(player->GetMapId()) || !IsSoloAdventurer(player))
    {
        player->RemoveAurasDueToSpell(LoneWolfSpellId);
        return;
    }

    if (!player->HasAura(LoneWolfSpellId))
    {
        player->CastSpell(player, LoneWolfSpellId, true);
        ChatHandler(player->GetSession()).SendSysMessage(
            "|cffffd100Lobo solitario|r: Khadgar reconoce que afrontas la expedicion sin compania.");
    }
}
}

class AdventurerGauntletLoneWolfMapScript : public AllMapScript
{
public:
    AdventurerGauntletLoneWolfMapScript()
        : AllMapScript("AdventurerGauntletLoneWolfMapScript") { }

    void OnPlayerEnterAll(Map* map, Player* player) override
    {
        if (map && player && IsGauntletDungeon(map->GetId()))
            UpdateLoneWolf(player, true);
    }

    void OnPlayerLeaveAll(Map* map, Player* player) override
    {
        if (map && player && IsGauntletDungeon(map->GetId()))
            player->RemoveAurasDueToSpell(LoneWolfSpellId);
    }
};

void AddAdventurerGauntletLoneWolfScripts()
{
    new AdventurerGauntletLoneWolfMapScript();
}
