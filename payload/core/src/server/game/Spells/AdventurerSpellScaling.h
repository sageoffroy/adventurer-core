// Generated from config/spelldraft/icy_touch.json. Do not edit by hand.
#ifndef ADVENTURER_SPELL_SCALING_H
#define ADVENTURER_SPELL_SCALING_H

#include <array>
#include <cstdint>

namespace AdventurerSpells
{
struct DamageRange
{
    std::int32_t minimum;
    std::int32_t maximum;
};

inline constexpr std::array<DamageRange, 80> IcyTouchLevels = {{
    {8, 9},
    {9, 10},
    {10, 11},
    {11, 12},
    {13, 14},
    {14, 15},
    {15, 16},
    {16, 17},
    {18, 20},
    {21, 22},
    {23, 25},
    {25, 27},
    {28, 30},
    {30, 32},
    {33, 35},
    {35, 37},
    {37, 40},
    {40, 43},
    {42, 45},
    {44, 48},
    {47, 50},
    {49, 53},
    {51, 55},
    {54, 58},
    {56, 60},
    {59, 63},
    {61, 66},
    {63, 68},
    {66, 71},
    {68, 73},
    {70, 76},
    {73, 78},
    {75, 81},
    {77, 83},
    {80, 86},
    {82, 88},
    {84, 91},
    {87, 94},
    {89, 96},
    {92, 99},
    {94, 101},
    {96, 104},
    {99, 106},
    {101, 109},
    {103, 111},
    {106, 114},
    {108, 117},
    {110, 119},
    {113, 122},
    {115, 124},
    {118, 127},
    {120, 129},
    {122, 132},
    {125, 134},
    {127, 137},
    {130, 140},
    {133, 143},
    {136, 147},
    {138, 150},
    {141, 153},
    {144, 156},
    {147, 159},
    {150, 162},
    {153, 165},
    {155, 167},
    {158, 170},
    {161, 173},
    {165, 178},
    {170, 183},
    {174, 188},
    {178, 193},
    {183, 198},
    {187, 203},
    {195, 211},
    {203, 220},
    {211, 228},
    {219, 237},
    {227, 245},
    {227, 245},
    {227, 245}
}};

constexpr bool IsIcyTouch(std::uint32_t spell)
{
    return spell == 45477 || spell == 49896 || spell == 49903 || spell == 49904 || spell == 49909;
}

constexpr DamageRange IcyTouchRange(std::uint32_t level)
{
    return IcyTouchLevels[(level < 1 ? 1 : level > 80 ? 80 : level) - 1];
}

constexpr std::int32_t IcyTouchManaCost(std::uint32_t baseMana)
{
    auto const cost = (std::uint64_t(baseMana) * 8 + 50) / 100;
    return std::int32_t(cost ? cost : 1);
}
}

#endif
