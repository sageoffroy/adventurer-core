# Aventureros de Azeroth — Gauntlet

Gauntlet is the dungeon/roguelike module of Aventureros de Azeroth. It is intentionally layered on top of the Adventurer + SpellDraft base rather than being part of SpellDraft itself.

## Project layering

```text
stable/spelldraft-v2
  = native Adventurer class + SpellDraft

stable/gauntlet-v2
  = stable/spelldraft-v2 + mod-adventurer-gauntlet
```

SpellDraft does not depend on Gauntlet. Gauntlet depends on the matching SpellDraft major version.

## Versioning rule

- `stable/spelldraft-v2` is the stable Adventurer/SpellDraft v2 base.
- `stable/gauntlet-v2` is Gauntlet running on SpellDraft v2.
- Gauntlet-only evolution may use `v2.1`, `v2.2`, and so on without changing the SpellDraft major version.
- When the stable SpellDraft base becomes `stable/spelldraft-v3`, Gauntlet is integrated on top of that base and becomes `stable/gauntlet-v3`.
- Do not merge Gauntlet changes back into SpellDraft merely because Gauntlet changes. The dependency direction is SpellDraft -> Gauntlet.

Old branches such as `feature/khadgar-gauntlet-v1`, `feature/khadgar-gauntlet-v1-clientfix`, and the old `aventurerosdeazeroth/feature/mod-dungeon-master` are historical development branches, not current architecture sources.

## Module location

Server-side Gauntlet implementation:

```text
modules/mod-adventurer-gauntlet/
```

Important areas:

- `src/AdventurerGauntlet.cpp` — main dungeon-run gameplay orchestration.
- `src/GauntletScaling.cpp` — Gauntlet creature/group scaling.
- `src/GauntletPermadeath.cpp` — run death/permadeath behavior.
- `src/CuratedRewards.cpp` — controlled boss reward generation. Current Ragefire checkpoint/final rewards are written directly to boss corpse loot.
- `src/AccountStash.cpp` — account stash behavior.
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

## Shared integration point

Gauntlet gameplay code remains isolated in its module. The main known shared technical integration with the Adventurer/SpellDraft base is the client/server item DBC pipeline, including `tools/sync_item_dbc.py`, because Gauntlet custom equipment must reach the same final client/server `Item.dbc` bundle.

Do not move Gauntlet gameplay logic into SpellDraft files merely to avoid this integration point.

## Installation/update flow

On a server that already has Adventurer/SpellDraft installed, use the Gauntlet branch's normal Adventurer update first, then install the module:

```bash
cd ~/adventurer-core

git fetch origin
git switch stable/gauntlet-v2
git reset --hard origin/stable/gauntlet-v2

./update.sh \
  --core-dir ~/aventurerosdeazeroth \
  --server-data-dir ~/aventurerosdeazeroth/env/dist/data \
  --dbc-src ~/dbc-clean-esMX/dbc/esMX \
  --client-dir "/mnt/c/Games/World of Warcraft 3.3.5a" \
  --locale esMX

CORE_DIR=~/aventurerosdeazeroth bash tools/khadgar_gauntlet/install.sh
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
