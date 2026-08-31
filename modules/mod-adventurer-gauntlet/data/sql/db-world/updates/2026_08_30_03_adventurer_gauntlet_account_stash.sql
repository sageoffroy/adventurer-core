-- Restore the persistent account-backed expedition stash and remove the obsolete
-- decorative reward chest from Goldshire. The reward chest template 910001 is
-- preserved for dynamic dungeon rewards.

DELETE FROM `gameobject` WHERE `id` = 910001 AND `map` = 0;

SET @GAUNTLET_STASH_SOURCE := 106318;
SET @GAUNTLET_STASH_ENTRY := 910002;

DELETE FROM `gameobject_template` WHERE `entry` = @GAUNTLET_STASH_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_account_stash`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_account_stash` AS
    SELECT * FROM `gameobject_template` WHERE `entry` = @GAUNTLET_STASH_SOURCE;
UPDATE `tmp_adventurer_gauntlet_account_stash`
SET
    `entry` = @GAUNTLET_STASH_ENTRY,
    `name` = 'Baul de Expediciones',
    `Data0` = 0,
    `Data1` = 0,
    `AIName` = '',
    `ScriptName` = 'go_adventurer_gauntlet_account_stash';
INSERT INTO `gameobject_template` SELECT * FROM `tmp_adventurer_gauntlet_account_stash`;
DROP TEMPORARY TABLE `tmp_adventurer_gauntlet_account_stash`;
