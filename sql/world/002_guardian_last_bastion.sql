-- Adventurer Core maintenance update for existing installations.
-- Last Bastion clones Warrior Last Stand (12975) as custom spell 290050.
-- AzerothCore stores the SpellScript binding in world.spell_script_names,
-- so the cloned spell needs the same server-side script association.

DELETE FROM `spell_script_names`
WHERE `spell_id` = 290050
  AND `ScriptName` = 'spell_warr_last_stand';

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES (290050, 'spell_warr_last_stand');
