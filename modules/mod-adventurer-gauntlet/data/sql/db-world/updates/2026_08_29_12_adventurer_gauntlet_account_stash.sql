-- Adventurer Gauntlet: shared account stash beside Khadgar.
-- Reuse a stock chest model; interaction is handled by GameObjectScript.

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
