# Rollback

Adventurer Core treats rollback as part of installation, not as a later repair
procedure.

## What is captured before apply

Before `apply.sh` mutates source, DBCs, client files, or places the pending world
migration, it validates both databases from the installed `worldserver.conf` and
creates a selective world-DB rollback snapshot.

The snapshot covers every row range modified by `001_adventurer.sql`:

- `playercreateinfo` for class 10
- `player_class_stats` for class 10
- `playercreateinfo_skills` for class mask 512
- `playercreateinfo_spell_custom` for class mask 512
- `playercreateinfo_action` for class 10
- class-slot-10 rows in the combat/regen DBC mirror tables
- the AzerothCore `updates` row for the Adventurer pending migration

The snapshot is stored under the installer-owned `.adventurer-core/database/`
state only after source application has created a transaction state. Passwords
are never copied into metadata; later commands re-read credentials from the
same `worldserver.conf` path.

## Rollback order

`rollback.sh` performs the following checks and operations:

1. Verify the DB snapshot hash and database identities.
2. Refuse if class-10 character rows still exist in the characters DB.
3. Verify every Adventurer-owned source/runtime/client file has not been
   modified after apply.
4. Restore the exact pre-install world-DB row ranges and verify their row counts.
5. Restore server DBC backups and the previous client Z patch.
6. Restore/erase owned core files and remove the transaction state.

The database restore SQL is idempotent: it deletes only the captured Adventurer
row ranges and then reinserts their pre-install contents. If a later file-stage
rollback is interrupted, the database restore can safely be run again.

## Character safeguard

Character creation happens after installation and is not an installer-owned DB
mutation. A class-10 character would become invalid if class-10 core support
were removed underneath it, so rollback does not attempt a broad SQL purge of
character-related tables.

Instead, rollback stops before any mutation whenever `characters.class = 10`
still exists, including recoverable/soft-deleted rows. Purge those test
characters through an appropriate AzerothCore character-management path first,
then rerun `rollback.sh`.

This is intentionally conservative: no rollback command is allowed to delete
unrelated character progression while trying to remove Adventurer Core.
