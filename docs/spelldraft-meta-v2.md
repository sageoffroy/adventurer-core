# SpellDraft meta mechanics v2

This document defines the first data-driven iteration after the playable v1 vertical slice.

## Goals

- Move the card catalog and balance knobs out of C++.
- Preserve the existing three-card weighted draft.
- Add persistent per-character reroll, bless, and destroy mechanics.
- Keep all three mechanics server-authoritative.
- Allow card/weight/threshold tuning without recompiling `worldserver`.

## Runtime files

The source package owns two seed files:

- `config/spelldraft/spelldraft.conf`
- `config/spelldraft/cards.csv`

The installer/runtime loader will seed them into the server data tree. Once seeded, the installed copies are operator-owned and must not be overwritten by later package upgrades.

The intended installed location is:

```text
<DataDir>/adventurer/spelldraft.conf
<DataDir>/adventurer/cards.csv
```

`DataDir` is the normal AzerothCore worldserver data directory.

## Card CSV contract

Columns:

```text
id;key;type;source_level;rarity;weight;rank_grants;requires_all;requires_any;unlocks;replaces_previous;name
```

### `rank_grants`

- `133` = one-rank card that grants one spell.
- `1784+921` = one-rank bundle that grants both spells.
- `12320/12852/12853` = three selectable passive ranks.
- Rank bundles are also legal: `100+2457/200+300`.

### Requirements

Requirement token syntax is `cardId:minRank`.

- `requires_all`: every listed requirement must be satisfied.
- `requires_any`: at least one listed requirement must be satisfied.
- Empty requirement fields mean no gate.

This is required for relationships such as Rogue finishers, where Eviscerate may be unlocked by any valid combo-point generator rather than by all of them.

## Source level cap

`source_level` is the original/design source level used to decide when the card can enter a pool. It is not necessarily the current player level requirement of the underlying spell.

For the initial prototype:

```ini
InitialActiveSourceLevelCap = 8
```

This lets the three initial active drafts draw from the audited level 1-8 catalog while still respecting dependency gates.

## Reroll

A reroll redraws the current unresolved offer and consumes one reroll charge.

Rules:

1. It does not consume the pending active/talent pick.
2. It does not grant any card.
3. When the eligible pool is large enough, the server excludes the current three cards from that redraw so the reroll produces a genuinely new offer.
4. If fewer than three alternative cards exist, already displayed cards may reappear only as necessary to fill the offer.
5. Charges persist through relog/restart.
6. Starting charges, gain interval, gain amount, and optional cap are configuration values.

Configuration:

```ini
[Reroll]
StartingCharges = 2
GainEveryLevels = 5
GainAmount = 1
MaxCharges = 0
```

`MaxCharges = 0` means no cap.

## Bless

Bless marks a card as favored for the current character. It never grants the card and never bypasses requirements.

Rules:

1. A blessed card receives a configurable multiplier to its final effective draw weight when eligible.
2. Rarity still applies normally.
3. Requirements still apply normally.
4. Destroyed cards can never be blessed into the pool.
5. A card already fully owned is not made eligible again merely because it is blessed.
6. `MaxActive` controls how many card blessings a character may maintain at once.
7. With `MaxActive = 1`, blessing a new card replaces the previous blessing.
8. Blessing persists through relog/restart.

Configuration:

```ini
[Bless]
MaxActive = 1
WeightMultiplierPercent = 300
```

For example, a card whose post-rarity effective weight is 55 becomes 165 while blessed at 300%.

## Destroy

Destroy permanently bans the selected card from that character's future pool.

Rules:

1. Destroy never grants the card.
2. The card is excluded before weighted selection.
3. Destroyed state persists through relog/restart.
4. Destroying a currently offered card immediately regenerates the unresolved offer.
5. Owned cards cannot be destroyed retroactively; destruction applies to cards that are still candidates.
6. A destroyed prerequisite may make dependent cards unreachable naturally; the server does not auto-fix the build graph.
7. Charges are independently configurable.

Configuration:

```ini
[Destroy]
StartingCharges = 1
GainEveryLevels = 10
GainAmount = 1
MaxCharges = 0
```

## Per-character state v2

The existing `character_settings` source remains `adventurer_draft_v1` so deployed test characters can be migrated in place.

The serialized state must gain:

- reroll charges
- destroy charges
- blessed card IDs
- destroyed card IDs

Schema v1 data must be accepted and migrated to v2 defaults rather than discarded.

## Protocol additions

Client to server:

```text
ADRAFT_REROLL
ADRAFT_BLESS:<cardId>
ADRAFT_DESTROY:<cardId>
```

Server to client offer payload must additionally expose current reroll/destroy charges and blessing state so the UI never guesses authority.

The server validates every action against the persisted current offer and current configuration.

## UI contract

The three-card chooser gains:

- one `Relanzar` button for the whole offer
- one `Bendecir` action on each displayed card
- one `Destruir` action on each displayed card
- visible reroll/destroy charge counts
- a visible blessed marker on a blessed card

The first implementation should favor correctness over decorative art.

## Reload

The desired operational endpoint is a GM-only reload command:

```text
.spelldraft reload
```

It reloads `spelldraft.conf` and `cards.csv` atomically. Invalid configuration must leave the previously loaded catalog active and report the validation error rather than partially replacing runtime state.

Reloading configuration does not mutate already learned spells or existing character ownership. It only changes future pool construction and meta-mechanic parameters.
