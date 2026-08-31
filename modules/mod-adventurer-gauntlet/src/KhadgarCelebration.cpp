#include "Creature.h"
#include "GameObject.h"
#include "Random.h"
#include "ScriptMgr.h"
#include "SharedDefines.h"

#include <array>

namespace
{
constexpr uint32 KhadgarEntry = 910000;
constexpr uint32 AccountStashEntry = 910002;
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
        if (!creature || creature->GetEntry() != KhadgarEntry || creature->GetMapId() != RagefireMapId || !creature->IsSummon())
            return;

        creature->CastSpell(creature, KhadgarTeleportVisual, true);
        creature->HandleEmoteCommand(EMOTE_ONESHOT_APPLAUD);
        creature->Say(
            KhadgarVictoryLines[urand(0, KhadgarVictoryLines.size() - 1)],
            LANG_UNIVERSAL);

        // The final boss now owns its reward directly. Khadgar only brings the
        // account stash so survivors can secure equipment before continuing.
        creature->SummonGameObject(
            AccountStashEntry,
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
