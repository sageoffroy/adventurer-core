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

        // Keep the normal instance bind authoritative. The saved coordinates are
        // only a short-lived reconnect fallback if the core places the player at
        // the entrance/outside while the same worldserver process is still up.
        player->BindToInstance();

        PendingRunResumes[player->GetGUID().GetCounter()] = {
            player->GetMapId(),
            player->GetPositionX(),
            player->GetPositionY(),
            player->GetPositionZ(),
            player->GetOrientation()
        };
    }

    void OnPlayerLogin(Player* player) override
    {
        if (!player)
            return;

        auto itr = PendingRunResumes.find(player->GetGUID().GetCounter());
        if (itr == PendingRunResumes.end())
            return;

        // If AzerothCore already restored the bound dungeon correctly, nothing
        // else is needed. Otherwise schedule the fallback for the first update,
        // when the player is fully present in the world.
        if (player->GetMapId() == itr->second.MapId && IsGauntletMap(player->GetMapId()))
            PendingRunResumes.erase(itr);
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
