#pragma once

#include "Define.h"

#include <vector>

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
    uint8 NativeBaseLevel;
};

DungeonDefinition const* GetDungeon(uint32 mapId);
DungeonDefinition const& GetRandomDungeon(ExpansionPool pool);
void GetDungeons(ExpansionPool pool, std::vector<DungeonDefinition const*>& out);
DungeonDefinition const* GetSpecificDungeonByMenuIndex(uint32 index);
bool IsSupportedDungeonMap(uint32 mapId);
}
