-- SpellDraft v4 owned active spell chains.
-- 920000-920011: Golpe siniestro (Adventurero)
-- 920020-920031: Embate brutal
-- 920040-920051: Tajo despiadado

-- Adventurer class mask = 512. Stock shield-capable classes receive skill 433
-- through playercreateinfo_skills; use the same native character-creation path.
DELETE FROM `playercreateinfo_skills`
WHERE `classMask` = 512 AND `skill` = 433;

INSERT INTO `playercreateinfo_skills` (`raceMask`, `classMask`, `skill`, `rank`, `comment`) VALUES
(0,512,433,0,'Shield');

DELETE FROM `spell_script_names`
WHERE `spell_id` BETWEEN 920000 AND 920011
   OR `spell_id` BETWEEN 920020 AND 920031
   OR `spell_id` BETWEEN 920040 AND 920051;

DELETE FROM `spell_ranks`
WHERE `first_spell_id` IN (920000, 920020, 920040)
   OR `spell_id` BETWEEN 920000 AND 920011
   OR `spell_id` BETWEEN 920020 AND 920031
   OR `spell_id` BETWEEN 920040 AND 920051;

INSERT INTO `spell_ranks` (`first_spell_id`, `spell_id`, `rank`) VALUES
(920000,920000,1),(920000,920001,2),(920000,920002,3),(920000,920003,4),
(920000,920004,5),(920000,920005,6),(920000,920006,7),(920000,920007,8),
(920000,920008,9),(920000,920009,10),(920000,920010,11),(920000,920011,12),
(920020,920020,1),(920020,920021,2),(920020,920022,3),(920020,920023,4),
(920020,920024,5),(920020,920025,6),(920020,920026,7),(920020,920027,8),
(920020,920028,9),(920020,920029,10),(920020,920030,11),(920020,920031,12),
(920040,920040,1),(920040,920041,2),(920040,920042,3),(920040,920043,4),
(920040,920044,5),(920040,920045,6),(920040,920046,7),(920040,920047,8),
(920040,920048,9),(920040,920049,10),(920040,920050,11),(920040,920051,12);

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`) VALUES
(920000,'spell_adventurer_sinister_strike'),
(920001,'spell_adventurer_sinister_strike'),
(920002,'spell_adventurer_sinister_strike'),
(920003,'spell_adventurer_sinister_strike'),
(920004,'spell_adventurer_sinister_strike'),
(920005,'spell_adventurer_sinister_strike'),
(920006,'spell_adventurer_sinister_strike'),
(920007,'spell_adventurer_sinister_strike'),
(920008,'spell_adventurer_sinister_strike'),
(920009,'spell_adventurer_sinister_strike'),
(920010,'spell_adventurer_sinister_strike'),
(920011,'spell_adventurer_sinister_strike'),
(920020,'spell_adventurer_brutal_slam'),
(920021,'spell_adventurer_brutal_slam'),
(920022,'spell_adventurer_brutal_slam'),
(920023,'spell_adventurer_brutal_slam'),
(920024,'spell_adventurer_brutal_slam'),
(920025,'spell_adventurer_brutal_slam'),
(920026,'spell_adventurer_brutal_slam'),
(920027,'spell_adventurer_brutal_slam'),
(920028,'spell_adventurer_brutal_slam'),
(920029,'spell_adventurer_brutal_slam'),
(920030,'spell_adventurer_brutal_slam'),
(920031,'spell_adventurer_brutal_slam'),
(920040,'spell_adventurer_ruthless_cleave'),
(920041,'spell_adventurer_ruthless_cleave'),
(920042,'spell_adventurer_ruthless_cleave'),
(920043,'spell_adventurer_ruthless_cleave'),
(920044,'spell_adventurer_ruthless_cleave'),
(920045,'spell_adventurer_ruthless_cleave'),
(920046,'spell_adventurer_ruthless_cleave'),
(920047,'spell_adventurer_ruthless_cleave'),
(920048,'spell_adventurer_ruthless_cleave'),
(920049,'spell_adventurer_ruthless_cleave'),
(920050,'spell_adventurer_ruthless_cleave'),
(920051,'spell_adventurer_ruthless_cleave');
