-- Adventurer Core: custom low-level contraband equipment sold by Remen Marcot.
-- Stock is intentionally scarce: each piece has 1-3 units available and
-- replenishes one unit every three days. Basic supplies remain unlimited.
SET @REMEN_MARCOT := 6121;
SET @RESTOCK_THREE_DAYS := 259200;

SET @SWORD_1H := 910210;
SET @SWORD_2H := 910211;
SET @DAGGER_MAIN := 910212;
SET @DAGGER_OFF := 910213;
SET @BOW := 910214;
SET @CLOAK := 910215;
SET @LEATHER_CHEST := 910216;
SET @MAIL_CHEST := 910217;
SET @LEATHER_GLOVES := 910218;
SET @MAIL_GLOVES := 910219;
SET @RARE_DAGGER := 910200;
SET @RARE_MACE := 910201;

-- Remove the temporary assortment of native green items. Remen now sells only
-- Adventurer-owned equipment plus his unlimited consumables and ammunition.
DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (4565, 8179, 2212, 18957, 9598, 5744, 4303, 2265, 6512, 4766)
  AND `ExtendedCost` = 0;

DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (
    @SWORD_1H, @SWORD_2H, @DAGGER_MAIN, @DAGGER_OFF, @BOW,
    @CLOAK, @LEATHER_CHEST, @MAIL_CHEST, @LEATHER_GLOVES, @MAIL_GLOVES
  )
  AND `ExtendedCost` = 0;

DELETE FROM `item_template`
WHERE `entry` IN (
  @SWORD_1H, @SWORD_2H, @DAGGER_MAIN, @DAGGER_OFF, @BOW,
  @CLOAK, @LEATHER_CHEST, @MAIL_CHEST, @LEATHER_GLOVES, @MAIL_GLOVES
);

DROP TEMPORARY TABLE IF EXISTS `_adventurer_contraband_clone`;
CREATE TEMPORARY TABLE `_adventurer_contraband_clone` LIKE `item_template`;

-- 1H sword: Worn Shortsword chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 25;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @SWORD_1H, `name` = 'Espada de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 8000, `SellPrice` = 1600,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- 2H sword: Training Sword chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 8178;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @SWORD_2H, `name` = 'Mandoble de contrabando', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 5, `BuyPrice` = 12000, `SellPrice` = 2400,
    `stat_type1` = 4, `stat_value1` = 2,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Two distinct dagger entries so a dual-wield build can buy one for each hand.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2092;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @DAGGER_MAIN, `name` = 'Daga de contrabando - mano derecha',
    `Quality` = 2, `ItemLevel` = 7, `RequiredLevel` = 3,
    `InventoryType` = 21, `BuyPrice` = 7000, `SellPrice` = 1400,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2092;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @DAGGER_OFF, `name` = 'Daga de contrabando - mano izquierda',
    `Quality` = 2, `ItemLevel` = 7, `RequiredLevel` = 3,
    `InventoryType` = 22, `BuyPrice` = 7000, `SellPrice` = 1400,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 6, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Bow: Worn Shortbow chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2504;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @BOW, `name` = 'Arco de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 9000, `SellPrice` = 1800,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Cloth cloak: Ragged Cloak chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 1372;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @CLOAK, `name` = 'Capa de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 5000, `SellPrice` = 1000,
    `stat_type1` = 7, `stat_value1` = 1,
    `stat_type2` = 6, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Leather chest: Dirty Leather Vest chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 85;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @LEATHER_CHEST, `name` = 'Coraza de cuero de contrabando', `Quality` = 2,
    `ItemLevel` = 8, `RequiredLevel` = 3, `BuyPrice` = 10000, `SellPrice` = 2000,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 2;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Mail chest: Light Mail Armor chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2392;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @MAIL_CHEST, `name` = 'Coraza de malla de contrabando', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 5, `BuyPrice` = 12000, `SellPrice` = 2400,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 2;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Leather gloves: Cracked Leather Gloves chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2125;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @LEATHER_GLOVES, `name` = 'Guantes de cuero de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 6000, `SellPrice` = 1200,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;
TRUNCATE TABLE `_adventurer_contraband_clone`;

-- Mail gloves: Light Mail Gloves chassis.
INSERT INTO `_adventurer_contraband_clone` SELECT * FROM `item_template` WHERE `entry` = 2397;
UPDATE `_adventurer_contraband_clone`
SET `entry` = @MAIL_GLOVES, `name` = 'Guantes de malla de contrabando', `Quality` = 2,
    `ItemLevel` = 8, `RequiredLevel` = 3, `BuyPrice` = 6500, `SellPrice` = 1300,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_contraband_clone`;

DROP TEMPORARY TABLE `_adventurer_contraband_clone`;

INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, @SWORD_1H,       2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @SWORD_2H,       1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @DAGGER_MAIN,    3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @DAGGER_OFF,     3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @BOW,            2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @CLOAK,          3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @LEATHER_CHEST,  2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @MAIL_CHEST,     1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @LEATHER_GLOVES, 3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @MAIL_GLOVES,    2, @RESTOCK_THREE_DAYS, 0, 0);

-- Bring the two existing blue contraband pieces under the same scarcity rule.
UPDATE `item_template`
SET `name` = CASE `entry`
    WHEN @RARE_DAGGER THEN 'Daga azul de contrabando'
    WHEN @RARE_MACE THEN 'Maza azul de contrabando'
    ELSE `name`
END
WHERE `entry` IN (@RARE_DAGGER, @RARE_MACE);

UPDATE `npc_vendor`
SET `maxcount` = 1,
    `incrtime` = @RESTOCK_THREE_DAYS
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (@RARE_DAGGER, @RARE_MACE)
  AND `ExtendedCost` = 0;
