#include "InstanceSaveMgr.h"
#include "Map.h"
#include "MapMgr.h"
#include "Player.h"
#include "ScriptMgr.h"

bool IsAdventurerGauntletFallen(Player* player);

namespace
{
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;

bool IsGauntletDungeon(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

void CleanupEmptyGauntletInstance(Player* player, uint32 mapId)
{
    if (!player)
        return;

    InstancePlayerBind* bind = sInstanceSaveMgr->PlayerGetBoundInstance(
        player->GetGUID(), mapId, DUNGEON_DIFFICULTY_NORMAL);
    if (!bind || !bind->save)
        return;

    InstanceSave* save = bind->save;
    uint32 instanceId = save->GetInstanceId();

    if (Map* map = sMapMgr->FindMap(mapId, instanceId))
    {
        if (!map->GetPlayers().isEmpty())
            return;

        if (!map->ToInstanceMap()->Reset(INSTANCE_RESET_ALL))
            return;
    }

    // The run is over and nobody remains in this copy. Remove the saved
    // encounter state and every bind pointing at this specific instance so a
    // future Adventurer cannot inherit its dead bosses.
    sInstanceSaveMgr->DeleteInstanceSavedData(instanceId);
    sInstanceSaveMgr->UnbindAllFor(save);
}
}

class AdventurerGauntletRunCleanupPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletRunCleanupPlayerScript()
        : PlayerScript("AdventurerGauntletRunCleanupPlayerScript") { }

    void OnPlayerMapChanged(Player* player) override
    {
        if (!player || !IsAdventurerGauntletFallen(player) || IsGauntletDungeon(player->GetMapId()))
            return;

        CleanupEmptyGauntletInstance(player, RagefireMapId);
        CleanupEmptyGauntletInstance(player, DeadminesMapId);
    }
};

void AddAdventurerGauntletRunCleanupScripts()
{
    new AdventurerGauntletRunCleanupPlayerScript();
}
