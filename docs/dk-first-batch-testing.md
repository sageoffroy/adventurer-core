# DK first batch: normal SpellDraft integration

Implementation branch: `feature/spelldraft-dk-adaptations-v1`, from
`stable/spelldraft-v1`. This is a test branch, not a stable release.

## Installation ownership

All modifications live in **adventurer-core** and use the existing installation
paths. **aventurerosdeazeroth** supplies the target server APIs and SQL schema;
the CI syntax check applies the package to that repository before checking C++.
There is no separate addon, manual SQL installation or alternate draft engine.

- `client.patch_dbc_copy` builds owned spell variants from the local clean DBCs.
  The server, root MPQ and esMX MPQ receive identical Spell.dbc contents.
- `cards.csv`, `catalog_metadata.csv` and `subclasses.json` feed the existing
  runtime catalog and native Talent.dbc rank generator.
- `core_patch.PAYLOAD_FILES` installs and tracks the C++ implementation.
  The existing custom loader registers it through `AddAdventurerCoreScripts`.
- `world.WORLD_UPDATES` stages the normal versioned SQL migration, including
  scripts, rank chains and AP coefficients.
- `UpgradeActiveSpellFamily` upgrades acquired abilities as before. Each
  ability takes one draft pick; level variants are not additional cards.
- `apply.sh` and `update.sh` check DB ID collisions before writing source/client
  files. Rollback removes DK rows only when the DK migration was applied.

Clean `Spell.dbc`, `Talent.dbc` and `SpellDuration.dbc` are read during the normal
build from `--dbc-src`; no manual extraction or upload is part of this workflow.
The checked-in `talent_dbc.sql` in the server repository defines the table but
does not populate native talent rows. It is not a replacement for Talent.dbc.

## First twelve cards

| Card | Ability | Root spell | Minimum level | Cost |
|---:|---|---:|---:|---|
| 211 | Presencia de sangre | 280001 | 1 | Free |
| 212 | Golpe sangriento | 280101 | 1 | 15 rage; rare |
| 213 | Transfusión de sangre | 280201 | 10 | All current rage → energy; excess lost |
| 214 | Orden oscura | 280301 | 10 | 10 rage |
| 215 | Toque helado | 280401 | 1 | 8% base mana |
| 216 | Presencia de escarcha | 280501 | 1 | Free |
| 217 | Helada mental | 280601 | 12 | 3% base mana |
| 218 | Cadenas de hielo | 280701 | 8 | 8% base mana |
| 219 | Atracción letal | 280801 | 1 | 30 energy |
| 220 | Golpe de peste | 280901 | 1 | 40 energy; grants one combo on hit |
| 221 | Golpe letal | 281001 | 1 | 35 energy plus 1–5 combos |
| 222 | Levantar muerto | 281101 | 10 | 50 energy |

Level 10 for Blood Tap/Dark Command and common rarity for abilities without
an explicit rarity decision are conservative test defaults, not newly approved
balance decisions. Death Strike uses rare as its provisional rarity.

Blood Strike, Icy Touch and Plague Strike have all 80 numeric variants. Weapon
additives are converted to the native integer field before the 40%/50%
mult; this introduces at most 0.2/0.25 effective damage of quantization between
anchors. Native high-level anchors are unchanged. Death Strike uses the actual
same-level Eviscerate rank from the installation's Spell.dbc, taking the stronger
rank at duplicate levels. Presences and utility spells do not gain ranks.

## Talents and dependencies

The normal generator makes these native talent cards eligible after the related
ability, with their real rank chains from Talent.dbc:

- Bloody Strikes (48977): Blood Strike.
- Improved Icy Touch (49175), Icy Reach (55061), Black Ice (49140): Icy Touch.
- Icy Reach (55061): Chains of Ice.
- Epidemic (49036): Icy Touch, Chains of Ice or Plague Strike.
- Unholy Command (49588): Death Grip.
- Vicious Strikes (51745), Outbreak (49013): Plague Strike.

Acquiring an ability unlocks talent **offers**, not free talent ranks. The
original DK family masks remain on every copied spell so these modifiers can
target it. Subversion's presence-dependent threat component, improved presences,
rune/runic-power talents and permanent-ghoul conversion are not enabled in this
batch. They must not be represented as already adapted.

Plague Strike also unlocks the existing Eviscerate and Slice and Dice cards.
Death Strike requires a combo generator, not an ability that applies diseases.
Its reference healing is not a second critical roll. Base and disease healing
still pass through normal healing modifiers.

## Verification and gameplay checks

Python tests cover all-level numeric curves, clean/native DBC preservation,
costs, absence of rune requirements, generated world ranks/script bindings,
catalog/talent integration and ID collision checks. Synthetic DBC fixtures test
the transformation; they are not presented as the user's client data.

CI syntax-checks all owned C++ scripts with the real target core headers and
compiler flags. It does not link/start worldserver or run the game. Gameplay
validation remains necessary after installing and rebuilding the test server.

1. Acquire cards through the existing SpellDraft debug pool. Confirm cards and
   related talent offers appear in their existing presentation tabs.
2. At levels 1/8/55/60/80, verify one visible rank per damage ability, correct
   resource costs and automatic rank upgrades after login/level changes.
3. Miss/dodge/parry Plague Strike: full energy cost, no combo or disease.
   Successful hits grant one combo even if the disease itself is resisted.
4. Blood Tap at 0 rage fails; at full energy consumes rage and wastes the gain.
5. Blood/Frost Presence replace one another, but do not remove warrior stances.
   Check armor with/without a shield and after changing equipment.
6. Icy Touch: AP scaling, Frost Fever and extra impact threat only in Frost
   Presence. Chains: 95% slow recovering 10 percentage points each second.
7. Death Strike with 1–5 combos, without diseases and with one/two own diseases;
   check healing after a killing blow. Another player's diseases do not count.
8. Grip against a normal enemy and separate pull/taunt immunities; Mind Freeze
   at melee range, school lock and no GCD; Dark Command without a stance.
9. Raise Dead: one 60-second guardian, existing pet preserved, no corpse/reagent,
   and three-minute cooldown starting on cast. This summon remains provisional.

If a live cards.csv was edited manually, the existing installer preserves it.
Compare it with cards.csv.dist before testing; a preserved old live catalog must
not be mistaken for missing C++ or DBC implementation.
