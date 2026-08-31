# SpellDraft — current model

This document describes the current SpellDraft behavior in this branch. It supersedes older version-specific design notes.

## Core idea

The card is the unit of progression. A card can grant one spell, several related spells, or one rank in a passive/talent chain.

SpellDraft is the progression system for the native Adventurer class. Talents are obtained as SpellDraft cards rather than through a fixed native talent tree.

## SpellDraft v3 visual layer

SpellDraft v3 adds a managed custom icon pack to the normal Adventurer client pipeline.

Source icons live in:

```text
client/icons/
```

After copying or changing `.blp` files, rebuild the stable icon catalogue with:

```bash
python3 tools/icon_pack.py catalog
```

The resulting `client/icons/catalog.csv` assigns persistent custom `SpellIcon.dbc` IDs beginning at `910000`. Existing filename-to-ID assignments are preserved when the catalogue is regenerated.

During `apply.sh` / `update.sh` the v3 client pipeline:

1. includes the custom BLP files in the Adventurer `patch-Z` root archive under `Interface\\Icons\\`;
2. makes `SpellIcon.dbc` part of the managed client/server DBC bundle;
3. adds catalogue rows for custom icons;
4. preserves the icon bundle when SpellDraft rank metadata rebuilds the client patch.

A custom BLP whose path/name matches a Blizzard icon overrides that icon through normal patch priority. New icon names remain available to custom spells through their assigned `SpellIcon.dbc` IDs.

The clean Blizzard MPQs and clean DBC source are not edited manually.

## Card data

Packaged card data lives in `config/spelldraft/cards.csv`.

The catalogue contains fields for card identity, type, source level, rarity, weight, rank grants, prerequisites/unlocks and display metadata.

Related metadata lives in `config/spelldraft/catalog_metadata.csv` and subclass presentation data lives in `config/spelldraft/subclasses.json`.

## Card types

- Active cards grant active abilities or active bundles.
- Talent cards grant passive/talent ranks and may progress through several spell IDs.

Active spell families rank automatically when the underlying spell family has later ranks and the character reaches the relevant level. Talent ranks are separate SpellDraft choices.

## Rarity and weight

Rarity and weight are separate concepts. Rarity controls the general draw difficulty of a quality; weight controls how strongly an eligible card competes with other eligible cards.

The runtime combines the configured values during weighted selection.

## Eligibility graph

Cards are filtered server-side before an offer is generated. A card can require another card or a minimum owned rank. Selecting a card can unlock other active or talent cards.

Dependent cards are not automatically granted unless a card explicitly bundles multiple spell grants.

## Progression

The current progression model queues active and talent picks independently. Level transitions can queue multiple unresolved picks, and unresolved offers persist across relog.

The runtime is authoritative: the client displays offers but does not decide eligibility or ownership.

## Meta mechanics

The current data-driven SpellDraft runtime includes persistent meta actions:

- Reroll: redraw the unresolved offer using configured charges/rules.
- Bless: favor a displayed card by increasing its effective future draw weight while eligible.
- Destroy: permanently exclude a candidate card for that character, subject to current-offer safety rules.

Balance/settings for these mechanics live in `config/spelldraft/spelldraft.conf`.

## Persistence

Per-character draft state is stored through the existing Adventurer SpellDraft persistence path. It includes owned card ranks, unresolved offer state and current meta-mechanic state/charges.

Existing schema/state is migrated by the current runtime when required; do not create a parallel persistence system for a feature.

## Runtime files

Packaged runtime seeds:

```text
config/spelldraft/cards.csv
config/spelldraft/spelldraft.conf
```

The install/update pipeline places editable runtime copies beside the AzerothCore data directory and maintains packaged defaults where the existing tooling supports `.dist` files. Normal catalogue/balance changes are designed to be data-driven rather than requiring a worldserver recompile.

## Server/client flow

```text
cards.csv + spelldraft.conf + metadata
  -> tools/spelldraft_runtime.py / generation helpers
  -> Adventurer server runtime
  -> per-character persisted state
  -> Adventurer addon protocol
  -> client/AdventurerDraftMeta.lua
  -> player chooses an offered card/meta action
  -> server validates and updates state/grants
```

## Presentation subclasses

SpellDraft uses four presentation families for organization/UI:

- Mercenario
- Explorador
- Hechicero
- Iluminado

They are presentation/organization metadata, not fixed talent trees.

## Source of truth rule

For current behavior, use this file plus repository code/config. `docs/spelldraft-v1.md` and `docs/spelldraft-meta-v2.md` are historical design records and must not override current implementation.
