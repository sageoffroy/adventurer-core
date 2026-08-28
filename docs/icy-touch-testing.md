# Native Icy Touch test branch

Branch: `feature/spelldraft-v1-with-dk`, based on stable `291259fd48dd`.
Only Icy Touch is added. The discarded 12-spell implementation is not included.

## Contract

- One SpellDraft card, ID 211, native spell root **45477**, level 1. Common is
  the initial test rarity; no final rarity was selected during design.
- Original ranks **45477, 49896, 49903, 49904, 49909**. No custom spell IDs or
  replacement rank chains. Rank 1 becomes available at level 1; the other native
  ranks still unlock at 61/67/73/78 through the existing SpellDraft rank upgrade.
- Every rank uses the **caster's current level** for damage. Staying on rank 1
  does not leave the player with level-1 damage. Levels above 80 use level 80.
- 8% **base mana**, rounded to the nearest integer, minimum 1 before ordinary
  cost modifiers. Intellect/gear do not turn this into 8% maximum mana. No runes
  or runic power generation. Instant, 20 yards, normal 1.5s GCD, no own cooldown.
- Direct base damage follows the complete table below. The native 0.1 AP
  coefficient, talents, crit, resistances and other modifiers run afterwards.
- Native **Frost Fever 55095** is still triggered by the original effect. It
  keeps 15s duration, a tick every 3s, 0.06325 AP per tick, attack-speed reduction
  and ownership/refresh/dispel rules. No extra disease cast or duplicate DoT.
- Preserved native family flags keep Improved Icy Touch, Icy Reach, Black Ice
  and Epidemic compatible. They are generated through catalog metadata and
  Talent.dbc, and require owning card 211 in SpellDraft. No fixed talent tree.
- The native Frost Presence helper **61261** already provides +600% Icy Touch
  threat. It is retained, not added a second time. **Frost Presence is not a
  draft card in this branch**; its adaptation remains a separate task.

## Integration and ownership

`config/spelldraft/icy_touch.json` is the reviewed source. `tools/dk_adaptations.py`
generates `AdventurerSpellScaling.h` and the client curve from it. Native
`SpellEffectInfo::CalcValue` replaces only the initial range for Adventurers
casting these five IDs, then uses the ordinary dice/modifier path. Explicit
custom base-point overrides are preserved. `CalcPowerCost` changes only the
rounding of their percentage cost. Both patches use the existing exact-anchor
source installer, including backup, verification and rollback.

The DBC staging pass modifies existing records and fails before writing if a
rank, disease trigger or required talent family is missing. It never clones a
spell. Names, visuals, effects, family masks, higher-rank levels and auxiliaries
remain native. **DBC edits to these IDs apply globally**, just like the existing
component-removal pass; they are not private copies for the Adventurer.

The same Spell.dbc is installed on the server and in both client archives.
The tooltip hook loads after the native tooltip frames, covers spellbook,
action-bar and spell-link tooltips, and displays **base damage before talents
plus the AP formula**, not a promise of final damage against every target.

No new world SQL or SpellScript binding is needed: the native rank family,
Frost Fever effect, AP coefficients and threat modifiers remain in use.

## Install on the existing stable installation

Stop worldserver and close WoW first. Keep the current server source checkout;
do not change branches or import modules in the server repository.

```bash
cd ~/adventurer-core
git fetch origin
git switch --track origin/feature/spelldraft-v1-with-dk
git pull --ff-only

./update.sh \
  --core-dir ~/aventurerosdeazeroth-clean \
  --server-data-dir ~/aventurerosdeazeroth-clean/env/dist/data \
  --dbc-src ~/dbc-clean-esMX/dbc/esMX \
  --client-dir "/mnt/c/Games/World of Warcraft 3.3.5a" \
  --locale esMX
```

**Rebuild and install worldserver using its existing configured CMake build
directory, then restart it.** This is required even though the card itself is
runtime data: the native damage/cost calculation changed. Restart WoW to load
the new DBC and Lua files. The installer does not compile the server.

The runtime installer advances managed catalogs automatically. If it reports
`preserved edits: cards.csv`, do not overwrite those edits: compare the live
catalog with its new `.dist` so card 211 and its four dependent talent families
are included. `icy_touch.json` is build input, not a hot-reload runtime file.

## First gameplay check

On a disposable Adventurer, select yourself and use `.learn 45477` for a direct
mechanics check. Learn it through SpellDraft separately to test talent-card
eligibility; a GM `.learn` does **not** create owned SpellDraft card state.

1. At level 1, tooltip base damage is **8–9 + 10% AP**. Cast on a normal hostile
   creature; mana is spent, no rune error appears, and one Frost Fever is applied.
2. At level 8 the base is **16–17**, level 20 **44–48**, level 55 **127–137**, and
   levels 78–80 **227–245**. Check intermediate levels too. Actual combat damage
   also includes AP, talents, crit and target mitigation.
3. Check mana immediately around a cast. With insufficient mana it must fail
   without spending resources. Do not use the GM power cheat for this check.
4. Reapply before Frost Fever expires: refresh the same caster's disease, do
   not stack another copy. Observe ticks at 3/6/9/12/15s without Epidemic.
5. Check every talent rank: Improved Icy Touch increases damage and attack-speed
   reduction; Icy Reach changes range; Black Ice affects Frost damage; Epidemic
   extends the disease. The tooltip deliberately labels the base before talents.
6. Re-login and level through 61/67/73/78 with the card owned. Check rank upgrades,
   action-bar usability, book tab and unchanged level-based damage across ranks.
7. Check a resisted/immune target, dispelling the disease, and two different
   casters. Native hit and disease rules must remain intact.

Automated checks cover the 80 approved values, compiled C++ curve/cost helper,
native row preservation, idempotence, failure before writes, catalog/talent
generation, client/server data agreement and Lua 5.1 tooltip execution. CI also
compile-checks the real patched SpellInfo translation unit and existing runtime
against actual core headers. **These checks are not an in-game test.** Real DBC
inputs, worldserver startup, rendering and combat still require the game test.

Native references: [Icy Touch](https://www.wowhead.com/wotlk/spell=45477/icy-touch),
[Frost Fever](https://www.wowhead.com/wotlk/spell=55095/frost-fever), and
[Frost Presence helper](https://www.wowhead.com/wotlk/spell=61261/frost-presence).

## Approved base damage, levels 1–80

All rows add 10% AP through the native coefficient and cost 8% base mana.

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
