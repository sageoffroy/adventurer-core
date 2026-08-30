#!/usr/bin/env python3
"""Make the Adventurer universal chassis use 75% of the best native formula.

The base core patcher historically emitted 80% formulas.  This narrow adapter
keeps upgrades compatible with already-installed 75% source by normalizing the
owned 75% form back to the known 80% predecessor before the normal transform,
then emits the 75% form.  Stock AzerothCore and older 95% Adventurer installs
continue to flow through the existing strict anchor checks.
"""

from __future__ import annotations

import core_patch


STAT_PATH = "src/server/game/Entities/Unit/StatSystem.cpp"
PLAYER_PATH = "src/server/game/Entities/Player/Player.cpp"


STAT_80_TO_75 = (
    ("Universal ranged baseline: 80% of Hunter's native formula.",
     "Universal ranged baseline: 75% of Hunter's native formula."),
    ("val2 = (level * 2.0f + effectiveAgility - 10.0f) * 0.80f;",
     "val2 = (level * 2.0f + effectiveAgility - 10.0f) * 0.75f;"),
    ("archetypes and keep 80% of whichever the current gear favours.",
     "archetypes and keep 75% of whichever the current gear favours."),
    ("val2 = (strengthBaseline > hybridBaseline ? strengthBaseline : hybridBaseline) * 0.80f;",
     "val2 = (strengthBaseline > hybridBaseline ? strengthBaseline : hybridBaseline) * 0.75f;"),
)

PLAYER_80_TO_75 = (
    ("0.044878f, // Adventurer 80% fallback; runtime compares complete native formulas",
     "0.042073f, // Adventurer 75% fallback; runtime compares complete native formulas"),
    ("return (found ? bestCrit * 0.80f : 0.0f) * 100.0f;",
     "return (found ? bestCrit * 0.75f : 0.0f) * 100.0f;"),
    ("then keep 80% of it as the Adventurer chassis baseline.",
     "then keep 75% of it as the Adventurer chassis baseline."),
    ("diminishing = found ? bestDiminishing * 0.80f : 0.0f;",
     "diminishing = found ? bestDiminishing * 0.75f : 0.0f;"),
    ("nondiminishing = found ? bestNondiminishing * 0.80f : 0.0f;",
     "nondiminishing = found ? bestNondiminishing * 0.75f : 0.0f;"),
)


def _replace_pairs(text: str, pairs: tuple[tuple[str, str], ...]) -> str:
    for old, new in pairs:
        text = text.replace(old, new)
    return text


def _normalize_75(text: str, pairs: tuple[tuple[str, str], ...]) -> str:
    for old, new in pairs:
        text = text.replace(new, old)
    return text


def _wrap(transform, pairs):
    def wrapped(text: str) -> str:
        normalized = _normalize_75(text, pairs)
        patched = transform(normalized)
        return _replace_pairs(patched, pairs)
    return wrapped


core_patch.TRANSFORMS[STAT_PATH] = _wrap(core_patch.TRANSFORMS[STAT_PATH], STAT_80_TO_75)
core_patch.TRANSFORMS[PLAYER_PATH] = _wrap(core_patch.TRANSFORMS[PLAYER_PATH], PLAYER_80_TO_75)
