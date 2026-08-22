#include "Language.h"
#include "Opcodes.h"
#include "Player.h"
#include "ScriptDefines/PlayerScript.h"
#include "SharedDefines.h"
#include "WorldPacket.h"

#include <algorithm>
#include <string>
#include <unordered_map>

namespace
{
constexpr uint32 SKILL_RIDING = 762;
constexpr uint32 SPELL_APPRENTICE_RIDING = 33388;
constexpr uint32 SPELL_BROWN_HORSE = 458;
constexpr uint32 SPELL_DUAL_WIELD = 674;
constexpr uint32 APPRENTICE_RIDING_VALUE = 75;

// Rage and Runic Power are stored at ten times the value shown by the 3.3.5a
// client. Energy is stored 1:1. These are the same native pool sizes used by
// SpellDraft's proven classless-resource implementation.
constexpr uint32 ADVENTURER_MAX_RAGE = 1000;
constexpr uint32 ADVENTURER_MAX_ENERGY = 100;
constexpr uint32 ADVENTURER_MAX_RUNIC_POWER = 1000;

// The 3.3.5a client refuses to expose combo points through GetComboPoints for a
// non-Rogue/non-Druid class even though AzerothCore's Unit combo-point backend
// is class agnostic. Keep Blizzard's target ComboFrame, but mirror the visible
// server count over the addon-message channel so FrameXML can feed that native
// frame for class 10.
constexpr uint32 ADVENTURER_COMBO_SYNC_INTERVAL_MS = 100;
constexpr char ADVENTURER_COMBO_PREFIX[] = "AdventurerCP";

struct ComboSyncState
{
    uint32 elapsed = 0;
    ObjectGuid selectedTarget = ObjectGuid::Empty;
    uint8 points = 0xFF; // impossible sentinel: force the first sync
};

struct RuneSyncState
{
    bool initialized = false;
    uint8 readyMask = 0;
};

std::unordered_map<uint64, ComboSyncState> comboSyncStates;
std::unordered_map<uint64, RuneSyncState> runeSyncStates;

constexpr uint32 UNIVERSAL_SKILLS[] =
{
    43, 44, 45, 46, 54, 55, 95, 136, 160, 162, 172, 173, 176,
    226, 228, 229, 293, 413, 414, 415, 433, 473
};

constexpr uint32 UNIVERSAL_SPELLS[] =
{
    81,    // Dodge (Passive)
    107,   // Block
    3127,  // Parry (Passive)
    SPELL_DUAL_WIELD,

    9078, 9077, 8737, 750, // Cloth, Leather, Mail, Plate

    196, 197, 198, 199, 201, 202, 227, 1180, 200, 15590,
    264, 5011, 266, 2567, 5009,

    75,    // Auto Shot
    5019,  // Shoot
    2764,  // Throw
    SPELL_APPRENTICE_RIDING,
    SPELL_BROWN_HORSE
};

constexpr uint32 HUMAN_SPELLS[] = { 59752, 20598, 20599, 20597, 20864 };
constexpr uint32 ORC_SPELLS[] = { 20572, 20573, 20575, 20574 };
constexpr uint32 DWARF_SPELLS[] = { 20594, 20596, 20595, 2481, 59224 };
constexpr uint32 NIGHT_ELF_SPELLS[] = { 58984, 20582, 20585, 20583 };
constexpr uint32 UNDEAD_SPELLS[] = { 7744, 20577, 5227, 20579 };
constexpr uint32 TAUREN_SPELLS[] = { 20549, 20550, 20552, 20551 };
constexpr uint32 GNOME_SPELLS[] = { 20589, 20591, 20593, 20592 };
constexpr uint32 TROLL_SPELLS[] = { 26297, 20555, 20557, 20558, 26290, 58943 };
constexpr uint32 BLOOD_ELF_SPELLS[] = { 28730, 28877, 822 };
constexpr uint32 DRAENEI_SPELLS[] = { 59547, 28878, 28875 };

bool IsAdventurer(Player const* player)
{
    return player && player->getClass() == CLASS_ADVENTURER;
}

void SendVisibleComboPoints(Player* player, uint8 points)
{
    // This is the same 3.3.5a packet shape that the old SpellDraft classless
    // implementation used successfully: CHAT_MSG_ADDON (0), LANG_ADDON, self
    // sender/receiver and a "prefix\tpayload" message. Keeping that proven wire
    // format avoids depending on the client's normal class-filtered combo API.
    std::string message = std::string(ADVENTURER_COMBO_PREFIX) + "\t" + std::to_string(points);

    WorldPacket data(SMSG_MESSAGECHAT, 100);
    data << uint8(0); // CHAT_MSG_ADDON
    data << int32(LANG_ADDON);
    data << player->GetGUID();
    data << uint32(0);
    data << player->GetGUID();
    data << uint32(message.length() + 1);
    data << message;
    data << uint8(0);
    player->SendDirectMessage(&data);
}

void UpdateComboPointSync(Player* player, uint32 diff)
{
    if (!IsAdventurer(player) || !player->IsInWorld())
        return;

    uint64 key = player->GetGUID().GetRawValue();
    ComboSyncState& state = comboSyncStates[key];
    state.elapsed += diff;
    if (state.elapsed < ADVENTURER_COMBO_SYNC_INTERVAL_MS)
        return;
    state.elapsed = 0;

    ObjectGuid selectedTarget = player->GetTarget();
    uint8 visiblePoints = selectedTarget ? player->GetComboPoints(selectedTarget) : 0;
    if (state.selectedTarget == selectedTarget && state.points == visiblePoints)
        return;

    state.selectedTarget = selectedTarget;
    state.points = visiblePoints;
    SendVisibleComboPoints(player, visiblePoints);
}

uint8 GetRuneReadyMask(Player const* player)
{
    uint8 mask = 0;
    for (uint8 index = 0; index < MAX_RUNES; ++index)
        if (player->GetRuneCooldown(index) == 0)
            mask |= uint8(1u << index);
    return mask;
}

void UpdateRuneClientSync(Player* player)
{
    if (!IsAdventurer(player) || !player->IsInWorld())
        return;

    uint64 key = player->GetGUID().GetRawValue();
    RuneSyncState& state = runeSyncStates[key];
    uint8 readyMask = GetRuneReadyMask(player);

    if (!state.initialized)
    {
        state.initialized = true;
        state.readyMask = readyMask;
        return;
    }

    uint8 newlyReady = uint8(readyMask & ~state.readyMask);
    state.readyMask = readyMask;

    // A native DK advances rune cooldowns locally in the 3.3.5a client, but
    // class 10 does not run that hidden DK-only usability transition. The
    // decisive clue is that relogging fixes the stale action immediately:
    // SMSG_RESYNC_RUNES replaces the client's complete rune state (type plus
    // remaining cooldown). Re-send that authoritative snapshot only when at
    // least one server rune actually crosses cooldown -> ready.
    if (newlyReady != 0)
        player->ResyncRunes(MAX_RUNES);
}

void LearnMissingSpells(Player* player, uint32 const* spells, uint32 count)
{
    for (uint32 i = 0; i < count; ++i)
        if (!player->HasSpell(spells[i]))
            player->learnSpell(spells[i]);
}

template <uint32 N>
void LearnMissingSpells(Player* player, uint32 const (&spells)[N])
{
    LearnMissingSpells(player, spells, N);
}

void LearnRacialBaseline(Player* player)
{
    switch (player->getRace())
    {
        case RACE_HUMAN: LearnMissingSpells(player, HUMAN_SPELLS); break;
        case RACE_ORC: LearnMissingSpells(player, ORC_SPELLS); break;
        case RACE_DWARF: LearnMissingSpells(player, DWARF_SPELLS); break;
        case RACE_NIGHTELF: LearnMissingSpells(player, NIGHT_ELF_SPELLS); break;
        case RACE_UNDEAD_PLAYER: LearnMissingSpells(player, UNDEAD_SPELLS); break;
        case RACE_TAUREN: LearnMissingSpells(player, TAUREN_SPELLS); break;
        case RACE_GNOME: LearnMissingSpells(player, GNOME_SPELLS); break;
        case RACE_TROLL: LearnMissingSpells(player, TROLL_SPELLS); break;
        case RACE_BLOODELF: LearnMissingSpells(player, BLOOD_ELF_SPELLS); break;
        case RACE_DRAENEI: LearnMissingSpells(player, DRAENEI_SPELLS); break;
        default: break;
    }
}

void SetLanguageSkill(Player* player, uint32 skillId)
{
    player->SetSkill(skillId, 1, 300, 300);
}

void SetRacialLanguages(Player* player)
{
    switch (player->getRace())
    {
        case RACE_HUMAN:
            SetLanguageSkill(player, 98);
            break;
        case RACE_DWARF:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 111);
            break;
        case RACE_NIGHTELF:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 113);
            break;
        case RACE_GNOME:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 313);
            break;
        case RACE_DRAENEI:
            SetLanguageSkill(player, 98); SetLanguageSkill(player, 759);
            break;
        case RACE_ORC:
            SetLanguageSkill(player, 109);
            break;
        case RACE_UNDEAD_PLAYER:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 673);
            break;
        case RACE_TAUREN:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 115);
            break;
        case RACE_TROLL:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 315);
            break;
        case RACE_BLOODELF:
            SetLanguageSkill(player, 109); SetLanguageSkill(player, 137);
            break;
        default:
            break;
    }
}

