-- Adventurer Core: shared starting setup for class 10.
SET @ADVENTURER_CLASS := 10;

-- All Alliance Adventurers begin together in the upstairs room of the Goldshire inn.
UPDATE `playercreateinfo`
SET
    `map` = 0,
    `zone` = 12,
    `position_x` = -9462.677,
    `position_y` = 0.9355503,
    `position_z` = 63.820717,
    `orientation` = 1.4957417
WHERE `class` = @ADVENTURER_CLASS
  AND `race` IN (1,3,4,7,11);

-- Every Adventurer starts with the same basic clothes and no class-specific weapon.
DELETE FROM `playercreateinfo_item`
WHERE `class` = @ADVENTURER_CLASS;

INSERT INTO `playercreateinfo_item` (`race`, `class`, `itemid`, `amount`, `Note`)
SELECT `race`, @ADVENTURER_CLASS, 20921, 1, 'Adventurer - Sun Cured Boots'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, 4907, 1, 'Adventurer - Woodland Tunic'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, 61, 1, 'Adventurer - Dwarven Leather Pants'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS;
