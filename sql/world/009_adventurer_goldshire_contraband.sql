-- Adventurer Core: continue the Goldshire introduction through Remen Marcot.
SET @ADVENTURER_CLASS_MASK := 512;
SET @ALLIANCE_RACE_MASK := 1101;
SET @FIRST_QUEST := 910100;
SET @SECOND_QUEST := 910101;
SET @THARYNN_BOUDEN := 66;
SET @REMEN_MARCOT := 6121;

-- Tharynn goes back to his stock inventory. The assorted Adventurer finds move
-- downstairs to Remen, who keeps all of his original quest/trainer behavior.
DELETE FROM `npc_vendor`
WHERE `entry` = @THARYNN_BOUDEN
  AND `item` IN (4565, 8179, 2212, 18957, 9598, 5744, 4303, 2265, 6512, 4766)
  AND `ExtendedCost` = 0;

UPDATE `creature_template`
SET `npcflag` = `npcflag` | 2 | 128
WHERE `entry` = @REMEN_MARCOT;

DELETE FROM `creature_queststarter`
WHERE `id` = @THARYNN_BOUDEN AND `quest` = @SECOND_QUEST;
DELETE FROM `creature_questender`
WHERE `id` = @REMEN_MARCOT AND `quest` = @SECOND_QUEST;
DELETE FROM `quest_offer_reward`
WHERE `ID` = @SECOND_QUEST;
DELETE FROM `quest_template_addon`
WHERE `ID` = @SECOND_QUEST;
DELETE FROM `quest_template`
WHERE `ID` = @SECOND_QUEST;

INSERT INTO `quest_template`
(`ID`, `QuestType`, `QuestLevel`, `MinLevel`, `QuestSortID`, `QuestInfoID`,
 `SuggestedGroupNum`, `RewardXPDifficulty`, `RewardMoney`, `Flags`,
 `AllowableRaces`, `LogTitle`, `LogDescription`, `QuestDescription`,
 `AreaDescription`, `QuestCompletionLog`, `VerifiedBuild`)
VALUES
(@SECOND_QUEST, 2, 3, 3, 12, 0,
 0, 0, 0, 0,
 @ALLIANCE_RACE_MASK,
 'Mercancía discreta',
 'Habla con Remen Marcot en el sótano de la Posada Orgullo de León.',
 'Keryn te mandó conmigo, ¿eh? Hizo bien.$B$BLo que tengo aquí sirve para viajeros comunes. Pero tú quizá necesites algo menos... corriente.$B$BTengo un amigo abajo, Remen Marcot. Digamos que de vez en cuando consigue mercancía que no suele aparecer en los estantes de Villadorada.$B$BVe a verlo antes de que siga viaje. Si llevas monedas, puede que tenga algo que te interese.',
 'Habla con Remen Marcot en el sótano de la posada.',
 'Habla con Remen Marcot en el sótano de la Posada Orgullo de León.',
 0);

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

-- Remen's permanent contraband table. Keep his original rows and only own the
-- entries listed here. The ten uncommon pieces are the assortment previously
-- exposed through Tharynn.
DELETE FROM `npc_vendor`
WHERE `entry` = @REMEN_MARCOT
  AND `item` IN (
    4565, 8179, 2212, 18957, 9598, 5744, 4303, 2265, 6512, 4766,
    2512, 2516, 4540, 159, 954, 955, 1180, 1181, 3012
  )
  AND `ExtendedCost` = 0;

INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@REMEN_MARCOT, 0, 4565, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 8179, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 2212, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 18957, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 9598, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 5744, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 4303, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 2265, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 6512, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 4766, 0, 0, 0, 0),
-- Basic ranged ammunition.
(@REMEN_MARCOT, 0, 2512, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 2516, 0, 0, 0, 0),
-- Low-level food and water.
(@REMEN_MARCOT, 0, 4540, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 159, 0, 0, 0, 0),
-- Low-level stat scrolls.
(@REMEN_MARCOT, 0, 954, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 955, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 1180, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 1181, 0, 0, 0, 0),
(@REMEN_MARCOT, 0, 3012, 0, 0, 0, 0);
