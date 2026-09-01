-- Adventurer Core: authoritative Alliance start and Goldshire introduction.
-- Custom item definitions live in 000. This file only decides what the player
-- starts with, how the two introductory quests work, and what Remen sells.

SET @ADVENTURER_CLASS := 10;
SET @ADVENTURER_CLASS_MASK := 512;
SET @ALLIANCE_RACE_MASK := 1101;
SET @FIRST_QUEST := 910100;
SET @SECOND_QUEST := 910101;
SET @KERYN_SYLVIUS := 917;
SET @THARYNN_BOUDEN := 66;
SET @REMEN_MARCOT := 6121;
SET @RESTOCK_THREE_DAYS := 259200;
SET @START_FOOD := 910202;

-- ---------------------------------------------------------------------------
-- Starting position and inventory.
-- ---------------------------------------------------------------------------
-- Alliance Adventurers begin together upstairs in the Lion's Pride Inn.
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

-- CharStartOutfit.dbc owns equipped clothing. These are inventory-only supplies.
DELETE FROM `playercreateinfo_item`
WHERE `class` = @ADVENTURER_CLASS;

INSERT INTO `playercreateinfo_item` (`race`, `class`, `itemid`, `amount`, `Note`)
SELECT `race`, @ADVENTURER_CLASS, 6948, 1, 'Adventurer - Hearthstone'
FROM `playercreateinfo` WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, 4500, 1, 'Adventurer - Traveler Backpack'
FROM `playercreateinfo` WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, @START_FOOD, 1, 'Adventurer - Level 3 travel ration'
FROM `playercreateinfo` WHERE `class` = @ADVENTURER_CLASS
UNION ALL
SELECT `race`, @ADVENTURER_CLASS, 19222, 1, 'Adventurer - Cheap Beer'
FROM `playercreateinfo` WHERE `class` = @ADVENTURER_CLASS;

-- ---------------------------------------------------------------------------
-- Quest 1: Keryn -> Tharynn.
-- ---------------------------------------------------------------------------
UPDATE `creature_template`
SET `npcflag` = `npcflag` | 2
WHERE `entry` IN (@KERYN_SYLVIUS, @THARYNN_BOUDEN);

DELETE FROM `creature_queststarter`
WHERE `id` = @KERYN_SYLVIUS AND `quest` = @FIRST_QUEST;
DELETE FROM `creature_questender`
WHERE `id` = @THARYNN_BOUDEN AND `quest` = @FIRST_QUEST;
DELETE FROM `quest_offer_reward` WHERE `ID` = @FIRST_QUEST;
DELETE FROM `quest_template_addon` WHERE `ID` = @FIRST_QUEST;
DELETE FROM `quest_template` WHERE `ID` = @FIRST_QUEST;

INSERT INTO `quest_template`
(`ID`, `QuestType`, `QuestLevel`, `MinLevel`, `QuestSortID`, `QuestInfoID`,
 `SuggestedGroupNum`, `RewardXPDifficulty`, `RewardMoney`, `Flags`,
 `AllowableRaces`, `LogTitle`, `LogDescription`, `QuestDescription`,
 `AreaDescription`, `QuestCompletionLog`, `RequiredNpcOrGo1`,
 `RequiredNpcOrGoCount1`, `VerifiedBuild`)
VALUES
(@FIRST_QUEST, 2, 1, 1, 12, 0,
 0, 0, 0, 0,
 @ALLIANCE_RACE_MASK,
 'Por fin despiertas',
 'Habla con Tharynn Bouden en Villadorada.',
 'Por fin te levantas. La noche fue dura... y, por lo que veo, bastante costosa.$B$BMientras dormías, alguien se llevó las viejas mercancías con las que llegaste. Armas, equipo... todo.$B$BPor suerte veo que tu bolsa de dinero la tenías bien guardada. Bien hecho. Hay que estar atento para percatarse de esas cosas; un buen aventurero aprende pronto a cuidar lo que realmente importa.$B$BAntes de que sigas viaje, ve a ver a Tharynn Bouden. Tiene algunos objetos que podrían serte de mucho valor ahí fuera.$B$BEcha un vistazo a lo que ofrece y elige con cuidado. A partir de ahora, tendrás que decidir por ti mismo qué clase de aventurero quieres ser.',
 'Habla con Tharynn Bouden en Villadorada.',
 'Habla con Tharynn Bouden en Villadorada.',
 @THARYNN_BOUDEN, 1, 0);

INSERT INTO `quest_template_addon` (`ID`, `AllowableClasses`)
VALUES (@FIRST_QUEST, @ADVENTURER_CLASS_MASK);
INSERT INTO `creature_queststarter` (`id`, `quest`)
VALUES (@KERYN_SYLVIUS, @FIRST_QUEST);
INSERT INTO `creature_questender` (`id`, `quest`)
VALUES (@THARYNN_BOUDEN, @FIRST_QUEST);
INSERT INTO `quest_offer_reward`
(`ID`, `Emote1`, `Emote2`, `Emote3`, `Emote4`, `EmoteDelay1`, `EmoteDelay2`,
 `EmoteDelay3`, `EmoteDelay4`, `RewardText`, `VerifiedBuild`)
