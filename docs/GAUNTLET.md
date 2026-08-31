# Aventureros de Azeroth — Gauntlet

Gauntlet is the dungeon/roguelike module of Aventureros de Azeroth. It is intentionally layered on top of the Adventurer + SpellDraft base rather than being part of SpellDraft itself.

## Project layering

```text
stable/spelldraft-v3
  = native Adventurer class + SpellDraft + v3 icon pack

stable/gauntlet-v3
  = stable/spelldraft-v3 + mod-adventurer-gauntlet
```

SpellDraft does not depend on Gauntlet. Gauntlet depends on the matching SpellDraft major version.

## Versioning rule

- A SpellDraft major version defines the Adventurer/SpellDraft base used by Gauntlet.
- `stable/gauntlet-v3` runs on `stable/spelldraft-v3`.
- Gauntlet-only evolution may use `v3.1`, `v3.2`, and so on without changing the SpellDraft major version.
- When SpellDraft eventually becomes `stable/spelldraft-v4`, Gauntlet is integrated on top of that base and becomes `stable/gauntlet-v4`.
- Do not merge Gauntlet changes back into SpellDraft merely because Gauntlet changes. The dependency direction is SpellDraft -> Gauntlet.

Old branches such as `feature/khadgar-gauntlet-v1`, `feature/khadgar-gauntlet-v1-clientfix`, and the old `aventurerosdeazeroth/feature/mod-dungeon-master` are historical development branches, not current architecture sources.

## Gauntlet v3 additions

### Lobo solitario

Custom aura spell `910501` is applied when an adventurer enters one of the currently managed Gauntlet dungeon maps alone and removed when leaving.

The first v3 implementation is intentionally a visible recognition aura rather than an unreviewed balance modifier. It validates the custom spell/name/tooltip/icon pipeline without silently changing combat tuning. Mechanical bonuses can be added later as an explicit Gauntlet balance decision.

When the SpellDraft v3 icon pack contains a file whose basename is:

```text
lobo_solitario.blp
```

`910501` automatically uses that custom `SpellIcon.dbc` entry. Until then it falls back to a stock icon so the mode remains testable.

### Libro de Objetos

The Libro de Objetos is Gauntlet account progression, not SpellDraft progression.

- Current custom Adventurer equipment in `910200-910224` and Gauntlet reward equipment in `911100-911399` are eligible for discovery when actually looted.
- Discovery is persisted by `account_id`, independently of the character that found the item.
- Character death or deletion does not remove a discovery.
- The client receives only discovered entries; undiscovered objects are not exposed by the book UI.
- The book is opened with `/objetos` or `/librodeobjetos` in the first v3 UI.

Persistence lives in:

```text
adventurer_gauntlet_account_collection
```

The Libro records discovery only. It is not storage and does not recreate or duplicate the item. The separate Baul de Expediciones remains the item-survival/storage mechanic.

## Module location

Server-side Gauntlet implementation:

```text
modules/mod-adventurer-gauntlet/
```

Important areas:

- `src/AdventurerGauntlet.cpp` — main dungeon-run gameplay orchestration.
- `src/GauntletScaling.cpp` — Gauntlet creature/group scaling.
- `src/GauntletPermadeath.cpp` — run death/permadeath behavior.
- `src/LoneWolf.cpp` — v3 solo-entry aura behavior.
- `src/CuratedRewards.cpp` — controlled boss reward generation. Current Ragefire checkpoint/final rewards are written directly to boss corpse loot.
- `src/AccountStash.cpp` — account stash behavior.
- `src/AccountCollection.cpp` — account-wide custom-item discoveries for Libro de Objetos.
- `src/SetBonuses.cpp` — custom Gauntlet set-bonus behavior.
- `src/KhadgarCelebration.cpp` — Khadgar-related run presentation/celebration behavior.
- `data/items/early_items.csv` — curated/custom reward item catalogue.
- `data/items/sets.csv` — Gauntlet set definitions.
- `data/sql/` — Gauntlet-owned database updates.

Client/build tooling:

```text
tools/khadgar_gauntlet/
```

This directory contains the Gauntlet installer, client addon pieces, item/set generators and DBC patch helpers. The historical directory name is retained to avoid needless path churn; it does not mean Khadgar is the whole feature.

`tools/gauntlet_spells.py` is the v3 source of truth for Gauntlet-owned custom Spell.dbc rows. Those rows are layered into the SpellDraft v3 client/server DBC pipeline so the client and worldserver receive the same data.

## Shared integration points

Gauntlet gameplay code remains isolated in its module. Shared technical integration is limited to data that must reach the common WoW client/server bundle:

- `tools/sync_item_dbc.py` for Gauntlet item metadata;
- the SpellDraft v3 icon/Spell DBC pipeline for Gauntlet-owned custom auras such as Lobo solitario.

Do not move Gauntlet gameplay logic into SpellDraft files merely to avoid these integration points.

## Installation/update flow

On a server that already has Adventurer/SpellDraft installed, use the Gauntlet branch's normal Adventurer update first, then install the module:

```bash
cd ~/adventurer-core

git fetch origin
git switch stable/gauntlet-v3
git reset --hard origin/stable/gauntlet-v3

./update.sh \
  --core-dir ~/aventurerosdeazeroth \
  --server-data-dir ~/aventurerosdeazeroth/env/dist/data \
  --dbc-src ~/dbc-clean-esMX/dbc/esMX \
  --client-dir "/mnt/c/Games/World of Warcraft 3.3.5a" \
  --locale esMX

CORE_DIR=~/aventurerosdeazeroth \
SERVER_DATA_DIR=~/aventurerosdeazeroth/env/dist/data \
CLIENT_DIR="/mnt/c/Games/World of Warcraft 3.3.5a" \
  bash tools/khadgar_gauntlet/install.sh
```

Then compile/install with the project-standard build command:

```bash
cd ~/aventurerosdeazeroth/build
make -j2
make install
```

Run from:

```bash
cd ~/aventurerosdeazeroth/env/dist/bin
./worldserver
```

## Development rule

For Gauntlet-only work, start from the latest stable Gauntlet branch for the current SpellDraft major version. Do not switch back to an old Khadgar or Dungeon Master feature branch.

When SpellDraft receives a new stable major version, integrate that stable base into Gauntlet once, validate both systems together, and then continue Gauntlet development on the new major line.
