-- Adventurer Core: authoritative class-10 definition for AzerothCore WotLK 3.3.5a.
-- This file owns what the Adventurer class IS: creation, skills, universal
-- stat chassis, DBC mirror curves and classless totem visual compatibility.

SET @ADVENTURER_CLASS := 10;
SET @ADVENTURER_CLASS_MASK := 512; -- 1 << (10 - 1)
SET @ADVENTURER_SCALE := 0.80;

-- Every playable race can create Adventurer. Reuse each race's Warrior start;
-- Blood Elf has no stock Warrior in WotLK, so its Paladin start is used.
-- Goldshire later overrides the Alliance starting position in 002.
DELETE FROM `playercreateinfo` WHERE `class` = @ADVENTURER_CLASS;
INSERT INTO `playercreateinfo`
(`race`, `class`, `map`, `zone`, `position_x`, `position_y`, `position_z`, `orientation`)
SELECT
    src.`race`, @ADVENTURER_CLASS, src.`map`, src.`zone`,
    src.`position_x`, src.`position_y`, src.`position_z`, src.`orientation`
FROM `playercreateinfo` AS src
WHERE
    (src.`class` = 1 AND src.`race` IN (1,2,3,4,5,6,7,8,11))
    OR (src.`class` = 2 AND src.`race` = 10);

-- Universal chassis: 80% of the strongest native value for each level/stat.
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

-- The class can learn every equipment discipline used by the classless game.
DELETE FROM `playercreateinfo_skills` WHERE `classMask` = @ADVENTURER_CLASS_MASK;
INSERT INTO `playercreateinfo_skills` (`raceMask`, `classMask`, `skill`, `rank`, `comment`) VALUES
(0,512,43,0,'Adventurer - Swords'),
(0,512,44,0,'Adventurer - Axes'),
(0,512,45,0,'Adventurer - Bows'),
(0,512,46,0,'Adventurer - Guns'),
(0,512,54,0,'Adventurer - Maces'),
(0,512,55,0,'Adventurer - Two-Handed Swords'),
(0,512,95,0,'Adventurer - Defense'),
(0,512,136,0,'Adventurer - Staves'),
(0,512,160,0,'Adventurer - Two-Handed Maces'),
(0,512,162,0,'Adventurer - Unarmed'),
(0,512,172,0,'Adventurer - Two-Handed Axes'),
(0,512,173,0,'Adventurer - Daggers'),
(0,512,176,0,'Adventurer - Thrown'),
(0,512,226,0,'Adventurer - Crossbows'),
(0,512,228,0,'Adventurer - Wands'),
(0,512,229,0,'Adventurer - Polearms'),
(0,512,293,0,'Adventurer - Plate Mail'),
(0,512,413,0,'Adventurer - Mail'),
(0,512,414,0,'Adventurer - Leather'),
(0,512,415,0,'Adventurer - Cloth'),
(0,512,433,0,'Adventurer - Shield'),
(0,512,473,0,'Adventurer - Fist Weapons');

-- Baseline spells are owned by the compiled Adventurer Core player hook.
DELETE FROM `playercreateinfo_spell_custom` WHERE `classmask` = @ADVENTURER_CLASS_MASK;

DELETE FROM `playercreateinfo_action` WHERE `class` = @ADVENTURER_CLASS;
INSERT INTO `playercreateinfo_action` (`race`,`class`,`button`,`action`,`type`)
SELECT `race`, @ADVENTURER_CLASS, 0, 6603, 0
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS;

-- ---------------------------------------------------------------------------
-- DBC mirror curves for class slot 10: 80% of the strongest native curve.
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

-- ---------------------------------------------------------------------------
-- Totem visuals for non-Shaman races.
-- Human/Gnome -> Dwarf, Night Elf -> Draenei, Undead/Blood Elf -> Orc.
-- ---------------------------------------------------------------------------
INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 1, `ModelID` FROM `player_totem_model` WHERE `RaceID` = 3;
INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 4, `ModelID` FROM `player_totem_model` WHERE `RaceID` = 11;
INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 5, `ModelID` FROM `player_totem_model` WHERE `RaceID` = 2;
INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 7, `ModelID` FROM `player_totem_model` WHERE `RaceID` = 3;
INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 10, `ModelID` FROM `player_totem_model` WHERE `RaceID` = 2;
