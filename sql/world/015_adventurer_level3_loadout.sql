-- Adventurer Core: level-3 expedition preparation pass.
-- Keep the first dungeon entry centered on level 3: remove rare contraband from
-- Remen, make every green starter piece usable at level 3, give the custom
-- weapons appropriate low-level green damage, and replace the unusable starting
-- apple with an Adventurer-owned well-fed food clone.

SET @ADVENTURER_CLASS := 10;
SET @REMEN_MARCOT := 6121;
SET @START_FOOD := 910202;
SET @START_FOOD_SOURCE := 3220; -- Blood Sausage; native food + Well Fed behavior.

SET @RARE_DAGGER := 910200;
SET @RARE_MACE := 910201;
SET @SWORD_1H := 910210;
SET @SWORD_2H := 910211;
SET @DAGGER_MAIN := 910212;
SET @DAGGER_OFF := 910213;
SET @BOW := 910214;
SET @MAIL_CHEST := 910217;
SET @MAIL_BELT := 910224;

-- Rare/blue contraband is no longer part of the pre-dungeon shop.
DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (@RARE_DAGGER, @RARE_MACE)
  AND `ExtendedCost` = 0;

-- All green starter equipment is intended for the normal level-3 dungeon entry.
UPDATE `item_template`
SET `RequiredLevel` = 3
WHERE `entry` IN (@SWORD_2H, @MAIL_CHEST, @MAIL_BELT);

-- The original clones inherited white starter-weapon damage. Give the green
-- contraband weapons a useful but deliberately modest level-3 baseline.
UPDATE `item_template`
SET `dmg_min1` = 5.0, `dmg_max1` = 7.0, `delay` = 2000
WHERE `entry` = @SWORD_1H;

UPDATE `item_template`
SET `dmg_min1` = 11.0, `dmg_max1` = 15.0, `delay` = 3000,
    `RequiredLevel` = 3
WHERE `entry` = @SWORD_2H;

UPDATE `item_template`
SET `dmg_min1` = 4.0, `dmg_max1` = 6.0, `delay` = 1700
WHERE `entry` IN (@DAGGER_MAIN, @DAGGER_OFF);

UPDATE `item_template`
SET `dmg_min1` = 6.0, `dmg_max1` = 9.0, `delay` = 2500
WHERE `entry` = @BOW;

-- Adventurer-owned level-3 food. Clone the native Blood Sausage so eating,
-- regeneration and Well Fed behavior remain entirely stock 3.3.5 mechanics.
DELETE FROM `item_template` WHERE `entry` = @START_FOOD;
DROP TEMPORARY TABLE IF EXISTS `_adventurer_start_food_clone`;
CREATE TEMPORARY TABLE `_adventurer_start_food_clone` LIKE `item_template`;
INSERT INTO `_adventurer_start_food_clone`
SELECT * FROM `item_template` WHERE `entry` = @START_FOOD_SOURCE;
UPDATE `_adventurer_start_food_clone`
SET `entry` = @START_FOOD,
    `name` = 'Racion de viaje del aventurero',
    `RequiredLevel` = 3,
    `BuyPrice` = 0,
    `SellPrice` = 0;
INSERT INTO `item_template` SELECT * FROM `_adventurer_start_food_clone`;
DROP TEMPORARY TABLE `_adventurer_start_food_clone`;

-- Future Adventurers receive the usable food instead of the old apple.
DELETE FROM `playercreateinfo_item`
WHERE `class` = @ADVENTURER_CLASS
  AND `itemid` IN (23172, @START_FOOD);

INSERT INTO `playercreateinfo_item` (`race`, `class`, `itemid`, `amount`, `Note`)
SELECT `race`, @ADVENTURER_CLASS, @START_FOOD, 1, 'Adventurer - Level 3 travel ration'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS;
