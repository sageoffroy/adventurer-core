-- Restore the Expedition Stash appearance to Doan's Strongbox (103821).
-- This is a new migration because the previous 910002 template migration may
-- already have been applied on existing installations.

SET @GAUNTLET_STASH_SOURCE := 103821;
SET @GAUNTLET_STASH_ENTRY := 910002;

DELETE FROM `gameobject_template` WHERE `entry` = @GAUNTLET_STASH_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_doan_stash`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_doan_stash` AS
    SELECT * FROM `gameobject_template` WHERE `entry` = @GAUNTLET_STASH_SOURCE;
UPDATE `tmp_adventurer_gauntlet_doan_stash`
SET
    `entry` = @GAUNTLET_STASH_ENTRY,
    `name` = 'Baul de Expediciones',
    `AIName` = '',
    `ScriptName` = 'go_adventurer_gauntlet_account_stash';
INSERT INTO `gameobject_template` SELECT * FROM `tmp_adventurer_gauntlet_doan_stash`;
DROP TEMPORARY TABLE `tmp_adventurer_gauntlet_doan_stash`;
