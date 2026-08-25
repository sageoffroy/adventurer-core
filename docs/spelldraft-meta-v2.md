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

`apply.sh` and `update.sh` install editable runtime copies beside AzerothCore's normal data directory and refresh packaged defaults as `.dist` files. Existing editable copies are never overwritten by a later package update.

Installed location:

```text
<DataDir>/spelldraft/spelldraft.conf
<DataDir>/spelldraft/cards.csv
<DataDir>/spelldraft/spelldraft.conf.dist
<DataDir>/spelldraft/cards.csv.dist
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

This supports relationships such as Rogue finishers, where Eviscerate may be unlocked by any valid combo-point generator rather than by all of them.

## Source level cap

`source_level` is the original/design source level used to decide when the card can enter a pool. It is not necessarily the current player level requirement of the underlying spell.

For the initial prototype:

```ini
InitialActiveSourceLevelCap = 8
```

This lets the three initial active drafts draw from the audited level 1-8 catalog while still respecting dependency gates. After the player passes the configured cap, the current player level becomes the active-card source cap.

## Reroll

A reroll redraws the current unresolved offer and consumes one reroll charge.

Rules:

1. It does not consume the pending active/talent pick.
2. It does not grant any card.
3. When the eligible pool is large enough, the server excludes the current three cards from that redraw so the reroll produces a genuinely new offer.
4. If fewer than three alternatives exist, displayed cards may reappear only as necessary to fill the offer.
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

`MaxCharges = 0` means no cap. These numbers are prototype balance values, not final game-design values.

## Bless

Bless marks a currently offered card as favored for the current character. It does not consume the draft pick: the player may bless one displayed card and then choose another card from the offer, making the blessed card more likely to return later.

Rules:

1. A blessed card receives a configurable multiplier to its final effective draw weight when eligible.
2. Rarity still applies normally.
3. Requirements still apply normally.
4. Destroyed cards can never be blessed into the pool.
5. A card already fully owned is not made eligible again merely because it is blessed.
6. The v2 implementation supports one active blessing; blessing another card replaces it.
7. Blessing persists through relog/restart.
8. If the blessed card reaches its final rank after being selected, the blessing is cleared.
9. Blessing currently has no consumable charge pool; while enabled it may be retargeted without spending a finite resource.

Configuration:

```ini
[Bless]
MaxActive = 1
WeightMultiplierPercent = 300
```

For v2, `MaxActive = 0` disables blessing and any non-zero value enables the single blessing slot. For example, a card whose post-rarity effective weight is 55 becomes 165 while blessed at 300%. The client reports this unlimited availability as `Bendiciones: ∞` instead of inventing a charge count that the server does not own.

## Destroy

Destroy permanently bans a currently offered card from that character's future pool.

Rules:

1. Destroy never grants the card and does not consume the pending draft pick.
2. The card is excluded from all future weighted selections for that character.
3. Destroyed state persists through relog/restart.
4. Destroying a card does **not** redraw or replace its current slot. The destroyed card stays visible in the unresolved offer, dimmed and unusable, so destroying never grants a free extra choice.
5. At least one selectable card must remain in the current offer; the server rejects an attempt to destroy the final usable card.
6. Owned cards cannot be destroyed retroactively; destruction applies to cards that are still candidates.
7. A destroyed prerequisite may make dependent cards unreachable naturally; the server does not auto-fix the build graph.
8. Charges are independently configurable.

Configuration:

```ini
[Destroy]
StartingCharges = 1
GainEveryLevels = 10
GainAmount = 1
MaxCharges = 0
```

These numbers are prototype balance values.

## Per-character state v2

The existing `character_settings` source remains `adventurer_draft_v1` so deployed test characters can migrate in place.

Serialized v2 state includes:

- reroll charges
- destroy charges
- blessed card ID
- destroyed card IDs
- existing owned ranks and unresolved offer

A destroyed card may intentionally remain inside the persisted unresolved offer as a blocked placeholder. It is still globally excluded from future pool construction.

Schema v1 data is accepted and migrated to v2 defaults rather than discarded.

## Protocol additions

Client to server:

```text
ADRAFT_REROLL
ADRAFT_BLESS:<cardId>
ADRAFT_DESTROY:<cardId>
```

Server to client meta payload:

```text
M|rerollCharges|destroyCharges|blessedCardId|blessMultiplierPercent
```

Each card record in the normal `O|...` offer payload carries an additional trailing destroyed flag so the client can render a persisted blocked slot without guessing server state.

The server validates every action against the current offer, eligibility graph and server-owned state.

## UI contract

The existing three-card chooser gains a footer with:

- `Relanzar`
- `Bendecir`
- `Destruir`
- visible reroll/destroy charge counts
- `Bendiciones: ∞` while the current unlimited blessing model is enabled
- a star marker when one of the displayed cards is the blessed card
- dimmed, disabled presentation for cards destroyed inside the current unresolved offer

`Bendecir` and `Destruir` enter a temporary selection mode; the next displayed card clicked is the target. Normal card selection is unchanged outside those modes. The normal `Elegir` action sits immediately under the rarity/rank metadata instead of being anchored to the bottom of the card and leaving a large empty gap.

## Runtime reload behavior

The server reads `<DataDir>/spelldraft/spelldraft.conf` and `cards.csv` at runtime. It refreshes runtime data before resolving/sending draft offers and on login/level transitions. Therefore normal catalog, weight, source-level and balance edits do not require recompiling `worldserver`.

If a later `cards.csv` read is invalid, the last valid in-memory catalog remains active instead of replacing it with partial data. A compiled prototype catalog exists only as a first-start safety fallback.

A dedicated GM convenience command such as:

```text
.spelldraft reload
```

can still be added later, but it is not required for the v2 runtime-data workflow.
