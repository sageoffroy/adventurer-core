# Adventurer Core

Patch layer for running the native **Adventurer (class ID 10)** and its SpellDraft gameplay on AzerothCore WotLK 3.3.5a.

The project makes the unused class slot 10 playable, installs the Adventurer server/client/runtime pieces, and uses SpellDraft cards for abilities and talents. Playerbots integration is optional and detected when present.

## Install

```bash
./preflight.sh --core-dir /path/to/azerothcore \
  --server-data-dir /path/to/server-data \
  --dbc-src /path/to/clean/dbc \
  --client-dir "/path/to/WoW 3.3.5a" \
  --locale esMX

./apply.sh --core-dir /path/to/azerothcore \
  --server-data-dir /path/to/server-data \
  --dbc-src /path/to/clean/dbc \
  --client-dir "/path/to/WoW 3.3.5a" \
  --locale esMX
```

For an existing Adventurer installation use `update.sh`. The installer does not compile worldserver; rebuild/restart separately when native server code changes.

## Documentation

Start here:

- [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) — project working rules for a new AI/developer session.
- [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) — repository map, important files and end-to-end flows.
- [`docs/SPELLDRAFT.md`](docs/SPELLDRAFT.md) — current SpellDraft behavior.
- [`docs/SPELL_WORKFLOW.md`](docs/SPELL_WORKFLOW.md) — how to adapt a spell without inventing a parallel architecture.
- [`docs/ROLLBACK.md`](docs/ROLLBACK.md) — detailed rollback behavior.

Older version-specific SpellDraft documents are historical references only; current behavior is defined by the documents above and repository code/config.
