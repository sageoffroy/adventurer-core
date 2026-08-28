"""First-batch DK spell transformation in the existing client/server pipeline.

The DBC and world preflights reject owned-ID collisions before installation.
Rage costs are stored in server units (ten units per displayed rage point).
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import struct

from dbc import DBC, DBCError, set_u32, u32


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

FROST_THREAT = 282001
DEATH_STRIKE_HEAL = 282002
RAISE_DEAD_GUARDIAN = 282003
AUXILIARY_IDS = {FROST_THREAT, DEATH_STRIKE_HEAL, RAISE_DEAD_GUARDIAN}
MINIMUM_LEVEL = {"blood_tap": 10, "dark_command": 10, "mind_freeze": 12,
                 "chains_of_ice": 8, "raise_dead": 10}
COOLDOWN_MS = {"blood_presence": 1000, "frost_presence": 1000,
               "dark_command": 8000, "mind_freeze": 10000,
               "chains_of_ice": 8000, "death_grip": 35000, "raise_dead": 180000}
NO_GCD = {"blood_presence", "frost_presence", "dark_command", "mind_freeze", "death_grip"}

# Only audited, resource-independent talents. Native family masks are retained
# on every owned rank. Rune/RP and permanent-ghoul talents are deliberately absent.
TALENTS = {
    "blood_strike": (48977,),
    "icy_touch": (49175, 55061, 49140, 49036),
    "chains_of_ice": (55061, 49036),
    "death_grip": (49588,),
    "plague_strike": (51745, 49013, 49036),
}


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
    owned = {spell for ability in ABILITIES for spell in ability.spell_ids} | AUXILIARY_IDS
    collisions = sorted(existing & owned)
    if collisions:
        raise DBCError(f"{path}: DK custom spell ID collisions: {collisions}")
    required = {ability.native_id for ability in ABILITIES} | set(EVISCERATE_RANKS)
    required.update((55078, 55095, 45470, 63611, 49575))
    missing = sorted(required - existing)
    if missing:
        raise DBCError(f"{path}: missing DK/Eviscerate templates: {missing}")
    return dbc


def _i32(row: bytearray, field: int) -> int:
    return struct.unpack_from("<i", row, field * 4)[0]


def _set_i32(row: bytearray, field: int, value: int) -> None:
    struct.pack_into("<i", row, field * 4, value)


def _float(row: bytearray, field: int) -> float:
    return struct.unpack_from("<f", row, field * 4)[0]


def _clear_effects(row: bytearray) -> None:
    for field in range(71, 131):
        set_u32(row, field, 0)
    for field in range(229, 232):
        set_u32(row, field, 0)


def _effect(row: bytearray, index: int, effect: int, value: int = 0,
            *, target: int = 6, aura: int = 0, misc: int = 0) -> None:
    set_u32(row, 71 + index, effect)
    set_u32(row, 74 + index, 1)
    _set_i32(row, 80 + index, value - 1)
    set_u32(row, 86 + index, target)
    set_u32(row, 95 + index, aura)
    _set_i32(row, 110 + index, misc)


def _text(dbc: DBC, row: bytearray, english: str, spanish: str) -> None:
    for locale in range(16):
        set_u32(row, 170 + locale, dbc.append_string(spanish if locale in (6, 7) else english))
        # Do not retain native rune/RP tooltips or native high-level rank labels.
        set_u32(row, 187 + locale, 0)
        set_u32(row, 153 + locale, 0)


def _duration(directory: Path, milliseconds: int) -> int:
    dbc = DBC.read(directory / "SpellDuration.dbc")
    if dbc.fields != 4 or dbc.record_size != 16:
        raise DBCError("SpellDuration.dbc: expected WotLK layout 4/16")
    rows = [row for row in dbc.records
            if _i32(row, 1) == milliseconds and _i32(row, 2) == 0
            and _i32(row, 3) == milliseconds]
    if not rows:
        raise DBCError(f"SpellDuration.dbc: no fixed {milliseconds}ms duration")
    return min(u32(row, 0) for row in rows)


def _eviscerate_template(templates: dict[int, bytearray], level: int) -> bytearray:
    # The server's native family upgrades discretely. At duplicate levels (60)
    # retain the later/stronger rank, matching the package's rank-up behavior.
    ranks = [templates[spell] for spell in EVISCERATE_RANKS]
    usable = [row for row in ranks if max(u32(row, 38), u32(row, 39)) <= level]
    return max(usable or ranks[:1], key=lambda row: (
        max(u32(row, 38), u32(row, 39)), _i32(row, 80) + 5 * _float(row, 119)))


def patch_dk_directory(directory: Path) -> dict[str, bool]:
    """Generate owned spells from clean source; never mutate native spells.

    Called once in the client's temporary staging directory, before packaging
    the SAME Spell.dbc bytes for server, root MPQ and locale MPQ. All validation
    and construction happens before the only write at the end.
    """
    path = directory / "Spell.dbc"
    dbc = preflight(path)
    talents = DBC.read(directory / "Talent.dbc")
    if talents.fields != 23 or talents.record_size != 92:
        raise DBCError("Talent.dbc: expected WotLK layout 23/92")
    native_talents = {u32(row, field) for row in talents.records for field in range(4, 9)}
    missing_talents = sorted({spell for ranks in TALENTS.values() for spell in ranks} - native_talents)
    if missing_talents:
        raise DBCError(f"Talent.dbc: missing DK talent definitions: {missing_talents}")
    templates = {u32(row, 0): row for row in dbc.records}
    duration_60s = _duration(directory, 60000)
    guardian_id = _i32(templates[46584], 81) + 1
    if guardian_id not in templates or not any(u32(templates[guardian_id], 71 + i) == 28 for i in range(3)):
        raise DBCError("Raise Dead: native guardian summon template not found")
    created = []
    for ability in ABILITIES:
        for offset, spell_id in enumerate(ability.spell_ids):
            level = offset + 1 if ability.scaled else MINIMUM_LEVEL.get(ability.key, 1)
            row = bytearray(templates[ability.native_id])
            for field in (1, 12, 13, 14, 15, 30, 37, 43, 44, 45, 226, 228):
                set_u32(row, field, 0)
            for field in (*range(50, 68), 222, 223, 77, 78, 79, 229, 230, 231):
                set_u32(row, field, 0)
            set_u32(row, 0, spell_id)
            set_u32(row, 38, level)
            set_u32(row, 39, level)
            set_u32(row, 28, 1)  # native instant-cast entry
            set_u32(row, 29, COOLDOWN_MS.get(ability.key, 0))
            set_u32(row, 41, {"rage": 1, "energy": 3, "energy_and_combo": 3}.get(ability.resource, 0))
            set_u32(row, 42, ability.cost)
            set_u32(row, 204, ability.base_mana_percent)
            set_u32(row, 205, 0 if ability.key in NO_GCD else 133)
            set_u32(row, 206, 0 if ability.key in NO_GCD else 1500)
            values = level_values(level)
            key = ability.key
            if key in ("blood_strike", "plague_strike"):
                _clear_effects(row)
                blood = key == "blood_strike"
                _effect(row, 0, 121, int(values["blood_raw_additive" if blood else "plague_raw_additive"]))
                _effect(row, 1, 31, 40 if blood else 50)
                if blood:
                    _effect(row, 2, 3, 25)  # native DK disease coefficient / 2
                bonus = values["blood_effective_additive" if blood else "plague_effective_additive"]
                _text(dbc, row,
                      f"Deals $s2% normalized weapon damage plus {bonus}. " +
                      ("12.5% more damage per disease you applied." if blood else "Applies Blood Plague and grants 1 combo point on a successful hit. Misses still cost full energy."),
                      f"Inflige $s2% del daño de arma normalizado más {bonus}. " +
                      ("Daño aumentado un 12,5% por cada enfermedad propia." if blood else "Aplica Peste de sangre y genera 1 punto de combo al acertar. Fallar también consume toda la energía."))
            elif key == "icy_touch":
                _clear_effects(row)
                _effect(row, 0, 2, int(values["icy_touch_min"]))
                set_u32(row, 74, int(values["icy_touch_max"]) - int(values["icy_touch_min"]) + 1)
                _text(dbc, row, "Deals $s1 Frost damage plus 10% attack power and applies Frost Fever. Sevenfold impact threat in Frost Presence.",
                      "Inflige $s1 de daño de Escarcha más un 10% del poder de ataque y aplica Fiebre de Escarcha. Amenaza del impacto multiplicada por 7 en Presencia de escarcha.")
            elif key == "blood_tap":
                _clear_effects(row)
                _effect(row, 0, 3, target=1)
                _text(dbc, row, "Consumes all current rage, granting 1 energy per displayed rage point. Overflow and fractional rage are lost. Requires positive rage.",
                      "Consume toda la ira actual y otorga 1 de energía por cada punto de ira. El exceso y las fracciones se pierden. Requiere tener ira.")
            elif key in ("blood_presence", "frost_presence"):
                _clear_effects(row)
                if key == "blood_presence":
                    _effect(row, 0, 6, 5, target=1, aura=79, misc=127)
                    _text(dbc, row, "Increases damage by 5% and heals for 4% of non-periodic damage dealt. Only one presence may be active; stances can coexist.",
                          "Aumenta el daño un 5% y sana un 4% del daño no periódico infligido. Solo una presencia activa; compatible con actitudes.")
                else:
                    _effect(row, 0, 6, 8, target=1, aura=137, misc=3)
                    _effect(row, 1, 6, -8, target=1, aura=87, misc=127)
                    _text(dbc, row, "8% more stamina, 60% more armor from gear excluding shields, 8% less damage taken and 45% more threat. Only one presence may be active.",
                          "Aumenta un 8% el aguante y un 60% la armadura del equipo sin escudo; reduce un 8% el daño recibido y aumenta un 45% la amenaza. Solo una presencia activa.")
            elif key == "chains_of_ice":
                _set_i32(row, 80, -96)  # -95% slow; native aura recovers 10% each second
                _text(dbc, row, "Slows by 95%, recovering 10 percentage points each second for 10 sec. Applies Frost Fever.",
                      "Ralentiza un 95%; recupera 10 puntos porcentuales por segundo durante 10 s. Aplica Fiebre de Escarcha.")
            elif key == "mind_freeze":
                _text(dbc, row, "Melee interrupt; locks the interrupted school for 4 sec. No global cooldown.",
                      "Interrumpe cuerpo a cuerpo y bloquea la escuela interrumpida durante 4 s. Sin reutilización global.")
            elif key == "dark_command":
                _text(dbc, row, "Taunts the target. Costs 10 rage; no stance required.",
                      "Provoca al objetivo. Cuesta 10 de ira; no requiere actitud.")
            elif key == "death_grip":
                _clear_effects(row)
                _effect(row, 0, 3)
                _text(dbc, row, "Pulls the enemy and taunts for 3 sec. Pull and taunt respect their respective immunities. No combo points.",
                      "Atrae al enemigo y lo provoca durante 3 s. Atracción y provocación respetan sus inmunidades. No genera combos.")
            elif key == "death_strike":
                reference = _eviscerate_template(templates, level)
                _clear_effects(row)
                _effect(row, 0, 2, _i32(reference, 80) + 1)
                set_u32(row, 74, u32(reference, 74))
                set_u32(row, 119, u32(reference, 119))
                # Copy native combo-required attributes, retaining the DK family.
                set_u32(row, 5, u32(row, 5) | (u32(reference, 5) & 0x00100000))
                _text(dbc, row, "Finisher: consumes 1-5 combo points. Deals 50% of same-level Eviscerate reference damage; heals 25% of that full reference plus 5% maximum health per own disease. No disease required.",
                      "Remate: consume 1-5 puntos de combo. Daño: 50% del daño de referencia de Eviscerar del mismo nivel. Sana un 25% de esa referencia completa más un 5% de vida máxima por enfermedad propia. No requiere enfermedades.")
            elif key == "raise_dead":
                _clear_effects(row)
                _effect(row, 0, 3, target=1)
                _text(dbc, row, "Summons one guardian ghoul for 60 sec. No corpse or reagent. Can coexist with a pet; 3 min cooldown starts on cast.",
                      "Invoca un necrófago guardián durante 60 s, sin cadáver ni componentes. Compatible con otra mascota. Reutilización de 3 min desde el lanzamiento.")
            created.append(row)

    threat = bytearray(templates[48263])
    _clear_effects(threat)
    _effect(threat, 0, 6, 45, target=1, aura=10, misc=127)
    _effect(threat, 1, 6, 0, target=1, aura=22, misc=1)
    _effect(threat, 2, 6, 0, target=1, aura=226)
    set_u32(threat, 100, 1000)
    heal = bytearray(templates[45470])
    _clear_effects(heal)
    _effect(heal, 0, 10, target=1)
    set_u32(heal, 6, u32(heal, 6) | 0x20000000)  # healing reference does not crit
    guardian = bytearray(templates[guardian_id])
    set_u32(guardian, 40, duration_60s)
    for spell, row in ((FROST_THREAT, threat), (DEATH_STRIKE_HEAL, heal), (RAISE_DEAD_GUARDIAN, guardian)):
        set_u32(row, 0, spell)
        for field in (1, 29, 30, 42, 43, 44, 45, 204, 205, 206, 226, 228, *range(50, 68), 222, 223):
            set_u32(row, field, 0)
        set_u32(row, 41, 0)
        set_u32(row, 38, 1)
        set_u32(row, 39, 1)
        created.append(row)
    dbc.records.extend(created)
    dbc.records.sort(key=lambda row: u32(row, 0))
    dbc.write(path)
    return {"Spell.dbc": True}


def owned_spell_ids() -> tuple[int, ...]:
    return tuple(sorted({spell for ability in ABILITIES for spell in ability.spell_ids} | AUXILIARY_IDS))


def world_sql() -> str:
    """Normal versioned world migration, generated from the same rank contract."""
    ids = ",".join(map(str, owned_spell_ids()))
    statements = ["-- Generated by tools/dk_adaptations.py:world_sql(); do not hand-edit.",
                  "-- Native DK spell rows are never modified.",
                  f"DELETE FROM `spell_ranks` WHERE `spell_id` IN ({ids});"]
    ranks = [f"({a.first_id},{spell},{rank})" for a in ABILITIES if a.scaled
             for rank, spell in enumerate(a.spell_ids, 1)]
    statements.append("INSERT INTO `spell_ranks` (`first_spell_id`,`spell_id`,`rank`) VALUES\n" + ",\n".join(ranks) + ";")
    statements.append(f"DELETE FROM `spell_script_names` WHERE `spell_id` IN ({ids});")
    bindings = [(spell, "spell_adventurer_dk") for a in ABILITIES for spell in a.spell_ids]
    bindings.extend(((280001, "aura_adventurer_dk_presence"), (280501, "aura_adventurer_dk_presence"),
                     (FROST_THREAT, "aura_adventurer_dk_frost_support"),
                     (280701, "aura_adventurer_dk_chains")))
    statements.append("INSERT INTO `spell_script_names` (`spell_id`,`ScriptName`) VALUES\n" +
                      ",\n".join(f"({spell},'{name}')" for spell, name in bindings) + ";")
    statements.append(f"DELETE FROM `spell_bonus_data` WHERE `entry` IN ({ids});")
    coefficients = [(spell, "0.1" if a.key == "icy_touch" else "0")
                    for a in ABILITIES if a.scaled for spell in a.spell_ids]
    coefficients.append((DEATH_STRIKE_HEAL, "0"))
    statements.append("INSERT INTO `spell_bonus_data` (`entry`,`direct_bonus`,`dot_bonus`,`ap_bonus`,`ap_dot_bonus`,`comments`) VALUES\n" +
                      ",\n".join(f"({spell},0,0,{ap},0,'Adventurer DK adaptation')" for spell, ap in coefficients) + ";")
    return "\n\n".join(statements) + "\n"