VALUES
(@FIRST_QUEST, 0, 0, 0, 0, 0, 0, 0, 0,
 'Así que Keryn te envía. He visto viajeros con mejor suerte... pero también con menos monedas.$B$BMira lo que tengo. Quizá encuentres algo que te sirva para empezar de nuevo.',
 0);

-- ---------------------------------------------------------------------------
-- Quest 2: Tharynn -> Remen.
-- ---------------------------------------------------------------------------
UPDATE `creature_template`
SET `npcflag` = `npcflag` | 2 | 128
WHERE `entry` = @REMEN_MARCOT;

DELETE FROM `creature_queststarter`
WHERE `id` = @THARYNN_BOUDEN AND `quest` = @SECOND_QUEST;
DELETE FROM `creature_questender`
WHERE `id` = @REMEN_MARCOT AND `quest` = @SECOND_QUEST;
DELETE FROM `quest_offer_reward` WHERE `ID` = @SECOND_QUEST;
DELETE FROM `quest_template_addon` WHERE `ID` = @SECOND_QUEST;
DELETE FROM `quest_template` WHERE `ID` = @SECOND_QUEST;

INSERT INTO `quest_template`
(`ID`, `QuestType`, `QuestLevel`, `MinLevel`, `QuestSortID`, `QuestInfoID`,
 `SuggestedGroupNum`, `RewardXPDifficulty`, `RewardMoney`, `Flags`,
 `AllowableRaces`, `LogTitle`, `LogDescription`, `QuestDescription`,
 `AreaDescription`, `QuestCompletionLog`, `RequiredNpcOrGo1`,
 `RequiredNpcOrGoCount1`, `VerifiedBuild`)
VALUES
(@SECOND_QUEST, 2, 3, 3, 12, 0,
 0, 0, 0, 0,
 @ALLIANCE_RACE_MASK,
 'Mercancía discreta',
 'Habla con Remen Marcot en el sótano de la Posada Orgullo de León.',
 'Keryn te mandó conmigo, ¿eh? Hizo bien.$B$BLo que tengo aquí sirve para viajeros comunes. Pero tú quizá necesites algo menos... corriente.$B$BTengo un amigo abajo, Remen Marcot. Digamos que de vez en cuando consigue mercancía que no suele aparecer en los estantes de Villadorada.$B$BVe a verlo antes de que siga viaje. Si llevas monedas, puede que tenga algo que te interese.',
 'Habla con Remen Marcot en el sótano de la posada.',
 'Habla con Remen Marcot en el sótano de la Posada Orgullo de León.',
 @REMEN_MARCOT, 1, 0);

INSERT INTO `quest_template_addon` (`ID`, `AllowableClasses`, `PrevQuestID`)
VALUES (@SECOND_QUEST, @ADVENTURER_CLASS_MASK, @FIRST_QUEST);
INSERT INTO `creature_queststarter` (`id`, `quest`)
VALUES (@THARYNN_BOUDEN, @SECOND_QUEST);
INSERT INTO `creature_questender` (`id`, `quest`)
VALUES (@REMEN_MARCOT, @SECOND_QUEST);
INSERT INTO `quest_offer_reward`
(`ID`, `Emote1`, `Emote2`, `Emote3`, `Emote4`, `EmoteDelay1`, `EmoteDelay2`,
 `EmoteDelay3`, `EmoteDelay4`, `RewardText`, `VerifiedBuild`)
VALUES
(@SECOND_QUEST, 0, 0, 0, 0, 0, 0, 0, 0,
 'Tharynn habla demasiado.$B$BPero si tienes dinero y sabes guardar silencio, quizá podamos hacer negocios. Mira lo que traje esta vez. No prometo tener lo mismo la próxima vez.',
 0);

-- ---------------------------------------------------------------------------
-- Remen inventory. Adventurer Core fully owns this vendor inventory: clear the
-- native stock first, then add only approved supplies, clothing and weapons.
-- ---------------------------------------------------------------------------
DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT;

-- Unlimited ammunition, food, water and low-level stat scrolls.
INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, 2512, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 2516, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 4540, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 159,  0, 0, 0, 0),
(@REMEN_MARCOT, 0, 954,  0, 0, 0, 0),
(@REMEN_MARCOT, 0, 955,  0, 0, 0, 0),
(@REMEN_MARCOT, 0, 1180, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 1181, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 3012, 0, 0, 0, 0);

-- Scarce custom armor/accessories.
INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, 910215, 3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910216, 2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910217, 1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910218, 3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910219, 2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910220, 3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910222, 3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910223, 2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910224, 1, @RESTOCK_THREE_DAYS, 0, 0);

-- Definitive scarce weapon lineup. IDs 910210/211/212/214/221 are retired and
-- never reused because older clients may have cached their previous identities.
INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, 910234, 3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910233, 1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910232, 2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910225, 2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910235, 2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910226, 1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910236, 2, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910227, 1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910228, 3, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910229, 1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910230, 1, @RESTOCK_THREE_DAYS, 0, 0),
(@REMEN_MARCOT, 0, 910231, 1, @RESTOCK_THREE_DAYS, 0, 0);
