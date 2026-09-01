-- Adventurer Gauntlet: boss reward policy.
-- Item definitions live outside Gauntlet. This table only decides which boss
-- receives which Gauntlet reward profile; CuratedRewards.cpp executes the roll.

DROP TABLE IF EXISTS `adventurer_gauntlet_loot_rule`;
CREATE TABLE `adventurer_gauntlet_loot_rule` (
    `creature_entry` INT UNSIGNED NOT NULL,
    `reward_profile` TINYINT UNSIGNED NOT NULL,
    PRIMARY KEY (`creature_entry`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- reward_profile 1 = checkpoint boss
-- reward_profile 2 = final boss
INSERT INTO `adventurer_gauntlet_loot_rule` (`creature_entry`, `reward_profile`) VALUES
(11517, 1), -- Oggleflint
(11518, 1), -- Jergosh
(11519, 1), -- Bazzalan
(11520, 2); -- Taragaman
