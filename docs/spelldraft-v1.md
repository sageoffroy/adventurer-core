# SpellDraft v1

## Goal

Build a small classless draft mode for the native Adventurer class. This mode does **not** use the four normal talent trees.

The implementation may reuse ideas and selected pieces from `bdodroid/mod-spelldraft`, but the target is deliberately much smaller: draft active abilities and passive talents while leveling, with connected prerequisites and rarity.

## Progression

- Level 1: obtain 3 active abilities through three draft picks.
- Level 5: obtain 1 active ability.
- Every 5 levels thereafter: obtain 1 active ability.
- From level 10 onward: obtain 1 passive talent every level.
- At levels 10, 15, 20, 25, etc. the active draft runs first, then the passive draft, so the newly selected active can immediately unlock talents for that level's passive pool.

## Rank rules

- Active ability ranks are automatic. An active card is selected only once; higher spell ranks are learned automatically when the character reaches the required level.
- Passive talent ranks are draft choices. Selecting rank 1 unlocks rank 2 for future passive drafts, and so on.
- A 1/1 passive is complete after one selection.

## Connected card graph

Cards are not all globally eligible.

A card can require another active ability, a passive talent, or a minimum passive rank. Selecting a card may therefore make new active and passive cards eligible.

Example:

- Battle Stance selected
  - Charge becomes eligible in the active pool.
  - Stance Mastery becomes eligible in the passive pool.

Dependent cards are **not** automatically granted. They become candidates for later drafts.

Generic root passives may be eligible without a specific active prerequisite.

## Rarity

Rarity controls draw probability. Deeper and more build-defining talents should generally be harder to obtain than generic early talents.

Examples:

- Vitality: common.
- Titan's Grip: epic.

The client should show the rarity of each offered card.

## What to reuse from mod-spelldraft

The upstream module already contains several useful mechanisms:

1. Three-choice server/client draft protocol (`SpellChoice`, `SpellChoiceRarities`, `SpellChoiceIsTalent`).
2. A three-card selection UI (`SpellChoice.xml` + the useful subset of `SpellChoice.lua`).
3. Automatic active spell ranking using `spell_ranks` + spell level data.
4. Talent-chain loading from `talent_dbc`, including progressive rank discovery.
5. Filtering first spell ranks out of active pools and excluding already-known spell families.
6. Pending-choice persistence across relogs as a design pattern.

These pieces should be extracted or rewritten cleanly rather than importing the whole upstream module.

## What is explicitly out of scope

Do not bring over:

- Prestige resets, ranks, titles, tokens, or prestige NPC flow.
- Prestige shop.
- Reroll and ban economy for v1.
- Lost Grimoires / Tome consumable progression.
- Custom Grimoire / SpellBook UI.
- Manual talent-point shop.
- Mystic Enchants / random enchantment services.
- Prestige nameplates.
- Death Knight catch-up/progression rules.
- Starter kits that automatically grant dependent abilities. Dependencies enter the pool instead.

## Server state

Do not reuse `prestige_stats` as the central state table. The draft should have its own small character state.

Target model:

- character draft state / pending draft
- owned active card families
- passive card progress (current rank)
- pending three choices and draft kind (`active` or `passive`)

The owned-card state, not a prestige counter, is the source used to evaluate graph prerequisites.

## First vertical slice

Before importing hundreds of cards, prove the graph with a tiny pool:

- Three root active candidates.
- Battle Stance as one possible root active.
- Charge locked behind Battle Stance.
- One passive locked behind Battle Stance.
- One generic passive with multiple ranks.

Acceptance test:

1. A fresh Adventurer receives three sequential active drafts at level 1.
2. Charge cannot appear before Battle Stance is owned.
3. Selecting Battle Stance makes Charge eligible for a future active draft and its linked passive eligible for passive drafts.
4. At level 5 exactly one active draft is generated.
5. At level 10 the active draft resolves first, followed by one passive draft.
6. Active spell ranks upgrade automatically with level.
7. Passive ranks require repeated draft selections.
8. Pending drafts survive relogging.

## Upstream licensing note

`bdodroid/mod-spelldraft` is GPLv3. If source or assets are copied rather than independently reimplemented, preserve the applicable GPLv3 notices and obligations.
