-- Adventurer Core: make the Goldshire introduction use real talk objectives.
-- The payload awards native TalkedToCreature credit when an Adventurer opens
-- gossip with the target NPC; these objective rows make the quest tracker show
-- 0/1 and prevent either quest from completing immediately on acceptance.
SET @FIRST_QUEST := 910100;
SET @SECOND_QUEST := 910101;
SET @THARYNN_BOUDEN := 66;
SET @REMEN_MARCOT := 6121;

UPDATE `quest_template`
SET `RequiredNpcOrGo1` = @THARYNN_BOUDEN,
    `RequiredNpcOrGoCount1` = 1
WHERE `ID` = @FIRST_QUEST;

UPDATE `quest_template`
SET `RequiredNpcOrGo1` = @REMEN_MARCOT,
    `RequiredNpcOrGoCount1` = 1
WHERE `ID` = @SECOND_QUEST;
