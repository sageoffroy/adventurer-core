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

-- CharStartOutfit.dbc owns the three equipped clothing pieces. Keep
-- playercreateinfo_item for inventory-only supplies so the clothes are not
-- duplicated into the backpack.
DELETE FROM `playercreateinfo_item`
WHERE `class` = @ADVENTURER_CLASS;

INSERT INTO `playercreateinfo_item` (`race`, `class`, `itemid`, `amount`, `Note`)
SELECT `race`, @ADVENTURER_CLASS, 6948, 1, 'Adventurer - Hearthstone'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, 4500, 1, 'Adventurer - Traveler Backpack'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, 23172, 1, 'Adventurer - Refreshing Red Apple'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, 19222, 1, 'Adventurer - Cheap Beer'
FROM `playercreateinfo`
WHERE `class` = @ADVENTURER_CLASS;
