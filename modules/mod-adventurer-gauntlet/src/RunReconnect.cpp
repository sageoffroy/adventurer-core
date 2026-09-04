#include "Player.h"
#include "PlayerSettings.h"
#include "RunProgress.h"
#include "ScriptMgr.h"

#include <unordered_map>

namespace
{
constexpr char const* GauntletSettingsSource = "adventurer_gauntlet";
constexpr uint32 GauntletSettingPledged = 0;

struct RunResumePoint
{
    uint32 MapId = 0;
    float X = 0.0f;
    float Y = 0.0f;
    float Z = 0.0f;
    float O = 0.0f;
};

std::unordered_map<uint32, RunResumePoint> PendingRunResumes;

bool IsPledged(Player* player)
{
    return player && player->GetPlayerSetting(GauntletSettingsSource, GauntletSettingPledged).IsEnabled();
}

RunResumePoint DefaultEntryFor(uint32 mapId)
{
    if (mapId == AdventurerGauntlet::RunProgress::DeadminesMapId)
        return {mapId, -16.4f, -383.07f, 61.78f, 1.86f};

    return {AdventurerGauntlet::RunProgress::RagefireMapId, 3.81f, -14.82f, -17.84f, 4.39f};
}
}

class AdventurerGauntletRunReconnectPlayerScript : public PlayerScript
{
public:
    AdventurerGauntletRunReconnectPlayerScript()
        : PlayerScript("AdventurerGauntletRunReconnectPlayerScript") { }

    void OnPlayerBeforeLogout(Player* player) override
    {
        if (!player || !IsPledged(player) || !AdventurerGauntlet::RunProgress::IsSupportedDungeonMap(player->GetMapId()))
            return;

        player->BindToInstance();
        AdventurerGauntlet::RunProgress::SaveLogoutPosition(player);
    }

    void OnPlayerLogin(Player* player) override
    {
        if (!player || !IsPledged(player))
            return;

        AdventurerGauntlet::RunProgress::ResumePoint persisted;
        if (!AdventurerGauntlet::RunProgress::LoadResumePoint(player, persisted))
            return;

        RunResumePoint point = persisted.LastPositionMatchesCurrentMap
            ? RunResumePoint{
                persisted.CurrentMap,
                persisted.LastPosition.X,
                persisted.LastPosition.Y,
                persisted.LastPosition.Z,
                persisted.LastPosition.O
            }
            : DefaultEntryFor(persisted.CurrentMap);

        if (player->GetMapId() == point.MapId &&
            AdventurerGauntlet::RunProgress::IsSupportedDungeonMap(player->GetMapId()))
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

        if (!IsPledged(player) || !AdventurerGauntlet::RunProgress::IsSupportedDungeonMap(point.MapId))
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
