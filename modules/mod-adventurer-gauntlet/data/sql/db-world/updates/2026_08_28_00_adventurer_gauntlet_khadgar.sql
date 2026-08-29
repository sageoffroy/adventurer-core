-- Adventurer Gauntlet: dedicated Khadgar template for the expedition entry point.
-- Clone stock Khadgar (18166) so the module never repurposes the original NPC.

SET @GAUNTLET_KHADGAR_SOURCE := 18166;
SET @GAUNTLET_KHADGAR_ENTRY := 910000;

DELETE FROM `creature_template` WHERE `entry` = @GAUNTLET_KHADGAR_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_khadgar`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_khadgar` AS
    SELECT * FROM `creature_template` WHERE `entry` = @GAUNTLET_KHADGAR_SOURCE;
UPDATE `tmp_adventurer_gauntlet_khadgar`
SET
    `entry` = @GAUNTLET_KHADGAR_ENTRY,
    `name` = 'Khadgar',
    `subname` = 'Maestro de Expediciones',
    `npcflag` = (`npcflag` | 1),
    `ScriptName` = 'npc_adventurer_gauntlet_khadgar';
INSERT INTO `creature_template` SELECT * FROM `tmp_adventurer_gauntlet_khadgar`;
DROP TEMPORARY TABLE `tmp_adventurer_gauntlet_khadgar`;

DELETE FROM `creature_template_model` WHERE `CreatureID` = @GAUNTLET_KHADGAR_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_khadgar_model`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_khadgar_model` AS
    SELECT * FROM `creature_template_model` WHERE `CreatureID` = @GAUNTLET_KHADGAR_SOURCE;
UPDATE `tmp_adventurer_gauntlet_khadgar_model`
SET `CreatureID` = @GAUNTLET_KHADGAR_ENTRY;
INSERT INTO `creature_template_model` SELECT * FROM `tmp_adventurer_gauntlet_khadgar_model`;
DROP TEMPORARY TABLE `tmp_adventurer_gauntlet_khadgar_model`;
