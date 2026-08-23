-- Adventurer Core maintenance update: universal class-10 chassis.
--
-- Design rule: Adventurer may become melee, ranged, tank, healer or caster,
-- but should not be the natural master of any one discipline. For every
-- level/curve this migration takes the strongest value present among the ten
-- native WotLK classes and keeps 95% of it.
--
-- This intentionally replaces the AVG() bootstrap from 001_adventurer.sql.
-- The bootstrap remains immutable history; this update is what brings both
-- existing and clean installations to the current chassis design.

SET @ADVENTURER_CLASS := 10;
SET @ADVENTURER_SCALE := 0.95;

-- ---------------------------------------------------------------------------
-- Base health, mana and primary attributes.
-- FLOOR keeps the Adventurer below the strongest native value instead of
-- occasionally rounding a small stat back up to the same value.
-- ---------------------------------------------------------------------------
DELETE FROM `player_class_stats`
WHERE `Class` = @ADVENTURER_CLASS;

INSERT INTO `player_class_stats`
(`Class`, `Level`, `BaseHP`, `BaseMana`, `Strength`, `Agility`, `Stamina`, `Intellect`, `Spirit`)
SELECT
    @ADVENTURER_CLASS,
    `Level`,
    CAST(FLOOR(MAX(`BaseHP`) * @ADVENTURER_SCALE) AS UNSIGNED),
    CAST(FLOOR(MAX(`BaseMana`) * @ADVENTURER_SCALE) AS UNSIGNED),
    CAST(FLOOR(MAX(`Strength`) * @ADVENTURER_SCALE) AS UNSIGNED),
    CAST(FLOOR(MAX(`Agility`) * @ADVENTURER_SCALE) AS UNSIGNED),
    CAST(FLOOR(MAX(`Stamina`) * @ADVENTURER_SCALE) AS UNSIGNED),
    CAST(FLOOR(MAX(`Intellect`) * @ADVENTURER_SCALE) AS UNSIGNED),
    CAST(FLOOR(MAX(`Spirit`) * @ADVENTURER_SCALE) AS UNSIGNED)
FROM `player_class_stats`
WHERE `Class` IN (1,2,3,4,5,6,7,8,9,11)
GROUP BY `Level`;

-- ---------------------------------------------------------------------------
-- Agility -> melee/ranged crit.
-- IDs 0..10 are class-1 slots; slot 9 is Adventurer/class 10.
-- ---------------------------------------------------------------------------
DELETE FROM `gtchancetomeleecritbase_dbc` WHERE `ID` = 9;
INSERT INTO `gtchancetomeleecritbase_dbc` (`ID`, `Data`)
SELECT 9, MAX(`Data`) * @ADVENTURER_SCALE
FROM `gtchancetomeleecritbase_dbc`
WHERE `ID` IN (0,1,2,3,4,5,6,7,8,10);

DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_melee_crit`;
CREATE TEMPORARY TABLE `tmp_adventurer_melee_crit` AS
SELECT MOD(`ID`, 100) AS `slot`, MAX(`Data`) * @ADVENTURER_SCALE AS `Data`
FROM `gtchancetomeleecrit_dbc`
WHERE FLOOR(`ID` / 100) + 1 IN (1,2,3,4,5,6,7,8,9,11)
GROUP BY MOD(`ID`, 100);

DELETE FROM `gtchancetomeleecrit_dbc` WHERE `ID` BETWEEN 900 AND 999;
INSERT INTO `gtchancetomeleecrit_dbc` (`ID`, `Data`)
SELECT 900 + `slot`, `Data` FROM `tmp_adventurer_melee_crit`;
DROP TEMPORARY TABLE `tmp_adventurer_melee_crit`;

-- ---------------------------------------------------------------------------
-- Intellect -> spell crit.
-- ---------------------------------------------------------------------------
DELETE FROM `gtchancetospellcritbase_dbc` WHERE `ID` = 9;
INSERT INTO `gtchancetospellcritbase_dbc` (`ID`, `Data`)
SELECT 9, MAX(`Data`) * @ADVENTURER_SCALE
FROM `gtchancetospellcritbase_dbc`
WHERE `ID` IN (0,1,2,3,4,5,6,7,8,10);

DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_spell_crit`;
CREATE TEMPORARY TABLE `tmp_adventurer_spell_crit` AS
SELECT MOD(`ID`, 100) AS `slot`, MAX(`Data`) * @ADVENTURER_SCALE AS `Data`
FROM `gtchancetospellcrit_dbc`
WHERE FLOOR(`ID` / 100) + 1 IN (1,2,3,4,5,6,7,8,9,11)
GROUP BY MOD(`ID`, 100);

