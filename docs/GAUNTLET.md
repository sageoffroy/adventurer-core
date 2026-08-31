# Aventureros de Azeroth — Gauntlet

Gauntlet is the dungeon/roguelike module of Aventureros de Azeroth. It is intentionally layered on top of the Adventurer + SpellDraft base rather than being part of SpellDraft itself.

## Project layering

```text
stable/spelldraft-v2
  = native Adventurer class + SpellDraft v2

stable/gauntlet-v2
  = stable/spelldraft-v2 + mod-adventurer-gauntlet

feature/spelldraft-v3
  = SpellDraft v2 + external/custom icon system

feature/gauntlet-v3
  = feature/spelldraft-v3 + Gauntlet v3 gameplay
```

SpellDraft does not depend on Gauntlet. Gauntlet depends on the matching SpellDraft major version.

## Versioning rule

- `stable/spelldraft-v2` is the stable Adventurer/SpellDraft v2 base.
- `stable/gauntlet-v2` is Gauntlet running on SpellDraft v2.
- Gauntlet-only evolution may use `v2.1`, `v2.2`, and so on without changing the SpellDraft major version.
- `feature/spelldraft-v3` and `feature/gauntlet-v3` are test/development branches until in-game validation is complete.
- When SpellDraft v3 is accepted, it becomes `stable/spelldraft-v3`; validated Gauntlet on that base becomes `stable/gauntlet-v3`.
- Do not merge Gauntlet changes back into SpellDraft merely because Gauntlet changes. The dependency direction is SpellDraft -> Gauntlet.

Old branches such as `feature/khadgar-gauntlet-v1`, `feature/khadgar-gauntlet-v1-clientfix`, and the old `aventurerosdeazeroth/feature/mod-dungeon-master` are historical development branches, not current architecture sources.

## Gauntlet v3 additions

### Lobo solitario

Spell ID `910501` is a Gauntlet-owned marker aura named **Lobo solitario**. It is automatically present while a pledged Adventurer is inside a supported Gauntlet dungeon without companions, and removed outside that condition.

The initial v3 implementation deliberately does not add an unrequested numeric combat bonus. It establishes the solo-run state and provides the first visible test of SpellDraft v3 custom icon support. The reserved custom SpellIcon ID is `910000`, backed by `lobo_solitario.blp` from the external icon pack.

### Libro de Objetos

The Libro de Objetos is an account-wide discovery collection for Gauntlet-created items in the current `911100-911399` namespace.

- Discovery happens when a character actually loots one of those items.
- The discovery is stored by account, not by character.
- Character death or later item loss does not remove the discovery.
- The book is a collection, not storage: it cannot restore or duplicate items.
- The client receives only discovered item IDs; undiscovered entries are not exposed by the book UI.
- During v3 testing the book opens with `/libro` or `/objetos`.

Persistence lives in `adventurer_gauntlet_account_collection` in the characters database.

## Module location

Server-side Gauntlet implementation:

```text
modules/mod-adventurer-gauntlet/
```

Important areas:

- `src/AdventurerGauntlet.cpp` — main dungeon-run gameplay orchestration.
- `src/GauntletScaling.cpp` — Gauntlet creature/group scaling and Lobo solitario state.
- `src/GauntletPermadeath.cpp` — run death/permadeath behavior.
- `src/CuratedRewards.cpp` — controlled boss reward generation; current checkpoint/final rewards are written directly to boss corpse loot.
- `src/AccountStash.cpp` — account stash behavior.
- `src/AccountCollection.cpp` — account-wide item discovery collection.
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

## SpellDraft v3 icon dependency

The large icon pack stays outside Git by default:

```text
~/adventurer-icons/
└── Interface/
    └── Icons/
        ├── lobo_solitario.blp
        └── ...
```

Files must currently be valid BLP1/BLP2 textures. SpellDraft v3 packs them into Adventurer-owned Z MPQs and extends `SpellIcon.dbc` for genuinely new icon paths. It does not replace Blizzard MPQ archives in place.

## Shared integration points

Gauntlet gameplay code remains isolated in its module. Shared technical integration is limited to the final client/server DBC bundle, principally `Spell.dbc`, `SpellIcon.dbc` and `Item.dbc`, because Gauntlet custom spells/items must reach the same client that SpellDraft uses.

Do not move Gauntlet gameplay logic into SpellDraft files merely to avoid these integration points.

## v3 test installation

Use `feature/gauntlet-v3` only while v3 is under test. The external icon pack must already exist at the path above.

```bash
cd ~/adventurer-core
git fetch origin
git switch feature/gauntlet-v3
git reset --hard origin/feature/gauntlet-v3

./update.sh \
  --core-dir ~/aventurerosdeazeroth \
  --server-data-dir ~/aventurerosdeazeroth/env/dist/data \
  --dbc-src ~/dbc-clean-esMX/dbc/esMX \
  --client-dir "/mnt/c/Games/World of Warcraft 3.3.5a" \
  --locale esMX

CORE_DIR=~/aventurerosdeazeroth \
SERVER_DATA_DIR=~/aventurerosdeazeroth/env/dist/data \
DBC_SRC=~/dbc-clean-esMX/dbc/esMX \
CLIENT_DIR="/mnt/c/Games/World of Warcraft 3.3.5a" \
  bash tools/khadgar_gauntlet/install.sh
```

Then compile/install:

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
