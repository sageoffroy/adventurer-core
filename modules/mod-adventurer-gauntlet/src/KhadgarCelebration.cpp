#include "Creature.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"

#include <array>

namespace
{
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 ExpeditionChestEntry = 910001;
constexpr uint32 KhadgarTeleportVisual = 41232;
constexpr uint32 RagefireMapId = 389;

constexpr std::array<char const*, 8> KhadgarVictoryLines = {
    "Pensaba que no llegarian ni al primer jefe.",
    "Admito que esperaba bastante menos de ustedes.",
    "No estuvo mal... para principiantes.",
    "Empiezo a creer que esto puede ponerse interesante.",
    "Bien. Sobrevivieron. No se acostumbren.",
    "Vaya. Tal vez no haya sobreestimado sus posibilidades despues de todo.",
    "Debo admitirlo: ya estaba preparando unas palabras para su funeral.",
    "Excelente. Ahora veamos cuanto dura esa confianza en la siguiente mazmorra."
};
}

class AdventurerGauntletKhadgarCelebrationScript : public AllCreatureScript
{
public:
    AdventurerGauntletKhadgarCelebrationScript()
        : AllCreatureScript("AdventurerGauntletKhadgarCelebrationScript") { }

    void OnCreatureAddWorld(Creature* creature) override
    {
        // The permanent Khadgar is outside the dungeon. A summoned Khadgar in
        // Ragefire is the expedition guide that appears after the final boss.
        if (!creature || creature->GetEntry() != KhadgarEntry || creature->GetMapId() != RagefireMapId || !creature->IsSummon())
            return;

        // Make his arrival visible instead of having him simply pop into existence.
        creature->CastSpell(creature, KhadgarTeleportVisual, true);
        creature->HandleEmoteCommand(EMOTE_ONESHOT_APPLAUD);
        creature->Say(
            KhadgarVictoryLines[urand(0, KhadgarVictoryLines.size() - 1)],
            LANG_UNIVERSAL);

        // The expedition chest uses a stock 3.3.5a chest model. For this milestone
        // it is deliberately empty; the random equipment generator is connected next.
        creature->SummonGameObject(
            ExpeditionChestEntry,
            creature->GetPositionX(),
            creature->GetPositionY() - 2.5f,
            creature->GetPositionZ(),
            0.0f,
            0.0f,
            0.0f,
            0.0f,
            1.0f,
            0);
    }
};

void AddAdventurerGauntletCelebrationScripts()
{
    new AdventurerGauntletKhadgarCelebrationScript();
}
