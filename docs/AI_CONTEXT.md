# Aventureros de Azeroth — AI working context

This file is intentionally short. Its purpose is to let a new ChatGPT/Codex session recover the project's working conventions without rediscovering the repository from scratch.

## Repository scope

- Work for Aventureros de Azeroth is done in this repository: `sageoffroy/adventurer-core`.
- The native Adventurer class and SpellDraft integration are maintained here.
- Do not create a parallel implementation in another repository or invent a second installation pipeline.

## Current SpellDraft / DK work

- Active development branch at the time this file was added: `feature/spelldraft-v1-with-dk`.
- DK spell adaptations must reuse the existing SpellDraft and core-patching mechanisms already present in this repository.
- `config/spelldraft/cards.csv` is the SpellDraft card catalogue.
- DK-specific adaptation logic exists in `tools/dk_adaptations.py`.
- Native core source transformations are centralized in `tools/core_patch.py`.
- Client/DBC/server changes must follow the existing `apply.sh` / `update.sh` pipeline rather than introducing a new installer.

## Development rules

1. Prefer the smallest change that makes the requested game behavior work.
2. Before adding a new mechanism, search for and reuse the existing pattern used by previous adapted spells/features.
3. Do not add tests, manifests, validators, CI checks, backup layers, migration frameworks, or other defensive infrastructure unless the user explicitly requests them or a concrete recurring failure justifies them and the user agrees.
4. Do not refactor unrelated code while implementing a spell.
5. Do not treat automated tests as the product goal. The primary validation loop for gameplay changes is: apply/update -> compile/start as needed -> test in game -> fix the observed failure.
6. If an existing test or ownership check blocks an otherwise valid requested change because it is stale, first determine whether that guard still provides real value. Do not automatically expand the guard or create more tests around it.
7. If a task can be solved by changing a few known files, do not perform a repository-wide redesign.
8. Keep changes reversible with normal Git history; avoid adding extra rollback machinery unless the existing installer genuinely requires it.

## Important repository behavior

- `tools/core_patch.py` uses exact/anchor-based source transformations. When a core source file must be modified, extend the existing transformation path instead of creating a second patching system.
- Existing ownership/update logic may reject modifications to core files that were not previously tracked. Treat that as an implementation detail of the current updater, not as a reason to build a new framework.
- The repository already contains substantial automated-test and ownership infrastructure. Do not add more by default.

## How a new AI session should start

Before changing code:

1. Read this file.
2. Read `docs/SPELL_WORKFLOW.md`.
3. Inspect the current branch and the latest commits relevant to the requested spell/feature.
4. Inspect the existing implementation files referenced by those commits.
5. State the minimal files that need to change before editing anything.
6. Reuse existing patterns; do not invent a new architecture unless the current one demonstrably cannot support the requested behavior.

If repository state contradicts this document, repository code and the user's explicit current instruction take precedence. Update this file only when a durable project convention changes.
