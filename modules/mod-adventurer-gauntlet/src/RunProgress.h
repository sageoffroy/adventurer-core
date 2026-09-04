#pragma once

#include "Define.h"

#include <string>
#include <vector>

class Player;

namespace AdventurerGauntlet::RunProgress
{
constexpr uint32 RagefireMapId = 389;
constexpr uint32 DeadminesMapId = 36;
constexpr uint32 HellfireRampartsMapId = 543;
constexpr uint32 AzjolNerubMapId = 601;

struct Position
{
    uint32 MapId = 0;
    float X = 0.0f;
    float Y = 0.0f;
    float Z = 0.0f;
    float O = 0.0f;
};

struct ActiveRun
{
    std::string CompanyName;
    std::string CampaignKey;
    uint8 RunLevel = 1;
    uint8 CurrentDungeon = 1;
    uint32 CurrentMap = 0;
    uint32 CurrentCheckpoint = 0;
    Position ReturnPoint;
};

struct ResumePoint
{
    uint32 CurrentMap = 0;
    Position LastPosition;
    bool LastPositionMatchesCurrentMap = false;
};

bool IsSupportedDungeonMap(uint32 mapId);

void StartRun(std::vector<Player*> const& members, std::string const& companyName, uint8 runLevel, uint32 initialMapId = RagefireMapId, std::string const& campaignKey = "");
void AdvanceDungeon(Player* player, uint8 dungeonIndex, uint32 mapId);
void SaveCheckpoint(Player* player, uint32 checkpoint);
void MarkMemberFallen(Player* player, bool runEnded);
void CompleteRun(Player* player);

bool LoadActiveRun(Player* player, ActiveRun& run);
uint32 LoadCheckpoint(Player* player);

void SaveLogoutPosition(Player* player);
bool LoadResumePoint(Player* player, ResumePoint& point);
}
