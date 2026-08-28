#include "Creature.h"
#include "Item.h"
#include "Player.h"
#include "ScriptMgr.h"
#include "Spell.h"
#include "SpellAuraEffects.h"
#include "SpellScript.h"
#include "SpellMgr.h"
#include "ThreatManager.h"

#include <algorithm>

namespace
{
enum AdventurerDKSpells : uint32
{
    BloodPresence = 280001,
    BloodStrike = 280101,
    BloodTap = 280201,
    DarkCommand = 280301,
    IcyTouch = 280401,
    FrostPresence = 280501,
    MindFreeze = 280601,
    ChainsOfIce = 280701,
    DeathGrip = 280801,
    PlagueStrike = 280901,
    DeathStrike = 281001,
    RaiseDead = 281101,
    FrostSupport = 282001,
    DeathStrikeHeal = 282002,
    RaiseDeadGuardian = 282003,
    NativeBloodPresence = 48266,
    NativeFrostPresence = 48263,
    NativeUnholyPresence = 48265,
    BloodPresenceHealing = 63611,
    FrostFever = 55095,
    BloodPlague = 55078,
    GripPull = 49560,
    GripTaunt = 49575
};

uint32 Family(uint32 spell)
{
    return 280001 + ((spell - 280001) / 100) * 100;
}

bool IsAdventurer(Unit const* unit)
{
    return unit && unit->IsPlayer() && unit->getClass() == CLASS_ADVENTURER;
}
}

// Bound only to owned IDs. Native DKs, native spells and their resource paths
// are untouched. All 80 damage variants keep the original DK family masks.
class spell_adventurer_dk : public SpellScript
{
    PrepareSpellScript(spell_adventurer_dk);

    int32 _referenceDamage = 0;
    uint32 _diseases = 0;

    bool Validate(SpellInfo const* /*info*/) override
    {
        return ValidateSpellInfo({FrostFever, BloodPlague, GripPull, GripTaunt,
            DeathStrikeHeal, RaiseDeadGuardian});
    }

    SpellCastResult CheckCast()
    {
        if (!IsAdventurer(GetCaster()))
            return SPELL_FAILED_BAD_TARGETS;
        if (GetCaster()->GetLevel() < GetSpellInfo()->SpellLevel)
            return SPELL_FAILED_LOWLEVEL;
        uint32 family = Family(GetSpellInfo()->Id);
        if (family == BloodTap && GetCaster()->GetPower(POWER_RAGE) <= 0)
            return SPELL_FAILED_NO_POWER;
        if (family == DeathStrike && !GetCaster()->GetComboPoints(GetExplTargetUnit()))
            return SPELL_FAILED_NO_COMBO_POINTS;
        if (family == RaiseDead)
            for (Unit* controlled : GetCaster()->m_Controlled)
                if (controlled->GetUInt32Value(UNIT_CREATED_BY_SPELL) == RaiseDeadGuardian)
                    return SPELL_FAILED_ALREADY_HAVE_SUMMON;
        if (family == DeathGrip && (GetCaster()->HasUnitState(UNIT_STATE_JUMPING)
            || GetCaster()->HasUnitMovementFlag(MOVEMENTFLAG_FALLING)))
            return SPELL_FAILED_MOVING;
        return SPELL_CAST_OK;
    }

    void PayResources()
    {
        Unit* caster = GetCaster();
        uint32 family = Family(GetSpellInfo()->Id);
        if (family == BloodTap)
        {
            int32 rage = caster->GetPower(POWER_RAGE);
            GetSpell()->m_powerCost = 0;
            caster->SetPower(POWER_RAGE, 0);
            caster->ModifyPower(POWER_ENERGY, rage / 10);
        }
        else if (family == PlagueStrike || family == DeathGrip)
        {
            // OnCast is after successful validation and before TakePower.
            // Charge exactly once, with native cost modifiers, including misses.
            // Clearing this cast's cost prevents native miss refunds/double pay.
            int32 cost = GetSpell()->GetPowerCost();
            GetSpell()->m_powerCost = 0;
            if (!caster->ToPlayer()->GetCommandStatus(CHEAT_POWER))
                caster->ModifyPower(POWER_ENERGY, -cost);
        }
    }

    void CalculateFinisher(SpellEffIndex /*index*/)
    {
        // DBC effect carries the same-level Eviscerate base roll and per-combo
        // value. AP is explicit because this spell retains its DK family.
        _referenceDamage = GetEffectValue() + int32(GetCaster()->GetTotalAttackPowerValue(BASE_ATTACK)
            * GetCaster()->GetComboPoints(GetHitUnit()) * 0.07f);
        _diseases = GetHitUnit()->GetDiseasesByCaster(GetCaster()->GetGUID());
        SetEffectValue(_referenceDamage / 2);
    }

    void HandleHit()
    {
        Unit* caster = GetCaster();
        Unit* target = GetHitUnit();
        if (!target)
            return;
        switch (Family(GetSpellInfo()->Id))
        {
            case IcyTouch:
                caster->CastSpell(target, FrostFever, true);
                if (caster->HasAura(FrostPresence))
                    target->GetThreatMgr().AddThreat(caster, float(GetHitDamage()) * 6.0f, GetSpellInfo());
                break;
            case ChainsOfIce:
                caster->CastSpell(target, FrostFever, true);
                break;
            case PlagueStrike:
                caster->CastSpell(target, BloodPlague, true);
                GetSpell()->AddComboPointGain(target, 1);
                break;
            case DeathStrike:
            {
                int32 healing = _referenceDamage / 4 + int32(CalculatePct(caster->GetMaxHealth(),
                    5 * _diseases));
                caster->CastCustomSpell(DeathStrikeHeal, SPELLVALUE_BASE_POINT0, healing, caster, true);
                break;
            }
            case DeathGrip:
            {
                // Separate casts preserve independent taunt/movement immunity.
                caster->CastSpell(target, GripTaunt, true);
                Creature* creature = target->ToCreature();
                if (!creature || (!creature->isWorldBoss() && !creature->IsDungeonBoss()))
                    caster->CastSpell(target, GripPull, true);
                break;
            }
            case RaiseDead:
            {
                SpellCastTargets targets;
                targets.SetDst(*caster);
                caster->CastSpell(targets, sSpellMgr->GetSpellInfo(RaiseDeadGuardian), nullptr,
                    TRIGGERED_FULL_MASK, nullptr, nullptr, caster->GetGUID());
                break;
            }
            default:
                break;
        }
    }

