#!/usr/bin/env python3
"""Apply Adventurer Core source transforms and fixed-item client metadata."""

from __future__ import annotations

import adventurer_items
import client
import core_patch

ITEM_DBC = "Item.dbc"

# Item.dbc participates in the same atomic client/server build as every other
# Adventurer DBC. The item catalog is the only editable fixed-item source.
client.CLASS_DBCS = client.CLASS_DBCS + (ITEM_DBC,)
client.DBC_NAMES = client.CLASS_DBCS + client.TALENT_DBCS
client.DBC_SOURCE_NAMES = client.DBC_NAMES + client.TALENT_SOURCE_ONLY_DBCS
client.ROOT_SHARED_DBCS = client.ROOT_SHARED_DBCS + (ITEM_DBC,)

_original_patch_dbc_copy = client.patch_dbc_copy


def _patch_dbc_copy(source, work):
    changed = _original_patch_dbc_copy(source, work)
    changed[ITEM_DBC] = (
        adventurer_items.patch_item_dbc(work / ITEM_DBC)
        or changed.get(ITEM_DBC, False)
    )
    return changed


client.patch_dbc_copy = _patch_dbc_copy


# Tame Beast (1515) is a native Hunter spell, but SpellDraft can legitimately
# grant it to class 10. Keep AzerothCore's normal tame flow and relax only the
# final class gate for an Adventurer that actually knows 1515.
def _patch_adventurer_tame_beast(text: str) -> str:
    clean = """    if (!m_caster->IsClass(CLASS_HUNTER, CLASS_CONTEXT_PET))
        return;"""
    patched = """    if (!m_caster->IsClass(CLASS_HUNTER, CLASS_CONTEXT_PET))
    {
        Player* player = m_caster->ToPlayer();
        if (!player || player->getClass() != CLASS_ADVENTURER || !player->HasSpell(1515))
            return;
    }"""
    return core_patch.replace_once(
        text,
        clean,
        patched,
        "SpellEffects Adventurer Tame Beast class gate",
    )


core_patch.TRANSFORMS["src/server/game/Spells/SpellEffects.cpp"] = _patch_adventurer_tame_beast

# Keep the source-layer universal chassis at 75% while accepting an existing
# owned 75% install on future upgrades.
import chassis_75  # noqa: E402,F401

# Import only after the client/core contracts above have been extended so the
# front-end captures the complete DBC list and patched source transforms.
import adventurer  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(adventurer.main())
