# Death Knight adaptation integration audit

## Status and provenance

Date: 2026-08-28. Branch: `feature/spelldraft-dk-adaptations-v1`.

Base: `stable/spelldraft-v1`, commit
`291259fd48dd5f18bebc188e27387cd825a4cf67`. The older
`feature/spelldraft-meta-v2` and `feature/spelldraft-meta-v3` both point to
`131d7ba`; neither is the selected stable base. Do not merge dungeon-master or
other experimental branches into this work.

This checkpoint creates the isolated branch and records the design and source
audit. **It does not activate the DK cards or implement their spell behavior.**
Running `update.sh` at this checkpoint will not install the adapted abilities.
The stable branch and its runtime catalog are unchanged.

The companion [design snapshot](dk-adaptations-design.md) preserves approved
values, provisional decisions and unresolved details. The last explicit decision
wins: only one presence at a time; the unused-combo Raise Dead idea is only a
note; Army costs half the maximum of EACH of mana, rage and energy.

The local package was inspected directly. For native C++ behavior, the audit
also inspected the exact mod-playerbots/AzerothCore commit referenced by the
package CI, `9fb906bb7296212ff42fc95ff73a92aaf8554f0d`. This is a reference, not
a claim that the user's running server uses that commit, nor a new SHA gate.
No installed server, live DBC bundle, client or database was available locally.

## Current registration and installation circuit

| Layer | Existing entry points | Consequence for DK work |
|---|---|---|
| Structural card registry | `config/spelldraft/cards.csv` | Add stable card IDs, one active card per family, dependencies and root grants. Never recycle existing IDs. |
| Rarity and talent relationships | `config/spelldraft/catalog_metadata.csv` | Add rows keyed by the actual granted spell ID. Metadata can override rarity or exclude a card with `unavailable`. |
| Runtime catalog generation | `tools/spelldraft_runtime.py`: `build_runtime_cards`, `build_packaged_files` | Metadata alone does not create an active card. Active roots must exist in the structural registry. |
| Native talent rank discovery | `parse_talent_dbc` | `Talent.dbc` supplies the real ranks; any referenced rank is normalized to the first rank. Invalid/non-talent references are reported, not turned into working talents. |
| Book/collection classification | `config/spelldraft/subclasses.json`, `tools/subclasses.py` | Every structural card needs one of the four existing presentation families. Do not introduce three new DK talent trees. |
| Generated classification | `build_runtime_subclasses` | Generates `card_subclasses.csv`; talents inherit classification or use an explicit override. |
| Server ownership and learning | `payload/core/src/server/scripts/Custom/adventurer_core.cpp` | Persists card ranks in `character_settings`, restores cards and upgrades native active chains on login/level transitions. |
| Talent collection UI | `adventurer_collections.cpp`, `client/AdventurerCollections.lua` | Shows acquired SpellDraft talents, not a fixed point-spending tree. |
| DBC/client build | `tools/client.py`: `patch_dbc_copy`, `build_patch` | Builds a common server/client DBC bundle and root/locale MPQs. Add the adaptation transform to this canonical path. |
| Native rank book mapping | `tools/spell_rank_tabs.py` | Expands package roots using the target core's `spell_ranks.sql`; populates subclass `SkillLineAbility` rows and removes inventory component fields. |
| C++ registration | `tools/core_patch.py`: `PAYLOAD_FILES`, `patch_custom_loader`, `plan` | A new spell payload needs explicit loader/ownership integration and matching fixture updates. Copying a C++ file alone is insufficient. |
| World changes | `tools/world.py`, `sql/world/` | Script bindings, owned clone ranks or coefficients require versioned migrations and verification. |
| Rollback ownership | `tools/database.py`: `WORLD_SCOPES`; `tools/upgrade.py` | Current DB snapshot covers chassis rows, not arbitrary DK spell rows. Extend backup/cleanup before adding spell mutations. Preserve original installation backups. |
| Install/update | `apply.sh`, `update.sh` | Core/client transformation, rank/component pass, runtime catalog installation and world migrations are separate steps. Rebuild the server for C++ changes. |

The structural snapshot has **200 cards: 193 active and 7 explicit talents**,
with maximum card ID 210, and **211 metadata rows**. None of the 21 DK roots
listed below is registered. The final number of runtime talents cannot be
deduced from these counts without the actual `Talent.dbc`.