    void Register() override
    {
        OnCheckCast += SpellCheckCastFn(spell_adventurer_dk::CheckCast);
        OnCast += SpellCastFn(spell_adventurer_dk::PayResources);
        // OnHit also fires on misses in this core; AfterHit is success-only.
        AfterHit += SpellHitFn(spell_adventurer_dk::HandleHit);
        if (Family(m_scriptSpellId) == DeathStrike)
            OnEffectLaunchTarget += SpellEffectFn(spell_adventurer_dk::CalculateFinisher,
                EFFECT_0, SPELL_EFFECT_SCHOOL_DAMAGE);
    }
};

class aura_adventurer_dk_frost_support : public AuraScript
{
    PrepareAuraScript(aura_adventurer_dk_frost_support);

    int32 ArmorBonus() const
    {
        Player* player = GetUnitOwner()->ToPlayer();
        if (!player)
            return 0;
        uint32 armor = 0;
        for (uint8 slot = EQUIPMENT_SLOT_START; slot < EQUIPMENT_SLOT_END; ++slot)
            if (Item* item = player->GetItemByPos(INVENTORY_SLOT_BAG_0, slot))
                if (!item->IsBroken() && item->GetTemplate()->InventoryType != INVTYPE_SHIELD)
                    armor += item->GetTemplate()->Armor;
        return int32(CalculatePct(armor, 60));
    }

    void CalculateArmor(AuraEffect const* /*effect*/, int32& amount, bool& /*recalculate*/)
    {
        amount = ArmorBonus();
    }

    void UpdateArmor(AuraEffect* /*effect*/)
    {
        if (AuraEffect* armor = GetAura()->GetEffect(EFFECT_1))
            armor->ChangeAmount(ArmorBonus());
    }

    void Register() override
    {
        DoEffectCalcAmount += AuraEffectCalcAmountFn(aura_adventurer_dk_frost_support::CalculateArmor,
            EFFECT_1, SPELL_AURA_MOD_RESISTANCE);
        OnEffectUpdatePeriodic += AuraEffectUpdatePeriodicFn(aura_adventurer_dk_frost_support::UpdateArmor,
            EFFECT_2, SPELL_AURA_PERIODIC_DUMMY);
    }
};

class aura_adventurer_dk_chains : public AuraScript
{
    PrepareAuraScript(aura_adventurer_dk_chains);

    void RecoverSpeed(AuraEffect* /*effect*/)
    {
        if (AuraEffect* slow = GetAura()->GetEffect(EFFECT_0))
            slow->ChangeAmount(std::min(0, slow->GetAmount() + 10));
    }

    void Register() override
    {
        OnEffectUpdatePeriodic += AuraEffectUpdatePeriodicFn(aura_adventurer_dk_chains::RecoverSpeed,
            EFFECT_1, SPELL_AURA_PERIODIC_DUMMY);
    }
};

class aura_adventurer_dk_presence : public AuraScript
{
    PrepareAuraScript(aura_adventurer_dk_presence);

    bool Validate(SpellInfo const* /*info*/) override
    {
        return ValidateSpellInfo({BloodPresence, FrostPresence, BloodPresenceHealing, FrostSupport});
    }

    void Apply(AuraEffect const* /*effect*/, AuraEffectHandleModes /*mode*/)
    {
        Unit* target = GetTarget();
        uint32 own = GetId();
        for (uint32 other : {uint32(BloodPresence), uint32(FrostPresence), uint32(NativeBloodPresence),
            uint32(NativeFrostPresence), uint32(NativeUnholyPresence)})
            if (other != own)
                target->RemoveAurasDueToSpell(other);
        target->CastSpell(target, own == BloodPresence ? BloodPresenceHealing : FrostSupport, true);
    }

    void Remove(AuraEffect const* /*effect*/, AuraEffectHandleModes /*mode*/)
    {
        GetTarget()->RemoveAurasDueToSpell(GetId() == BloodPresence ? BloodPresenceHealing : FrostSupport);
    }

    void Register() override
    {
        AuraType type = m_scriptSpellId == BloodPresence ? SPELL_AURA_MOD_DAMAGE_PERCENT_DONE
            : SPELL_AURA_MOD_TOTAL_STAT_PERCENTAGE;
        AfterEffectApply += AuraEffectApplyFn(aura_adventurer_dk_presence::Apply, EFFECT_0, type, AURA_EFFECT_HANDLE_REAL);
        AfterEffectRemove += AuraEffectRemoveFn(aura_adventurer_dk_presence::Remove, EFFECT_0, type, AURA_EFFECT_HANDLE_REAL);
    }
};

void AddAdventurerDKScripts()
{
    RegisterSpellScript(spell_adventurer_dk);
    RegisterSpellScript(aura_adventurer_dk_presence);
    RegisterSpellScript(aura_adventurer_dk_frost_support);
    RegisterSpellScript(aura_adventurer_dk_chains);
}
