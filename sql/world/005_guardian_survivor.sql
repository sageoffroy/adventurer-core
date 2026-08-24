-- Adventurer Guardian Superviviente runtime binding.
--
-- The three Adventurer-owned Superviviente rank spells clone Ardent Defender
-- data only for this class. Keep Paladin spell rows untouched and attach the
-- clones to AzerothCore's proven absorb/death-save runtime script.
DELETE FROM `spell_script_names`
WHERE `spell_id` IN (290150, 290151, 290152)
  AND `ScriptName` = 'spell_pal_ardent_defender';

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES
(290150, 'spell_pal_ardent_defender'),
(290151, 'spell_pal_ardent_defender'),
(290152, 'spell_pal_ardent_defender');
