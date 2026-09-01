SET @GAUNTLET_BANK_SOURCE := 103821;
SET @GAUNTLET_BANK_ENTRY := 910002;

DELETE FROM `gameobject_template` WHERE `entry` = @GAUNTLET_BANK_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_account_bank`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_account_bank` AS
    SELECT * FROM `gameobject_template` WHERE `entry` = @GAUNTLET_BANK_SOURCE;
UPDATE `tmp_adventurer_gauntlet_account_bank`
SET
    `entry` = @GAUNTLET_BANK_ENTRY,
    `name` = 'Banco de Expediciones',
    `Data0` = 0,
    `Data1` = 0,
    `AIName` = '',
    `ScriptName` = 'go_adventurer_gauntlet_account_bank';
INSERT INTO `gameobject_template` SELECT * FROM `tmp_adventurer_gauntlet_account_bank`;
DROP TEMPORARY TABLE `tmp_adventurer_gauntlet_account_bank`;