void ApplyUniversalResources(Player* player, bool initializeCurrent = false)
{
    if (!IsAdventurer(player))
        return;

    // Mana remains the Adventurer's native primary pool and therefore keeps
    // AzerothCore's normal class/stat scaling. Auxiliary pools are always
    // available so abilities from every native class can spend/generate them.
    if (player->GetMaxPower(POWER_RAGE) < ADVENTURER_MAX_RAGE)
        player->SetMaxPower(POWER_RAGE, ADVENTURER_MAX_RAGE);
    if (player->GetMaxPower(POWER_ENERGY) < ADVENTURER_MAX_ENERGY)
        player->SetMaxPower(POWER_ENERGY, ADVENTURER_MAX_ENERGY);
    if (player->GetMaxPower(POWER_RUNIC_POWER) < ADVENTURER_MAX_RUNIC_POWER)
        player->SetMaxPower(POWER_RUNIC_POWER, ADVENTURER_MAX_RUNIC_POWER);

    if (initializeCurrent)
    {
        player->SetPower(POWER_RAGE, 0);
        player->SetPower(POWER_ENERGY, ADVENTURER_MAX_ENERGY);
        player->SetPower(POWER_RUNIC_POWER, 0);
    }
}

void ApplyRuntimeCapabilities(Player* player)
{
    uint32 allWeapons = (1u << MAX_ITEM_SUBCLASS_WEAPON) - 1u;
    uint32 allArmor = (1u << MAX_ITEM_SUBCLASS_ARMOR) - 1u;

    player->AddWeaponProficiency(allWeapons);
    player->AddArmorProficiency(allArmor);
    player->SetCanParry(true);
    player->SetCanBlock(true);
    player->UpdateDefenseBonusesMod();
    ApplyUniversalResources(player);
}

