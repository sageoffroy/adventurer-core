# Architecture

Adventurer Core is a patch layer, not an AzerothCore module.

Its only responsibility is making the unused WotLK class slot 10 a native,
playable, classless **Adventurer**. It must remain usable without ALE,
SpellDraft, progression, Dungeon Master, or any future Aventureros gameplay
module.

## Ownership boundaries

Adventurer Core owns:

- `CLASS_ADVENTURER = 10` and the playable class mask;
- EnumUtils support for class 10;
- safe class-10 avoidance/stat constants;
- neutral level/stat rows in the world DB;
- all playable race/class-10 creation rows;
- universal weapon/armor baseline, dodge/parry/block, languages and racials;
- native Mana plus auxiliary Rage and Energy resource pools;
- the narrow class-10 combo-point bridge needed by the 3.3.5a client;
- classless item-use compatibility where stock `AllowableClass` masks would
  otherwise reject class 10;
- class-10 DBC rows used by both worldserver and the WotLK client;
- enUS `Adventurer` and esMX `Aventurero` player-visible class naming;
- the client creation patch needed to expose exactly one class per playable race.

The Adventurer does **not** impersonate a Death Knight. Adventurer Core must not
attach DK ability-class context, rune state, RuneFrame handling, or Runic Power
to class 10. Individual DK-origin abilities may later be adapted by gameplay
content to use Adventurer resources without changing this chassis rule.

Adventurer Core does **not** own:

- draft rules or random abilities;
- custom spells or spell scaling;
- talents/metaprogression;
- dungeon rewards;
- ALE or Lua integration;
- Playerbots behavior beyond remaining compatible with a Playerbots core.

## Installation model

`apply.sh` will be the only normal entry point. The final installer must:

1. identify and validate the target core;
2. refuse unsupported core revisions by default;
3. preflight every source transformation before changing files;
4. back up only files it owns;
5. patch the core and stage the world DB migration;
6. patch the server DBC payload from clean WotLK 3.3.5a data;
7. build and install the client patch, prioritizing esMX;
8. record hashes and ownership in a state manifest;
9. run `verify.sh` automatically;
10. never use `git reset --hard`, `git clean`, or overwrite unrelated user work.

`rollback.sh` may reverse only files whose current hashes still match the files
written by Adventurer Core. It must stop rather than destroy subsequent edits.

## Compatibility gate

During bootstrap, `compatibility.json` intentionally contains no supported
commit. This prevents the package from being presented as apply-ready before the
new clean Playerbots installation supplies its exact base commit. Once that SHA
is known, the complete transformation will be tested against that tree and the
compatibility gate will be frozen.
