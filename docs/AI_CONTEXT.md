# Aventureros de Azeroth — AI working context

This file lets a new ChatGPT/Codex session recover the project's working conventions without rediscovering the repository from scratch.

## Repository scope

- Work for Aventureros de Azeroth is done in this repository: `sageoffroy/adventurer-core`.
- The native Adventurer class and SpellDraft integration are maintained here.
- Gauntlet is the dungeon/roguelike module layered on top of the matching stable SpellDraft major version.
- Do not create a parallel implementation in another repository or invent a second installation pipeline.

## Stable branch model

- `stable/spelldraft-v3` = Adventurer + SpellDraft v3 + managed custom icon layer.
- `stable/gauntlet-v3` = SpellDraft v3 + `mod-adventurer-gauntlet`.
- Gauntlet-only evolution may advance as `v3.1`, `v3.2`, etc. without changing the SpellDraft major version.
- A future SpellDraft major version is integrated once into Gauntlet and starts the matching Gauntlet major line.
- Gauntlet depends on SpellDraft; SpellDraft must not acquire Gauntlet gameplay logic merely to keep branches synchronized.
- Old `feature/khadgar-gauntlet-*` branches and the old `aventurerosdeazeroth/feature/mod-dungeon-master` branch are historical references, not active bases for new work.

## Development rules

1. Prefer the smallest change that makes the requested game behavior work.
2. Before adding a new mechanism, search for and reuse the existing pattern used by previous features.
3. Do not add tests, manifests, validators, CI checks, backup layers, migration frameworks, or other defensive infrastructure unless the user explicitly requests them or a concrete recurring failure justifies them and the user agrees.
4. Do not refactor unrelated code while implementing a feature.
5. Do not treat automated tests as the product goal. The primary validation loop is: apply/update -> compile/start as needed -> test in game -> fix the observed failure.
6. If an existing test or ownership check blocks an otherwise valid requested change because it is stale, first determine whether that guard still provides real value. Do not automatically expand the guard or create more tests around it.
7. If a task can be solved by changing a few known files, do not perform a repository-wide redesign.
8. Keep changes reversible with normal Git history; avoid adding extra rollback machinery unless the existing installer genuinely requires it.
9. For Gauntlet-only work, start from the latest stable Gauntlet branch for the current SpellDraft major version, not from an old Khadgar/Dungeon Master feature branch.

## Existing architecture

- Native core source transformations are centralized in `tools/core_patch.py`.
- DBC work uses the existing `tools/dbc.py` path.
- Client changes use the existing `tools/client.py` path.
- SpellDraft catalogue/runtime work uses `config/spelldraft/` and the existing runtime tooling.
- SpellDraft v3 custom BLP sources live in `client/icons/`; `tools/icon_pack.py` owns their stable catalogue and `tools/icon_client.py` layers them into the existing client/DBC pipeline.
- Gauntlet server gameplay lives under `modules/mod-adventurer-gauntlet/`.
- Gauntlet-specific client/build helpers live under `tools/khadgar_gauntlet/`; the historical directory name is retained only to avoid path churn.
- Gauntlet v3 owns Lobo solitario and Libro de Objetos; neither belongs in the SpellDraft gameplay layer.
- Shared Gauntlet/base integration is limited to common client/server data such as item metadata and Gauntlet custom Spell.dbc rows.
- Client/DBC/server changes must follow the existing `apply.sh` / `update.sh` pipeline rather than introducing a second user-facing installer.

## How a new AI session should start

Before changing code:

1. Read this file.
2. Read `docs/PROJECT_GUIDE.md`.
3. If the task is SpellDraft-related, read `docs/SPELLDRAFT.md`.
4. If adapting a spell, read `docs/SPELL_WORKFLOW.md`.
5. If the task is dungeon/Gauntlet-related, read `docs/GAUNTLET.md` and `modules/mod-adventurer-gauntlet/README.md`.
6. Inspect the current branch and the latest commits relevant to the requested feature.
7. Inspect the existing implementation files referenced by those commits.
8. State the minimal files that need to change before editing anything.
9. Reuse existing patterns; do not invent a new architecture unless the current one demonstrably cannot support the requested behavior.

If repository state contradicts this document, repository code and the user's explicit current instruction take precedence. Update this file only when a durable project convention changes.
