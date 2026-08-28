"""Authoritative first-batch DK contract and level curves.

This module does not activate unfinished cards. IDs are proposed owned IDs;
the DBC preflight must reject collisions before any installation writes.
Rage costs are stored in server units (ten units per displayed rage point).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from dbc import DBC, DBCError, u32


@dataclass(frozen=True)
class Ability:
    key: str
    branch: str
    native_id: int
    first_id: int
    resource: str
    cost: int
    base_mana_percent: int = 0
    scaled: bool = False

    @property
    def spell_ids(self) -> tuple[int, ...]:
        return tuple(range(self.first_id, self.first_id + (80 if self.scaled else 1)))


# Order is intentional: these are the FIRST FOUR agreed abilities per branch,
# not four arbitrary spells selected from the completed design.
ABILITIES = (
    Ability("blood_presence", "blood", 48266, 280001, "mana", 0),
    Ability("blood_strike", "blood", 45902, 280101, "rage", 150, scaled=True),
    Ability("blood_tap", "blood", 45529, 280201, "all_current_rage", 0),
    Ability("dark_command", "blood", 56222, 280301, "rage", 100),
    Ability("icy_touch", "frost", 45477, 280401, "mana", 0, 8, True),
    Ability("frost_presence", "frost", 48263, 280501, "mana", 0),
    Ability("mind_freeze", "frost", 47528, 280601, "mana", 0, 3),
    Ability("chains_of_ice", "frost", 45524, 280701, "mana", 0, 8),
    Ability("death_grip", "unholy", 49576, 280801, "energy", 30),
    Ability("plague_strike", "unholy", 45462, 280901, "energy", 40, scaled=True),
    Ability("death_strike", "unholy", 49998, 281001, "energy_and_combo", 35, scaled=True),
    Ability("raise_dead", "unholy", 46584, 281101, "energy", 50),
)

# Additives here are EFFECTIVE damage after the weapon multiplier. Keeping
# decimal strings prevents binary-float rounding from changing native anchors.
BLOOD_STRIKE = ((1, "7"), (8, "14"), (55, "104"), (59, "118"),
                (64, "138.8"), (69, "164.4"), (74, "250"), (80, "305.6"))
PLAGUE_STRIKE = ((1, "4"), (8, "8"), (55, "62.5"), (60, "75.5"),
                 (65, "89"), (70, "108"), (75, "157"), (80, "189"))
ICY_TOUCH_MIN = ((1, "8"), (8, "16"), (55, "127"), (61, "144"),
                 (67, "161"), (73, "187"), (78, "227"), (80, "227"))
ICY_TOUCH_MAX = ((1, "9"), (8, "17"), (55, "137"), (61, "156"),
                 (67, "173"), (73, "203"), (78, "245"), (80, "245"))

EVISCERATE_RANKS = (2098, 6760, 6761, 6762, 8623, 8624,
                    11299, 11300, 31016, 26865, 48667, 48668)


def interpolate(anchors: tuple[tuple[int, str], ...], level: int) -> Decimal:
    if not 1 <= level <= 80:
        raise ValueError("DK level must be between 1 and 80")
    if not anchors or anchors[0][0] != 1 or anchors[-1][0] != 80:
        raise ValueError("Curve must cover levels 1 through 80")
    if any(a[0] >= b[0] for a, b in zip(anchors, anchors[1:])):
        raise ValueError("Curve anchors must have strictly increasing levels")
    for (low, start), (high, end) in zip(anchors, anchors[1:]):
        if low <= level <= high:
            return Decimal(start) + (Decimal(end) - Decimal(start)) * (level - low) / (high - low)
    raise ValueError("Level is not covered by curve")


def rounded(value: Decimal) -> int:
    return int(value.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def level_values(level: int) -> dict[str, int | Decimal]:
    """Native weapon effects multiply their additive as well as weapon damage.

    Encode the additive BEFORE that multiplication; never feed the effective
    table value directly into EffectBasePoints. Native effects have integer
    resolution, so effective damage is quantized to 0.4 and 0.5 respectively.
    """
    blood_raw = rounded(interpolate(BLOOD_STRIKE, level) / Decimal("0.4"))
    plague_raw = rounded(interpolate(PLAGUE_STRIKE, level) / Decimal("0.5"))
    return {
        "blood_raw_additive": blood_raw,
        "blood_effective_additive": Decimal(blood_raw) * Decimal("0.4"),
        "plague_raw_additive": plague_raw,
        "plague_effective_additive": Decimal(plague_raw) * Decimal("0.5"),
        "icy_touch_min": rounded(interpolate(ICY_TOUCH_MIN, level)),
        "icy_touch_max": rounded(interpolate(ICY_TOUCH_MAX, level)),
    }


def blood_tap_energy(current_rage: int, current_energy: int, maximum_energy: int = 100) -> int:
    """Energy gained; ALL rage is consumed, including any unusable remainder."""
    if current_rage <= 0:
        raise ValueError("Blood Tap requires positive rage")
    if not 0 <= current_energy <= maximum_energy:
        raise ValueError("Energy is outside its valid range")
    return min(current_rage // 10, maximum_energy - current_energy)


def preflight(path: Path) -> DBC:
    """Read a CLEAN Spell.dbc, failing without writing on absent/colliding IDs.

    Clean input is required deliberately: installation ownership must be checked
    by the installer before reusing already-generated custom spell rows.
    """
    dbc = DBC.read(path)
    if dbc.fields != 234 or dbc.record_size != 936:
        raise DBCError(f"{path}: expected WotLK Spell.dbc layout 234/936")
    ids = [u32(row, 0) for row in dbc.records]
    existing = set(ids)
    if len(ids) != len(existing):
        raise DBCError(f"{path}: duplicate spell IDs")
    owned = {spell for ability in ABILITIES for spell in ability.spell_ids}
    collisions = sorted(existing & owned)
    if collisions:
        raise DBCError(f"{path}: DK custom spell ID collisions: {collisions}")
    required = {ability.native_id for ability in ABILITIES} | set(EVISCERATE_RANKS)
    required.update((55078, 55095))
    missing = sorted(required - existing)
    if missing:
        raise DBCError(f"{path}: missing DK/Eviscerate templates: {missing}")
    return dbc
