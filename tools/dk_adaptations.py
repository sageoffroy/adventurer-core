"""Adapt native Icy Touch in the normal Adventurer DBC/source/client pipeline.

No cloned IDs, new rank chains, disease scripts or parallel runtime are used.
The reviewed curve is shared by the native effect calculation and its tooltip.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import struct

from dbc import DBC, DBCError, set_u32, u32

ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "config/spelldraft/icy_touch.json"
HEADER_RELATIVE = "src/server/game/Spells/AdventurerSpellScaling.h"
MARKER = "@ADVENTURER_ICY_TOUCH_DAMAGE@"


def load_spec() -> dict:
    spec = json.loads(SPEC_PATH.read_text(encoding="utf-8"))
    if spec.get("schema") != 1 or spec.get("native_ranks") != [45477, 49896, 49903, 49904, 49909]:
        raise DBCError("Icy Touch: invalid schema or native rank family")
    if spec.get("native_levels") != [55, 61, 67, 73, 78] or spec.get("base_mana_percent") != 8:
        raise DBCError("Icy Touch: invalid native anchors or reviewed mana cost")
    anchors = spec["anchors"]
    if (not anchors or anchors[0][0] != 1 or anchors[-1][0] != 80
            or any(len(a) != 3 or any(type(x) is not int for x in a) or not 0 < a[1] <= a[2]
                   for a in anchors)
            or any(a[0] >= b[0] for a, b in zip(anchors, anchors[1:]))):
        raise DBCError("Icy Touch: curve must cover levels 1..80 with ordered integer anchors")
    return spec


def damage_range(level: int, spec: dict | None = None) -> tuple[int, int]:
    if not 1 <= level <= 80:
        raise ValueError("Icy Touch level must be in 1..80")
    anchors = (spec or load_spec())["anchors"]
    for start, end in zip(anchors, anchors[1:]):
        if start[0] <= level <= end[0]:
            width = end[0] - start[0]
            # Exact rational interpolation, nearest integer, ties upwards.
            return tuple((2 * (start[i] * width + (end[i] - start[i]) * (level - start[0]))
                          + width) // (2 * width) for i in (1, 2))
    raise ValueError("Icy Touch level is not covered")


def render_header() -> bytes:
    spec = load_spec()
    rows = ",\n".join(f"    {{{low}, {high}}}" for low, high in
                       (damage_range(level, spec) for level in range(1, 81)))
    ids = " || ".join(f"spell == {spell}" for spell in spec["native_ranks"])
    return f"""// Generated from config/spelldraft/icy_touch.json. Do not edit by hand.
#ifndef ADVENTURER_SPELL_SCALING_H
#define ADVENTURER_SPELL_SCALING_H

#include <array>
#include <cstdint>

namespace AdventurerSpells
{{
struct DamageRange
{{
    std::int32_t minimum;
    std::int32_t maximum;
}};

inline constexpr std::array<DamageRange, 80> IcyTouchLevels = {{{{
{rows}
}}}};

constexpr bool IsIcyTouch(std::uint32_t spell)
{{
    return {ids};
}}

constexpr DamageRange IcyTouchRange(std::uint32_t level)
{{
    return IcyTouchLevels[(level < 1 ? 1 : level > 80 ? 80 : level) - 1];
}}

constexpr std::int32_t IcyTouchManaCost(std::uint32_t baseMana)
{{
    auto const cost = (std::uint64_t(baseMana) * {spec['base_mana_percent']} + 50) / 100;
    return std::int32_t(cost ? cost : 1);
}}
}}

#endif
""".encode("utf-8")


def render_lua_data() -> bytes:
    spec = load_spec()
    rows = ",\n".join(f"    {{{low}, {high}}}" for low, high in
                       (damage_range(level, spec) for level in range(1, 81)))
    # Fallback for older non-Adventurer characters viewing a spell link.
    native = ", ".join(f"[{spell}] = {{{low}, {high}}}" for spell, (low, high) in
                       zip(spec["native_ranks"], (damage_range(1 if i == 0 else level, spec)
                           for i, level in enumerate(spec["native_levels"]))))
    return f"""-- Generated from config/spelldraft/icy_touch.json; same values as the server.