void FinalizeNewAdventurer(Player* player)
{
    if (!IsAdventurer(player))
        return;

    uint32 maxSkillValue = std::min<uint32>(player->GetLevel() * 5u, 400u);
    for (uint32 skillId : UNIVERSAL_SKILLS)
        player->SetSkill(skillId, 0, maxSkillValue, maxSkillValue);

    LearnMissingSpells(player, UNIVERSAL_SPELLS);
    player->SetSkill(SKILL_RIDING, 1, APPRENTICE_RIDING_VALUE, APPRENTICE_RIDING_VALUE);
    LearnRacialBaseline(player);
    SetRacialLanguages(player);
    ApplyRuntimeCapabilities(player);
    ApplyUniversalResources(player, true);

    // PLAYERHOOK_ON_CREATE runs after AzerothCore's original creation
    // transaction. Persist the completed class baseline before the temporary
    // Player object is destroyed.
    player->SaveToDB(false, false);
}
}

class AdventurerCorePlayerScript : public PlayerScript
{
public:
    AdventurerCorePlayerScript() : PlayerScript("AdventurerCorePlayerScript",
    {
        PLAYERHOOK_ON_CREATE,
        PLAYERHOOK_ON_LOGIN,
        PLAYERHOOK_ON_LOGOUT,
        PLAYERHOOK_ON_LEVEL_CHANGED,
        PLAYERHOOK_ON_UPDATE,
        PLAYERHOOK_ON_AFTER_UPDATE,
        PLAYERHOOK_ON_AFTER_UPDATE_MAX_POWER,
        PLAYERHOOK_ON_PLAYER_HAS_ACTIVE_POWER_TYPE,
        PLAYERHOOK_ON_PLAYER_IS_CLASS
    }) { }

