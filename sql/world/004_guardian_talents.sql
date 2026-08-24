-- Adventurer Guardian talent runtime data.
--
-- The current Guardian tree no longer uses the retired custom Last Bastion
-- spell 290050. Remove its historical script binding on upgraded installs.
DELETE FROM `spell_script_names`
WHERE `spell_id` = 290050
  AND `ScriptName` = 'spell_warr_last_stand';

-- Última Carga is an Adventurer-localized clone of Warrior Last Stand. The
-- underlying mechanic is server scripted, so bind the cloned spell to the same
-- proven AzerothCore script instead of reimplementing it.
DELETE FROM `spell_script_names`
WHERE `spell_id` = 290090
  AND `ScriptName` = 'spell_warr_last_stand';

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES (290090, 'spell_warr_last_stand');

-- Superviviente owns Adventurer-localized clones of all three Ardent Defender
-- ranks. Bind each custom spell to AzerothCore's proven absorb/death-save
-- script; the native Paladin spell rows and names remain untouched.
DELETE FROM `spell_script_names`
WHERE `spell_id` IN (290150, 290151, 290152)
  AND `ScriptName` = 'spell_pal_ardent_defender';

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES
(290150, 'spell_pal_ardent_defender'),
(290151, 'spell_pal_ardent_defender'),
(290152, 'spell_pal_ardent_defender');

-- Golpes de barrido keeps Blizzard's Sweeping Strikes proc logic but its custom
-- Spell.dbc row removes the Warrior stance requirement for Adventurer.
DELETE FROM `spell_script_names`
WHERE `spell_id` = 290180
  AND `ScriptName` = 'spell_warr_sweeping_strikes';

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES (290180, 'spell_warr_sweeping_strikes');

-- Arrojar escudo (custom spell 290240) clones Avenger's Shield only for its
-- shield requirement, chain projectile and daze mechanics. Adventurer's design
-- removes spell-power scaling and native base damage, then uses 24% AP as the
-- complete direct-damage contribution. Spell.dbc changes the school to Physical.
DELETE FROM `spell_bonus_data`
WHERE `entry` = 290240;

INSERT INTO `spell_bonus_data`
(`entry`, `direct_bonus`, `dot_bonus`, `ap_bonus`, `ap_dot_bonus`)
VALUES
(290240, 0.0, 0.0, 0.24, 0.0);