DELETE FROM `gtchancetospellcrit_dbc` WHERE `ID` BETWEEN 900 AND 999;
INSERT INTO `gtchancetospellcrit_dbc` (`ID`, `Data`)
SELECT 900 + `slot`, `Data` FROM `tmp_adventurer_spell_crit`;
DROP TEMPORARY TABLE `tmp_adventurer_spell_crit`;

-- ---------------------------------------------------------------------------
-- Combat-rating conversion. GetRatingMultiplier() uses the class scalar
-- directly, so the largest native scalar is the most favourable conversion.
-- Class 10 occupies IDs 289..320 (32 ratings per class).
-- ---------------------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_ratings`;
CREATE TEMPORARY TABLE `tmp_adventurer_ratings` AS
SELECT MOD(`ID` - 1, 32) + 1 AS `slot`, MAX(`Data`) * @ADVENTURER_SCALE AS `Data`
FROM `gtoctclasscombatratingscalar_dbc`
WHERE FLOOR((`ID` - 1) / 32) + 1 IN (1,2,3,4,5,6,7,8,9,11)
GROUP BY MOD(`ID` - 1, 32) + 1;

DELETE FROM `gtoctclasscombatratingscalar_dbc` WHERE `ID` BETWEEN 289 AND 320;
INSERT INTO `gtoctclasscombatratingscalar_dbc` (`ID`, `Data`)
SELECT 288 + `slot`, `Data` FROM `tmp_adventurer_ratings`;
DROP TEMPORARY TABLE `tmp_adventurer_ratings`;

-- ---------------------------------------------------------------------------
-- Health regeneration from Spirit.
-- ---------------------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_regen_hp`;
CREATE TEMPORARY TABLE `tmp_adventurer_regen_hp` AS
SELECT MOD(`ID`, 100) AS `slot`, MAX(`Data`) * @ADVENTURER_SCALE AS `Data`
FROM `gtoctregenhp_dbc`
WHERE FLOOR(`ID` / 100) + 1 IN (1,2,3,4,5,6,7,8,9,11)
GROUP BY MOD(`ID`, 100);

DELETE FROM `gtoctregenhp_dbc` WHERE `ID` BETWEEN 900 AND 999;
INSERT INTO `gtoctregenhp_dbc` (`ID`, `Data`)
SELECT 900 + `slot`, `Data` FROM `tmp_adventurer_regen_hp`;
DROP TEMPORARY TABLE `tmp_adventurer_regen_hp`;

DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_regen_hp_spt`;
CREATE TEMPORARY TABLE `tmp_adventurer_regen_hp_spt` AS
SELECT MOD(`ID`, 100) AS `slot`, MAX(`Data`) * @ADVENTURER_SCALE AS `Data`
FROM `gtregenhpperspt_dbc`
WHERE FLOOR(`ID` / 100) + 1 IN (1,2,3,4,5,6,7,8,9,11)
GROUP BY MOD(`ID`, 100);

DELETE FROM `gtregenhpperspt_dbc` WHERE `ID` BETWEEN 900 AND 999;
INSERT INTO `gtregenhpperspt_dbc` (`ID`, `Data`)
SELECT 900 + `slot`, `Data` FROM `tmp_adventurer_regen_hp_spt`;
DROP TEMPORARY TABLE `tmp_adventurer_regen_hp_spt`;

-- ---------------------------------------------------------------------------
-- Mana regeneration from Spirit. The bootstrap copied Paladin wholesale;
-- this now follows the same universal 95%-of-best rule as the rest of class 10.
-- ---------------------------------------------------------------------------
DROP TEMPORARY TABLE IF EXISTS `tmp_adventurer_regen_mp_spt`;
CREATE TEMPORARY TABLE `tmp_adventurer_regen_mp_spt` AS
SELECT MOD(`ID`, 100) AS `slot`, MAX(`Data`) * @ADVENTURER_SCALE AS `Data`
FROM `gtregenmpperspt_dbc`
WHERE FLOOR(`ID` / 100) + 1 IN (1,2,3,4,5,6,7,8,9,11)
GROUP BY MOD(`ID`, 100);

DELETE FROM `gtregenmpperspt_dbc` WHERE `ID` BETWEEN 900 AND 999;
INSERT INTO `gtregenmpperspt_dbc` (`ID`, `Data`)
SELECT 900 + `slot`, `Data` FROM `tmp_adventurer_regen_mp_spt`;
DROP TEMPORARY TABLE `tmp_adventurer_regen_mp_spt`;
