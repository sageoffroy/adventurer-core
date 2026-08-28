# Adventurer Core

A patch layer for AzerothCore WotLK 3.3.5a that turns class slot 10 into the playable **Adventurer / Aventurero** class and installs the project's SpellDraft gameplay.

## What this repository contains

- native class-10 server integration;
- SpellDraft cards, progression, persistence and meta mechanics;
- DBC transformations for server/client;
- client UI/resource changes;
- world database changes required by Adventurer;
- optional Playerbots compatibility;
- install, update and rollback tooling.

Talents are obtained through SpellDraft cards. Adventurer does not use a fixed Guardian/Champion/Scholar talent tree.

## Documentation

Start here:

- [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) — repository map, responsibilities and end-to-end flows.
- [`docs/SPELLDRAFT.md`](docs/SPELLDRAFT.md) — current SpellDraft model and runtime behavior.
- [`docs/SPELL_WORKFLOW.md`](docs/SPELL_WORKFLOW.md) — how to adapt an existing WoW spell without inventing a parallel implementation.
- [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) — working rules for new AI sessions.
- [`docs/ROLLBACK.md`](docs/ROLLBACK.md) — detailed rollback behavior.
- [`docs/spells/`](docs/spells/) — approved per-spell implementation notes and gameplay checks.

## Normal commands

Clean install:

```bash
./apply.sh \
  --core-dir /path/to/azerothcore \
  --server-data-dir /path/to/server-data \
  --dbc-src /path/to/clean/dbc \
  --client-dir "/path/to/WoW 3.3.5a" \
  --locale esMX
```

Update an existing Adventurer installation:

```bash
./update.sh \
  --core-dir /path/to/azerothcore \
  --server-data-dir /path/to/server-data \
  --dbc-src /path/to/clean/dbc \
  --client-dir "/path/to/WoW 3.3.5a" \
  --locale esMX
```

Full rollback:

```bash
./rollback.sh --core-dir /path/to/azerothcore
```

`preflight.sh` performs the existing compatibility preflight. `verify.sh` performs the existing verification pass. The installer does not compile `worldserver`; rebuilding remains a separate visible step when C++ changes require it.