The stable architecture deliberately removes legacy fixed talent trees.
`tools/talents.py` is cleanup-only for old Guardian/Champion/Scholar rows.
Do not resurrect 290000-series legacy talent clones or re-enable DK runes,
runic power, or blanket `IsClass(DEATH_KNIGHT)` impersonation.

## Critical integration findings

### Card level is not a strict minimum cast/offer level

`IsCardEligible` uses `InitialActiveSourceLevelCap = 10` at early levels and
`ActiveSourceLevelLookahead = 3` afterward. Simply putting `source_level=20`
would permit a level-20 area in a level-17 offer. The design explicitly forbids
Hervor before 20. Add an opt-in hard minimum for the new cards, in both normal
and debug eligibility, without changing the established pool behavior for all
old cards. Spell learn/cast levels must agree with this minimum as well.

### Active card rank is not character-level scaling

`UpgradeActiveSpellFamily` follows `sSpellMgr->GetNextSpellInChain` and picks a
native rank using `max(BaseLevel, SpellLevel)`. It does not interpolate daily
design tables. `rank_grants` separated by `/` are acquired CARD ranks, not a
ready-made per-character-level curve. Do not turn 80 level rows into 80 draft
picks or leave native upgrades able to replace the adapted spell with a
runic-cost spell.

Use one authored numeric source for server damage and client tooltips. Before
coding, select and test either owned spell variants/rank chains or a narrowly
scoped class-10 implementation. Owned variants isolate native classes better,
but require explicit auxiliary IDs, native family masks, bindings and rank
metadata. Reusing stock IDs globally would also affect native DKs and bots.
No ID range is reserved by this audit; verify it against real DBC/world data.

### Multi-resource casts require server support

The inspected `Spell::CheckPower`/`TakePower` path uses one `PowerType` and one
`m_powerCost`. Asolar and Army need a shared atomic check/payment path. Do not
spend energy in an after-hit handler after the mana payment already succeeded.
Capture costs consistently, validate every resource before payment, and avoid
double charges from triggered effects or individual Army summons.

Mana costs in most Frost spells are percentages of BASE mana. Army is
explicitly a percentage of MAXIMUM mana/rage/energy. Rage uses tenths internally:
the package defines maximum rage as 1000 for the displayed 100. A 50%-maximum
Army cost is 500 internal rage, not 50. Blood Tap's 1:1 conversion must use
displayed rage units before restoring energy.

The native `TakePower` implementation reduces cost on many failed energy/rage
attacks. That conflicts with the approved full-cost failures for Asolar and
Plague Strike. Keep the custom rule scoped to those adaptations; do not alter
all rogue/warrior spells. Decide/test interaction with refund talents.

### Existing scripts cannot be copied without auditing auxiliary effects

| Native path inspected | Relevant issue |
|---|---|
| `spell_dk_blood_boil::Load` | Requires DK ability context; a class-10 caster does not automatically get identical script behavior. |
| `spell_dk_raise_dead` | Checks reagent spell 48289, chooses guardian/pet depending on Master of Ghouls, and removes the initiating cooldown. Clearing only root 46584's DBC reagents does not implement our component-free, cast-start cooldown design. |
| `spell_dk_anti_magic_shell_self` | Reads capacity from an effect, and after absorption triggers runic-power energize 49088. Replace capacity with the captured combo rule and suppress resource generation. |
| `spell_dk_death_strike` | Counts own diseases and triggers a heal, including an Improved Death Strike modifier. It does not contain the approved 50%/25% Eviscerate reference split. |
| `spell_dk_icebound_fortitude` | Uses defense threshold 400; our approved level-dependent threshold is 5 times character level. |
| `spell_dk_presence` | Uses exact original presence IDs and auxiliary auras, including movement, healing and armor-related effects. Cloning the parent ID alone breaks these comparisons. |
| `spell_dk_master_of_ghouls`, `Pet.cpp` | Uses DK pet visibility and class-context paths. Persistent pet support must work for class 10 without enabling the DK resource system. |
| `spell_dk_death_and_decay` / aura / 52212 | Periodic parent triggers a damage spell. Preserve one coefficient application, pulse count and threat; no energy cost per pulse. |

Other low-level damage logic also lives outside `spell_dk.cpp`. Review the
native weapon/disease calculation paths when choosing IDs and preserve own-
caster disease checks and weapon normalization. Do not apply the weapon
percentage twice to the already-effective additive values in the design.

### Catalog updates can be preserved rather than installed

