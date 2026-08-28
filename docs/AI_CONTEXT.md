# Aventureros de Azeroth — AI working context

This file is intentionally short. Its purpose is to let a new ChatGPT/Codex session recover the project's working conventions without rediscovering the repository from scratch.

## Repository scope

- Work for Aventureros de Azeroth is done in this repository: `sageoffroy/adventurer-core`.
- The native Adventurer class and SpellDraft integration are maintained here.
- Do not create a parallel implementation in another repository or invent a second installation pipeline.

## Read before changing code

1. Read this file.
2. Read `docs/PROJECT_GUIDE.md` for the repository map and system flows.
3. If the task involves SpellDraft, read `docs/SPELLDRAFT.md`.
4. If the task involves adapting a spell, read `docs/SPELL_WORKFLOW.md` and the closest existing file under `docs/spells/`.
5. Inspect the current branch and the latest commits relevant to the requested feature.
6. Inspect the existing implementation files referenced by those commits.
7. State the minimal files that need to change before editing anything.

Do not rely on branch names recorded in documentation as current state. The checked-out branch and Git history are the source of truth.

## Development rules

1. Prefer the smallest change that makes the requested game behavior work.
2. Before adding a new mechanism, search for and reuse the existing pattern used by previous adapted spells/features.
3. Do not add tests, manifests, validators, CI checks, backup layers, migration frameworks, or other defensive infrastructure unless the user explicitly requests them or a concrete recurring failure justifies them and the user agrees.
4. Do not refactor unrelated code while implementing a spell or gameplay feature.
5. Do not treat automated tests as the product goal. The primary validation loop for gameplay changes is: apply/update -> compile/start as needed -> test in game -> fix the observed failure.
6. If an existing test or ownership check blocks an otherwise valid requested change because it is stale, first determine whether that guard still provides real value. Do not automatically expand the guard or create more tests around it.
7. If a task can be solved by changing a few known files, do not perform a repository-wide redesign.
8. Keep changes reversible with normal Git history; avoid adding extra rollback machinery unless the existing installer genuinely requires it.
9. Reuse the existing `apply.sh` / `update.sh` / core-patch / DBC / client pipeline instead of building parallel tooling.

## Important repository behavior

- `tools/core_patch.py` contains exact/anchor-based transformations for native AzerothCore source files.
- `tools/dk_adaptations.py` contains existing DK-specific adaptation logic.
- `config/spelldraft/cards.csv` is the SpellDraft card catalogue.
- Existing ownership/update logic may reject modifications to core files that were not previously tracked. Treat that as an implementation detail of the current updater, not as a reason to build a new framework.
- The repository already contains substantial automated-test and ownership infrastructure. Do not add more by default.

## Source-of-truth order

When information conflicts, use this order:

1. The user's explicit current instruction.
2. The current repository code and checked-out branch.
3. `docs/PROJECT_GUIDE.md` and current feature documentation.
4. This file.
5. Historical Git commits and archived design notes.

Update this file only when a durable project convention changes.
