# Adventurer Core

A reproducible patch layer for adding native **Adventurer (class ID 10)**
support to a compatible AzerothCore WotLK 3.3.5a Playerbots source tree.

> **Bootstrap status:** the historical implementation is being extracted and
> audited. The installer intentionally refuses production application until the
> exact clean Playerbots base commit is frozen in `compatibility.json`.

## Design

Adventurer Core is **not an AzerothCore module** and has no dependency on ALE,
SpellDraft, progression systems, or Dungeon Master. It modifies the compatible
core and its WotLK data so class slot 10 is a real playable class.

Technical names, code, filenames, and documentation structure are English.
`enUS` is the canonical locale and **esMX is first-class** for player-visible
content (`Adventurer` / `Aventurero`).

The intended final workflow is:

```bash
./apply.sh --core-dir /path/to/playerbots-core \
  --server-data-dir /path/to/install/data \
  --client-dir "/path/to/WoW 3.3.5a" \
  --locale esMX
```

The script will own the complete transformation: core source, world migration,
server DBCs, client patch, state tracking, and verification. It will not compile
unless explicitly requested; compilation remains a separate, visible build step.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for ownership boundaries and
safety rules.
