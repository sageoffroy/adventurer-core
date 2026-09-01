-- Adventurer Gauntlet: place the expedition chest at the player-measured cellar point.

SET @GAUNTLET_CHEST_ENTRY := 910001;

UPDATE `gameobject`
SET `position_x` = -9473.4300,
    `position_y` = -8.5882200,
    `position_z` = 49.877900,
    `orientation` = 6.230820
WHERE `id` = @GAUNTLET_CHEST_ENTRY
  AND `map` = 0;
