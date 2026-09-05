# SpellDraft — current model

This document describes the current SpellDraft behavior in this branch. It supersedes older version-specific design notes.

## Core idea

The card is the unit of progression. A card can grant one spell, several related spells, or one rank in a passive/talent chain.

SpellDraft is the progression system for the native Adventurer class. Talents are obtained as SpellDraft cards rather than through a fixed native talent tree.

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

SpellDraft uses three persistent meta currencies:

- Reroll: redraw the unresolved offer. Characters start with **3**.
- Bless: increase the future draw weight of one eligible displayed card. Characters start with **1**.
- Destroy: permanently exclude one eligible card from that character's pool. Characters start with **1**.

None of these currencies are regenerated automatically by leveling. Additional charges are intended to come from special Gauntlet loot. There is currently no configured accumulation cap; drop rates are the balancing control. Balance/settings live in `config/spelldraft/spelldraft.conf`.

Gauntlet drops three tradeable, single-use SpellDraft currency scrolls through an independent **1%** auxiliary roll:

- **Scroll de Suerte** (`910237`, `INV_Scroll_11`): +1 Reroll.
- **Scroll de Bendición** (`910238`, `INV_Scroll_15`): +1 Bless.
- **Scroll del Olvido** (`910239`, `INV_Scroll_16`): +1 Destroy.

On a successful scroll roll, the distribution is **50% / 25% / 25%** respectively. The scroll is consumed on use, the new charge is persisted immediately, and the SpellDraft counters are refreshed. This roll is independent from equipment, ammo, potion, stock-scroll and bag rolls.

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
