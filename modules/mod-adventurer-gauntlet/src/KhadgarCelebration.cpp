#include "Creature.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"

#include <array>

namespace
{
constexpr uint32 KhadgarEntry = 910000;
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

        creature->HandleEmoteCommand(EMOTE_ONESHOT_APPLAUD);
        creature->Say(
            KhadgarVictoryLines[urand(0, KhadgarVictoryLines.size() - 1)],
            LANG_UNIVERSAL);
    }
};

void AddAdventurerGauntletCelebrationScripts()
{
    new AdventurerGauntletKhadgarCelebrationScript();
}
