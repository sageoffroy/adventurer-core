# SpellDraft — spell adaptation workflow

Operational guide for adapting an existing WoW spell for Adventurer/SpellDraft. Read [`PROJECT_GUIDE.md`](PROJECT_GUIDE.md) first for the repository map and [`SPELLDRAFT.md`](SPELLDRAFT.md) for the current card/runtime model.

The rule is **not** to touch every file listed here. Inspect the existing path and change only what the requested spell actually needs.

## Start here

For every spell adaptation:

1. Identify the existing card entry in `config/spelldraft/cards.csv`.
2. Inspect the closest already-working spell or spell-family adaptation.
3. Check `docs/spells/` for an approved implementation that can serve as a pattern.
4. Determine whether the change is catalogue-only, DBC/client data, server runtime, native core behavior, or a combination.
5. List the minimal files that need modification before editing.
6. Reuse the existing `apply.sh` / `update.sh` pipeline.

Do not begin by creating a new module, framework, test suite, manifest, validator, migration mechanism or rollback layer.

## Relevant existing paths

### SpellDraft catalogue and metadata

- `config/spelldraft/cards.csv` — card catalogue used by SpellDraft.
- `config/spelldraft/catalog_metadata.csv` — metadata/dependency information where applicable.
- `config/spelldraft/spelldraft.conf` — editable SpellDraft configuration seed.
- `config/spelldraft/subclasses.json` — presentation-subclass data.
- Spell-specific configuration may exist under `config/spelldraft/` when the implementation already uses that pattern, for example `icy_touch.json`.

### DK adaptations

- `tools/dk_adaptations.py` — existing DK-specific spell adaptation logic.

For DK spells, inspect this file before inventing another implementation path.

### Native core patches

- `tools/core_patch.py` — exact-anchor transformations for native AzerothCore source files.
- `payload/core/` — source files owned by Adventurer and copied into the core.

Only touch native AzerothCore source through the existing core-patch/install mechanism unless there is a verified technical reason that mechanism cannot express the requested behavior.

### DBC / client / runtime tooling

- `tools/dbc.py` — core Adventurer DBC transformations.
- `tools/dk_adaptations.py` — DK-specific DBC/config-derived adaptation data.
- `tools/spell_rank_tabs.py` — SpellDraft spell/rank/tab related generation.
- `tools/spelldraft_runtime.py` — runtime SpellDraft catalogue/config installation.
- `tools/client.py` — client patch and client-side data installation.
- `apply.sh` — clean installation entrypoint.
- `update.sh` — update entrypoint for an existing installation.
- `rollback.sh` — rollback entrypoint.
- `preflight.sh` / `verify.sh` — existing validation entrypoints. Do not add new validation layers by default.

## Decision tree

### A. Catalogue/selection only

Prefer changing `cards.csv` and existing metadata/config only. Do not touch C++ or DBC unless actual game behavior requires it.

### B. WotLK spell data needs adaptation

Use the existing DBC adaptation path. Preserve the native spell identity whenever possible and change only the fields required by Adventurer/SpellDraft.

For rank/scaling work, follow the project's existing single-spell scaling conventions instead of creating a parallel rank system.

### C. DK-specific behavior

Inspect and extend `tools/dk_adaptations.py` first.

If data changes cannot express the behavior and native server logic is genuinely required, use the existing `tools/core_patch.py` path.

### D. Native AzerothCore source change

1. Identify the exact native file that must change.
2. Add the smallest exact transformation necessary to the existing core patcher.
3. Do not build a new ownership/migration/test framework around the file.
4. If existing ownership machinery blocks the new file, change only what is necessary for the current updater to accept it.

`src/server/game/Spells/SpellInfo.cpp` is already part of the Icy Touch implementation and must not be treated as a novel architectural problem again. See [`spells/ICY_TOUCH.md`](spells/ICY_TOUCH.md).

## Scaling

Scaling is part of the implementation, not an optional cleanup step.

Before finishing a spell:

- preserve the intended WotLK progression/anchors used by the project;
- verify the values at relevant levels;
- when multiple original ranks share a level, use the project's established stronger-anchor rule where applicable;
- do not invent extra ranks simply to make a table regular;
- include changing cast time, resource cost, direct damage/healing, periodic totals/duration and other rank-specific properties when relevant.

Reuse an existing scaling helper when one already exists instead of duplicating the formula.

## Validation policy

Default loop:

1. Make the minimal change.
2. Run `apply.sh` or `update.sh` as appropriate.
3. Compile/restart only when changed server code requires it.
4. Test the spell in game.
5. Fix the actual observed error or incorrect behavior.

Do not create new automated tests unless the user explicitly requests them or approves them for a specific recurring failure.

Existing tests are not a reason to enlarge a spell change. If a stale test fails solely because implementation details changed, assess whether it should be updated, removed or ignored rather than redesigning the feature around it.

## Before editing checklist

A new AI session should be able to answer:

- What branch is checked out?
- Where is the card/catalogue entry?
- What existing adapter currently changes this spell or the closest equivalent?
- Does the behavior require DBC, runtime/server logic, native C++, client metadata, or catalogue data only?
- What is the established scaling behavior?
- What are the smallest files that must change?

If those answers are not known, inspect the repository first. Do not fill the gaps by inventing new architecture.
