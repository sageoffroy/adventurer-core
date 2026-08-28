# Architecture

Adventurer Core is a patch layer for AzerothCore WotLK 3.3.5a. It combines the
native class-10 chassis with the SpellDraft v1 gameplay runtime used by this
project.

## Ownership boundaries

Adventurer Core owns:

- `CLASS_ADVENTURER = 10` and the playable class mask;
- EnumUtils support for class 10;
- class-10 stats, resources, equipment compatibility, languages and racials;
- all playable race/class-10 creation rows;
- class-10 DBC rows used by worldserver and the WotLK client;
- the four SpellDraft presentation subclasses (Mercenario, Explorador,
  Hechicero and Iluminado) and their custom SkillLines;
- SpellDraft active/talent card progression, persistence and meta actions;
- the `Libro de talentos`, which displays talents actually owned through
  SpellDraft;
- client patches required for the class, resource HUD and SpellDraft UI;
- optional Playerbots compatibility when `modules/mod-playerbots` is present.

Adventurer Core does **not** own or use a fixed native talent tree. In
particular, the historical Guardian/Champion/Scholar trees, custom TalentTab
rows and 290000-series cloned talent spells are obsolete. Current DBC tooling
contains only a compatibility purge for those old Adventurer-owned ranges so an
upgrade cannot leave ghost fixed talents behind.

## Talent model

The `feature/spelldraft-v1-with-dk` branch adds native Icy Touch through the same
DBC, catalog and source-patch pipeline. Its reviewed 1–80 base-damage curve is
shared with the client tooltip. See [test contract](icy-touch-testing.md).

`config/spelldraft/cards.csv` is the runtime catalog. Entries with
`type=talent` define the talent cards available through SpellDraft and their
rank spell IDs. The server persists the owned rank and `Libro de talentos`
requests that collection over the Adventurer addon protocol.

No talent is granted by a fixed tree, talent-point spending UI or Guardian
branch. The stock Talent/TalentTab/Spell DBC files are never populated with a
new Adventurer tree.

## Installation model

`apply.sh` is the normal clean-install entry point. It:

1. validates the target as an AzerothCore source tree;
2. preflights every required source transformation by exact anchors/APIs;
3. validates DBC/client inputs and database rollback capability;
4. stages generated runtime/client data before mutation;
5. patches the native class-10 source and world rows;
6. builds subclass/SpellDraft client data and purges legacy fixed-talent rows if present;
7. installs editable SpellDraft runtime data;
8. applies Playerbots integration only when that module exists;
9. records hashes and ownership for verification/rollback.

Compatibility is based on the actual source shapes/APIs required by the patch,
not on a whitelist of Git commit SHAs. A source change fails only when a real
required anchor or API is incompatible.

`rollback.sh` reverses only package-owned state whose hashes still match. It
must stop rather than destroy subsequent unrelated edits.
