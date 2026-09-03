#include "Item.h"
#include "Player.h"
#include "ScriptDefines/PlayerScript.h"
#include "SpellInfo.h"
#include "SpellScript.h"
#include "SpellScriptLoader.h"
#include "Util.h"

#include <algorithm>

namespace
{
constexpr uint8 SinisterWeaponPercent = 75;
constexpr uint8 SinisterDaggerPercent = 100;
constexpr uint8 RuthlessCleaveWeaponPercent = 65;
constexpr uint32 AdventurerClassId = 10;
constexpr uint32 ShieldProficiencySpell = 9116;

bool UsesMainHandDagger(Player* player)
{
    if (!player)
        return false;

    Item* weapon = player->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_MAINHAND);
    if (!weapon)
        return false;

    ItemTemplate const* item = weapon->GetTemplate();
    return item && item->Class == ITEM_CLASS_WEAPON && item->SubClass == ITEM_SUBCLASS_WEAPON_DAGGER;
}

int32 FlatRankBonus(SpellInfo const* spellInfo, Unit* caster)
{
    if (!spellInfo || !caster)
        return 0;

    return std::max<int32>(0, spellInfo->Effects[EFFECT_0].CalcValue(caster));
}

int32 ScaleWeaponPortion(int32 totalDamage, int32 flatBonus, uint8 percent)
{
    if (totalDamage <= 0)
        return totalDamage;

    int32 weaponPortion = std::max<int32>(0, totalDamage - flatBonus);
    return flatBonus + CalculatePct(weaponPortion, percent);
}

void EnsureShieldProficiency(Player* player)
{
    if (!player || player->getClass() != AdventurerClassId)
        return;

    if (!player->HasSpell(ShieldProficiencySpell))
        player->learnSpell(ShieldProficiencySpell);
}
}

class spell_adventurer_sinister_strike : public SpellScript
{
    PrepareSpellScript(spell_adventurer_sinister_strike);

    bool Load() override
    {
        return GetCaster() && GetCaster()->IsPlayer();
    }

    void HandleHit()
    {
        Player* player = GetCaster()->ToPlayer();
        if (!player || !GetHitUnit() || GetHitDamage() <= 0)
            return;

        uint8 percent = UsesMainHandDagger(player) ? SinisterDaggerPercent : SinisterWeaponPercent;
        SetHitDamage(
            ScaleWeaponPortion(
                GetHitDamage(),
                FlatRankBonus(GetSpellInfo(), GetCaster()),
                percent));
    }

    void Register() override
    {
        OnHit += SpellHitFn(spell_adventurer_sinister_strike::HandleHit);
    }
};

class spell_adventurer_brutal_slam : public SpellScript
{
    PrepareSpellScript(spell_adventurer_brutal_slam);

    bool Load() override
    {
        return GetCaster() && GetCaster()->IsPlayer();
    }

    void HandleHit()
    {
        Unit* caster = GetCaster();
        if (!caster || !GetHitUnit() || GetHitDamage() <= 0)
            return;

        uint8 level = caster->GetLevel();
        float limit = caster->HasAura(2565) ? 2.0f : 1.0f;
        uint32 blockValue = caster->GetShieldBlockValue(
            uint32(float(level) * 24.5f * limit),
            uint32(float(level) * 34.5f * limit));

        SetHitDamage(GetHitDamage() + int32(blockValue));
    }

    void Register() override
    {
        OnHit += SpellHitFn(spell_adventurer_brutal_slam::HandleHit);
    }
};

class spell_adventurer_ruthless_cleave : public SpellScript
{
    PrepareSpellScript(spell_adventurer_ruthless_cleave);

    bool Load() override
    {
        _successfulHits = 0;
        _comboGranted = false;
        return GetCaster() && GetCaster()->IsPlayer();
    }

    void HandleHit()
    {
        Unit* target = GetHitUnit();
        if (!target || GetHitDamage() <= 0)
            return;

        SetHitDamage(
            ScaleWeaponPortion(
                GetHitDamage(),
                FlatRankBonus(GetSpellInfo(), GetCaster()),
                RuthlessCleaveWeaponPercent));

        ++_successfulHits;
        if (_successfulHits < 2 || _comboGranted)
            return;

        Player* player = GetCaster()->ToPlayer();
        Unit* comboTarget = GetExplTargetUnit();
        if (!player || !comboTarget)
            return;

        player->AddComboPoints(comboTarget, 1);
        _comboGranted = true;
    }

    void Register() override
    {
        OnHit += SpellHitFn(spell_adventurer_ruthless_cleave::HandleHit);
    }

private:
    uint8 _successfulHits = 0;
    bool _comboGranted = false;
};

class AdventurerSpellDraftV4PlayerScript : public PlayerScript
{
public:
    AdventurerSpellDraftV4PlayerScript()
        : PlayerScript("AdventurerSpellDraftV4PlayerScript") { }

    void OnPlayerLogin(Player* player) override
    {
        EnsureShieldProficiency(player);
    }

    void OnPlayerCreate(Player* player) override
    {
        EnsureShieldProficiency(player);
    }
};

void AddAdventurerSpellDraftV4Scripts()
{
    RegisterSpellScript(spell_adventurer_sinister_strike);
    RegisterSpellScript(spell_adventurer_brutal_slam);
    RegisterSpellScript(spell_adventurer_ruthless_cleave);
    new AdventurerSpellDraftV4PlayerScript();
}
