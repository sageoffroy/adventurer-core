-- Native-style set presentation is provided client-side by AdventurerGauntletSets.
-- Keep item descriptions empty so the set bonus text is not duplicated in yellow.
UPDATE `item_template`
SET `description` = ''
WHERE `entry` IN (911100, 911101, 911102, 911103);
