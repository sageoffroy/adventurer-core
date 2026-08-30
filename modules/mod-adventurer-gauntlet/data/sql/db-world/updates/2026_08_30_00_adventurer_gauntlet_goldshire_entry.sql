-- Adventurer Gauntlet: move the optional expedition entry point into the
-- hidden Lion's Pride Inn cellar corner chosen for the challenge.
--
-- Khadgar/chest are custom entries, so all persistent world spawns for those
-- entries are removed before creating the single intended Goldshire pair.
-- The old Pack Mule cleanup is deliberately restricted to the immediate
-- Goldshire/Lion's Pride area so stock Pack Mules elsewhere remain untouched.

SET @GAUNTLET_KHADGAR_ENTRY := 910000;
SET @GAUNTLET_CHEST_ENTRY := 910001;
SET @OLD_PACK_MULE_ENTRY := 16225;

-- Remove any previous persistent placements of the custom entry NPC/chest.
DELETE FROM `creature`
WHERE `id1` = @GAUNTLET_KHADGAR_ENTRY;

DELETE FROM `gameobject`
WHERE `id` = @GAUNTLET_CHEST_ENTRY;

-- Remove the leftover development Pack Mule only around Goldshire.
DELETE FROM `creature`
WHERE `id1` = @OLD_PACK_MULE_ENTRY
  AND `map` = 0
  AND `position_x` BETWEEN -9525.0 AND -9420.0
  AND `position_y` BETWEEN -80.0 AND 80.0
  AND `position_z` BETWEEN 40.0 AND 80.0;

-- Hidden challenge corner in the Lion's Pride Inn cellar.
SET @CGUID := (SELECT COALESCE(MAX(`guid`), 0) + 1 FROM `creature`);
INSERT INTO `creature`
(`guid`, `id1`, `map`, `position_x`, `position_y`, `position_z`, `orientation`, `spawntimesecs`, `MovementType`)
VALUES
(@CGUID, @GAUNTLET_KHADGAR_ENTRY, 0, -9472.8000, -5.32661, 49.87780, 5.55015, 300, 0);

-- Keep the expedition chest close to Khadgar, tucked beside the barrels rather
-- than in the player's normal path through the cellar.
SET @OGUID := (SELECT COALESCE(MAX(`guid`), 0) + 1 FROM `gameobject`);
INSERT INTO `gameobject`
(`guid`, `id`, `map`, `position_x`, `position_y`, `position_z`, `orientation`, `rotation0`, `rotation1`, `rotation2`, `rotation3`, `spawntimesecs`, `animprogress`, `state`)
VALUES
(@OGUID, @GAUNTLET_CHEST_ENTRY, 0, -9474.0000, -4.65000, 49.87780, 5.55015,
 0.0, 0.0, 0.3583666, -0.9335810, 300, 255, 1);
