#include "DatabaseEnv.h"
#include "Player.h"
#include "PlayerSettings.h"
#include "ScriptMgr.h"

#include <unordered_map>

namespace
{
constexpr char const* GauntletSettingsSource = "adventurer_gauntlet";
constexpr uint32 GauntletSettingPledged = 0;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;

struct RunResumePoint
{
    uint32 MapId = 0;
    float X = 0.0f;
    float Y = 0.0f;
    float Z = 0.0f;
    float O = 0.0f;
};

std::unordered_map<uint32, RunResumePoint> PendingRunResumes;

bool IsGauntletMap(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

bool IsPledged(Player* player)
{
    return player && player->GetPlayerSetting(GauntletSettingsSource, GauntletSettingPledged).IsEnabled();
}

RunResumePoint DefaultEntryFor(uint32 mapId)
{
    if (mapId == DeadminesMapId)
        return {DeadminesMapId, -16.4f, -383.07f, 61.78f, 1.86f};

    return {RagefireMapId, 3.81f, -14.82f, -17.84f, 4.39f};
}

bool LoadPersistentResume(Player* player, RunResumePoint& point)
{
    if (!player)
        return false;

    QueryResult result = CharacterDatabase.Query(
        "SELECT r.`current_map`, m.`last_map`, m.`last_x`, m.`last_y`, m.`last_z`, m.`last_o` "
        "FROM `adventurer_gauntlet_runs` r "
        "JOIN `adventurer_gauntlet_run_members` m ON m.`run_id` = r.`run_id` "
        "WHERE m.`character_guid` = {} AND r.`status` = 'active' "
        "ORDER BY r.`run_id` DESC LIMIT 1",
        player->GetGUID().GetCounter());

    if (!result)
        return false;

    Field* fields = result->Fetch();
    uint32 currentMap = fields[0].Get<uint32>();
    if (!IsGauntletMap(currentMap))
        return false;

    uint32 lastMap = fields[1].Get<uint32>();
    if (lastMap == currentMap)
    {
        point = {
            currentMap,
            fields[2].Get<float>(),
            fields[3].Get<float>(),
            fields[4].Get<float>(),
            fields[5].Get<float>()
        };
    }
    else
        point = DefaultEntryFor(currentMap);

    return true;
}
}

class AdventurerGauntletRunReconnectPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletRunReconnectPlayerScript()
        : PlayerScript("AdventurerGauntletRunReconnectPlayerScript") { }

    void OnPlayerBeforeLogout(Player* player) override
    {
        if (!player || !IsPledged(player) || !IsGauntletMap(player->GetMapId()))
            return;

        player->BindToInstance();

        CharacterDatabase.DirectExecute(
            "UPDATE `adventurer_gauntlet_run_members` m "
            "JOIN `adventurer_gauntlet_runs` r ON r.`run_id` = m.`run_id` "
            "SET m.`last_map` = {}, m.`last_x` = {}, m.`last_y` = {}, "
            "    m.`last_z` = {}, m.`last_o` = {}, m.`updated_at` = CURRENT_TIMESTAMP "
            "WHERE m.`character_guid` = {} AND r.`status` = 'active'",
            player->GetMapId(),
            player->GetPositionX(),
            player->GetPositionY(),
            player->GetPositionZ(),
            player->GetOrientation(),
            player->GetGUID().GetCounter());
    }

    void OnPlayerLogin(Player* player) override
    {
        if (!player || !IsPledged(player))
            return;

        RunResumePoint point;
        if (!LoadPersistentResume(player, point))
            return;

        if (player->GetMapId() == point.MapId && IsGauntletMap(player->GetMapId()))
            return;

        PendingRunResumes[player->GetGUID().GetCounter()] = point;
    }

    void OnPlayerUpdate(Player* player, uint32 /*diff*/) override
    {
        if (!player)
            return;

        auto itr = PendingRunResumes.find(player->GetGUID().GetCounter());
        if (itr == PendingRunResumes.end())
            return;

        RunResumePoint point = itr->second;
        PendingRunResumes.erase(itr);

        if (!IsPledged(player) || !IsGauntletMap(point.MapId))
            return;

        if (player->GetMapId() == point.MapId)
            return;

        player->TeleportTo(
            point.MapId,
            point.X,
            point.Y,
            point.Z,
            point.O,
            TELE_TO_GM_MODE);
    }
};

void AddAdventurerGauntletRunReconnectScripts()
{
    new AdventurerGauntletRunReconnectPlayerScript();
}