`spelldraft_runtime.install` updates unedited managed files using hashes and
`.dist` baselines. A manually edited live `cards.csv` is preserved wholesale.
Therefore a successful package update alone does not prove new cards are in
the live pool. Verify both live and `.dist` catalogs; reconcile edits explicitly
instead of silently overwriting them. Keep server/client spell metadata and
`card_subclasses.csv` consistent with the actual live card set.

## Talent activation plan

An associated talent becomes eligible, not automatically learned. The generator
creates one synthetic card `1000000 + first_talent_spell_id`, with the chain
from `Talent.dbc` and an OR (`requires_any`) of the source ACTIVE CARD IDs.
Several abilities can unlock the same talent without duplicating it.

Do not fill `talent_spells` by copying every native DK talent. Maintain a
reviewed ability-to-talent matrix after the adapted spell IDs are fixed:

| Candidate group | Required audit before registration |
|---|---|
| Damage/crit modifiers for Blood Strike, Icy Touch, Plague Strike, Obliterate | Confirm family masks match adapted variants and modifiers do not apply twice. |
| Disease duration/damage and Wandering Plague | Confirm own-disease IDs, AP coefficients, refresh/consumption behavior and zero combo generation from ticks/procs. |
| Improved Death Strike | Decide whether it modifies base healing, disease healing or both; no decision is implied by the native script. |
| Annihilation | Its native disease-consumption interaction changes Asolar's approved consume-after-hit behavior; make this an explicit talent exception only if approved. |
| Magic Suppression / Anti-Magic Shell improvements | Separate per-hit absorption, total capacity and combo scaling; never restore runic-power generation inadvertently. |
| Master of Ghouls and ghoul improvements | Permanent controlled pet is a separate improvement, not part of the base provisional summon; audit pet conflicts and class-10 lifecycle. |
| Improved presences | Preserve one active presence and native affected-spell scope. Any rune-cooldown component requires redesign. |
| Rune conversion, rune refresh, runic-power generation/spending | Keep unavailable until an explicit resource adaptation exists. Native scripts refer to runes or DK class checks. |

The exact talent IDs/ranks are **not yet certified** against the user's DBCs.
Neither this document nor metadata eligibility alone proves a talent works.
Do not grant glyphs, set bonuses or triggered spells as talent cards.

Existing finishers also need a dependency audit. Eviscerate card 50 and Slice
and Dice card 55 currently require cards 14, 51 or 53 (Sinister Strike,
Backstab, Gouge). Once Plague Strike/Asolar exist, adding only their own DK
finishers would leave existing finishers inaccessible to those generators.
Review all generator/finisher dependencies, including cat-form bundles, and
keep self-buff finishers usable without a melee-range attack requirement.
Asolar generates combos only with a disease, so its dependency usefulness is
conditional. Do not require diseases for Death Strike itself.

## Ability inventory and readiness

IDs below are original references, **not reserved adapted IDs**. A dash means
an unresolved design value, not permission to choose it silently.

| Ability | Original root | Entry level in design | Main implementation work |
|---|---:|---:|---|
| Blood Presence | 48266 | 1 | Free activation, approved damage/heal amounts, auxiliary auras, exclusivity. |
| Blood Strike | 45902 | 1 | Rage, level interpolation, own disease multiplier; expand full table from approved anchors. |
| Blood Tap | 45529 | — | Drain current rage, convert displayed units 1:1 to energy; overflow lost, no cooldown. |
| Dark Command | 56222 | — | 10 rage; no stance; keep existing Taunt bundled with Defensive Stance. |
| Blood Boil | 48721 | 20 | 61-row curve, disease bonus once, single rage payment. |
| Strangulate | 47476 | 24 | Melee range, rage, silence and native non-player interrupt behavior. |
| Frost Presence | 48263 | 1 | Free activation, exact armor scope, stamina, reduction and explicit threat multiplier. |
| Icy Touch | 45477 | 1 | 80-row curve, base-mana cost, Frost Fever, presence-specific impact threat. |
| Mind Freeze | 47528 | 12 | Base-mana cost, melee interrupt, no GCD. |
| Chains of Ice | 45524 | 8 | Base-mana cost, custom 8s cooldown, snare progression, same Frost Fever. |
| Obliterate | 49020 | 20 | 61-row curve, atomic mana/energy cost, conditionally one combo before disease removal. |
| Icebound Fortitude | 48792 | 20 | Base-mana cost and defense threshold by level. |
| Horn of Winter | 57330 | 10 | 71-row stat curve, restore 5% BASE mana only to caster, overflow lost. |
| Death Grip | 49576 | 1 | Energy, displacement/taunt immunities separately, no GCD. |
| Plague Strike | 45462 | 1 | 80-row curve, energy, one combo on hit, own Blood Plague. |
| Death Strike | 49998 | — | Reference Eviscerate curve plus combo handling and independent healing; unresolved details below. |
| Raise Dead | 46584 | 10 | Provisional 60s guardian, 50 energy, reagent/auxiliary and cooldown handling. |
| Death and Decay | 43265 | 20 | 61-row curve, 60 energy, persistent area, AP and elevated threat. |
| Anti-Magic Shell | 48707 | 20 | 25 energy, self-finisher, 15/30/45/60/75% max-health capacity, fixed 5s. |
| Unholy Presence | 48265 | General presence rule | Preserve original affected spells and no-rank behavior; finalize activation metadata. |
| Army of the Dead | 42650 | 40 proposed | Atomic 50% of all three MAX resources, channel/summons/interruption. |

