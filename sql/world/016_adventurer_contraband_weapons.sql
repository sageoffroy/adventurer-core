-- Adventurer Core: definitive first-pass level-3 contraband weapon lineup.
-- Armor remains unchanged for now. Remen sells no blue contraband weapons.

SET @REMEN_MARCOT := 6121;
SET @RESTOCK_THREE_DAYS := 259200;

SET @DAGGER := 910212;
SET @SWORD_2H := 910211;
SET @SWORD_1H := 910210;
SET @BOW := 910214;
SET @SHIELD := 910221;
SET @MACE := 910225;
SET @AXE_2H := 910226;
SET @POLEARM := 910227;
SET @THROWN := 910228;
SET @CROSSBOW := 910229;
SET @ARCANE_STAFF := 910230;
SET @DARKWOOD_STAFF := 910231;

SET @OLD_OFFHAND_DAGGER := 910213;
SET @RARE_DAGGER := 910200;
SET @RARE_MACE := 910201;

-- Own only the weapon rows. Armor/accessory stock is intentionally untouched.
DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (
    @RARE_DAGGER, @RARE_MACE,
    @DAGGER, @OLD_OFFHAND_DAGGER, @SWORD_2H, @SWORD_1H, @BOW, @SHIELD,
    @MACE, @AXE_2H, @POLEARM, @THROWN, @CROSSBOW, @ARCANE_STAFF, @DARKWOOD_STAFF
  )
  AND `ExtendedCost` = 0;

DELETE FROM `item_template`
WHERE `entry` IN (
    @DAGGER, @SWORD_2H, @SWORD_1H, @BOW, @SHIELD,
    @MACE, @AXE_2H, @POLEARM, @THROWN, @CROSSBOW, @ARCANE_STAFF, @DARKWOOD_STAFF
);

DROP TEMPORARY TABLE IF EXISTS `_adventurer_weapon_clone`;
CREATE TEMPORARY TABLE `_adventurer_weapon_clone` LIKE `item_template`;

-- Destripadora de Callejón: Daga dentada (4947) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 4947;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @DAGGER, `name` = 'Destripadora de Callejón', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 6.0, `dmg_max1` = 12.0, `delay` = 1500,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 30, `BuyPrice` = 1625, `SellPrice` = 325;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Acero del Contrabandista: Espada bastarda firme (4939) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 4939;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @SWORD_2H, `name` = 'Acero del Contrabandista', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 16.0, `dmg_max1` = 25.0, `delay` = 2700,
    `stat_type1` = 3, `stat_value1` = 2,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 45, `BuyPrice` = 1975, `SellPrice` = 395;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Hoja del Desguace: Hoja Leñomaleza (18957) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 18957;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @SWORD_1H, `name` = 'Hoja del Desguace', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 11.0, `dmg_max1` = 21.0, `delay` = 3000,
    `stat_type1` = 7, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 40, `BuyPrice` = 1250, `SellPrice` = 250;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Rompehuesos: Maza hiriente (4948) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 4948;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @MACE, `name` = 'Rompehuesos', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 9.0, `dmg_max1` = 18.0, `delay` = 2300,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 40, `BuyPrice` = 1630, `SellPrice` = 326;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Arco del Fugitivo: Arco corvo Bosque Negro (4763) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 4763;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @BOW, `name` = 'Arco del Fugitivo', `Quality` = 2,
    `ItemLevel` = 9, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 11.0, `dmg_max1` = 21.0, `delay` = 2700,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 30, `BuyPrice` = 675, `SellPrice` = 135;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Cortacuellos: Hacha severa (4562) chassis, with fixed Strength/Stamina instead of a random suffix.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 4562;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @AXE_2H, `name` = 'Cortacuellos', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 18.0, `dmg_max1` = 27.0, `delay` = 3200,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 45, `BuyPrice` = 1490, `SellPrice` = 298;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Rodela del Matón: Escudo de infantería (7108) chassis. Preserve its native random enchantment pool.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 7108;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @SHIELD, `name` = 'Rodela del Matón', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `armor` = 207, `block` = 4,
    `MaxDurability` = 45, `BuyPrice` = 1045, `SellPrice` = 209;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Lanza del Saqueador: Lanza taraceada con perlas (1406) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 1406;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @POLEARM, `name` = 'Lanza del Saqueador', `Quality` = 2,
    `ItemLevel` = 13, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 15.0, `dmg_max1` = 37.0, `delay` = 3200,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 4, `stat_value2` = 1,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 65, `BuyPrice` = 4395, `SellPrice` = 879;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Colmillos del Rufián: Sajagargantas (29584) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 29584;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @THROWN, `name` = 'Colmillos del Rufián', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 10.0, `dmg_max1` = 18.0, `delay` = 1800,
    `stat_type1` = 3, `stat_value1` = 2,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 0, `BuyPrice` = 875, `SellPrice` = 175;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Ballesta del Verdugo: Ballesta de destrucción de Arugoo (27401) chassis, deliberately without stats.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 27401;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @CROSSBOW, `name` = 'Ballesta del Verdugo', `Quality` = 2,
    `ItemLevel` = 12, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 16.0, `dmg_max1` = 25.0, `delay` = 2800,
    `stat_type1` = 0, `stat_value1` = 0,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 35, `BuyPrice` = 1500, `SellPrice` = 300;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Bastón del Ocultista: Bastón Arcano (9514) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 9514;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @ARCANE_STAFF, `name` = 'Bastón del Ocultista', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 16.0, `dmg_max1` = 25.0, `delay` = 2900,
    `stat_type1` = 5, `stat_value1` = 2,
    `stat_type2` = 6, `stat_value2` = 1,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 45, `BuyPrice` = 1530, `SellPrice` = 306;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;
TRUNCATE TABLE `_adventurer_weapon_clone`;

-- Rama Podrida: Bastón Leñoscuro (3446) chassis.
INSERT INTO `_adventurer_weapon_clone` SELECT * FROM `item_template` WHERE `entry` = 3446;
UPDATE `_adventurer_weapon_clone`
SET `entry` = @DARKWOOD_STAFF, `name` = 'Rama Podrida', `Quality` = 2,
    `ItemLevel` = 13, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 23.0, `dmg_max1` = 35.0, `delay` = 3200,
    `stat_type1` = 7, `stat_value1` = 3,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 50, `BuyPrice` = 2960, `SellPrice` = 592;
INSERT INTO `item_template` SELECT * FROM `_adventurer_weapon_clone`;

DROP TEMPORARY TABLE `_adventurer_weapon_clone`;

-- Scarce contraband stock. Basic supplies and all existing armor rows remain unchanged.
INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, @DAGGER,         3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @SWORD_2H,       1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @SWORD_1H,       2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @MACE,           2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @BOW,            2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @AXE_2H,         1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @SHIELD,         2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @POLEARM,        1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @THROWN,         3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @CROSSBOW,       1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @ARCANE_STAFF,   1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, @DARKWOOD_STAFF, 1, @RESTOCK_THREE_DAYS, 0, 0);
