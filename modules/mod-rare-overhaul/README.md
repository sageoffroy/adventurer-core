# Rare Overhaul v1

Portable AzerothCore module for making open-world rares more rewarding and more dangerous without modifying the core.

## Scope

V1 intentionally does only three things:

1. Adds the curated rare loot dataset from `StraysFromPath/mod-rare-drops`.
2. Multiplies maximum health of Rare and Rare Elite creatures at runtime.
3. Multiplies damage dealt by Rare and Rare Elite creatures at runtime.

No additional combat mechanics are included in v1.

## Defaults

```ini
RareOverhaul.Enable = 1
RareOverhaul.Difficulty.Enable = 1
RareOverhaul.HealthMultiplier = 2.0
RareOverhaul.DamageMultiplier = 2.0
```

The difficulty layer detects creatures by `creature_template.rank`, so it also applies automatically to rares added by another compatible AzerothCore database.

The runtime layer does not update `creature_template`, which keeps the feature removable and avoids permanently multiplying database values on repeated installs.

## Loot

The installer imports the loot SQL from the pinned upstream commit:

`StraysFromPath/mod-rare-drops@cf6ea06d32d751328836b65d9b7270975aa3c68a`

The upstream dataset is copied into the installed module as `data/sql/db-world/base/rare_overhaul_loot.sql` and its MIT license is retained as `LICENSE.rare-drops`.

## Install from adventurer-core

```bash
CORE_DIR=~/aventurerosdeazeroth bash tools/rare_overhaul/install.sh
```

Then rerun CMake for the AzerothCore build, compile with `make -j2`, and run `make install`.

## Portability

The installed `modules/mod-rare-overhaul` directory is self-contained after installation and can be copied to another compatible AzerothCore server. Its configuration and SQL stay inside the module.
