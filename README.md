# Adventurer Core

A reproducible patch layer for adding native **Adventurer (class ID 10)**
support to a compatible AzerothCore WotLK 3.3.5a Playerbots source tree.

> **Validated target:** `mod-playerbots/azerothcore-wotlk` commit
> `9fb906bb7296212ff42fc95ff73a92aaf8554f0d` is the first explicitly supported
> core baseline. Other commits are rejected unless intentionally overridden for
> development.

## Design

Adventurer Core is **not an AzerothCore module** and has no dependency on ALE,
SpellDraft, progression systems, or Dungeon Master. It modifies the compatible
core and its WotLK data so class slot 10 is a real playable class.

Technical names, code, filenames, and documentation structure are English.
`enUS` is the canonical locale and **esMX is first-class** for player-visible
content (`Adventurer` / `Aventurero`).

The workflow is:

```bash
./preflight.sh --core-dir /path/to/playerbots-core \
  --server-data-dir /path/to/install/data \
  --client-dir "/path/to/WoW 3.3.5a" \
  --locale esMX

./apply.sh --core-dir /path/to/playerbots-core \
  --server-data-dir /path/to/install/data \
  --client-dir "/path/to/WoW 3.3.5a" \
  --locale esMX
```

`preflight.sh` is read-only. It validates the exact core baseline, DBC/client
inputs, database connectivity, rollback tooling, and builds the generated
client/talent bundle in temporary storage.

`apply.sh` owns the complete transformation: core source, pending world
migration, server DBCs, client patch, state tracking, and verification. Before
any mutation it takes a selective snapshot of every world-DB row range the
Adventurer migration can replace, including the AzerothCore `updates` marker.
Database credentials are never written to the rollback state.

The installer does not compile the server; compilation remains a separate,
visible build step.

## Full rollback

```bash
./rollback.sh --core-dir /path/to/playerbots-core
```

Rollback restores the owned source files, generated server DBCs, client Z patch,
and the exact pre-install world-DB row set. It verifies snapshot hashes and the
configured database identities before changing anything.

Rollback deliberately refuses if any class-10 character rows remain in the
characters database. Remove/purge Adventurer test characters first; the tool
will never remove native class support underneath a recoverable class-10
character.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for ownership boundaries and
safety rules, and [`docs/ROLLBACK.md`](docs/ROLLBACK.md) for rollback details.
