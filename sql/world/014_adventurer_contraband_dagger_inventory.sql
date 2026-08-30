-- Adventurer Core: keep custom contraband daggers as native one-hand daggers.
-- InventoryType 13 matches the Worn Dagger chassis and lets normal weapon
-- validation decide which hand can use the item.
SET @DAGGER_MAIN := 910212;
SET @DAGGER_OFF := 910213;

UPDATE `item_template`
SET `InventoryType` = 13
WHERE `entry` IN (@DAGGER_MAIN, @DAGGER_OFF);
