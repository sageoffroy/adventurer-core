-- Adventurer Gauntlet: lore-first Khadgar introduction and confirmation.
-- These texts replace the stock generic greeting for the permanent Goldshire
-- expedition entry NPC. The C++ gossip script selects them directly by ID.

DELETE FROM `npc_text` WHERE `ID` IN (910000, 910001);

INSERT INTO `npc_text` (`ID`, `text0_0`, `Probability0`) VALUES
(910000,
 'Veo que no has venido hasta aqui en busca de una vida tranquila.$B$BPuedo llevarte por los lugares mas peligrosos de Azeroth. Alli encontraras enemigos mucho mas temibles... pero tambien algunos de sus mejores botines.$B$BHay un precio. Si decides seguirme, tu muerte sera definitiva. Si caes, ninguna magia podra devolverte a la vida. Solo quedara tu espiritu para recordar hasta donde llegaste.',
 1),
(910001,
 'Cada expedicion te llevara de un peligro al siguiente. Yo abrire el camino, pero una vez que comiences no habra regreso si caes.$B$B¿Estas dispuesto a arriesgarlo todo?',
 1);
