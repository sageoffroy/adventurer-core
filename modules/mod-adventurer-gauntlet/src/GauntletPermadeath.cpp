#include "Chat.h"
#include "Player.h"
#include "PlayerSettings.h"
#include "ScriptMgr.h"

namespace
{
constexpr char const* GauntletSettingsSource = "adventurer_gauntlet";
constexpr uint32 GauntletSettingPledged = 0;
constexpr uint32 GauntletSettingFallen = 1;
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;

bool IsGauntletMap(uint32 mapId)
{
    return mapId == RagefireMapId || mapId == DeadminesMapId;
}

bool HasGauntletSetting(Player* player, uint32 index)
{
    return player && player->GetPlayerSetting(GauntletSettingsSource, index).IsEnabled();
}

void PersistGauntletSetting(Player* player, uint32 index, uint32 value)
{
    if (!player)
        return;

    player->UpdatePlayerSetting(GauntletSettingsSource, index, value);
    PlayerSettingsStore::UpdateSetting(player->GetGUID().GetCounter(), GauntletSettingsSource, index, value);
}

void SendPledgeStatus(Player* player)
{
    if (!player)
        return;

    ChatHandler(player->GetSession()).SendSysMessage(
        "|cffb048f8Juramento del Ultimo Aliento|r: el pacto de Khadgar sigue vigente. Tu proxima muerte sera definitiva.");
}
}

class AdventurerGauntletPermadeathScript : public PlayerScript
{
public:
    AdventurerGauntletPermadeathScript() : PlayerScript("AdventurerGauntletPermadeathScript") { }

    void OnPlayerMapChanged(Player* player) override
    {
        if (!player || !IsGauntletMap(player->GetMapId()))
            return;

        if (!HasGauntletSetting(player, GauntletSettingPledged))
        {
            PersistGauntletSetting(player, GauntletSettingPledged, 1);
            ChatHandler(player->GetSession()).SendSysMessage(
                "|cffffd100El pacto de Khadgar ha quedado sellado.|r Desde este momento, si caes, ninguna magia podra devolverte a la vida.");
        }

        if (!HasGauntletSetting(player, GauntletSettingFallen))
            SendPledgeStatus(player);
    }

    void OnPlayerJustDied(Player* player) override
    {
        if (!player || !HasGauntletSetting(player, GauntletSettingPledged) || HasGauntletSetting(player, GauntletSettingFallen))
            return;

        PersistGauntletSetting(player, GauntletSettingFallen, 1);

        // The original gauntlet development loop resurrected fallen characters
        // after returning them from the dungeon. This script is registered after
        // that loop and immediately restores the intended permanent-death state.
        if (player->IsAlive())
            player->KillPlayer();

        ChatHandler(player->GetSession()).SendSysMessage(
            "|cffff2020Has caido.|r Tu aventura ha terminado. Puedes permanecer como espiritu, pero este personaje no volvera a la vida.");
    }

    bool OnPlayerCanResurrect(Player* player) override
    {
        return !HasGauntletSetting(player, GauntletSettingFallen);
    }

    void OnPlayerLogin(Player* player) override
    {
        if (!player || !HasGauntletSetting(player, GauntletSettingPledged))
            return;

        if (!HasGauntletSetting(player, GauntletSettingFallen))
        {
            SendPledgeStatus(player);
            return;
        }

        if (player->IsAlive())
            player->KillPlayer();

        ChatHandler(player->GetSession()).SendSysMessage(
            "|cffaaaaaaEste aventurero cayo durante el desafio de Khadgar. Su muerte es definitiva.|r");
    }
};

void AddAdventurerGauntletPermadeathScripts()
{
    new AdventurerGauntletPermadeathScript();
}
