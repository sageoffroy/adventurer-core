# SpellDraft — spell adaptation workflow

This is the operational guide for adapting an existing WoW spell for Adventurer/SpellDraft. It is not a requirement to touch every file listed here. Inspect the existing path and change only what the requested spell actually needs.

## Start here

For every spell adaptation:

1. Identify the existing SpellDraft card entry in `config/spelldraft/cards.csv`.
2. Inspect the current adaptation mechanism for the same spell family or the closest already-working spell.
3. Determine whether the change is data-only, DBC/client data, server-runtime behavior, native core behavior, or a combination.
4. List the minimal files that need modification before editing.
5. Reuse the existing apply/update pipeline.

Do not begin by creating a new module, framework, test suite, manifest, validator, or migration mechanism.

## Relevant existing paths

### SpellDraft catalogue and metadata

- `config/spelldraft/cards.csv` — card catalogue used by SpellDraft.
- `config/spelldraft/catalog_metadata.csv` — catalogue metadata where applicable.
- `config/spelldraft/spelldraft.conf` — SpellDraft configuration.
- `config/spelldraft/subclasses.json` — subclass data; only relevant when the requested change affects subclass behavior/presentation.

### Native core patches

- `tools/core_patch.py` — existing exact-anchor transformations for AzerothCore source files.
- `payload/core/` — Adventurer-owned source payloads installed into the core.

Only touch native AzerothCore source through the existing core-patch/install mechanism unless there is a verified technical reason that mechanism cannot express the required change.

### DBC / client / runtime tooling

- `tools/dbc.py` — DBC transformation/install logic.
- `tools/client.py` — client-side patching/install logic.
- `tools/spelldraft_runtime.py` — SpellDraft packaged/runtime catalogue/config handling.
- `tools/spell_rank_tabs.py` — rank/tab generation path.
- `apply.sh` — clean/application entrypoint.
- `update.sh` — update entrypoint for an existing Adventurer installation.
- `rollback.sh` — existing rollback entrypoint.
- `preflight.sh` / `verify.sh` — existing validation entrypoints. Do not add new validation layers by default.

## Decision tree

### A. Catalogue/selection only

Prefer changing catalogue/metadata only. Do not touch C++ or DBC unless actual game behavior requires it.

### B. Native WotLK spell data needs adaptation

Use the existing DBC adaptation path. Preserve the original spell identity whenever possible and change only fields required for the Adventurer/SpellDraft behavior.

For rank/scaling work, follow the project's existing conventions instead of creating a parallel rank system.

### C. Native server behavior is required

1. Identify the exact native file that must change.
2. Add the smallest exact transformation necessary to `tools/core_patch.py`.
3. Reuse an existing helper/payload if appropriate.
4. Do not build a new ownership/migration/test framework around the file.
5. If existing ownership machinery blocks the new file, modify only what is necessary for the current updater to accept it.

## Scaling

Scaling is part of the spell implementation, not an optional cleanup step.

Before finishing a spell:

- preserve the intended WotLK progression/anchors used by the project;
- verify values at relevant levels;
- when multiple original ranks share a level, use the project's established stronger-anchor rule where applicable;
- do not invent extra ranks merely to regularize a table;
- account for cast time, resource cost, direct damage/healing, periodic totals/duration and other values that change between ranks.

If an existing helper already handles the required scaling pattern, extend/reuse it rather than duplicating formulas.

## Validation policy

Default loop:

1. Make the minimal change.
2. Run `apply.sh` or `update.sh` as appropriate.
3. Compile/restart only when changed server code requires it.
4. Test the spell in game.
5. Fix the actual observed error or incorrect behavior.

Do not create new automated tests unless the user explicitly asks for them or approves them for a specific recurring failure.

Existing tests are not a reason to enlarge a spell change. If a stale test fails solely because implementation details changed, assess whether the test should be updated, removed, or ignored rather than redesigning the feature to satisfy it.

## Before editing checklist

A new AI session should be able to answer:

- What branch am I on?
- Where is the card/catalogue entry?
- What existing implementation is the closest pattern?
- Does the requested behavior require DBC, runtime/server logic, native C++, client metadata, or only catalogue data?
- What is the established scaling behavior?
- What are the smallest files that must change?

If those answers are not known, inspect the repository first. Do not fill gaps by inventing new architecture.
