#include "Item.h"
#include "Player.h"
#include "ScriptDefines/PlayerScript.h"
#include "SpellInfo.h"
#include "SpellMgr.h"
#include "SpellScript.h"
#include "SpellScriptLoader.h"
#include "Util.h"

#include <algorithm>
#include <array>

namespace
{
constexpr uint8 SinisterWeaponPercent = 75;
constexpr uint8 SinisterDaggerPercent = 100;
constexpr uint8 RuthlessCleaveWeaponPercent = 65;
constexpr uint32 AdventurerClassId = 10;
constexpr uint32 ShieldProficiencySpell = 9116;
constexpr std::array<uint32, 3> CustomRankRoots = { 920000, 920020, 920040 };

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

bool KnowsAnyRank(Player* player, uint32 rootSpellId)
{
    if (!player)
        return false;

    uint32 current = sSpellMgr->GetFirstSpellInChain(rootSpellId);
    while (current)
    {
        if (player->HasSpell(current))
            return true;
        current = sSpellMgr->GetNextSpellInChain(current);
    }
    return false;
}

void UpgradeCustomRankChain(Player* player, uint32 rootSpellId)
{
    if (!player || !KnowsAnyRank(player, rootSpellId))
        return;

    uint32 current = sSpellMgr->GetFirstSpellInChain(rootSpellId);
    uint32 best = 0;
    uint32 level = player->GetLevel();

    while (current)
    {
        SpellInfo const* info = sSpellMgr->GetSpellInfo(current);
        if (!info)
            break;

        uint32 requiredLevel = std::max(info->BaseLevel, info->SpellLevel);
        if (requiredLevel <= level)
            best = current;

        current = sSpellMgr->GetNextSpellInChain(current);
    }

    if (best && !player->HasSpell(best))
        player->learnSpell(best);
}

void UpgradeKnownCustomRanks(Player* player)
{
    if (!player || player->getClass() != AdventurerClassId)
        return;

    for (uint32 rootSpellId : CustomRankRoots)
        UpgradeCustomRankChain(player, rootSpellId);
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
        UpgradeKnownCustomRanks(player);
    }

    void OnPlayerCreate(Player* player) override
    {
        EnsureShieldProficiency(player);
    }

    void OnPlayerLevelChanged(Player* player, uint8 /*oldLevel*/) override
    {
        UpgradeKnownCustomRanks(player);
    }
};

void AddAdventurerSpellDraftV4Scripts()
{
    RegisterSpellScript(spell_adventurer_sinister_strike);
    RegisterSpellScript(spell_adventurer_brutal_slam);
    RegisterSpellScript(spell_adventurer_ruthless_cleave);
    new AdventurerSpellDraftV4PlayerScript();
}
