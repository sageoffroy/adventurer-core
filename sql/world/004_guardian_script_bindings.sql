-- Adventurer Core maintenance update: authoritative Guardian SpellScript bindings.
--
-- Custom Guardian talent spells live in the Adventurer-owned 290000..299999
-- reservation. Older development iterations left script bindings attached to
-- IDs that have since been reused for different cloned talents. Those stale
-- rows are dangerous: AzerothCore will instantiate a native SpellScript against
-- an unrelated DBC shape, producing startup validation failures and dead hooks.
--
-- Make this range authoritative instead of trying to repair historical rows one
-- by one. At present Last Bastion (290050) is the only Guardian clone that
-- intentionally requires a native AzerothCore SpellScript; it clones Warrior
-- Last Stand (12975) and therefore uses spell_warr_last_stand.

DELETE FROM `spell_script_names`
WHERE (`spell_id` BETWEEN 290000 AND 299999)
   OR (`spell_id` BETWEEN -299999 AND -290000);

INSERT INTO `spell_script_names` (`spell_id`, `ScriptName`)
VALUES (290050, 'spell_warr_last_stand');
