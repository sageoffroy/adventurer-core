-- Adventurer Gauntlet: runtime corrections from the v3 in-game pass.

SET @LONE_WOLF := 910501;
SET @GAUNTLET_CHEST_ENTRY := 910001;

-- Lobo solitario is a self aura and must not require an equipped item.
UPDATE `spell_dbc`
SET `EquippedItemClass` = -1,
    `EquippedItemSubClassMask` = 0,
    `EquippedItemInventoryTypeMask` = 0
WHERE `ID` = @LONE_WOLF;

-- Move the expedition chest decisively out of the crate pile and beside
-- Khadgar instead of making another sub-meter adjustment.
UPDATE `gameobject`
SET `position_x` = -9470.5760,
    `position_y` = 5.1200000,
    `position_z` = 49.794514
WHERE `id` = @GAUNTLET_CHEST_ENTRY
  AND `map` = 0;