    void OnPlayerCreate(Player* player) override
    {
        FinalizeNewAdventurer(player);
    }

    void OnPlayerLogin(Player* player) override
    {
        if (IsAdventurer(player))
        {
            ApplyRuntimeCapabilities(player);
            uint64 key = player->GetGUID().GetRawValue();
            comboSyncStates.erase(key);
            runeSyncStates.erase(key);
        }
    }

    void OnPlayerLogout(Player* player) override
    {
        uint64 key = player->GetGUID().GetRawValue();
        comboSyncStates.erase(key);
        runeSyncStates.erase(key);
    }

    void OnPlayerUpdate(Player* player, uint32 diff) override
    {
        UpdateComboPointSync(player, diff);
    }

    void OnPlayerAfterUpdate(Player* player, uint32 /*diff*/) override
    {
        UpdateRuneClientSync(player);
    }

    void OnPlayerLevelChanged(Player* player, uint8 /*oldLevel*/) override
    {
        if (IsAdventurer(player))
            ApplyRuntimeCapabilities(player);
    }

    void OnPlayerAfterUpdateMaxPower(Player* player, Powers& power, float& value) override
    {
        if (!IsAdventurer(player))
            return;

        // Preserve a native-sized floor for every auxiliary pool while still
        // allowing talents/auras to increase that pool above the baseline.
        switch (power)
        {
            case POWER_RAGE:
                value = std::max(value, static_cast<float>(ADVENTURER_MAX_RAGE));
                break;
            case POWER_ENERGY:
                value = std::max(value, static_cast<float>(ADVENTURER_MAX_ENERGY));
                break;
            case POWER_RUNIC_POWER:
                value = std::max(value, static_cast<float>(ADVENTURER_MAX_RUNIC_POWER));
                break;
            default:
                break;
        }
    }

    bool OnPlayerHasActivePowerType(Player const* player, Powers power) override
    {
        if (!IsAdventurer(player))
            return false;
        if (player->getPowerType() == power)
            return false; // Native Mana continues through AzerothCore's stock path.

        switch (power)
        {
            case POWER_RAGE:
            case POWER_ENERGY:
            case POWER_RUNIC_POWER:
                return player->GetMaxPower(power) > 0;
            default:
                return false;
        }
    }

    Optional<bool> OnPlayerIsClass(Player const* player, Classes playerClass, ClassContext context) override
    {
        if (!IsAdventurer(player))
            return std::nullopt;

        // AzerothCore already routes rune initialization, rune-cost checks,
        // cooldown regeneration and Runic Power decay through this ABILITY
        // context. Treating Adventurer as DK only there gives it the complete
        // native rune economy without inheriting DK starting levels, quests,
        // taxis, etc.
        if (playerClass == CLASS_DEATH_KNIGHT && context == CLASS_CONTEXT_ABILITY)
            return true;

        return std::nullopt;
    }
};

void AddAdventurerCoreScripts()
{
    new AdventurerCorePlayerScript();
}