#include "Chat.h"
#include "DungeonCatalog.h"
#include "Player.h"
#include "PlayerSettings.h"
#include "ScriptMgr.h"
#include "SpellAuras.h"

namespace
{
constexpr char const* GauntletSettingsSource = "adventurer_gauntlet";
constexpr uint32 GauntletSettingPledged = 0;
constexpr uint32 GauntletSettingFallen = 1;
constexpr uint32 PledgeAuraSpellId = 910500;
bool IsGauntletMap(uint32 mapId)
{
    return AdventurerGauntlet::DungeonCatalog::IsSupportedDungeonMap(mapId);
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

void EnsurePledgeAura(Player* player)
{
    if (!player || !player->IsAlive() || !HasGauntletSetting(player, GauntletSettingPledged) || HasGauntletSetting(player, GauntletSettingFallen))
        return;

    if (!player->HasAura(PledgeAuraSpellId))
        player->CastSpell(player, PledgeAuraSpellId, true);

    if (Aura* aura = player->GetAura(PledgeAuraSpellId))
    {
        aura->SetMaxDuration(-1);
        aura->SetDuration(-1);
    }
}

void RemovePledgeAura(Player* player)
{
    if (player)
        player->RemoveAurasDueToSpell(PledgeAuraSpellId);
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

        EnsurePledgeAura(player);
    }

    void OnPlayerJustDied(Player* player) override
    {
        if (!player || !HasGauntletSetting(player, GauntletSettingPledged) || HasGauntletSetting(player, GauntletSettingFallen))
            return;

        PersistGauntletSetting(player, GauntletSettingFallen, 1);
        RemovePledgeAura(player);

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
            EnsurePledgeAura(player);
            return;
        }

        RemovePledgeAura(player);
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
