-- Adventurer Gauntlet: world placement and gossip.
-- Templates live in 001_gauntlet_core.sql; this file owns where the permanent
-- Goldshire entry NPC exists and the text he presents.

SET @GAUNTLET_KHADGAR_ENTRY := 910000;
SET @GAUNTLET_REWARD_CHEST_ENTRY := 910001;
SET @GAUNTLET_BANK_ENTRY := 910002;
SET @OLD_PACK_MULE_ENTRY := 16225;

DELETE FROM `npc_text` WHERE `ID` IN (910000, 910001);
INSERT INTO `npc_text` (`ID`, `text0_0`, `Probability0`) VALUES
(910000,
 'Veo que no has venido hasta aqui en busca de una vida tranquila.$B$BPuedo llevarte por los lugares mas peligrosos de Azeroth. Alli encontraras enemigos mucho mas temibles... pero tambien algunos de sus mejores botines.$B$BHay un precio. Si decides seguirme, tu muerte sera definitiva. Si caes, ninguna magia podra devolverte a la vida. Solo quedara tu espiritu para recordar hasta donde llegaste.',
 1),
(910001,
 'Cada expedicion te llevara de un peligro al siguiente. Yo abrire el camino, pero una vez que comiences no habra regreso si caes.$B$B¿Estas dispuesto a arriesgarlo todo?',
 1);

-- One permanent Khadgar in the Lion's Pride Inn cellar.
DELETE FROM `creature` WHERE `id` = @GAUNTLET_KHADGAR_ENTRY;

-- The reward chest is not a permanent Goldshire object and the account bank is
-- summoned dynamically beside Khadgar by AccountBank.cpp.
DELETE FROM `gameobject`
WHERE `map` = 0
  AND `id` IN (@GAUNTLET_REWARD_CHEST_ENTRY, @GAUNTLET_BANK_ENTRY);

-- Remove only the old development Pack Mule around Goldshire.
DELETE FROM `creature`
WHERE `id` = @OLD_PACK_MULE_ENTRY
  AND `map` = 0
  AND `position_x` BETWEEN -9525.0 AND -9420.0
  AND `position_y` BETWEEN -80.0 AND 80.0
  AND `position_z` BETWEEN 40.0 AND 80.0;

SET @CGUID := (SELECT COALESCE(MAX(`guid`), 0) + 1 FROM `creature`);
INSERT INTO `creature`
(`guid`, `id`, `map`, `position_x`, `position_y`, `position_z`, `orientation`, `spawntimesecs`, `MovementType`)
VALUES
(@CGUID, @GAUNTLET_KHADGAR_ENTRY, 0, -9471.7130, 5.2467003, 49.794514, 4.9018545, 300, 0);
