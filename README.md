# Adventurer Core

A reproducible patch layer for running the native **Adventurer (class ID 10)**
and its SpellDraft v1 gameplay on AzerothCore WotLK 3.3.5a.

The installer supports both stock AzerothCore and a core with
`modules/mod-playerbots`. Playerbots integration is detected automatically and
is skipped when that module is not present.

## Design

Adventurer Core makes the unused WotLK class slot 10 a real playable classless
class and installs the SpellDraft runtime used to obtain abilities and talents.

Talents are **exclusively SpellDraft cards**. There is no native fixed
Guardian/Champion/Scholar talent tree. The client `Libro de talentos` is a
collection view of talents actually obtained through SpellDraft.

The four presentation families used by the spellbook and talent collection are:

- Mercenario
- Explorador
- Hechicero
- Iluminado

Technical names, code, filenames, and documentation structure are English.
`enUS` is the canonical locale and **esMX is first-class** for player-visible
content (`Adventurer` / `Aventurero`).

## Installation

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

`preflight.sh` is read-only. Compatibility is validated from the actual
AzerothCore source files, exact patch anchors and APIs required by Adventurer;
it is not gated by a frozen Git commit SHA.

`apply.sh` owns the complete transformation: core source, native class world
rows, SpellDraft runtime data, server DBCs, subclass metadata, client patch,
state tracking and rollback snapshot. If Playerbots is present its small
compatibility layer/profile is applied as an optional extension.

Old development installations may contain fixed Guardian/Champion/Scholar DBC
rows in Adventurer-owned ID ranges. Current builds never generate those rows;
the DBC build only removes them when found so upgrades converge to the
SpellDraft-only talent model.

The installer does not compile the server; compilation remains a separate,
visible build step.

## Full rollback

```bash
./rollback.sh --core-dir /path/to/azerothcore
```

Rollback restores owned source files, generated server DBCs, client patch and
the exact pre-install world-DB row set. It verifies ownership before modifying
anything and refuses to destroy unrelated edits.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for ownership boundaries and
[`docs/ROLLBACK.md`](docs/ROLLBACK.md) for rollback details.
