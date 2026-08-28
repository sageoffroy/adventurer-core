# SpellDraft — current system

This document is the current functional source of truth for SpellDraft. Older versioned notes such as `spelldraft-v1.md` and `spelldraft-meta-v2.md` are historical only.

## Purpose

SpellDraft is the Adventurer classless progression system. Active abilities and passive talents are obtained as cards rather than through a fixed class spellbook/talent tree.

The server owns eligibility, weighted selection, persistence and validation. The client displays offers and meta actions; it does not decide what is legal.

## Authoritative packaged data

### `config/spelldraft/cards.csv`

Packaged card catalogue. Current columns are:

```text
id;key;type;source_level;rarity;weight;rank_grants;requires_all;requires_any;unlocks;replaces_previous;name
```

A card is the progression unit. One card may grant one spell, several spells, or successive passive ranks.

### `config/spelldraft/catalog_metadata.csv`

Additional metadata used by the current catalogue/generation path, including relationships required by presentation/talent generation where applicable.

### `config/spelldraft/spelldraft.conf`

Editable runtime configuration seed. The install/update tooling places runtime copies under the server data directory and maintains packaged defaults according to the current runtime installer behavior.

### `config/spelldraft/subclasses.json`

Presentation metadata for the four Adventurer families:

- Mercenario
- Explorador
- Hechicero
- Iluminado

These are presentation/collection groupings, not fixed native talent trees.

## Card model

### Types

- `active` — active ability card selected once; native family ranks can progress automatically according to the current rank logic.
- `talent` — passive/talent card whose successive ranks are separate draft progressions where configured.

### `rank_grants`

The field may represent a single spell, a bundle, or successive ranks. Existing tooling is the authority for exact parsing; do not create a second card format.

### Rarity and weight

Rarity and weight are separate inputs to weighted selection. Rarity expresses broad draw scarcity; weight tunes competition among eligible cards.

Use the current runtime/config values rather than copying historical balance numbers from old documentation.

### Requirements and graph

Cards can depend on other owned cards/ranks through `requires_all`, `requires_any` and related graph metadata. Dependent cards become eligible; they are not automatically granted unless the card itself explicitly bundles grants.

Eligibility is server-authoritative.

## Progression

The current project retains the established Adventurer loop:

- level 1 begins with three sequential active-card choices;
- level 5 grants another active choice;
- every 5 levels thereafter grants an active choice;
- from level 10 onward the character also gains passive/talent choices according to the current runtime implementation;
- when active and talent choices coincide, the active choice is resolved first so it can affect the talent pool.

If repository runtime code differs from this document, inspect the current implementation before editing and update this document as part of the same gameplay change.

## Active ranks

An active ability card is chosen once. Higher native ranks of the granted spell family are handled by the existing SpellDraft rank-upgrade path when the character reaches the required levels.

Do not create duplicate custom rank chains merely to make a spell scale from level 1. A spell adaptation may instead keep native rank identities and adapt scaling behavior, as Icy Touch does.

## Talent ranks

Talent cards may expose successive ranks as repeated talent draft choices. For stock passive chains represented by separate spell IDs, the current replacement behavior prevents accidental stacking where configured.

Adventurer's `Libro de talentos` reflects talents actually obtained through SpellDraft. It is not a spendable native fixed talent tree.

## Meta mechanics

### Reroll

Reroll redraws the unresolved offer and consumes a reroll charge according to current runtime configuration/state. It does not consume the pending draft choice or grant a card.

### Bless

Bless marks an offered card as favored, increasing its effective draw weight according to current configuration. The current implementation supports the project's existing single active blessing model.

### Destroy

Destroy bans an offered card from that character's future pool according to current charge/config rules. The server protects the unresolved offer from being reduced to an invalid no-choice state.

Exact balance values belong in `spelldraft.conf`, not in this document.

## Persistence

SpellDraft state is persisted per character using the existing Adventurer draft state implementation. It includes owned card/rank state, pending choices/current offer and the meta-mechanic state required by the current schema.

The runtime accepts its supported older serialized state and migrates it according to current implementation. Do not create a new persistence system for a normal card/spell feature.

## Runtime files

The packaged `cards.csv` and `spelldraft.conf` are installed into the server data directory by the existing runtime tooling. Editable runtime copies and `.dist` packaged defaults are managed by `tools/spelldraft_runtime.py` and the apply/update pipeline.

Normal catalogue/balance edits are intended to use that runtime-data path when supported; C++ recompilation is only needed when the actual server/native behavior changes.

## Client/server flow

High level:

```text
server computes pending draft
  -> filters eligible catalogue
  -> weighted selection
  -> sends offer through Adventurer addon protocol
  -> client/AdventurerDraftMeta.lua displays three cards
  -> player chooses/meta-acts
  -> server validates action against persisted offer/state
  -> server teaches/progresses card grants
  -> updated state persists
```

The client may display native spell information/tooltips, but legality and ownership remain server-side.

## Main implementation files

- `config/spelldraft/cards.csv` — catalogue.
- `config/spelldraft/catalog_metadata.csv` — metadata.
- `config/spelldraft/spelldraft.conf` — balance/meta config.
- `tools/spelldraft_runtime.py` — runtime data handling.
- `tools/spell_rank_tabs.py` — rank/tab related generation.
- `tools/subclasses.py` — presentation subclasses.
- `tools/talents.py` — talent helper/generation logic.
- `payload/core/src/server/scripts/Custom/adventurer_core.cpp` — server Adventurer/SpellDraft runtime integration.
- `payload/core/src/server/scripts/Custom/adventurer_collections.cpp` — collection/talent-book server support.
- `client/AdventurerDraftMeta.lua` — client offer/meta UI.
- `client/AdventurerCollections.lua` — client collection/talent-book UI.

## Adding or adapting a spell

Do not infer the implementation from this document alone. Follow `SPELL_WORKFLOW.md`:

```text
catalogue
  -> closest existing adaptation
  -> data/DBC first
  -> feature adapter if present
  -> native core patch only if required
  -> apply/update
  -> compile if required
  -> in-game test
```

For the current DK pattern see `docs/spells/ICY_TOUCH.md`.

## Validation policy

The product goal is correct gameplay, not a green test suite.

Default validation:

1. Apply/update the package.
2. Compile/restart when the changed code requires it.
3. Test the draft/spell/talent behavior in game.
4. Correct the actual observed failure.

Do not add new tests, manifests or validation frameworks by default.
