-- Adventurer Core: authoritative custom item definitions.
-- This file defines what Adventurer-owned items ARE. It does not decide who
-- sells them or where they drop; distribution belongs to Goldshire/Gauntlet.

SET @START_FOOD := 910202;
SET @START_FOOD_SOURCE := 3220; -- Blood Sausage: stock food + Well Fed behavior.

SET @SWORD_1H := 910210;
SET @SWORD_2H := 910211;
SET @DAGGER := 910212;
SET @BOW := 910214;
SET @CLOAK := 910215;
SET @LEATHER_CHEST := 910216;
SET @MAIL_CHEST := 910217;
SET @LEATHER_GLOVES := 910218;
SET @MAIL_GLOVES := 910219;
SET @CLOTH_GLOVES := 910220;
SET @SHIELD := 910221;
SET @CLOTH_BELT := 910222;
SET @LEATHER_BELT := 910223;
SET @MAIL_BELT := 910224;
SET @MACE := 910225;
SET @AXE_2H := 910226;
SET @POLEARM := 910227;
SET @THROWN := 910228;
SET @CROSSBOW := 910229;
SET @ARCANE_STAFF := 910230;
SET @DARKWOOD_STAFF := 910231;

DELETE FROM `item_template`
WHERE `entry` IN (
    @START_FOOD,
    @SWORD_1H, @SWORD_2H, @DAGGER, @BOW,
    @CLOAK, @LEATHER_CHEST, @MAIL_CHEST, @LEATHER_GLOVES, @MAIL_GLOVES,
    @CLOTH_GLOVES, @SHIELD, @CLOTH_BELT, @LEATHER_BELT, @MAIL_BELT,
    @MACE, @AXE_2H, @POLEARM, @THROWN, @CROSSBOW, @ARCANE_STAFF, @DARKWOOD_STAFF
);

DROP TEMPORARY TABLE IF EXISTS `_adventurer_item_clone`;
CREATE TEMPORARY TABLE `_adventurer_item_clone` LIKE `item_template`;

-- ---------------------------------------------------------------------------
-- Starting food.
-- ---------------------------------------------------------------------------
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = @START_FOOD_SOURCE;
UPDATE `_adventurer_item_clone`
SET `entry` = @START_FOOD,
    `name` = 'Racion de viaje del aventurero',
    `RequiredLevel` = 3,
    `BuyPrice` = 0,
    `SellPrice` = 0;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- ---------------------------------------------------------------------------
-- Armor and accessories. These retain the currently approved first-pass values.
-- ---------------------------------------------------------------------------
-- Capa de contrabando: Ragged Cloak (1372).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 1372;
UPDATE `_adventurer_item_clone`
SET `entry` = @CLOAK, `name` = 'Capa de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 5000, `SellPrice` = 1000,
    `stat_type1` = 7, `stat_value1` = 1,
    `stat_type2` = 6, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Coraza de cuero de contrabando: Dirty Leather Vest (85).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 85;
UPDATE `_adventurer_item_clone`
SET `entry` = @LEATHER_CHEST, `name` = 'Coraza de cuero de contrabando', `Quality` = 2,
    `ItemLevel` = 8, `RequiredLevel` = 3, `BuyPrice` = 10000, `SellPrice` = 2000,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 2;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Coraza de malla de contrabando: Light Mail Armor (2392).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 2392;
UPDATE `_adventurer_item_clone`
SET `entry` = @MAIL_CHEST, `name` = 'Coraza de malla de contrabando', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 5, `BuyPrice` = 12000, `SellPrice` = 2400,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 2;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Guantes de cuero de contrabando: Cracked Leather Gloves (2125).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 2125;
UPDATE `_adventurer_item_clone`
SET `entry` = @LEATHER_GLOVES, `name` = 'Guantes de cuero de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 6000, `SellPrice` = 1200,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Guantes de malla de contrabando: Light Mail Gloves (2397).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 2397;
UPDATE `_adventurer_item_clone`
SET `entry` = @MAIL_GLOVES, `name` = 'Guantes de malla de contrabando', `Quality` = 2,
    `ItemLevel` = 8, `RequiredLevel` = 3, `BuyPrice` = 6500, `SellPrice` = 1300,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Guantes de tela de contrabando: Thin Cloth Gloves (2119).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 2119;
UPDATE `_adventurer_item_clone`
SET `entry` = @CLOTH_GLOVES, `name` = 'Guantes de tela de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 5500, `SellPrice` = 1100,
    `stat_type1` = 5, `stat_value1` = 1,
    `stat_type2` = 6, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Cinturón de tela de contrabando: Thin Cloth Belt (3599).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 3599;
UPDATE `_adventurer_item_clone`
SET `entry` = @CLOTH_BELT, `name` = 'Cinturón de tela de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 5000, `SellPrice` = 1000,
    `stat_type1` = 5, `stat_value1` = 1,
    `stat_type2` = 6, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Cinturón de cuero de contrabando: Cracked Leather Belt (2122).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 2122;
UPDATE `_adventurer_item_clone`
SET `entry` = @LEATHER_BELT, `name` = 'Cinturón de cuero de contrabando', `Quality` = 2,
    `ItemLevel` = 7, `RequiredLevel` = 3, `BuyPrice` = 6000, `SellPrice` = 1200,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Cinturón de malla de contrabando: Light Mail Belt (2393).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 2393;
