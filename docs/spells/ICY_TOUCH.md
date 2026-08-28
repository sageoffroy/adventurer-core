# Icy Touch — Adventurer / SpellDraft

Approved implementation notes for the current native Icy Touch adaptation. This is a gameplay/implementation contract, not a test-framework specification.

## Identity

- SpellDraft card ID: `211`.
- Native root spell: `45477`.
- Native ranks: `45477`, `49896`, `49903`, `49904`, `49909`.
- No cloned/custom replacement spell IDs.
- Rank 1 is available from level 1 through SpellDraft; later native ranks keep their normal 61/67/73/78 progression through the existing rank-upgrade path.

## Adapted behavior

- Damage uses the caster's **current level**, even when the character still has rank 1.
- Level is capped at 80 for this damage curve.
- Cost is **8% base mana**, rounded to nearest integer with minimum 1 before normal cost modifiers.
- It does not require runes and does not generate runic power for Adventurer.
- Instant cast.
- 20 yard range.
- Normal 1.5 second GCD.
- No separate custom cooldown.
- Native 0.1 AP coefficient remains in the ordinary spell calculation path after the adapted base-damage range.

## Native mechanics intentionally preserved

### Frost Fever

Native Frost Fever `55095` remains triggered by Icy Touch's original effect.

Preserve native:

- 15 second base duration;
- 3 second tick interval;
- AP scaling;
- attack-speed reduction;
- ownership/refresh/dispel behavior.

Do not add a second disease cast or duplicate DoT.

### Talents/family behavior

Native family flags remain so the relevant WotLK relationships continue to work, including the project's adapted availability for:

- Improved Icy Touch;
- Icy Reach;
- Black Ice;
- Epidemic.

These are SpellDraft talent-card relationships, not a fixed Adventurer talent tree.

### Threat

The native Frost Presence helper `61261` already contains Icy Touch threat behavior. Do not duplicate that modifier. Frost Presence itself is a separate adaptation task.

## Source/data path

### Reviewed source data

`config/spelldraft/icy_touch.json`

This is build/generation input for this adaptation, not a generic runtime hot-reload file.

### DK adapter

`tools/dk_adaptations.py`

Consumes the approved source data and participates in generating the shared spell-scaling/client data used by this implementation.

### Shared payload

`payload/core/src/server/game/Spells/AdventurerSpellScaling.h`

Contains/generated from the shared curve/helper data required by the native calculation patch.

### Native core transformation

`tools/core_patch.py`

The current adaptation patches native `src/server/game/Spells/SpellInfo.cpp` through the existing exact-anchor core patch path.

The important behavior is:

- for Adventurer casts of the five native Icy Touch rank IDs, `SpellEffectInfo::CalcValue` substitutes the approved level-based initial damage range, then continues through the ordinary native dice/modifier calculation path;
- explicit custom base-point overrides remain respected;
- `CalcPowerCost` adapts the percentage-mana rounding needed by the approved cost behavior.

`SpellInfo.cpp` is therefore an **existing known part of this adaptation**. Future sessions must not rediscover it as a new architecture problem.

### DBC/client

The existing DBC adaptation path modifies the required native records while preserving native identity, visuals, effects, family relationships and rank family.

Client/server spell data must remain consistent through the existing `tools/dbc.py` / `tools/client.py` pipeline. `client/AdventurerSpellTooltips.lua` displays the Adventurer base-damage curve before talents plus the AP relationship.

DBC edits to native spell IDs are global unless the implementation explicitly uses private copies. Do not assume these records are Adventurer-only.

## Approved base-damage curve

All rows below are the adapted base range before the native +10% AP coefficient and later talents/crit/resistance/mitigation.

| Level | Base damage |
|---:|---:|
| 1 | 8–9 |
| 2 | 9–10 |
| 3 | 10–11 |
| 4 | 11–12 |
| 5 | 13–14 |
| 6 | 14–15 |
| 7 | 15–16 |
| 8 | 16–17 |
| 9 | 18–20 |
| 10 | 21–22 |
| 11 | 23–25 |
| 12 | 25–27 |
| 13 | 28–30 |
| 14 | 30–32 |
| 15 | 33–35 |
| 16 | 35–37 |
| 17 | 37–40 |
| 18 | 40–43 |
| 19 | 42–45 |
| 20 | 44–48 |
| 21 | 47–50 |
| 22 | 49–53 |
| 23 | 51–55 |
| 24 | 54–58 |
| 25 | 56–60 |
| 26 | 59–63 |
| 27 | 61–66 |
| 28 | 63–68 |
| 29 | 66–71 |
| 30 | 68–73 |
| 31 | 70–76 |
| 32 | 73–78 |
| 33 | 75–81 |
| 34 | 77–83 |
| 35 | 80–86 |
| 36 | 82–88 |
| 37 | 84–91 |
| 38 | 87–94 |
| 39 | 89–96 |
| 40 | 92–99 |
| 41 | 94–101 |
| 42 | 96–104 |
| 43 | 99–106 |
| 44 | 101–109 |
| 45 | 103–111 |
| 46 | 106–114 |
| 47 | 108–117 |
| 48 | 110–119 |
| 49 | 113–122 |
| 50 | 115–124 |
| 51 | 118–127 |
| 52 | 120–129 |
| 53 | 122–132 |
| 54 | 125–134 |
| 55 | 127–137 |
| 56 | 130–140 |
| 57 | 133–143 |
| 58 | 136–147 |
| 59 | 138–150 |
| 60 | 141–153 |
| 61 | 144–156 |
| 62 | 147–159 |
| 63 | 150–162 |
| 64 | 153–165 |
| 65 | 155–167 |
| 66 | 158–170 |
| 67 | 161–173 |
| 68 | 165–178 |
| 69 | 170–183 |
| 70 | 174–188 |
| 71 | 178–193 |
| 72 | 183–198 |
| 73 | 187–203 |
| 74 | 195–211 |
| 75 | 203–220 |
| 76 | 211–228 |
| 77 | 219–237 |
| 78 | 227–245 |
| 79 | 227–245 |
| 80 | 227–245 |

## Normal apply/update path

On an existing Adventurer installation use the repository's normal `update.sh` flow. Because this implementation changes native C++ calculation code, rebuild/install `worldserver` after the update and restart it. Restart WoW when client DBC/Lua payload changes need to be reloaded.

Do not create a separate Icy Touch installer.

## In-game validation

A direct mechanics check can use `.learn 45477` on a disposable Adventurer. This verifies spell mechanics only; a GM `.learn` does not create SpellDraft card ownership.

Gameplay checks:

1. Level 1: base tooltip range `8–9 + 10% AP`; cast spends mana, produces no rune requirement and applies one Frost Fever.
2. Spot-check the curve, including level 8 `16–17`, level 20 `44–48`, level 55 `127–137`, and levels 78–80 `227–245`.
3. Confirm cost behavior with normal mana (not an infinite-power GM cheat), including insufficient-mana failure.
4. Reapply before Frost Fever expires: refresh the same caster's disease rather than stacking a duplicate.
5. Confirm Frost Fever ticks and native dispel/ownership behavior.
6. With the SpellDraft card owned, verify native rank progression at 61/67/73/78 while damage still follows current character level.
7. Verify relevant SpellDraft talent ranks affect the expected native family behavior.
8. Test resisted/immune targets and two different casters to ensure native hit/disease rules remain intact.

If these checks reveal a real gameplay failure, fix that failure through the smallest existing implementation path. Do not add a new test/ownership framework by default.