local IcyTouchLevels = {{
{rows}
}}
local IcyTouchNativeRanks = {{{native}}}
local IcyTouchDamageMarker = "{MARKER}"
""".encode("utf-8")


def patch_dk_directory(directory: Path) -> dict[str, bool]:
    """Edit native rows in staging; write only after every preflight succeeds."""
    spec = load_spec()
    path = directory / "Spell.dbc"
    dbc = DBC.read(path)
    if (dbc.fields, dbc.record_size) != (234, 936):
        raise DBCError("Icy Touch: expected WotLK Spell.dbc layout 234/936")
    rows = {u32(row, 0): row for row in dbc.records}
    if len(rows) != len(dbc.records):
        raise DBCError("Icy Touch: duplicate Spell.dbc IDs")
    missing = sorted(set(spec["native_ranks"] + [55095]) - rows.keys())
    if missing:
        raise DBCError(f"Icy Touch: missing native spells {missing}")

    talents = DBC.read(directory / "Talent.dbc")
    if (talents.fields, talents.record_size) != (23, 92):
        raise DBCError("Icy Touch: expected WotLK Talent.dbc layout 23/92")
    talent_families = {u32(row, 4): [u32(row, i) for i in range(4, 9) if u32(row, i)]
                       for row in talents.records}
    for talent in spec["talent_roots"]:
        if talent not in talent_families or any(rank not in rows for rank in talent_families[talent]):
            raise DBCError(f"Icy Touch: missing native talent family {talent}")
    for spell in spec["native_ranks"]:
        row = rows[spell]
        if u32(row, 71) != 2 or u32(row, 72) != 64 or u32(row, 117) != 55095:
            raise DBCError(f"Icy Touch {spell}: expected native damage + Frost Fever trigger")
        if u32(row, 208) != 15 or not u32(row, 209) & 2 or u32(row, 227) != 16:
            raise DBCError(f"Icy Touch {spell}: unexpected native DK family/flags or Frost school")

    before = dbc.to_bytes()
    descriptions = {
        "en": f"Deals {MARKER} base Frost damage (before talents), plus 10% of your attack power. "
              "Infects the target with Frost Fever, dealing periodic damage and reducing melee "
              "and ranged attack speed by $55095s2% for $55095d. "
              "Very high threat in Frost Presence. Costs 8% of base mana; no runes or runic power.",
        "es": f"Inflige {MARKER} de daño base de Escarcha (antes de talentos), más un 10% de tu poder de ataque. "
              "Aplica Fiebre de Escarcha: causa daño periódico y reduce la velocidad de ataque cuerpo a cuerpo "
              "y a distancia un $55095s2% durante $55095d. "
              "Amenaza muy elevada en Presencia de escarcha. Cuesta un 8% del maná base; sin runas ni poder rúnico.",
    }
    for spell in spec["native_ranks"]:
        row = rows[spell]
        for field in (12, 13, 14, 15, 41, 42, 43, 44, 45, 226, 228):
            set_u32(row, field, 0)
        set_u32(row, 204, spec["base_mana_percent"])
        # Amount scaling belongs to the narrowly scoped native CalcValue patch.
        struct.pack_into("<f", row, 77 * 4, 0.0)
        if spell == spec["native_ranks"][0]:
            set_u32(row, 38, 1)
            set_u32(row, 39, 1)
            low, high = damage_range(1, spec)
            set_u32(row, 80, low - 1)
            set_u32(row, 74, high - low + 1)
        for locale in range(16):
            set_u32(row, 170 + locale, dbc.append_string(descriptions["es" if locale in (6, 7) else "en"]))
    after = dbc.to_bytes()
    if after != before:
        path.write_bytes(after)
    return {"Spell.dbc": after != before}


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate/check the shared native Icy Touch curve")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    header = ROOT / "payload/core" / HEADER_RELATIVE
    expected = render_header()
    if args.check:
        if not header.is_file() or header.read_bytes() != expected:
            raise SystemExit("Icy Touch generated header is stale; run tools/dk_adaptations.py")
    else:
        header.parent.mkdir(parents=True, exist_ok=True)
        header.write_bytes(expected)


if __name__ == "__main__":
    main()
