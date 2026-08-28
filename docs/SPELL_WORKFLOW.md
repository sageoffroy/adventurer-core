# SpellDraft — spell adaptation workflow

This is an operational guide for adapting an existing WoW spell for the Adventurer/SpellDraft system. It is not a requirement to touch every file listed here. The rule is to inspect the existing path and change only what the requested spell actually needs.

## Start here

For every spell adaptation:

1. Identify the existing SpellDraft card entry in `config/spelldraft/cards.csv`.
2. Inspect the current adaptation mechanism for the same spell family or the closest already-working spell.
3. Determine whether the change is data-only (catalog/DBC/client metadata), server-runtime behavior, native core behavior, or a combination.
4. List the minimal files that need modification before editing.
5. Reuse the existing apply/update pipeline.

Do not begin by creating a new module, framework, test suite, manifest, validator, or migration mechanism.

## Relevant existing paths

### SpellDraft catalogue and metadata

- `config/spelldraft/cards.csv` — card catalogue used by SpellDraft.
- `config/spelldraft/catalog_metadata.csv` — catalogue metadata where applicable.
- `config/spelldraft/spelldraft.conf` — SpellDraft configuration.
- `config/spelldraft/subclasses.json` — subclass data; only relevant when the requested change affects subclass behavior.
- Spell-specific configuration may exist under `config/spelldraft/` (for example `icy_touch.json`). Reuse this pattern only when the current implementation already expects spell-specific configuration.

### DK adaptations

- `tools/dk_adaptations.py` — existing DK-specific spell adaptation logic.

For DK spells, inspect this file before inventing another implementation path.

### Native core patches

- `tools/core_patch.py` — existing exact-anchor transformations for AzerothCore source files.
- `payload/core/` — Adventurer-owned source payloads that are installed into the core.

Only touch native AzerothCore source through the existing core-patch/install mechanism unless there is a verified technical reason that mechanism cannot express the required change.

### DBC / client / runtime tooling

- `tools/dbc.py` — DBC transformation/install logic.
- `tools/client.py` — client-side patching/install logic.
- `apply.sh` — clean/application entrypoint.
- `update.sh` — update entrypoint for an existing Adventurer installation.
- `rollback.sh` — existing rollback entrypoint.
- `preflight.sh` / `verify.sh` — existing validation entrypoints. Do not add new validation layers by default.

## Decision tree

### A. The spell only needs catalogue/selection changes

Prefer changing the SpellDraft catalogue/metadata only. Do not touch C++ or DBC unless required by actual game behavior.

### B. The spell needs its WotLK spell data adapted

Use the existing DBC adaptation path. Preserve the original spell identity whenever possible and change only the fields required for the Adventurer/SpellDraft behavior.

For rank/scaling work, follow the project's existing single-spell scaling conventions instead of creating a parallel rank system.

### C. The spell requires DK-specific behavior changes

Inspect and extend `tools/dk_adaptations.py` first.

If the required behavior cannot be represented through DBC/data changes and genuinely requires native server logic, then use the existing `tools/core_patch.py` path.

### D. The spell requires a native AzerothCore source change

1. Identify the exact native file that must change.
2. Add the smallest exact transformation necessary to the existing core patcher.
3. Do not build a new ownership/migration/test framework around the file.
4. If existing ownership machinery blocks the new file, modify only what is necessary for the current updater to accept the file; do not expand the scope into unrelated safeguards.

`src/server/game/Spells/SpellInfo.cpp` is already part of the current DK adaptation work and must not be treated as a novel architectural problem again.

## Scaling

Scaling is part of the spell implementation, not an optional cleanup step.

Before finishing a spell:

- preserve the intended WotLK progression/anchors used by the project;
- verify the values used at the relevant levels;
- when multiple original ranks share a level, use the project's established stronger-anchor rule where applicable;
- do not invent extra ranks simply to make a table look regular;
- keep cast time, resource cost, direct damage/healing, periodic totals/duration and other changing rank data in mind when the original spell varies them.

If an existing helper already handles single-spell scaling, extend/reuse it rather than duplicating the formula elsewhere.

## Validation policy

Default development loop:

1. Make the minimal change.
2. Run `apply.sh` or `update.sh` as appropriate.
3. Compile/restart only when the changed server code requires it.
4. Test the spell in game.
5. Fix the actual observed error or incorrect behavior.

Do not create new automated tests unless the user explicitly asks for them or approves them for a specific recurring failure.

Existing tests are not a reason to enlarge a spell change. If a stale test fails solely because implementation details changed, assess whether the test should be updated, removed, or ignored rather than automatically redesigning the feature to satisfy it.

## Before editing checklist

A new AI session should be able to answer these questions before changing a spell:

- What branch am I on?
- Where is the card/catalogue entry?
- What existing adapter currently changes this spell or the closest equivalent?
- Does the requested behavior require DBC, runtime/server logic, native C++, client metadata, or only catalogue data?
- What is the established scaling behavior?
- What are the smallest files that must change?

If those answers are not known, inspect the repository first. Do not fill the gaps by inventing new architecture.
