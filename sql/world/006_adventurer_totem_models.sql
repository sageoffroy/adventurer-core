-- Adventurer classless totem visual compatibility.
-- WotLK only defines player_totem_model rows for native Shaman races.
-- Adventurer can learn Shaman totems on any playable race, so provide visual
-- fallbacks for races that have no stock rows. Existing custom rows are kept.
--
-- Fallback families:
--   Human (1)      -> Dwarf (3)
--   Night Elf (4)  -> Draenei (11)
--   Undead (5)     -> Orc (2)
--   Gnome (7)      -> Dwarf (3)
--   Blood Elf (10) -> Orc (2)

INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 1, `ModelID`
FROM `player_totem_model`
WHERE `RaceID` = 3;

INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 4, `ModelID`
FROM `player_totem_model`
WHERE `RaceID` = 11;

INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 5, `ModelID`
FROM `player_totem_model`
WHERE `RaceID` = 2;

INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 7, `ModelID`
FROM `player_totem_model`
WHERE `RaceID` = 3;

INSERT IGNORE INTO `player_totem_model` (`TotemID`, `RaceID`, `ModelID`)
SELECT `TotemID`, 10, `ModelID`
FROM `player_totem_model`
WHERE `RaceID` = 2;
