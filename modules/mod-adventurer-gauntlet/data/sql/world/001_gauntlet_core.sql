-- Adventurer Gauntlet: core world definitions.
-- This file defines Gauntlet-owned templates and server-side spell metadata.

SET @GAUNTLET_KHADGAR_SOURCE := 18166;
SET @GAUNTLET_KHADGAR_ENTRY := 910000;
SET @GAUNTLET_REWARD_CHEST_SOURCE := 106318;
SET @GAUNTLET_REWARD_CHEST_ENTRY := 910001;
SET @GAUNTLET_BANK_SOURCE := 103821;
SET @GAUNTLET_BANK_ENTRY := 910002;
SET @LONE_WOLF := 910501;

DELETE FROM `creature_template` WHERE `entry` = @GAUNTLET_KHADGAR_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_khadgar`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_khadgar` AS
    SELECT * FROM `creature_template` WHERE `entry` = @GAUNTLET_KHADGAR_SOURCE;
UPDATE `tmp_adventurer_gauntlet_khadgar`
SET `entry` = @GAUNTLET_KHADGAR_ENTRY,
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

DELETE FROM `gameobject_template` WHERE `entry` = @GAUNTLET_REWARD_CHEST_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_reward_chest`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_reward_chest` AS
    SELECT * FROM `gameobject_template` WHERE `entry` = @GAUNTLET_REWARD_CHEST_SOURCE;
UPDATE `tmp_adventurer_gauntlet_reward_chest`
SET `entry` = @GAUNTLET_REWARD_CHEST_ENTRY,
    `name` = 'Cofre de Expedicion',
    `Data0` = 0,
    `Data1` = 0,
    `AIName` = '',
    `ScriptName` = '';
INSERT INTO `gameobject_template` SELECT * FROM `tmp_adventurer_gauntlet_reward_chest`;
DROP TEMPORARY TABLE `tmp_adventurer_gauntlet_reward_chest`;

DELETE FROM `gameobject_template` WHERE `entry` = @GAUNTLET_BANK_ENTRY;
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_gauntlet_account_bank`;
CREATE TEMPORARY TABLE `tmp_adventurer_gauntlet_account_bank` AS
    SELECT * FROM `gameobject_template` WHERE `entry` = @GAUNTLET_BANK_SOURCE;
UPDATE `tmp_adventurer_gauntlet_account_bank`
SET `entry` = @GAUNTLET_BANK_ENTRY,
    `name` = 'Banco de Expediciones',
    `Data0` = 0,
    `Data1` = 0,
    `AIName` = '',
    `ScriptName` = 'go_adventurer_gauntlet_account_bank';
INSERT INTO `gameobject_template` SELECT * FROM `tmp_adventurer_gauntlet_account_bank`;
DROP TEMPORARY TABLE `tmp_adventurer_gauntlet_account_bank`;

DELETE FROM `spell_dbc` WHERE `ID` = @LONE_WOLF;
INSERT INTO `spell_dbc`
(`ID`, `DurationIndex`,
 `Effect_1`, `Effect_2`, `Effect_3`,
 `EffectBasePoints_1`, `EffectBasePoints_2`, `EffectBasePoints_3`,
 `ImplicitTargetA_1`, `ImplicitTargetA_2`, `ImplicitTargetA_3`,
 `EffectAura_1`, `EffectAura_2`, `EffectAura_3`,
 `SpellIconID`,
 `Name_Lang_enUS`, `Name_Lang_esES`, `Name_Lang_esMX`,
 `Description_Lang_enUS`, `Description_Lang_esES`, `Description_Lang_esMX`,
 `AuraDescription_Lang_enUS`, `AuraDescription_Lang_esES`, `AuraDescription_Lang_esMX`,
 `SchoolMask`, `EquippedItemClass`, `EquippedItemSubclass`, `EquippedItemInvTypes`)
VALUES
(@LONE_WOLF, 21,
 6, 6, 6,
 19, 9, 9,
 1, 1, 1,
 31, 192, 216,
 910000,
 'Lone Wolf', 'Lobo solitario', 'Lobo solitario',
 '+20% damage dealt, +10% haste and +20% movement speed while facing Khadgar''s Challenge alone.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento mientras afrontas solo el Desafío de Khadgar.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento mientras afrontas solo el Desafío de Khadgar.',
 '+20% damage dealt, +10% haste and +20% movement speed.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento.',
 '+20% de daño infligido, +10% de celeridad y +20% de velocidad de movimiento.',
 1, -1, 0, 0);
