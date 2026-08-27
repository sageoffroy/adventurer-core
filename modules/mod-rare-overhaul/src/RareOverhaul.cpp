#include "Config.h"
#include "Creature.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"
#include "Unit.h"

#include <algorithm>
#include <limits>

namespace
{
bool RareOverhaulEnabled = true;
bool RareDifficultyEnabled = true;
float RareHealthMultiplier = 2.0f;
float RareDamageMultiplier = 2.0f;

bool IsRareRank(CreatureTemplate const* creatureTemplate)
{
    if (!creatureTemplate)
        return false;

    return creatureTemplate->rank == CREATURE_ELITE_RARE ||
           creatureTemplate->rank == CREATURE_ELITE_RAREELITE;
}

bool IsRareCreature(Creature const* creature)
{
    return creature && IsRareRank(creature->GetCreatureTemplate());
}

uint32 ScaleUnsigned(uint32 value, float multiplier)
{
    if (value == 0 || multiplier == 1.0f)
        return value;

    double const scaled = static_cast<double>(value) * static_cast<double>(multiplier);
    double const capped = std::min(scaled, static_cast<double>(std::numeric_limits<uint32>::max()));
    return static_cast<uint32>(capped);
}
}

class RareOverhaulConfigScript : public WorldScript
{
public:
    RareOverhaulConfigScript() : WorldScript("RareOverhaulConfigScript") { }

    void OnBeforeConfigLoad(bool /*reload*/) override
    {
        RareOverhaulEnabled = sConfigMgr->GetOption<bool>("RareOverhaul.Enable", true);
        RareDifficultyEnabled = sConfigMgr->GetOption<bool>("RareOverhaul.Difficulty.Enable", true);
        RareHealthMultiplier = std::max(0.0f, sConfigMgr->GetOption<float>("RareOverhaul.HealthMultiplier", 2.0f));
        RareDamageMultiplier = std::max(0.0f, sConfigMgr->GetOption<float>("RareOverhaul.DamageMultiplier", 2.0f));
    }
};

class RareOverhaulCreatureScript : public AllCreatureScript
{
public:
    RareOverhaulCreatureScript() : AllCreatureScript("RareOverhaulCreatureScript") { }

    void OnCreatureAddWorld(Creature* creature) override
    {
        if (!RareOverhaulEnabled || !RareDifficultyEnabled || !IsRareCreature(creature))
            return;

        uint32 const oldMaxHealth = creature->GetMaxHealth();
        if (!oldMaxHealth)
            return;

        uint32 const newMaxHealth = std::max<uint32>(1, ScaleUnsigned(oldMaxHealth, RareHealthMultiplier));
        creature->SetMaxHealth(newMaxHealth);
        creature->SetHealth(newMaxHealth);
    }
};

class RareOverhaulUnitScript : public UnitScript
{
public:
    RareOverhaulUnitScript() : UnitScript("RareOverhaulUnitScript") { }

    uint32 DealDamage(Unit* attacker, Unit* /*victim*/, uint32 damage, DamageEffectType /*damageType*/) override
    {
        if (!RareOverhaulEnabled || !RareDifficultyEnabled || !attacker || damage == 0)
            return damage;

        Creature* creature = attacker->ToCreature();
        if (!IsRareCreature(creature))
            return damage;

        return ScaleUnsigned(damage, RareDamageMultiplier);
    }
};

void AddRareOverhaulScripts()
{
    new RareOverhaulConfigScript();
    new RareOverhaulCreatureScript();
    new RareOverhaulUnitScript();
}
