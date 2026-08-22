#include "Player.h"
#include "ScriptDefines/PlayerScript.h"
#include "SharedDefines.h"

#include <algorithm>

namespace
{
constexpr uint32 SKILL_RIDING = 762;
constexpr uint32 SPELL_APPRENTICE_RIDING = 33388;
constexpr uint32 SPELL_BROWN_HORSE = 458;
constexpr uint32 SPELL_DUAL_WIELD = 674;
constexpr uint32 APPRENTICE_RIDING_VALUE = 75;

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

void ApplyRuntimeCapabilities(Player* player)
{
    uint32 allWeapons = (1u << MAX_ITEM_SUBCLASS_WEAPON) - 1u;
    uint32 allArmor = (1u << MAX_ITEM_SUBCLASS_ARMOR) - 1u;

    player->AddWeaponProficiency(allWeapons);
    player->AddArmorProficiency(allArmor);
    player->SetCanParry(true);
    player->SetCanBlock(true);
    player->UpdateDefenseBonusesMod();
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
        PLAYERHOOK_ON_LEVEL_CHANGED
    }) { }

    void OnPlayerCreate(Player* player) override
    {
        FinalizeNewAdventurer(player);
    }

    void OnPlayerLogin(Player* player) override
    {
        if (IsAdventurer(player))
            ApplyRuntimeCapabilities(player);
    }

    void OnPlayerLevelChanged(Player* player, uint8 /*oldLevel*/) override
    {
        if (IsAdventurer(player))
            ApplyRuntimeCapabilities(player);
    }
};

void AddAdventurerCoreScripts()
{
    new AdventurerCorePlayerScript();
}
