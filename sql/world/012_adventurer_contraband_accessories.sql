-- Adventurer Core: additional low-level contraband accessories for Remen Marcot.
-- These are Adventurer-owned clones of native low-level item chassis.
SET @REMEN_MARCOT := 6121;
SET @RESTOCK_THREE_DAYS := 259200;

SET @CLOTH_GLOVES := 910220;
SET @SHIELD := 910221;
SET @CLOTH_BELT := 910222;
SET @LEATHER_BELT := 910223;
SET @MAIL_BELT := 910224;

DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (@CLOTH_GLOVES, @SHIELD, @CLOTH_BELT, @LEATHER_BELT, @MAIL_BELT)
  AND `ExtendedCost` = 0;

DELETE FROM `item_template`
WHERE `entry` IN (@CLOTH_GLOVES, @SHIELD, @CLOTH_BELT, @LEATHER_BELT, @MAIL_BELT);

DROP TEMPORARY TABLE IF EXISTS `_adventurer_contraband_clone`;
CREATE TEMPORARY TABLE `_adventurer_contraband_clone` LIKE `item_template`;

-- Thin Cloth Gloves chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2119;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @CLOTH_GLOVES, `name` = 'Guantes de tela de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 5500, `SellPrice` = 1100,
    `stat_type1` = 5, `stat_value1` = 1,
    `stat_type2` = 6, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Small Shield chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2133;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @SHIELD, `name` = 'Escudo de contrabando', `Quality` = 2,
    `ItemLevel` = 8, `RequiredLevel` = 3, `BuyPrice` = 9000, `SellPrice` = 1800,
    `stat_type1` = 7, `stat_value1` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Thin Cloth Belt chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 3599;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @CLOTH_BELT, `name` = 'Cinturón de tela de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 5000, `SellPrice` = 1000,
    `stat_type1` = 5, `stat_value1` = 1,
    `stat_type2` = 6, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Cracked Leather Belt chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2122;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @LEATHER_BELT, `name` = 'Cinturón de cuero de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 6000, `SellPrice` = 1200,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Light Mail Belt chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2393;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @MAIL_BELT, `name` = 'Cinturón de malla de contrabando', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 5, `BuyPrice` = 7500, `SellPrice` = 1500,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;

DROP TEMPORARY TABLE `_adventurer_contraband_clone`;

INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, @CLOTH_GLOVES,  3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @SHIELD,        2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @CLOTH_BELT,    3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @LEATHER_BELT,  2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @MAIL_BELT,     1, @RESTOCK_THREE_DAYS, 0, 0);
