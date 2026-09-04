#pragma once

#include "Define.h"

#include <array>
#include <string_view>

namespace AdventurerGauntlet::CampaignCatalog
{
constexpr char StormwindShadowKey[] = "stormwind_shadow";

struct CampaignStage
{
    uint8 Index;
    uint32 MapId;
    uint32 FinalBossEntry;
    char const* TransitionText;
};

struct CampaignDefinition
{
    char const* Key;
    char const* Name;
    std::array<CampaignStage, 4> Stages;
};

CampaignDefinition const* GetCampaign(std::string_view key);
CampaignStage const* GetStage(CampaignDefinition const& campaign, uint8 index);
CampaignStage const* GetStageForMap(CampaignDefinition const& campaign, uint32 mapId);
}
