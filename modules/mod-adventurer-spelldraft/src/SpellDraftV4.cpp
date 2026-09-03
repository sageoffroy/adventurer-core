#include "Item.h"
#include "Player.h"
#include "SpellInfo.h"
#include "SpellScript.h"
#include "SpellScriptLoader.h"

#include <algorithm>

namespace
{
constexpr uint8 SinisterWeaponPercent = 75;
constexpr uint8 SinisterDaggerPercent = 100;
constexpr uint8 RuthlessCleaveWeaponPercent = 65;

bool UsesMainHandDagger(Player const* player)
{
    if (!player)
        return false;

    Item* weapon = player->GetItemByPos(INVENTORY_SLOT_BAG_0, EQUIPMENT_SLOT_MAINHAND);
    if (!weapon)
        return false;

    ItemTemplate const* item = weapon->GetTemplate();
    return item && item->Class == ITEM_CLASS_WEAPON && item->SubClass == ITEM_SUBCLASS_WEAPON_DAGGER;
}

int32 FlatRankBonus(SpellScript const* script)
{
    if (!script || !script->GetSpellInfo() || !script->GetCaster())
        return 0;

    return std::max<int32>(0, script->GetSpellInfo()->Effects[EFFECT_0].CalcValue(script->GetCaster()));
}

int32 ScaleWeaponPortion(int32 totalDamage, int32 flatBonus, uint8 percent)
{
    if (totalDamage <= 0)
        return totalDamage;

    int32 weaponPortion = std::max<int32>(0, totalDamage - flatBonus);
    return flatBonus + CalculatePct(weaponPortion, percent);
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
        SetHitDamage(ScaleWeaponPortion(GetHitDamage(), FlatRankBonus(this), percent));
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
            ScaleWeaponPortion(GetHitDamage(), FlatRankBonus(this), RuthlessCleaveWeaponPercent));

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

void AddAdventurerSpellDraftV4Scripts()
{
    RegisterSpellScript(spell_adventurer_sinister_strike);
    RegisterSpellScript(spell_adventurer_brutal_slam);
    RegisterSpellScript(spell_adventurer_ruthless_cleave);
}
