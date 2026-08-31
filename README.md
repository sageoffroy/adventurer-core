# Adventurer Core

Patch layer for running **Aventureros de Azeroth** on AzerothCore WotLK 3.3.5a.

The project has two technical layers:

- **Adventurer + SpellDraft** — the native Adventurer class (class ID 10), its server/client/runtime integration, SpellDraft card progression, and the shared client visual/DBC layer.
- **Gauntlet** — the dungeon/roguelike module layered on top of the matching stable SpellDraft major version.

Current stable relationship:

```text
stable/spelldraft-v3
  = Adventurer + SpellDraft v3 + managed icon pack

stable/gauntlet-v3
  = SpellDraft v3 + mod-adventurer-gauntlet
```

Gauntlet depends on SpellDraft; SpellDraft does not depend on Gauntlet. Gauntlet-only releases may advance as `v3.1`, `v3.2`, etc. A future SpellDraft major version creates the corresponding Gauntlet major line after integration.

## SpellDraft v3 icons

Custom `.blp` icons live in `client/icons/`. Run `python3 tools/icon_pack.py catalog` after adding/changing the pack. The normal `apply.sh` / `update.sh` pipeline then places the icons and managed `SpellIcon.dbc` into the Adventurer client patch; Blizzard MPQs are not edited manually.

## Adventurer / SpellDraft install

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

Gauntlet has an additional module installation step documented in [`docs/GAUNTLET.md`](docs/GAUNTLET.md). Gauntlet v3 adds `Lobo solitario` and the account-wide `Libro de Objetos`.

## Documentation

Start here:

- [`docs/AI_CONTEXT.md`](docs/AI_CONTEXT.md) — project working rules for a new AI/developer session.
- [`docs/PROJECT_GUIDE.md`](docs/PROJECT_GUIDE.md) — repository map, important files and end-to-end flows.
- [`docs/SPELLDRAFT.md`](docs/SPELLDRAFT.md) — current Adventurer/SpellDraft behavior and v3 icon pipeline.
- [`docs/SPELL_WORKFLOW.md`](docs/SPELL_WORKFLOW.md) — how to adapt a spell without inventing a parallel architecture.
- [`docs/GAUNTLET.md`](docs/GAUNTLET.md) — Gauntlet module boundaries, versioning, v3 systems and install/update flow.
- [`docs/ROLLBACK.md`](docs/ROLLBACK.md) — detailed rollback behavior.

Old `feature/khadgar-gauntlet-*` branches and the old `aventurerosdeazeroth/feature/mod-dungeon-master` branch are historical development references only. They are not current architecture sources.

Older version-specific SpellDraft documents are historical references only; current behavior is defined by the documents above and repository code/config.