Several Blood/Frost rarities were never explicitly assigned. The design file
marks them as such; do not present them as approved. Likewise, the Army entry
level and rarity originated in the retained proposal, while the triple cost
was explicitly approved.

Death Strike is the principal numeric blocker: the formula is approved, but
there is no full level-by-1-to-5-combo table, entry level or rarity, nor settled
critical/random-roll/modifier/failure handling. The stable catalog references
native Eviscerate 2098 (card 50), not a custom Eviscerate table. The inspected
native chain has 12 ranks, including the second level-60 rank. Resolve duplicate
level anchors by retaining the stronger rank, as already established in the
project, and verify actual values in `Spell.dbc` before deriving 50% damage and
25% healing. The 25% is from Eviscerate BEFORE mitigation, not from the halved
Death Strike damage and not from maximum health.

## Delivery order and verification gates

1. Finalize unresolved metadata and Death Strike values; reserve owned IDs only
   after inspecting live DBC/world ranges. Create one typed spell/curve source.
2. Implement server/client spell transformation together, including auxiliary
   spells, tooltip locales, class eligibility, single-presence behavior and
   rank upgrade integration. Keep unrelated classes/bots unchanged.
3. Implement shared resource payment and combo support, then the individual
   damage/healing/guardian scripts. Do not expose unimplemented cards.
4. Register the cards, metadata and subclass coverage as one consistent change;
   enforce hard level minima without changing existing draft eligibility.
5. Enable only audited talents, with tested generator/finisher dependencies.
6. Integrate world SQL ownership, install/update staging, verification and
   rollback. Test interrupted updates and edited live catalogs.
7. Rebuild and test on the target server/client. First check low levels, then
   original high-level anchors, resources, diseases, combos, threat and summons.

Extend existing test suites at their natural integration points:

- `test_spelldraft_design_catalog.py`, `test_spelldraft_authoritative_pool.py`,
  `test_spelldraft_v1.py`: grants, IDs, rarity, dependencies and hard minima.
- `test_spelldraft_subclasses.py`, rank/tab and component suites: every owned
  spell/rank appears once and auxiliary requirements are removed deliberately.
- `test_dbc.py`, `test_client.py`: real layouts, enUS/esMX tooltips, resource
  display, preserve native masks/rows where intended, idempotent builds.
- `test_core_patch.py`, transitions and resources suites: exact anchors,
  loader ownership, no global DK impersonation, rage units and source changes.
- `test_database.py`, `test_upgrade.py`, `test_world.py`: new SQL scopes,
  reversible migrations, preserved backups and no partial success reports.
- Runtime/server tests: atomic insufficient-resource failures; full cost on
  specified misses; combo capture before consumption; enemy-owned diseases
  excluded; Caparazon capacity versus per-hit fraction; Army partial channels;
  one presence; low-level pet stats; no runic-power leakage.

Python fixture tests do not prove C++ compilation, live DBC values or gameplay.

## Checks completed for this audit checkpoint

- `python -m unittest discover -s tests`: **130 tests passed**.
- Every `tests/test_*.py` executed individually: **26 files, zero failed exits**.
- No live DBC regeneration, world SQL execution, C++ build or in-game test.
- Documentation-only checkpoint: runtime files remain byte-for-byte unchanged.

To fetch this branch without installing anything:

```bash
cd ~/adventurer-core
git fetch origin
git switch --track origin/feature/spelldraft-dk-adaptations-v1
```

If a local branch of that name already exists, use `git switch
feature/spelldraft-dk-adaptations-v1` instead. Do not force checkout over local
changes. Do not run the installer expecting DK abilities at this checkpoint.