UPDATE `_adventurer_item_clone`
SET `entry` = @MAIL_BELT, `name` = 'Cinturón de malla de contrabando', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 5, `BuyPrice` = 7500, `SellPrice` = 1500,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- ---------------------------------------------------------------------------
-- Definitive level-3 weapon lineup.
-- ---------------------------------------------------------------------------
-- Destripadora de Callejón: Daga dentada (4947).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 4947;
UPDATE `_adventurer_item_clone`
SET `entry` = @DAGGER, `name` = 'Destripadora de Callejón', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 6.0, `dmg_max1` = 12.0, `delay` = 1500,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 30, `BuyPrice` = 1625, `SellPrice` = 325;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Acero del Contrabandista: Espada bastarda firme (4939).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 4939;
UPDATE `_adventurer_item_clone`
SET `entry` = @SWORD_2H, `name` = 'Acero del Contrabandista', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 16.0, `dmg_max1` = 25.0, `delay` = 2700,
    `stat_type1` = 3, `stat_value1` = 2,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 45, `BuyPrice` = 1975, `SellPrice` = 395;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Hoja del Desguace: Hoja Leñomaleza (18957).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 18957;
UPDATE `_adventurer_item_clone`
SET `entry` = @SWORD_1H, `name` = 'Hoja del Desguace', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 11.0, `dmg_max1` = 21.0, `delay` = 3000,
    `stat_type1` = 7, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 40, `BuyPrice` = 1250, `SellPrice` = 250;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Rompehuesos: Maza hiriente (4948).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 4948;
UPDATE `_adventurer_item_clone`
SET `entry` = @MACE, `name` = 'Rompehuesos', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 9.0, `dmg_max1` = 18.0, `delay` = 2300,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 40, `BuyPrice` = 1630, `SellPrice` = 326;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Arco del Fugitivo: Arco corvo Bosque Negro (4763).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 4763;
UPDATE `_adventurer_item_clone`
SET `entry` = @BOW, `name` = 'Arco del Fugitivo', `Quality` = 2,
    `ItemLevel` = 9, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 11.0, `dmg_max1` = 21.0, `delay` = 2700,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 30, `BuyPrice` = 675, `SellPrice` = 135;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Cortacuellos: Hacha severa (4562).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 4562;
UPDATE `_adventurer_item_clone`
SET `entry` = @AXE_2H, `name` = 'Cortacuellos', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 18.0, `dmg_max1` = 27.0, `delay` = 3200,
    `stat_type1` = 4, `stat_value1` = 1,
    `stat_type2` = 7, `stat_value2` = 1,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 45, `BuyPrice` = 1490, `SellPrice` = 298;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Rodela del Matón: Escudo de infantería (7108), preserving its enchant pool.
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 7108;
UPDATE `_adventurer_item_clone`
SET `entry` = @SHIELD, `name` = 'Rodela del Matón', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `armor` = 207, `block` = 4,
    `MaxDurability` = 45, `BuyPrice` = 1045, `SellPrice` = 209;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Lanza del Saqueador: Lanza taraceada con perlas (1406).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 1406;
UPDATE `_adventurer_item_clone`
SET `entry` = @POLEARM, `name` = 'Lanza del Saqueador', `Quality` = 2,
    `ItemLevel` = 13, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 15.0, `dmg_max1` = 37.0, `delay` = 3200,
    `stat_type1` = 3, `stat_value1` = 1,
    `stat_type2` = 4, `stat_value2` = 1,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 65, `BuyPrice` = 4395, `SellPrice` = 879;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Colmillos del Rufián: Sajagargantas (29584).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 29584;
UPDATE `_adventurer_item_clone`
SET `entry` = @THROWN, `name` = 'Colmillos del Rufián', `Quality` = 2,
    `ItemLevel` = 11, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 10.0, `dmg_max1` = 18.0, `delay` = 1800,
    `stat_type1` = 3, `stat_value1` = 2,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 0, `BuyPrice` = 875, `SellPrice` = 175;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Ballesta del Verdugo: Ballesta de destrucción de Arugoo (27401).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 27401;
UPDATE `_adventurer_item_clone`
SET `entry` = @CROSSBOW, `name` = 'Ballesta del Verdugo', `Quality` = 2,
    `ItemLevel` = 12, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 16.0, `dmg_max1` = 25.0, `delay` = 2800,
    `stat_type1` = 0, `stat_value1` = 0,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 35, `BuyPrice` = 1500, `SellPrice` = 300;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Bastón del Ocultista: Bastón Arcano (9514).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 9514;
UPDATE `_adventurer_item_clone`
SET `entry` = @ARCANE_STAFF, `name` = 'Bastón del Ocultista', `Quality` = 2,
    `ItemLevel` = 10, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 16.0, `dmg_max1` = 25.0, `delay` = 2900,
    `stat_type1` = 5, `stat_value1` = 2,
    `stat_type2` = 6, `stat_value2` = 1,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 45, `BuyPrice` = 1530, `SellPrice` = 306;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;
TRUNCATE TABLE `_adventurer_item_clone`;

-- Rama Podrida: Bastón Leñoscuro (3446).
INSERT INTO `_adventurer_item_clone` SELECT * FROM `item_template` WHERE `entry` = 3446;
UPDATE `_adventurer_item_clone`
SET `entry` = @DARKWOOD_STAFF, `name` = 'Rama Podrida', `Quality` = 2,
    `ItemLevel` = 13, `RequiredLevel` = 3, `bonding` = 2,
    `AllowableClass` = -1, `AllowableRace` = -1,
    `dmg_min1` = 23.0, `dmg_max1` = 35.0, `delay` = 3200,
    `stat_type1` = 7, `stat_value1` = 3,
    `stat_type2` = 0, `stat_value2` = 0,
    `RandomProperty` = 0, `RandomSuffix` = 0,
    `MaxDurability` = 50, `BuyPrice` = 2960, `SellPrice` = 592;
INSERT INTO `item_template` SELECT * FROM `_adventurer_item_clone`;

DROP TEMPORARY TABLE `_adventurer_item_clone`;
