#!/usr/bin/env python3
"""Attach SpellDraft v3 icons and Gauntlet v3 DBC rows to the client pipeline."""

from __future__ import annotations

import client
import gauntlet_spells
import icon_pack

SPELL_ICON_DBC = "SpellIcon.dbc"
_enabled = False


def enable() -> None:
    global _enabled
    if _enabled:
        return
    _enabled = True

    if SPELL_ICON_DBC not in client.CLASS_DBCS:
        client.CLASS_DBCS = client.CLASS_DBCS + (SPELL_ICON_DBC,)
    client.TALENT_SOURCE_ONLY_DBCS = tuple(
        name for name in client.TALENT_SOURCE_ONLY_DBCS if name != SPELL_ICON_DBC
    )
    client.DBC_NAMES = client.CLASS_DBCS + client.TALENT_DBCS
    client.DBC_SOURCE_NAMES = client.DBC_NAMES + client.TALENT_SOURCE_ONLY_DBCS
    if SPELL_ICON_DBC not in client.ROOT_SHARED_DBCS:
        client.ROOT_SHARED_DBCS = client.ROOT_SHARED_DBCS + (SPELL_ICON_DBC,)

    original_patch_dbc_copy = client.patch_dbc_copy

    def patch_dbc_copy(source, work):
        changed = original_patch_dbc_copy(source, work)
        changed[SPELL_ICON_DBC] = icon_pack.patch_spell_icon(work / SPELL_ICON_DBC)
        gauntlet_changed = gauntlet_spells.patch(work / "Spell.dbc")
        changed["Spell.dbc"] = gauntlet_changed or changed.get("Spell.dbc", False)
        return changed

    client.patch_dbc_copy = patch_dbc_copy

    original_build_archive_files = client.build_archive_files

    def build_archive_files(work):
        root_files, locale_files = original_build_archive_files(work)
        icon_files = icon_pack.icon_archive_files()
        overlap = set(root_files) & set(icon_files)
        if overlap:
            raise client.ClientError(
                "SpellDraft v3 icon pack collides with another Adventurer client payload: "
                + ", ".join(sorted(overlap))
            )
        root_files.update(icon_files)
        return root_files, locale_files

    client.build_archive_files = build_archive_files
