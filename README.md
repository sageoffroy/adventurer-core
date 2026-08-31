# Adventurer Core — SpellDraft v3

Patch layer for running the native **Adventurer (class ID 10)** and its SpellDraft gameplay on AzerothCore WotLK 3.3.5a.

`stable/spelldraft-v3` contains the Adventurer class, SpellDraft progression, the tested Tame Beast compatibility, and the v3 managed custom-icon layer. Gauntlet gameplay is not part of this branch; the matching dungeon layer is `stable/gauntlet-v3`.

## SpellDraft v3 icon pack

Custom `.blp` icon sources live in:

```text
client/icons/
```

After adding/changing the pack:

```bash
python3 tools/icon_pack.py catalog
```

The normal `apply.sh` / `update.sh` pipeline packages them into the Adventurer client patch under `Interface\\Icons\\` and maintains custom `SpellIcon.dbc` entries for new icon names. Matching Blizzard icon names override the stock visual through patch priority; Blizzard MPQs are not edited manually.

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
- [`docs/SPELLDRAFT.md`](docs/SPELLDRAFT.md) — current SpellDraft behavior and v3 icon pipeline.
- [`docs/SPELL_WORKFLOW.md`](docs/SPELL_WORKFLOW.md) — how to adapt a spell without inventing a parallel architecture.
- [`docs/ROLLBACK.md`](docs/ROLLBACK.md) — detailed rollback behavior.

Older version-specific SpellDraft documents are historical references only; current behavior is defined by the documents above and repository code/config.
