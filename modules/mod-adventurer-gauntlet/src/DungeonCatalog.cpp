#include "DungeonCatalog.h"

#include "Random.h"

#include <array>

namespace AdventurerGauntlet::DungeonCatalog
{
namespace
{
constexpr std::array<DungeonDefinition, 5> ClassicDungeons = {{
    { 389, "Sima Ignea", 3.81f, -14.82f, -17.84f, 4.39f, ExpansionPool::Classic },
    { 36, "Minas de la Muerte", -16.4f, -383.07f, 61.78f, 1.86f, ExpansionPool::Classic },
    { 34, "Las Mazmorras de Ventormenta", 54.23f, 0.28f, -18.34f, 6.26f, ExpansionPool::Classic },
    { 33, "Castillo de Colmillo Oscuro", -229.135f, 2109.18f, 76.8898f, 1.267f, ExpansionPool::Classic },
    { 189, "Monasterio Escarlata - Cementerio", 1688.99f, 1053.48f, 18.6775f, 0.00117f, ExpansionPool::Classic },
}};

constexpr std::array<DungeonDefinition, 4> OutlandDungeons = {{
    { 543, "Murallas del Fuego Infernal", -1355.24f, 1641.12f, 68.2491f, 0.6687f, ExpansionPool::Outland },
    { 542, "El Horno de Sangre", -3.9967f, 14.6363f, -44.8009f, 4.88748f, ExpansionPool::Outland },
    { 547, "Recinto de los Esclavos", 120.101f, -131.957f, -0.801547f, 1.47574f, ExpansionPool::Outland },
    { 557, "Tumbas de Mana", 0.0191f, 0.9478f, -0.9543f, 3.03164f, ExpansionPool::Outland },
}};

constexpr std::array<DungeonDefinition, 4> NorthrendDungeons = {{
    { 601, "Azjol-Nerub", 413.314f, 795.968f, 831.351f, 5.5f, ExpansionPool::Northrend },
    { 574, "Fortaleza de Utgarde", 153.789f, -86.548f, 12.551f, 0.304f, ExpansionPool::Northrend },
    { 576, "El Nexo", 145.87f, -10.554f, -16.636f, 1.528f, ExpansionPool::Northrend },
    { 604, "Gundrak", 1891.84f, 832.169f, 176.669f, 2.109f, ExpansionPool::Northrend },
}};

constexpr std::array<DungeonDefinition, 2> CampaignOnlyDungeons = {{
    { 230, "Profundidades de Roca Negra", 456.929f, 34.0923f, -68.0896f, 4.71239f, ExpansionPool::Classic },
    { 249, "Guarida de Onyxia", 29.1607f, -71.3372f, -8.18032f, 4.58f, ExpansionPool::Classic },
}};

template <std::size_t N>
DungeonDefinition const* FindIn(std::array<DungeonDefinition, N> const& pool, uint32 mapId)
{
    for (DungeonDefinition const& dungeon : pool)
        if (dungeon.MapId == mapId)
            return &dungeon;

    return nullptr;
}

template <std::size_t N>
DungeonDefinition const& Pick(std::array<DungeonDefinition, N> const& pool)
{
    return pool[urand(0, uint32(N - 1))];
}
}

DungeonDefinition const* GetDungeon(uint32 mapId)
{
    if (DungeonDefinition const* dungeon = FindIn(ClassicDungeons, mapId))
        return dungeon;
    if (DungeonDefinition const* dungeon = FindIn(OutlandDungeons, mapId))
        return dungeon;
    if (DungeonDefinition const* dungeon = FindIn(NorthrendDungeons, mapId))
        return dungeon;
    return FindIn(CampaignOnlyDungeons, mapId);
}

DungeonDefinition const& GetRandomDungeon(ExpansionPool pool)
{
    switch (pool)
    {
        case ExpansionPool::Classic:
            return Pick(ClassicDungeons);
        case ExpansionPool::Outland:
            return Pick(OutlandDungeons);
        case ExpansionPool::Northrend:
            return Pick(NorthrendDungeons);
    }

    return ClassicDungeons.front();
}

void GetDungeons(ExpansionPool pool, std::vector<DungeonDefinition const*>& out)
{
    out.clear();

    auto append = [&out](auto const& source)
    {
        for (DungeonDefinition const& dungeon : source)
            out.push_back(&dungeon);
    };

    switch (pool)
    {
        case ExpansionPool::Classic:
            append(ClassicDungeons);
            break;
        case ExpansionPool::Outland:
            append(OutlandDungeons);
            break;
        case ExpansionPool::Northrend:
            append(NorthrendDungeons);
            break;
    }
}

DungeonDefinition const* GetSpecificDungeonByMenuIndex(uint32 index)
{
    std::vector<DungeonDefinition const*> all;
    all.reserve(ClassicDungeons.size() + OutlandDungeons.size() + NorthrendDungeons.size());
    for (DungeonDefinition const& dungeon : ClassicDungeons)
        all.push_back(&dungeon);
    for (DungeonDefinition const& dungeon : OutlandDungeons)
        all.push_back(&dungeon);
    for (DungeonDefinition const& dungeon : NorthrendDungeons)
        all.push_back(&dungeon);

    return index < all.size() ? all[index] : nullptr;
}

bool IsSupportedDungeonMap(uint32 mapId)
{
    return GetDungeon(mapId) != nullptr;
}
}
