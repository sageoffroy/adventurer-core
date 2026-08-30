#include "Chat.h"
#include "Creature.h"
#include "InstanceSaveMgr.h"
#include "Map.h"
#include "MapMgr.h"
#include "Player.h"
#include "ScriptMgr.h"

#include <algorithm>
#include <unordered_map>

bool IsAdventurerGauntletFallen(Player* player);

namespace
{
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;

std::unordered_map<uint32, uint8> DynamicGauntletInstanceLevels;

bool IsGauntletDungeon(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

bool LooksLikeActiveGauntletInstance(Map* map, uint8 expectedLevel)
{
    if (!map || !IsGauntletDungeon(map->GetId()) || !map->GetInstanceId())
        return false;

    bool foundCreature = false;
    for (auto const& [spawnId, creature] : map->GetCreatureBySpawnIdStore())
    {
        (void)spawnId;
        if (!creature || creature->IsPet() || creature->IsTrigger() || creature->IsSummon())
            continue;

        foundCreature = true;
        if (creature->GetLevel() != expectedLevel)
            return false;
    }

    return foundCreature;
}

uint8 GetHighestLivingPlayerLevel(Map* map, uint8 fallback)
{
    uint8 level = fallback;
    if (!map)
        return level;

    for (auto const& ref : map->GetPlayers())
    {
        Player* player = ref.GetSource();
        if (player && player->IsAlive())
            level = std::max<uint8>(level, player->GetLevel());
    }

    return level;
}

void ScaleGauntletInstance(Map* map, uint8 level)
{
    if (!map || !level)
        return;

    uint32 instanceId = map->GetInstanceId();
    if (!instanceId)
        return;

    auto itr = DynamicGauntletInstanceLevels.find(instanceId);
    if (itr != DynamicGauntletInstanceLevels.end() && itr->second >= level)
        return;

    DynamicGauntletInstanceLevels[instanceId] = level;
    map->LoadAllGrids();

    for (auto const& [spawnId, creature] : map->GetCreatureBySpawnIdStore())
    {
        (void)spawnId;
        if (!creature || !creature->IsAlive() || creature->IsPet() || creature->IsTrigger() || creature->IsSummon())
            continue;

        uint32 oldHealth = creature->GetHealth();
        uint32 oldMaxHealth = creature->GetMaxHealth();

        creature->SelectLevel();

        uint32 newMaxHealth = creature->GetMaxHealth();
        if (oldMaxHealth && newMaxHealth)
        {
            uint32 scaledHealth = static_cast<uint32>(
                std::max<uint64>(1, (static_cast<uint64>(oldHealth) * newMaxHealth) / oldMaxHealth));
            creature->SetHealth(std::min<uint32>(scaledHealth, newMaxHealth));
        }
    }

    for (auto const& ref : map->GetPlayers())
        if (Player* player = ref.GetSource())
            ChatHandler(player->GetSession()).PSendSysMessage(
                "La expedicion avanza: {} ahora se adapta al nivel |cffffd100{}|r.",
                map->GetId() == RagefireMapId ? "Sima Ignea" : "Minas de la Muerte",
                level);
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

    DynamicGauntletInstanceLevels.erase(instanceId);

    // The run is over and nobody remains in this copy. Remove the saved
    // encounter state and every bind pointing at this specific instance so a
    // future Adventurer cannot inherit its dead bosses.
    sInstanceSaveMgr->DeleteInstanceSavedData(instanceId);
    sInstanceSaveMgr->UnbindAllFor(save);
}
}

class AdventurerGauntletDynamicCreatureScript : public AllCreatureScript
{
public:
    AdventurerGauntletDynamicCreatureScript()
        : AllCreatureScript("AdventurerGauntletDynamicCreatureScript") { }

    void OnBeforeCreatureSelectLevel(CreatureTemplate const* /*creatureTemplate*/, Creature* creature, uint8& level) override
    {
        if (!creature || !IsGauntletDungeon(creature->GetMapId()))
            return;

        auto itr = DynamicGauntletInstanceLevels.find(creature->GetInstanceId());
        if (itr != DynamicGauntletInstanceLevels.end())
            level = itr->second;
    }
};

class AdventurerGauntletRunCleanupPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletRunCleanupPlayerScript()
        : PlayerScript("AdventurerGauntletRunCleanupPlayerScript") { }

    void OnPlayerLevelChanged(Player* player, uint8 oldLevel) override
    {
        if (!player || !player->IsAlive() || IsAdventurerGauntletFallen(player))
            return;

        Map* map = player->GetMap();
        if (!map || !IsGauntletDungeon(map->GetId()) || !map->GetInstanceId())
            return;

        uint32 instanceId = map->GetInstanceId();
        bool knownGauntlet = DynamicGauntletInstanceLevels.find(instanceId) != DynamicGauntletInstanceLevels.end();
        if (!knownGauntlet && !LooksLikeActiveGauntletInstance(map, oldLevel))
            return;

        uint8 targetLevel = GetHighestLivingPlayerLevel(map, player->GetLevel());
        ScaleGauntletInstance(map, targetLevel);
    }

    void OnPlayerMapChanged(Player* player) override
    {
        if (!player || !IsAdventurerGauntletFallen(player) || IsGauntletDungeon(player->GetMapId()))
            return;

        CleanupEmptyGauntletInstance(player, RagefireMapId);
        CleanupEmptyGauntletInstance(player, DeadminesMapId);
    }
};

class AdventurerGauntletRunCleanupMapScript : public AllMapScript
{
public:
    AdventurerGauntletRunCleanupMapScript()
        : AllMapScript("AdventurerGauntletRunCleanupMapScript") { }

    void OnDestroyInstance(MapInstanced* /*mapInstanced*/, Map* map) override
    {
        if (map && IsGauntletDungeon(map->GetId()))
            DynamicGauntletInstanceLevels.erase(map->GetInstanceId());
    }
};

void AddAdventurerGauntletRunCleanupScripts()
{
    // Registered after AdventurerGauntletCreatureScript, so this level hook can
    // override the initial fixed run level once the party levels inside a run.
    new AdventurerGauntletDynamicCreatureScript();
    new AdventurerGauntletRunCleanupPlayerScript();
    new AdventurerGauntletRunCleanupMapScript();
}
