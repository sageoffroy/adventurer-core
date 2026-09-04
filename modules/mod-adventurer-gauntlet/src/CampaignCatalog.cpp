#include "CampaignCatalog.h"

namespace AdventurerGauntlet::CampaignCatalog
{
namespace
{
constexpr CampaignDefinition StormwindShadow = {
    StormwindShadowKey,
    "La sombra sobre Ventormenta",
    {{
        {
            1, 36, 639,
            "En los ultimos pensamientos de VanCleef, Khadgar encuentra un nombre: Bazil Thredd, encerrado en las Mazmorras de Ventormenta."
        },
        {
            2, 34, 1716,
            "Los recuerdos de Thredd muestran cartas, una figura entre los nobles y una obsesion con Montana Roca Negra. Khadgar decide seguir esa pista."
        },
        {
            3, 230, 9019,
            "En la mente de Thaurissan aparece Nefarian... y una hermana que viaja entre Roca Negra y Ventormenta. Khadgar ya sabe a quien busca: Onyxia."
        },
        {
            4, 249, 10184,
            "Onyxia ha caido. La sombra sobre Ventormenta termina aqui."
        },
    }}
};
}

CampaignDefinition const* GetCampaign(std::string_view key)
{
    return key == StormwindShadow.Key ? &StormwindShadow : nullptr;
}

CampaignStage const* GetStage(CampaignDefinition const& campaign, uint8 index)
{
    if (index < 1 || index > campaign.Stages.size())
        return nullptr;

    return &campaign.Stages[index - 1];
}

CampaignStage const* GetStageForMap(CampaignDefinition const& campaign, uint32 mapId)
{
    for (CampaignStage const& stage : campaign.Stages)
        if (stage.MapId == mapId)
            return &stage;

    return nullptr;
}
}
