-- Adventurer Gauntlet: use Doan's Strongbox appearance for the account stash.
-- Keep the custom entry, script and interaction data; copy only its visual model/scale.

UPDATE `gameobject_template` AS `stash`
JOIN `gameobject_template` AS `doan`
    ON `doan`.`entry` = 103821
SET
    `stash`.`displayId` = `doan`.`displayId`,
    `stash`.`size` = `doan`.`size`
WHERE `stash`.`entry` = 910002;
