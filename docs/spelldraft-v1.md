# SpellDraft v1

## Goal

Build a small classless draft mode for the native Adventurer class. This mode does **not** use the four normal talent trees.

The first implementation deliberately focuses on the playable loop: choose active ability cards, choose passive talent cards, preserve the choices, and grow the eligible pools through prerequisites. Prestige, shops, rerolls, bans, custom grimoires, mystic enchants, and Death Knight catch-up are not part of v1.

## Core rule: the card is the unit

The draft does not treat one spell ID as one mandatory choice.

A card may teach one or several spells. This is important for abilities that are weak, incomplete, or useless by themselves: they can be bundled into one meaningful pick instead of consuming several draft choices.

Example in the first vertical slice:

- `Stealth` card teaches Stealth + Pick Pocket in one active pick.

A card contains:

- `type`: active or talent
- `rarity`
- `weight`
- one or more rank grant lists
- prerequisites
- graph unlock metadata
- whether a new passive rank replaces the previous rank spell

## Rarity and weight are different

Rarity answers: **how difficult is this quality of card to draw in general?**

Weight answers: **once this card is eligible, how strongly should it compete with other eligible cards?**

The first server implementation combines the two for weighted random selection, but stores them separately so either axis can be tuned without changing the other.

Current rarity multipliers:

- Common: 100
- Uncommon: 55
- Rare: 25
- Epic: 10
- Legendary: 3

A normal card uses base weight `100`.

Important example:

- Battle Stance is a normal Common root card.
- Charge is completely absent from the eligible pool until Battle Stance is owned.
- Once eligible, Charge remains Common but has base weight `500` (five times the standard base weight), making it much more likely to appear without granting it for free.

This is the intended replacement for upstream starter kits that immediately teach dependent abilities.

## Progression

- Level 1: obtain 3 active abilities through three sequential draft picks.
- Level 5: obtain 1 active ability.
- Every 5 levels thereafter: obtain 1 active ability.
- From level 10 onward: obtain 1 passive talent every level.
- At levels 10, 15, 20, 25, etc. the active draft runs first, then the passive draft, so the newly selected active can immediately unlock talents for that level's passive pool.

The server tracks pending active and talent picks independently. If the player gains several levels at once or relogs with unresolved choices, the backlog is preserved.

## Rank rules

- Active ability cards are selected once.
- Higher ranks of their granted spell families are learned automatically when the character reaches the required spell level.
- Passive talent ranks are separate draft choices.
- Selecting rank 1 of a passive makes rank 2 the next selectable rank of that same card, and so on.
- A 1/1 passive is complete after one selection.
- For stock talent chains represented by separate spell IDs, the new passive rank replaces the previous rank spell so the auras do not stack accidentally.

## Connected card graph

Cards are not all globally eligible.

A card can require another active card, a passive card, or a minimum passive rank. Selecting a card may therefore make new active and passive cards eligible.

Example:

- Battle Stance selected
  - Charge becomes eligible in the active pool with boosted weight.
  - Tactical Mastery becomes eligible in the talent pool.

Dependent cards are **not** automatically granted.

Eligibility is enforced on the server. The client receives only the three cards selected from the already-filtered eligible pool, and the server validates every pick against the current offer again before teaching anything.

## First playable catalog

The small v1 pool exists only to prove the engine before importing the real catalog.

### Active roots

- Battle Stance
- Fireball
- Frostbolt
- Shadow Bolt
- Smite
- Lightning Bolt
- Wrath
- Heroic Strike
- Rejuvenation
- Stealth + Pick Pocket bundle
- Arcane Intellect
- Healing Wave
- Sinister Strike

### Gated active

- Charge: requires Battle Stance; Common; base weight 500

### Passive/talent cards

- Cruelty: 5 ranks
- Deflection: 5 ranks
- Anticipation: 5 ranks
- Improved Fireball: 5 ranks; requires Fireball
- Improved Frostbolt: 5 ranks; requires Frostbolt
- Tactical Mastery: 3 ranks; requires Battle Stance
- Improved Heroic Strike: 3 ranks; requires Heroic Strike

These are test cards, not a declaration of the final balance or final catalog.

## Persistence

The first implementation stores a compact serialized state in AzerothCore's existing `character_settings` table under source:

`adventurer_draft_v1`

Persisted state includes:

- last processed level
- pending active picks
- pending talent picks
- current offer kind
- current three offered card IDs
- owned card ranks

This deliberately avoids importing upstream `prestige_stats` or any prestige schema.

## Client/server protocol

The existing Adventurer FrameXML payload contains a minimal three-card chooser; it is not the upstream SpellDraft addon.

Client to server uses hidden self-whisper commands:

- `ADRAFT_READY`
- `ADRAFT_PICK:<cardId>`

Server to client uses addon prefix:

- `AdventurerDraft`

Payload kinds:

- `O|...` current offer
- `C` close/no pending draft
- `E|...` rejected/invalid state

Each offered card currently sends enough metadata for the test UI to show:

- card ID
- display spell ID
- rarity
- base weight
- number of spells granted by that rank
- next rank
- maximum rank

The client uses native `GetSpellInfo` and spell tooltips for the displayed spell, so the first test does not require a separate generated spell database.

## What was reused conceptually from mod-spelldraft

The upstream module proved several useful mechanisms:

1. Three-choice server/client draft flow.
2. Automatic active spell ranking.
3. Progressive talent ranks.
4. Server-side filtering and prerequisites.
5. Pending-choice persistence.
6. Bundling dependent abilities as starter kits.

Our v1 rewrites the small subset needed by the native Adventurer and changes starter-kit behavior into generic card bundles plus graph unlocks.

## What is explicitly out of scope

Do not bring over for v1:

- Prestige resets, ranks, titles, tokens, or prestige NPC flow.
- Prestige shop.
- Reroll and ban economy.
- Lost Grimoires / Tome consumable progression.
- Custom Grimoire / SpellBook UI.
- Manual talent-point shop.
- Mystic Enchants / random enchantment services.
- Prestige nameplates.
- Death Knight catch-up/progression rules.
- Automatic granting of graph-dependent cards such as Charge after Battle Stance.

## Initial acceptance test

Use a **new Adventurer** for the first end-to-end test.

1. On entering the world at level 1, a three-card active offer appears.
2. Selecting one card teaches its granted spell(s) and immediately opens the next unresolved active choice.
3. Exactly three level-1 active picks are consumed.
4. Charge never appears before Battle Stance is owned.
5. If Battle Stance is selected early enough, Charge becomes eligible for a later active draft and has elevated draw weight; it is not guaranteed and is not learned for free.
6. The Stealth bundle teaches both Stealth and Pick Pocket for one choice.
7. At level 5 exactly one new active pick is queued.
8. At level 10 the active pick is resolved before the talent pick.
9. Eligible passives show their next rank; repeated ranks require repeated talent drafts.
10. Active spell families automatically acquire level-appropriate ranks.
11. Logging out with an unresolved offer and logging back in restores that same offer.
12. Standard Adventurer talent points remain disabled while this draft loop is active.

## Upstream licensing note

`bdodroid/mod-spelldraft` is GPLv3. If source or assets are copied rather than independently reimplemented, preserve the applicable GPLv3 notices and obligations.
