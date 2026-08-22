-- Adventurer Core maintenance update for existing installations.
--
-- This update owns two pieces of runtime state:
--   1. Last Bastion's server-side SpellScript binding.
--   2. The Adventurer class-10 chassis curves.
--
-- Chassis design: Adventurer is a universal class, but not the natural master
-- of any one discipline. For every level/curve we take the strongest value
-- present among the ten native WotLK classes and keep 95% of it. This avoids
-- the old AVG() bootstrap, which made class 10 mediocre everywhere and left it
-- unable to grow naturally into melee, ranged, tank, healer or caster builds.

SET @ADVENTURER_CLASS := 10;
SET @ADVENTURER_SCALE := 0.95;

-- Last Bastion clones Warrior Last Stand (12975) as custom spell 290050.
-- AzerothCore stores the SpellScript binding in world.spell_script_names,
-- so the cloned spell needs the same server-side script association.
DELETE FROM `spell_script_names`
WHERE `spell_id` = 290050
  AND `ScriptName` = 'spell_warr_last_stand';

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES (290050, 'spell_warr_last_stand');

-- ---------------------------------------------------------------------------
-- Base health, mana and primary attributes, levels 1..whatever the target DB
-- provides. Class 10 is deliberately excluded from the source set.
-- FLOOR keeps the Adventurer strictly below a native maximum instead of
-- occasionally rounding a small stat back up to exactly the best value.
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
-- Mana regeneration from Spirit. The old bootstrap copied Paladin wholesale;
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
