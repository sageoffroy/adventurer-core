-- Adventurer Core: Goldshire introduction quest and early green vendor stock.
SET @ADVENTURER_CLASS_MASK := 512;
SET @ALLIANCE_RACE_MASK := 1101;
SET @QUEST_ID := 910100;
SET @KERYN_SYLVIUS := 917;
SET @THARYNN_BOUDEN := 66;

-- Keryn already lives upstairs in the Lion's Pride Inn. Tharynn is the trade
-- supplies vendor outside in Goldshire. Preserve all existing NPC flags while
-- ensuring both can participate in the quest relation.
UPDATE `creature_template`
SET `npcflag` = `npcflag` | 2
WHERE `entry` IN (@KERYN_SYLVIUS, @THARYNN_BOUDEN);

DELETE FROM `creature_queststarter`
WHERE `id` = @KERYN_SYLVIUS AND `quest` = @QUEST_ID;
DELETE FROM `creature_questender`
WHERE `id` = @THARYNN_BOUDEN AND `quest` = @QUEST_ID;
DELETE FROM `quest_offer_reward`
WHERE `ID` = @QUEST_ID;
DELETE FROM `quest_template_addon`
WHERE `ID` = @QUEST_ID;
DELETE FROM `quest_template`
WHERE `ID` = @QUEST_ID;

INSERT INTO `quest_template`
(`ID`, `QuestType`, `QuestLevel`, `MinLevel`, `QuestSortID`, `QuestInfoID`,
 `SuggestedGroupNum`, `RewardXPDifficulty`, `RewardMoney`, `Flags`,
 `AllowableRaces`, `LogTitle`, `LogDescription`, `QuestDescription`,
 `AreaDescription`, `QuestCompletionLog`, `VerifiedBuild`)
VALUES
(@QUEST_ID, 2, 1, 1, 12, 0,
 0, 0, 0, 0,
 @ALLIANCE_RACE_MASK,
 'Por fin despiertas',
 'Habla con Tharynn Bouden en Villadorada.',
 'Por fin te levantas. La noche fue dura... y, por lo que veo, bastante costosa.$B$BMientras dormías, alguien se llevó las viejas mercancías con las que llegaste. Armas, equipo... todo.$B$BPor suerte veo que tu bolsa de dinero la tenías bien guardada. Bien hecho. Hay que estar atento para percatarse de esas cosas; un buen aventurero aprende pronto a cuidar lo que realmente importa.$B$BAntes de que sigas viaje, ve a ver a Tharynn Bouden. Tiene algunos objetos que podrían serte de mucho valor ahí fuera.$B$BEcha un vistazo a lo que ofrece y elige con cuidado. A partir de ahora, tendrás que decidir por ti mismo qué clase de aventurero quieres ser.',
 'Habla con Tharynn Bouden en Villadorada.',
 'Habla con Tharynn Bouden en Villadorada.',
 0);

INSERT INTO `quest_template_addon` (`ID`, `AllowableClasses`)
VALUES (@QUEST_ID, @ADVENTURER_CLASS_MASK);

INSERT INTO `creature_queststarter` (`id`, `quest`)
VALUES (@KERYN_SYLVIUS, @QUEST_ID);

INSERT INTO `creature_questender` (`id`, `quest`)
VALUES (@THARYNN_BOUDEN, @QUEST_ID);

INSERT INTO `quest_offer_reward`
(`ID`, `Emote1`, `Emote2`, `Emote3`, `Emote4`, `EmoteDelay1`, `EmoteDelay2`,
 `EmoteDelay3`, `EmoteDelay4`, `RewardText`, `VerifiedBuild`)
VALUES
(@QUEST_ID, 0, 0, 0, 0, 0, 0, 0, 0,
 'Así que Keryn te envía. He visto viajeros con mejor suerte... pero también con menos monedas.$B$BMira lo que tengo. Quizá encuentres algo que te sirva para empezar de nuevo.',
 0);

-- Keep Tharynn's original trade-supply inventory and add a small assortment
-- of uncommon early-game finds. Some are immediately usable and others become
-- relevant during the first few levels, so the stock feels like assorted
-- valuables rather than a prescribed class kit.
DELETE FROM `npc_vendor`
WHERE `entry` = @THARYNN_BOUDEN
  AND `item` IN (4565, 8179, 2212, 18957, 9598, 5744, 4303, 2265, 6512, 4766)
  AND `ExtendedCost` = 0;

INSERT INTO `npc_vendor`
(`entry`, `slot`, `item`, `maxcount`, `incrtime`, `ExtendedCost`, `VerifiedBuild`)
VALUES
(@THARYNN_BOUDEN, 0, 4565, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 8179, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 2212, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 18957, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 9598, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 5744, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 4303, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 2265, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 6512, 0, 0, 0, 0),
(@THARYNN_BOUDEN, 0, 4766, 0, 0, 0, 0);
