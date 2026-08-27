# Aventureros de Azeroth — Server Foundation v1

## Goal

Build a new AzerothCore server from a clean, pinned upstream commit and layer Aventureros-specific gameplay on top without turning the core into an untraceable patch pile.

## Build policy

- Keep the upstream AzerothCore source clean whenever a module/hook can express the change.
- Pin every external input by commit SHA.
- Absorb small third-party gameplay scripts/data into `adventurer-core` after audit instead of depending on abandoned or WIP repositories.
- Keep client/DBC modifications in the existing reproducible Adventurer client pipeline.
- Add one gameplay layer at a time and smoke-test before the next layer.

## Foundation pass 1

1. AzerothCore clean upstream.
2. `mod-TimeIsTime` for accelerated/controlled realm time.
3. `mod-ale` as the supported Lua gameplay engine.
4. `mod-aoe-loot` as low-risk quality of life.

No PlayerBots. No Dungeon Master in the foundation build.

## TimeIsTime / darker nights

`mod-TimeIsTime` only changes the client realm clock packet and time speed. It does not itself change zone lighting intensity.

Decision:

- retain TimeIsTime as the clock/day-night controller;
- do not fork it merely to fake darkness;
- implement darker nights as an Adventurer client-lighting layer after the clean server smoke test;
- preserve daylight readability while making the night interval materially darker than stock 3.3.5a.

The final darkness curve must be tested in several lighting environments (open field, forest, capital, cave entrance) before being locked.

## AutoBalance

Candidate for pass 2. AutoBalance is useful because Aventureros is expected to run dungeons with small variable groups. It scales instance creature/boss stats according to player count.

It does not solve open-world creature scaling and should not be treated as such.

Use the `stable` ref first and validate it against the pinned 2026 AzerothCore base before enabling it in the permanent manifest.

## Adapted gameplay sources

### Rare Drops

Approved. Import audited loot data only. Do not install the upstream repository as a module.

Requirements before import:

- collision audit against existing `creature_loot_template` rows;
- Adventurer-owned comments/identifiers;
- rollback support;
- retain a curated list of rares suitable for later mini-boss upgrades.

### Bonus Loot Chest

Approved for reimplementation on ALE.

Initial Aventurer behavior:

- boss kills only; no quest-completion chest;
- dedicated Adventurer gameobject ID;
- curated item pool rather than arbitrary `item_template` selection;
- conservative rarity distribution;
- configuration separated from script logic.

### Cursed Relic

Approved as a special world-event concept, not as a direct copy.

Requirements:

- one global relic, not one per faction;
- persistent DB-backed state across worldserver restarts;
- ALE implementation;
- dedicated Adventurer IDs;
- risk/reward design rather than pure punishment;
- cure mechanic and transfer rules audited against logout/death/delete edge cases.

### Item Affixes

Design/reference source only for now. Do not install the full module.

Possible future scope:

- universal stat affixes;
- no original-class skill affixes;
- no original talent-tree assumptions;
- no separate meta-progression system;
- study Imprints independently as a possible legendary-item mechanic.

## Deferred modules

- PlayerBots: excluded from the current direction.
- Dungeon Master: potentially useful source material, but requires too much redesign for the foundation build.
- Individual Progression: overlaps the custom Adventurer progression model.
- Challenge Modes: overlaps future custom dungeon systems.
- AH bots: not part of the initial economy until actual player/economy needs are known.
- Transmog: harmless but non-essential; defer until gameplay foundation is stable.

## Integration order

1. Clean foundation compile.
2. Empty-server boot and DB smoke test.
3. TimeIsTime functional test.
4. AoE Loot functional test.
5. ALE hello/event smoke test.
6. AutoBalance compile + one dungeon test with 1/2/3 players.
7. Rare Drops import.
8. Bonus Loot Chest ALE implementation.
9. Darker-night client layer.
10. Cursed Relic implementation.
11. Reapply/port Adventurer class/resource/talent systems onto the verified foundation.
12. Evaluate Dungeon Master pieces only after the base dungeon loop is fun without it.
