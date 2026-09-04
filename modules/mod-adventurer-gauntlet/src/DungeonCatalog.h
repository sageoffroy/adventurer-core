#pragma once

#include "Define.h"

namespace AdventurerGauntlet::DungeonCatalog
{
enum class ExpansionPool : uint8
{
    Classic,
    Outland,
    Northrend,
};

struct DungeonDefinition
{
    uint32 MapId;
    char const* Name;
    float X;
    float Y;
    float Z;
    float O;
    ExpansionPool Pool;
};

DungeonDefinition const* GetDungeon(uint32 mapId);
DungeonDefinition const& GetRandomDungeon(ExpansionPool pool);
bool IsSupportedDungeonMap(uint32 mapId);
}
