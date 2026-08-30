-- Adventurer Core: two low-level rare contraband items for Remen Marcot.
-- These clone native low-level shapes/stats into Adventurer-owned entries so
-- no stock item is globally modified.
SET @REMEN_MARCOT := 6121;
SET @RARE_DAGGER := 910200;
SET @RARE_MACE := 910201;

DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (@RARE_DAGGER, @RARE_MACE)
  AND `ExtendedCost` = 0;

DELETE FROM `item_template`
WHERE `entry` IN (@RARE_DAGGER, @RARE_MACE);

DROP TEMPORARY TABLE IF EXISTS `_adventurer_item_clone`;
CREATE TEMPORARY TABLE `_adventurer_item_clone` LIKE `item_template`;

-- Jeweled Dagger is a native required-level-5 green. Preserve its actual
-- combat fields but turn the Adventurer-owned clone into a rare contraband
-- version with a price that makes the starting gold meaningful.
INSERT INTO `_adventurer_item_clone`
SELECT * FROM `item_template` WHERE `entry` = 1917;
UPDATE `_adventurer_item_clone`
SET `entry` = @RARE_DAGGER,
    `name` = 'Daga enjoyada de contrabando',
    `Quality` = 3,
    `RequiredLevel` = 5,
    `BuyPrice` = 25000,
    `SellPrice` = 5000;
INSERT INTO `item_template`
SELECT * FROM `_adventurer_item_clone`;

TRUNCATE TABLE `_adventurer_item_clone`;

-- Kobold Mining Shovel supplies a native low-level two-handed mace chassis.
INSERT INTO `_adventurer_item_clone`
SELECT * FROM `item_template` WHERE `entry` = 1195;
UPDATE `_adventurer_item_clone`
SET `entry` = @RARE_MACE,
    `name` = 'Maza de excavador clandestino',
    `Quality` = 3,
    `RequiredLevel` = 5,
    `BuyPrice` = 30000,
    `SellPrice` = 6000;
INSERT INTO `item_template`
SELECT * FROM `_adventurer_item_clone`;

DROP TEMPORARY TABLE `_adventurer_item_clone`;

INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, @RARE_DAGGER, 1, 1800, 0, 0),
(@REMEN_MARCOT, 0, @RARE_MACE, 1, 1800, 0, 0);
