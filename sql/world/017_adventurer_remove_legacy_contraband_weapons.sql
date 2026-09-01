-- Adventurer Core: remove only the legacy native weapons from Remen Marcot.
-- Keep armor, accessories, ammunition, food, water, scrolls and other supplies intact.

SET @REMEN_MARCOT := 6121;

DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (4565, 8179, 18957, 5744, 4303, 2265, 4766)
  AND `ExtendedCost` = 0;
